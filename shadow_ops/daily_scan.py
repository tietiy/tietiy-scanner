"""shadow_ops/daily_scan.py — Step 4 of shadow_ops v1 daily scan.

Takes a scan_date, runs the canonical signal-detection + rule-match pipeline
across the 188-symbol universe, and emits CandidateSignal / TradeCard /
LifecycleEvent / ScanEvent records to a journal directory.

Active rules (filtered from unified_rules_v4_1_FINAL.json):
  - rule_019_bear_uptri_hot_refinement (boost)  — UP_TRI / Bear / sub_regime=hot
  - rule_031_bear_uptri_it_hot          (overlay) — UP_TRI / IT / Bear / sub_regime=hot
  - kill_001                            (kill)    — DOWN_TRI / Bank / Bear

Trade card emission:
  - rule_019_match=True  → CandidateSignal + TradeCard (PROPOSED) + lifecycle
                            rule_031_confirm=1 IF rule_031 also matched (IT sector)
  - kill_001_match=True  → CandidateSignal only (disposition=SUPPRESSED_BY_KILL_001)
  - rule_031_match alone → impossible given current rule shapes (rule_031 ⇒ rule_019
                            also matches), but if it ever does, dispatched as
                            RULE_031_OVERLAY_ONLY

Canonical-source imports (no fork, no duplication):
  - scanner.scanner_core.detect_signals     — signal generation
  - lab.factory.production_backtest.harness.matches_rule — rule predicate

regime_score and sector_momentum are passed as defaults; verified annotation-only
in scanner_core (no decision logic), and no active rule examines them.
See TODO note near `_DEFAULT_REGIME_SCORE` for forward-compatibility caveats.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# --- Canonical imports --------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
sys.path.insert(0, str(_REPO_ROOT / "scanner"))
sys.path.insert(0, str(_REPO_ROOT / "lab" / "factory" / "production_backtest"))

from scanner_core import detect_signals                                # noqa: E402
from harness import matches_rule                                       # noqa: E402

# --- Shadow-internal imports --------------------------------------------------
from shadow_ops.data_ingest import (
    DEFAULT_CACHE_DIR,
    DEFAULT_UNIVERSE_CSV,
    daily_data_ingest,
    parquet_path_for_symbol,
)
from shadow_ops.journal import JournalWriter
from shadow_ops.regime_classifier import classify_regime_for_date
from shadow_ops.schemas import (
    CandidateSignal,
    ScanEvent,
    TradeCard,
)


# ============================================================
# Constants
# ============================================================

DEFAULT_RULES_PATH = (
    _REPO_ROOT / "lab" / "factory" / "step5_finalization"
    / "L4_opus_output" / "unified_rules_v4_1_FINAL.json"
)
DEFAULT_RUN_ROOT = _REPO_ROOT / "shadow_ops" / "runs"

ACTIVE_RULE_IDS = (
    "rule_019_bear_uptri_hot_refinement",
    "rule_031_bear_uptri_it_hot",
    "kill_001",
)

MIN_BARS_FOR_DETECT = 60      # mirror scanner/scanner_core.prepare()
R_TARGET_MULTIPLIER = 2.0     # per arch §14.7 / scanner/main.py:427-429

# TODO(shadow): regime_score and sector_momentum are passed as defaults
# because no current active rule (rule_019, rule_031, kill_001) examines them.
# If a future deployable rule uses sec_mom='Leading' or regime_score thresholds,
# shadow will silently see zero matches on those rules. At that point, mirror
# scanner/main.py's regime_score (ret20-based) and sector_momentum (sector
# index momentum) computation here.
_DEFAULT_REGIME_SCORE = 0
_DEFAULT_SECTOR_MOMENTUM: Dict[str, str] = {}


# ============================================================
# Result dataclass
# ============================================================

@dataclass
class ScanResult:
    """Summary of a single daily_scan invocation."""
    scan_event_id: str
    scan_date: str
    regime: str
    sub_regime: Optional[str]
    run_dir: str
    n_signals_universe: int
    n_signals_post_filter: int
    n_candidate_signals_emitted: int
    n_trade_cards_emitted: int
    n_kill_001_suppressed: int
    n_rule_031_overlay_count: int
    symbols_scanned: int
    symbols_skipped: List[Tuple[str, str]] = field(default_factory=list)  # (symbol, reason)
    elapsed_ms: int = 0
    scan_status: str = "OK"


# ============================================================
# Helpers
# ============================================================

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_commit_sha() -> str:
    """Best-effort: returns short SHA, or 'unknown' if not in a git repo."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def _file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_universe_with_sectors(universe_csv: Path) -> List[Tuple[str, str]]:
    """Read fno_universe.csv → list of (symbol, sector). Skips header."""
    df = pd.read_csv(universe_csv)
    if "symbol" not in df.columns or "sector" not in df.columns:
        raise ValueError(f"universe csv missing required columns: {universe_csv}")
    return [(str(r["symbol"]), str(r["sector"])) for _, r in df.iterrows()]


