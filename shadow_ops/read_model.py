"""shadow_ops/read_model.py — Step 7 of shadow_ops v1.

Materialized read-model regenerator. Derives current-state view of every
trade card from the immutable event log:
  - trade_cards.jsonl       (PROPOSED snapshots, append-only — Step 4)
  - lifecycle_events.jsonl  (state transitions — Steps 5+)
  - fill_simulations.jsonl  (counterfactual fills — Steps 5+)

Output: trade_cards_current.jsonl (regenerated atomically each call) +
trade_cards_current.jsonl.checksum sidecar.

The append-only event logs remain the SOURCE OF TRUTH. trade_cards_current.jsonl
is a DERIVED VIEW — operator must never edit it directly. Re-running the
regenerator overwrites the file; same input events produce byte-identical output.

DERIVATION LOGIC

For each PROPOSED TradeCard snapshot:
  1. Seed TradeCardCurrent with identity + proposed parameters
  2. Walk lifecycle events in write order; populate actual_entry_* on
     PROPOSED→ACTIVE; populate exit_reason / exit_day on terminal transitions
  3. Walk fill simulations in write order; populate actual_exit_* and
     realized_pnl_pct from the LATEST terminal fill (STOP/TARGET/EXPIRY)
  4. Derive realized_R = pnl_pct / risk_pct, rounded to 4 decimals.
     risk_pct = abs(proposed_entry - proposed_stop) / proposed_entry * 100.
  5. Direction derived as LONG if proposed_target > proposed_entry, else SHORT.

NOTE on realized_R precision: realized_R interacts with pnl_pct's 2-decimal
rounding in the canonical simulator. A "perfect" 2R target hit can come out as
1.9998 or 2.0001 depending on price arithmetic — not exactly 2.0. Tests and
spot-checks use tolerance assertions (|realized_R - expected| < 0.01).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from shadow_ops.journal import JournalReader
from shadow_ops.schemas import (
    FillSimulation,
    LifecycleEvent,
    TradeCard,
)


# ============================================================
# Constants
# ============================================================

OUTPUT_FILENAME = "trade_cards_current.jsonl"
TERMINAL_FILL_TYPES = frozenset({"STOP", "TARGET", "EXPIRY"})


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class TradeCardCurrent:
    """Derived current-state view of a trade card.

    Combines the original PROPOSED snapshot with everything learned from
    subsequent lifecycle + fill events. NOT an Event — no JSONL append
    semantics, no validate(), no event_id discriminator.
    """
    schema_version: str = "v1"

    # Identity (from PROPOSED snapshot)
    card_id: str = ""
    symbol: str = ""
    sector: str = ""
    rule_id: str = ""
    rule_031_confirm: int = 0
    kill_001_match: bool = False
    scan_date: str = ""
    scan_event_id: str = ""
    candidate_signal_id: str = ""

    # Proposed parameters (from PROPOSED snapshot)
    proposed_entry_price: float = 0.0
    proposed_stop: float = 0.0
    proposed_target: float = 0.0
    atr: float = 0.0
    direction: str = ""

    # Current state (derived from lifecycle history)
    current_state: str = "PROPOSED"
    state_history: List[Dict[str, str]] = field(default_factory=list)

    # Actuals
    actual_entry_date: Optional[str] = None
    actual_entry_price: Optional[float] = None
    actual_exit_date: Optional[str] = None
    actual_exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    exit_day: Optional[int] = None

    # Realized
    realized_pnl_pct: Optional[float] = None
    realized_R: Optional[float] = None

    # Provenance (latest terminal FillSimulation's data_source — terminal cards only)
    data_source: Optional[str] = None
    data_source_sha256: Optional[str] = None


@dataclass
class ReadModelResult:
    run_dir: str
    n_cards: int
    n_proposed: int
    n_active: int
    n_hypothetical_filled: int
    n_hypothetical_stopped: int
    n_expired: int
    output_path: str
    output_sha256: str
    elapsed_ms: int
    status: str = "OK"


# ============================================================
# Derivation
# ============================================================

def _direction_from_card(card: TradeCard) -> str:
    return "LONG" if card.proposed_target > card.proposed_entry_price else "SHORT"


def _group_by_card_id(events: List) -> Dict[str, List]:
    by_id: Dict[str, List] = {}
    for ev in events:
        by_id.setdefault(ev.card_id, []).append(ev)
    return by_id


def _derive_current(card: TradeCard,
                    lcs: List[LifecycleEvent],
                    fills: List[FillSimulation]) -> TradeCardCurrent:
    """Walk one card's lifecycle + fill events; build TradeCardCurrent."""
    cur = TradeCardCurrent(
        card_id=card.card_id,
        symbol=card.symbol,
        sector=card.sector,
        rule_id=card.rule_id,
        rule_031_confirm=card.rule_031_confirm,
        kill_001_match=card.kill_001_match,
        scan_date=card.scan_date,
        scan_event_id=card.scan_event_id,
        candidate_signal_id=card.candidate_signal_id,
        proposed_entry_price=card.proposed_entry_price,
        proposed_stop=card.proposed_stop,
        proposed_target=card.proposed_target,
        atr=card.atr,
        direction=_direction_from_card(card),
        current_state=card.current_state,                  # PROPOSED initially
        state_history=[dict(entry) for entry in card.state_history],
    )

    # 2. Walk lifecycle events in write order
    for lc in lcs:
        cur.current_state = lc.to_state
        cur.state_history.append({
            "state": lc.to_state,
            "timestamp_utc": lc.timestamp_utc,
            "reason": lc.reason,
        })
        if lc.to_state == "ACTIVE":
            cur.actual_entry_date = lc.trigger_data.get("actual_entry_date")
            ep = lc.trigger_data.get("actual_entry_price")
            cur.actual_entry_price = float(ep) if ep is not None else None
        elif lc.to_state in ("HYPOTHETICAL_FILLED", "HYPOTHETICAL_STOPPED", "EXPIRED"):
            cur.exit_reason = lc.reason
            ed = lc.trigger_data.get("exit_day")
            cur.exit_day = int(ed) if ed is not None else None

    # 3. Walk fills; capture exit data from the LATEST terminal fill
    for fill in fills:
        if (fill.fill_attempt_type in TERMINAL_FILL_TYPES
                and fill.fill_decision == "FILLED"):
            cur.actual_exit_date = fill.fill_date
            cur.actual_exit_price = (float(fill.fill_price)
                                     if fill.fill_price is not None else None)
            cur.realized_pnl_pct = (float(fill.pnl_pct)
                                    if fill.pnl_pct is not None else None)
            cur.data_source = fill.data_source or None
            cur.data_source_sha256 = fill.data_source_sha256 or None

    # 4. realized_R derivation
    if cur.realized_pnl_pct is not None and cur.proposed_entry_price > 0:
        risk_pct = (abs(cur.proposed_entry_price - cur.proposed_stop)
                    / cur.proposed_entry_price * 100.0)
        if risk_pct > 0:
            cur.realized_R = round(cur.realized_pnl_pct / risk_pct, 4)

    return cur