def _load_active_rules(rules_path: Path) -> Dict[str, dict]:
    """Load unified_rules_v4_1_FINAL.json and return {rule_id: rule_dict}
    for the 3 active rule IDs. Raises if any expected rule is missing."""
    payload = json.loads(rules_path.read_text())
    rules = {r["id"]: r for r in payload["rules"]}
    out: Dict[str, dict] = {}
    for rid in ACTIVE_RULE_IDS:
        if rid not in rules:
            raise ValueError(f"required rule not found in {rules_path}: {rid}")
        out[rid] = rules[rid]
    return out


def _load_symbol_ohlc(symbol: str,
                      cache_dir: Path,
                      scan_ts: pd.Timestamp) -> Optional[pd.DataFrame]:
    """Load per-symbol parquet, truncate to scan_ts inclusive. Returns None
    if file missing or insufficient bars (caller logs the skip)."""
    parquet_path = parquet_path_for_symbol(symbol, cache_dir)
    if not parquet_path.exists():
        return None
    df = pd.read_parquet(parquet_path)
    df.index = pd.to_datetime(df.index, errors="coerce")
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df[df.index.notna()]
    df = df.loc[df.index <= scan_ts]
    df = df.dropna(subset=["Close"])
    if len(df) < MIN_BARS_FOR_DETECT:
        return None
    return df


def _load_nifty_close(cache_dir: Path, scan_ts: pd.Timestamp) -> pd.Series:
    nifty_parquet = cache_dir / "_index_NSEI.parquet"
    if not nifty_parquet.exists():
        raise FileNotFoundError(f"nifty parquet missing: {nifty_parquet}")
    df = pd.read_parquet(nifty_parquet)
    df.index = pd.to_datetime(df.index)
    closes = df["Close"].sort_index().dropna()
    return closes.loc[closes.index <= scan_ts]


def _build_signal_row(signal_dict: dict, sub_regime: Optional[str]) -> pd.Series:
    """Inject sub_regime into the signal dict so harness.matches_rule() can
    evaluate sub_regime_constraint + condition checks."""
    enriched = dict(signal_dict)
    enriched["sub_regime"] = sub_regime
    return pd.Series(enriched)


def _rule_features_snapshot(signal_dict: dict,
                            classifier_inputs: Dict[str, object]) -> Dict[str, object]:
    """Per arch §3.3.2: 2 market-level + 4 per-symbol features."""
    return {
        # Market-level (2)
        "feat_nifty_vol_percentile_20d": classifier_inputs.get("feat_nifty_vol_percentile_20d"),
        "feat_nifty_60d_return_pct": classifier_inputs.get("feat_nifty_60d_return_pct"),
        # Per-symbol (4)
        "atr": signal_dict.get("atr"),
        "stop": signal_dict.get("stop"),
        "pivot_price": signal_dict.get("pivot_price"),
        "entry_est": signal_dict.get("entry_est"),
    }


def _compute_target(entry: float, stop: float, direction: str) -> float:
    """2R target per arch §14.7."""
    risk = abs(entry - stop)
    if direction == "LONG":
        return round(entry + R_TARGET_MULTIPLIER * risk, 2)
    return round(entry - R_TARGET_MULTIPLIER * risk, 2)


def _resolve_run_dir(run_dir: Optional[Path], scan_date_iso: str) -> Path:
    if run_dir is not None:
        out = Path(run_dir)
    else:
        out = DEFAULT_RUN_ROOT / scan_date_iso
    out.mkdir(parents=True, exist_ok=True)
    return out


# ============================================================
# Public API
# ============================================================