# ============================================================
# Atomic write + checksum
# ============================================================

def _atomic_write_jsonl(path: Path, items: List[TradeCardCurrent]) -> str:
    """Write items to path atomically. Returns SHA-256 hex of new file content.
    Output is deterministic (json.dumps with sort_keys + fixed separators)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    h = hashlib.sha256()
    with open(tmp, "w", encoding="utf-8") as f:
        for item in items:
            line = json.dumps(asdict(item), separators=(",", ":"),
                              sort_keys=True) + "\n"
            f.write(line)
            h.update(line.encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return h.hexdigest()


def _write_checksum_sidecar(jsonl_path: Path, sha_hex: str) -> None:
    """Mirrors Step 3's sidecar convention."""
    ck = Path(str(jsonl_path) + ".checksum")
    ck.write_text(sha_hex)


def _check_parquet_sha_drift(run_dir: Path, cache_dir: Path,
                              fills: List[FillSimulation]) -> None:
    """Compare each unique parquet referenced by a fill against the current
    parquet on disk. Emits one PARQUET_SHA_DRIFT alert per drifted parquet.

    This is post-hoc tamper-evidence: if a parquet was modified after a fill
    was simulated, future re-runs of lifecycle would produce different fills,
    and the audit trail would diverge from reality.
    """
    import hashlib
    from shadow_ops.alerts import emit_alert

    # Collect (data_source_relpath, recorded_sha) pairs; dedupe on path
    by_path: Dict[str, str] = {}     # path → recorded sha (last fill wins)
    for f in fills:
        if f.data_source and f.data_source_sha256:
            by_path[f.data_source] = f.data_source_sha256

    repo_root = Path(__file__).resolve().parent.parent
    for rel_path, recorded_sha in by_path.items():
        absolute = (repo_root / rel_path) if not Path(rel_path).is_absolute() else Path(rel_path)
        if not absolute.exists():
            emit_alert(
                run_dir, "WARNING", "PARQUET_SHA_DRIFT",
                module="read_model",
                message=f"recorded parquet missing: {rel_path}",
                context={"path": rel_path, "recorded_sha256": recorded_sha,
                         "reason": "file_missing"},
            )
            continue
        h = hashlib.sha256()
        with open(absolute, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        current_sha = h.hexdigest()
        if current_sha != recorded_sha:
            emit_alert(
                run_dir, "WARNING", "PARQUET_SHA_DRIFT",
                module="read_model",
                message=(f"parquet SHA drift on {rel_path}: "
                         f"recorded={recorded_sha[:16]}..., "
                         f"current={current_sha[:16]}..."),
                context={"path": rel_path,
                         "recorded_sha256": recorded_sha,
                         "current_sha256": current_sha},
            )


# ============================================================
# Public API
# ============================================================

def regenerate_read_model(run_dir: Path,
                          cache_dir: Optional[Path] = None) -> ReadModelResult:
    """Regenerate trade_cards_current.jsonl from the event log.

    Idempotent: same input events → byte-identical output. Existing file
    overwritten atomically.

    If cache_dir is supplied, also checks for parquet SHA drift: any
    FillSimulation whose recorded data_source_sha256 doesn't match the
    current parquet's SHA produces a PARQUET_SHA_DRIFT alert (Step 9).
    """
    t0 = time.monotonic()
    run_dir = Path(run_dir)

    reader = JournalReader(run_dir)
    cards = reader.all_trade_cards()
    lcs = reader.all_lifecycle_events()
    fills = reader.all_fill_simulations()

    lcs_by_card = _group_by_card_id(lcs)
    fills_by_card = _group_by_card_id(fills)

    currents: List[TradeCardCurrent] = []
    counters = {
        "PROPOSED": 0, "ACTIVE": 0,
        "HYPOTHETICAL_FILLED": 0, "HYPOTHETICAL_STOPPED": 0,
        "EXPIRED": 0,
    }

    for card in cards:
        cur = _derive_current(
            card,
            lcs_by_card.get(card.card_id, []),
            fills_by_card.get(card.card_id, []),
        )
        currents.append(cur)
        counters[cur.current_state] = counters.get(cur.current_state, 0) + 1

    output_path = run_dir / OUTPUT_FILENAME
    sha = _atomic_write_jsonl(output_path, currents)
    _write_checksum_sidecar(output_path, sha)

    # --- Step 9: optional parquet SHA drift detection ---
    if cache_dir is not None:
        _check_parquet_sha_drift(run_dir, cache_dir, fills)

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    return ReadModelResult(
        run_dir=str(run_dir),
        n_cards=len(currents),
        n_proposed=counters["PROPOSED"],
        n_active=counters["ACTIVE"],
        n_hypothetical_filled=counters["HYPOTHETICAL_FILLED"],
        n_hypothetical_stopped=counters["HYPOTHETICAL_STOPPED"],
        n_expired=counters["EXPIRED"],
        output_path=str(output_path),
        output_sha256=sha,
        elapsed_ms=elapsed_ms,
        status="OK",
    )


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    ap = argparse.ArgumentParser(description="shadow_ops read-model regenerator")
    ap.add_argument("--run-dir", type=str, required=True,
                    help="path to a daily_scan run directory")
    args = ap.parse_args()

    try:
        result = regenerate_read_model(Path(args.run_dir))
    except Exception:
        traceback.print_exc()
        return 2

    print(json.dumps(asdict(result), indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_main_cli())