def daily_scan(scan_date: date,
               run_dir: Optional[Path] = None,
               cache_dir: Path = DEFAULT_CACHE_DIR,
               universe_path: Path = DEFAULT_UNIVERSE_CSV,
               rules_path: Path = DEFAULT_RULES_PATH,
               run_data_ingest: bool = False) -> ScanResult:
    """Run shadow ops daily scan for `scan_date`. See module docstring.

    Args:
      scan_date: date to scan (today, or a historical date for cross-validation).
      run_dir: directory for this run's JSONL files. Defaults to
               shadow_ops/runs/<scan_date>/.
      cache_dir: lab/cache root (per-symbol + nifty parquets).
      universe_path: data/fno_universe.csv with symbol+sector columns.
      rules_path: unified_rules_v4_1_FINAL.json.
      run_data_ingest: if True, refresh parquets via shadow_ops.data_ingest first.
                       Default False — assumes data is already current.

    Returns:
      ScanResult with summary counts and final scan_status.
    """
    t0 = time.monotonic()
    scan_ts = pd.Timestamp(scan_date)
    scan_date_iso = scan_ts.date().isoformat()

    out_run_dir = _resolve_run_dir(run_dir, scan_date_iso)
    writer = JournalWriter(out_run_dir)

    # 1. Optional fresh data ingest (real-world daily run; tests skip)
    if run_data_ingest:
        daily_data_ingest(end_date=scan_date, cache_dir=cache_dir,
                          universe_path=universe_path)

    # 2. Regime + sub_regime
    classification = classify_regime_for_date(scan_date, cache_dir=cache_dir)
    regime = classification.regime
    sub_regime = classification.sub_regime

    # 3. Universe + active rules + nifty closes
    universe = _load_universe_with_sectors(universe_path)
    active_rules = _load_active_rules(rules_path)
    nifty_close = _load_nifty_close(cache_dir, scan_ts)

    rule_019 = active_rules["rule_019_bear_uptri_hot_refinement"]
    rule_031 = active_rules["rule_031_bear_uptri_it_hot"]
    kill_001 = active_rules["kill_001"]

    # 4. IDs
    scan_event_id = f"scan_{scan_date_iso}_001"
    cand_seq_per_symbol: Dict[str, int] = {}

    # 5. Counters
    n_signals_universe = 0
    n_signals_post_filter = 0
    n_candidate_signals_emitted = 0
    n_trade_cards_emitted = 0
    n_kill_001_suppressed = 0
    n_rule_031_overlay = 0
    symbols_scanned = 0
    symbols_skipped: List[Tuple[str, str]] = []
    had_per_symbol_error = False

    # 6. Per-symbol scan
    for symbol, sector in universe:
        df = _load_symbol_ohlc(symbol, cache_dir, scan_ts)
        if df is None:
            symbols_skipped.append((symbol, "missing_or_insufficient"))
            continue
        try:
            signals = detect_signals(
                df, symbol, sector,
                regime, _DEFAULT_REGIME_SCORE,
                _DEFAULT_SECTOR_MOMENTUM,
                nifty_close=nifty_close,
            )
        except Exception as e:
            symbols_skipped.append((symbol, f"detect_signals_error:{type(e).__name__}"))
            had_per_symbol_error = True
            continue

        symbols_scanned += 1
        n_signals_universe += len(signals)

        for sig in signals:
            row = _build_signal_row(sig, sub_regime)
            r019 = matches_rule(row, rule_019)
            r031 = matches_rule(row, rule_031)
            k001 = matches_rule(row, kill_001)

            if not (r019 or r031 or k001):
                continue
            n_signals_post_filter += 1

            # Determine disposition
            if r019:
                disposition = "TRADE_CARD_PROPOSED"
            elif k001:
                disposition = "SUPPRESSED_BY_KILL_001"
            else:
                disposition = "RULE_031_OVERLAY_ONLY"

            # Emit candidate_signal
            seq = cand_seq_per_symbol.get(symbol, 0) + 1
            cand_seq_per_symbol[symbol] = seq
            cand_event_id = f"cand_{scan_date_iso}_{symbol}_{seq:03d}"

            cand = CandidateSignal(
                event_id=cand_event_id,
                event_type="candidate_signal",
                timestamp_utc=_now_utc_iso(),
                scan_event_id=scan_event_id,
                scan_date=scan_date_iso,
                symbol=symbol,
                sector=sector,
                signal=sig.get("signal", ""),
                regime=regime,
                sub_regime=sub_regime,
                rule_019_match=bool(r019),
                rule_031_match=bool(r031),
                kill_001_match=bool(k001),
                trigger_disposition=disposition,
                rule_features_snapshot=_rule_features_snapshot(
                    sig, classification.inputs),
            )
            writer.write_event(cand)
            n_candidate_signals_emitted += 1

            if k001:
                n_kill_001_suppressed += 1
            if r031:
                n_rule_031_overlay += 1

            # Emit trade_card + lifecycle for rule_019 matches
            if r019:
                entry = float(sig.get("entry_est", 0) or 0)
                stop = float(sig.get("stop", 0) or 0)
                direction = sig.get("direction", "LONG")
                target = _compute_target(entry, stop, direction)

                card_id = f"card_{scan_date_iso}_{symbol}"
                card_event_id = f"card_snap_{scan_date_iso}_{symbol}_001"

                card = TradeCard(
                    event_id=card_event_id,
                    event_type="trade_card",
                    timestamp_utc=_now_utc_iso(),
                    card_id=card_id,
                    scan_event_id=scan_event_id,
                    candidate_signal_id=cand_event_id,
                    symbol=symbol,
                    sector=sector,
                    rule_id="rule_019_bear_uptri_hot_refinement",
                    rule_031_confirm=1 if r031 else 0,
                    kill_001_match=bool(k001),
                    scan_date=scan_date_iso,
                    proposed_entry_price=round(entry, 2),
                    proposed_stop=round(stop, 2),
                    proposed_target=target,
                    atr=float(sig.get("atr", 0) or 0),
                    current_state="PROPOSED",
                    state_history=[{
                        "state": "PROPOSED",
                        "timestamp_utc": _now_utc_iso(),
                        "reason": "rule_019_match",
                    }],
                )
                writer.write_event(card)
                # Note: no creation-time lifecycle_event. The TradeCard's
                # state_history already records the PROPOSED creation moment.
                # LifecycleEvents are reserved for actual state CHANGES
                # (begin emitting in Step 5, T+1 fill simulation).
                n_trade_cards_emitted += 1

    # 7. Final ScanEvent
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    scan_status = "OK"
    if had_per_symbol_error:
        scan_status = "PARTIAL"

    rules_sha = _file_sha256(Path(rules_path))
    nifty_sha = _file_sha256(cache_dir / "_index_NSEI.parquet")

    scan_event = ScanEvent(
        event_id=scan_event_id,
        event_type="scan_event",
        timestamp_utc=_now_utc_iso(),
        scan_date=scan_date_iso,
        regime=regime,
        sub_regime=sub_regime,
        sub_regime_inputs=dict(classification.inputs),
        n_signals_universe=n_signals_universe,
        n_signals_post_filter=n_signals_post_filter,
        scan_status=scan_status,
        scan_duration_ms=elapsed_ms,
        git_commit_sha=_git_commit_sha(),
        data_versions={
            "rules_path_sha256": rules_sha,
            "nifty_parquet_sha256": nifty_sha,
            "regime_features_sha": classification.features_sha,
        },
    )
    writer.write_event(scan_event)

    return ScanResult(
        scan_event_id=scan_event_id,
        scan_date=scan_date_iso,
        regime=regime,
        sub_regime=sub_regime,
        run_dir=str(out_run_dir),
        n_signals_universe=n_signals_universe,
        n_signals_post_filter=n_signals_post_filter,
        n_candidate_signals_emitted=n_candidate_signals_emitted,
        n_trade_cards_emitted=n_trade_cards_emitted,
        n_kill_001_suppressed=n_kill_001_suppressed,
        n_rule_031_overlay_count=n_rule_031_overlay,
        symbols_scanned=symbols_scanned,
        symbols_skipped=symbols_skipped,
        elapsed_ms=elapsed_ms,
        scan_status=scan_status,
    )


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="shadow_ops daily_scan")
    ap.add_argument("--scan-date", type=str, default=None,
                    help="YYYY-MM-DD; defaults to today UTC")
    ap.add_argument("--run-dir", type=str, default=None)
    ap.add_argument("--no-data-ingest", action="store_true",
                    help="skip yfinance refresh (faster; assumes parquets are current)")
    args = ap.parse_args()

    if args.scan_date:
        sd = date.fromisoformat(args.scan_date)
    else:
        sd = datetime.now(timezone.utc).date()

    try:
        result = daily_scan(
            scan_date=sd,
            run_dir=Path(args.run_dir) if args.run_dir else None,
            run_data_ingest=not args.no_data_ingest,
        )
    except Exception:
        traceback.print_exc()
        return 2

    print(json.dumps({
        "scan_event_id": result.scan_event_id,
        "scan_date": result.scan_date,
        "regime": result.regime,
        "sub_regime": result.sub_regime,
        "run_dir": result.run_dir,
        "n_signals_universe": result.n_signals_universe,
        "n_signals_post_filter": result.n_signals_post_filter,
        "n_candidate_signals_emitted": result.n_candidate_signals_emitted,
        "n_trade_cards_emitted": result.n_trade_cards_emitted,
        "n_kill_001_suppressed": result.n_kill_001_suppressed,
        "n_rule_031_overlay_count": result.n_rule_031_overlay_count,
        "symbols_scanned": result.symbols_scanned,
        "symbols_skipped_count": len(result.symbols_skipped),
        "elapsed_ms": result.elapsed_ms,
        "scan_status": result.scan_status,
    }, indent=2))
    return 0 if result.scan_status in ("OK", "PARTIAL") else 1


if __name__ == "__main__":
    sys.exit(_main_cli())
