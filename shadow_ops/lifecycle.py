"""shadow_ops/lifecycle.py — Step 5 of shadow_ops v1.

Day-by-day evaluator for open trade cards. AUDIT-FAITHFUL: mirrors
lab/infrastructure/signal_replayer.py:compute_d6_outcome bit-for-bit so
that shadow's exit outcomes are bit-for-bit equivalent to the audit
pipeline's enriched_signals.parquet for any historical signal.

Operating model: operator runs once per trading day (T+1 onward) for cards
created by daily_scan. Each invocation advances every open card by exactly
one trading day's state changes. No multi-day catchup; if a day is missed,
the operator must run lifecycle for each missing date in order.

State machine (audit-faithful — only 4 transitions used in v1):
  PROPOSED → ACTIVE                  always, T+1 unconditional, entry at D1 OPEN
  ACTIVE → HYPOTHETICAL_STOPPED       D1-D5 OR D6 intraday stop hit
  ACTIVE → HYPOTHETICAL_FILLED        D1-D5 OR D6 intraday target hit
                                      (stop wins same-day double-hit)
  ACTIVE → EXPIRED                    D6 exit at OPEN, no prior intraday hit

NO_FILL and SKIPPED states are never auto-emitted in v1. Reserved for future
operator manual override (e.g., kill_001 cluster pause).

ROUNDING POLICY (mirrors canonical):
  - exit_price stored at FULL precision (signal_replayer.py:192,201,211,220,243)
  - pnl_pct stored ROUNDED to 2 decimals (signal_replayer.py:193,202,212,221,245)
  - W/L/F classification uses the UNROUNDED pnl (signal_replayer.py:232)
  - ohlcv embedded at full precision (no rounding at storage time)

IDEMPOTENCY: event_ids are deterministic per (card_id, eval_date, in-call seq).
Re-running for the same eval_date attempts to write identical event_ids and
raises DuplicateEventIdError on the first collision.

CANONICAL SOURCE: lab/infrastructure/signal_replayer.py (compute_d6_outcome).
DO NOT FORK that logic. This module mirrors it; cross-validation tests detect
drift.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from shadow_ops.data_ingest import (
    DEFAULT_CACHE_DIR,
    daily_data_ingest,
    parquet_path_for_symbol,
)
from shadow_ops.journal import (
    DuplicateEventIdError,
    JournalReader,
    JournalWriter,
)
from shadow_ops.schemas import (
    FillSimulation,
    LifecycleEvent,
    TradeCard,
)


# ============================================================
# Constants — mirror signal_replayer.py
# ============================================================

HOLDING_DAYS = 6                  # signal_replayer.py:88
TARGET_R_MULTIPLE = 2.0           # signal_replayer.py:87
FLAT_THRESHOLD_PCT = 0.5          # signal_replayer.py:86

OPEN_STATES = frozenset({"PROPOSED", "ACTIVE"})


# ============================================================
# Errors
# ============================================================

class LifecycleError(Exception):
    pass


# ============================================================
# Result dataclass
# ============================================================

@dataclass
class LifecycleResult:
    eval_date: str
    run_dir: str
    n_open_cards_at_start: int
    n_transitions_emitted: int
    n_entries: int
    n_stops: int
    n_targets: int
    n_expired: int
    n_d6_win: int
    n_d6_loss: int
    n_d6_flat: int
    n_skipped: List[Tuple[str, str]] = field(default_factory=list)
    elapsed_ms: int = 0
    status: str = "OK"


# ============================================================
# Helpers
# ============================================================

def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_symbol_ohlc(symbol: str, cache_dir: Path) -> pd.DataFrame:
    """Load full per-symbol parquet (no truncation; lifecycle needs forward bars)."""
    p = parquet_path_for_symbol(symbol, cache_dir)
    if not p.exists():
        raise LifecycleError(f"missing parquet for {symbol}: {p}")
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index, errors="coerce")
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df[df.index.notna()].dropna(subset=["Close"])
    return df.sort_index()


def _post_scan_window(df: pd.DataFrame, scan_ts: pd.Timestamp,
                      eval_ts: pd.Timestamp) -> pd.DataFrame:
    """Slice of df with index in (scan_ts, eval_ts]. Last row = eval_date bar
    (or earlier if eval_date isn't in this symbol's parquet)."""
    return df[(df.index > scan_ts) & (df.index <= eval_ts)]


def _compute_pnl_pct(direction: str, proposed_entry: float,
                     exit_price: float) -> float:
    """Audit-faithful PnL anchored to PROPOSED entry, NOT actual D1 fill.
    Mirrors signal_replayer.py:187,196,206,215,228,230. Returns UNROUNDED."""
    if direction == "LONG":
        return (exit_price - proposed_entry) / proposed_entry * 100.0
    return (proposed_entry - exit_price) / proposed_entry * 100.0


def _classify_d6_pnl(pnl_pct_unrounded: float) -> str:
    """Mirror signal_replayer.py:232-237. Uses unrounded pnl for the band check."""
    if abs(pnl_pct_unrounded) < FLAT_THRESHOLD_PCT:
        return "day6_flat"
    return "day6_win" if pnl_pct_unrounded > 0 else "day6_loss"


def _bar_ohlcv(bar: pd.Series) -> Dict[str, float]:
    """Embed full-precision OHLCV from a bar. No rounding."""
    return {
        "open": float(bar["Open"]),
        "high": float(bar["High"]),
        "low": float(bar["Low"]),
        "close": float(bar["Close"]),
        "volume": float(bar["Volume"]) if "Volume" in bar.index else 0.0,
    }


def _direction_for_card(card: TradeCard) -> str:
    """Direction inferred from target vs entry geometry. LONG: target > entry."""
    return "LONG" if card.proposed_target > card.proposed_entry_price else "SHORT"


# ============================================================
# Sequence allocator (deterministic per call)
# ============================================================

class _SeqAllocator:
    """Allocates 1-based sequence numbers per (card_id, eval_iso). Resets each
    invocation of evaluate_open_cards — that's why re-running raises
    DuplicateEventIdError on identical event_ids."""
    def __init__(self) -> None:
        self.counts: Dict[Tuple[str, str], int] = {}

    def next(self, card_id: str, eval_iso: str) -> int:
        key = (card_id, eval_iso)
        seq = self.counts.get(key, 0) + 1
        self.counts[key] = seq
        return seq


# ============================================================
# Event emission helpers
# ============================================================

def _emit_entry(card: TradeCard, bar: pd.Series, eval_date: date,
                writer: JournalWriter, seq_alloc: _SeqAllocator,
                counters: Dict[str, int]) -> None:
    eval_iso = eval_date.isoformat()
    bar_iso = bar.name.date().isoformat()
    seq = seq_alloc.next(card.card_id, eval_iso)
    d1_open = float(bar["Open"])

    fill = FillSimulation(
        event_id=f"fill_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="fill_simulation",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        fill_attempt_type="ENTRY",
        fill_date=bar_iso,
        fill_decision="FILLED",
        fill_price=d1_open,
        ohlcv=_bar_ohlcv(bar),
        fill_logic_applied="audit_faithful_t1_open_unconditional",
        pnl_pct=None,
    )
    writer.write_event(fill)

    lc = LifecycleEvent(
        event_id=f"lc_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="lifecycle_event",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        from_state="PROPOSED",
        to_state="ACTIVE",
        reason="entry_t1_open",
        trigger_data={
            "actual_entry_price": d1_open,
            "actual_entry_date": bar_iso,
            "fill_event_id": fill.event_id,
        },
    )
    writer.write_event(lc)
    counters["entries"] += 1


def _emit_stop(card: TradeCard, bar: pd.Series, day_n: int, eval_date: date,
               writer: JournalWriter, seq_alloc: _SeqAllocator,
               counters: Dict[str, int]) -> None:
    eval_iso = eval_date.isoformat()
    bar_iso = bar.name.date().isoformat()
    seq = seq_alloc.next(card.card_id, eval_iso)
    direction = _direction_for_card(card)
    stop_px = float(card.proposed_stop)
    pnl_unrounded = _compute_pnl_pct(direction, float(card.proposed_entry_price), stop_px)

    fill = FillSimulation(
        event_id=f"fill_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="fill_simulation",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        fill_attempt_type="STOP",
        fill_date=bar_iso,
        fill_decision="FILLED",
        fill_price=stop_px,
        ohlcv=_bar_ohlcv(bar),
        fill_logic_applied=f"stop_hit_d{day_n}",
        pnl_pct=round(pnl_unrounded, 2),
    )
    writer.write_event(fill)

    lc = LifecycleEvent(
        event_id=f"lc_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="lifecycle_event",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        from_state="ACTIVE",
        to_state="HYPOTHETICAL_STOPPED",
        reason=f"stop_hit_d{day_n}",
        trigger_data={
            "exit_price": stop_px,
            "exit_date": bar_iso,
            "exit_day": day_n,
            "pnl_pct": round(pnl_unrounded, 2),
            "fill_event_id": fill.event_id,
        },
    )
    writer.write_event(lc)
    counters["stops"] += 1


def _emit_target(card: TradeCard, bar: pd.Series, day_n: int, eval_date: date,
                 writer: JournalWriter, seq_alloc: _SeqAllocator,
                 counters: Dict[str, int]) -> None:
    eval_iso = eval_date.isoformat()
    bar_iso = bar.name.date().isoformat()
    seq = seq_alloc.next(card.card_id, eval_iso)
    direction = _direction_for_card(card)
    target_px = float(card.proposed_target)
    pnl_unrounded = _compute_pnl_pct(direction, float(card.proposed_entry_price), target_px)

    fill = FillSimulation(
        event_id=f"fill_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="fill_simulation",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        fill_attempt_type="TARGET",
        fill_date=bar_iso,
        fill_decision="FILLED",
        fill_price=target_px,
        ohlcv=_bar_ohlcv(bar),
        fill_logic_applied=f"target_hit_d{day_n}",
        pnl_pct=round(pnl_unrounded, 2),
    )
    writer.write_event(fill)

    lc = LifecycleEvent(
        event_id=f"lc_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="lifecycle_event",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        from_state="ACTIVE",
        to_state="HYPOTHETICAL_FILLED",
        reason=f"target_hit_d{day_n}",
        trigger_data={
            "exit_price": target_px,
            "exit_date": bar_iso,
            "exit_day": day_n,
            "pnl_pct": round(pnl_unrounded, 2),
            "fill_event_id": fill.event_id,
        },
    )
    writer.write_event(lc)
    counters["targets"] += 1


def _emit_expired(card: TradeCard, bar: pd.Series, eval_date: date,
                  writer: JournalWriter, seq_alloc: _SeqAllocator,
                  counters: Dict[str, int]) -> None:
    eval_iso = eval_date.isoformat()
    bar_iso = bar.name.date().isoformat()
    seq = seq_alloc.next(card.card_id, eval_iso)
    direction = _direction_for_card(card)
    d6_open = float(bar["Open"])
    pnl_unrounded = _compute_pnl_pct(direction, float(card.proposed_entry_price), d6_open)
    sub = _classify_d6_pnl(pnl_unrounded)  # day6_win / day6_loss / day6_flat

    fill = FillSimulation(
        event_id=f"fill_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="fill_simulation",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        fill_attempt_type="EXPIRY",
        fill_date=bar_iso,
        fill_decision="FILLED",
        fill_price=d6_open,
        ohlcv=_bar_ohlcv(bar),
        fill_logic_applied=f"day6_open_exit_{sub.split('_')[1]}",
        pnl_pct=round(pnl_unrounded, 2),
    )
    writer.write_event(fill)

    lc = LifecycleEvent(
        event_id=f"lc_{eval_iso}_{card.card_id}_{seq:03d}",
        event_type="lifecycle_event",
        timestamp_utc=_now_utc_iso(),
        card_id=card.card_id,
        from_state="ACTIVE",
        to_state="EXPIRED",
        reason="d6_open_exit",
        trigger_data={
            "exit_price": d6_open,
            "exit_date": bar_iso,
            "exit_day": HOLDING_DAYS,
            "pnl_pct": round(pnl_unrounded, 2),
            "outcome_subtype": sub,
            "fill_event_id": fill.event_id,
        },
    )
    writer.write_event(lc)
    counters["expired"] += 1
    counters[f"d6_{sub.split('_')[1]}"] += 1


# ============================================================
# Per-card advancement
# ============================================================

def _current_state(card: TradeCard, reader: JournalReader) -> str:
    """Latest state — derived from lifecycle log if any, else from card snapshot."""
    try:
        return reader.latest_trade_card_state(card.card_id)
    except KeyError:
        return card.current_state


def _advance_one_card(card: TradeCard,
                     eval_date: date,
                     reader: JournalReader,
                     writer: JournalWriter,
                     cache_dir: Path,
                     seq_alloc: _SeqAllocator,
                     counters: Dict[str, int]) -> Optional[str]:
    """Advance a single card by exactly one trading day. Returns None on
    advance OR a skip-reason string."""
    state = _current_state(card, reader)
    if state not in OPEN_STATES:
        return f"already_terminal:{state}"

    df = _load_symbol_ohlc(card.symbol, cache_dir)
    scan_ts = pd.Timestamp(card.scan_date)
    eval_ts = pd.Timestamp(eval_date)

    post = _post_scan_window(df, scan_ts, eval_ts)
    day_n = len(post)

    if day_n == 0:
        return "before_scan_date"
    if day_n > HOLDING_DAYS:
        raise LifecycleError(
            f"card {card.card_id}: day_n={day_n} > HOLDING_DAYS={HOLDING_DAYS}; "
            f"operator missed days — backfill missing eval_dates first"
        )

    eval_bar = post.iloc[-1]
    eval_bar_date = post.index[-1]
    if eval_bar_date.date() != eval_date:
        return f"no_bar_for_eval_date:got_{eval_bar_date.date().isoformat()}"

    direction = _direction_for_card(card)

    # ── D1 ENTRY (PROPOSED → ACTIVE) ─────────────────────────────
    if state == "PROPOSED":
        if day_n != 1:
            raise LifecycleError(
                f"card {card.card_id}: state=PROPOSED but day_n={day_n} (expected 1); "
                f"operator missed days — backfill missing eval_dates first"
            )
        _emit_entry(card, eval_bar, eval_date, writer, seq_alloc, counters)
        state = "ACTIVE"  # fall through to intraday check on the same bar

    # ── INTRADAY STOP/TARGET (D1-D6) ─────────────────────────────
    if state == "ACTIVE":
        low = float(eval_bar["Low"])
        high = float(eval_bar["High"])
        stop_px = float(card.proposed_stop)
        target_px = float(card.proposed_target)

        stop_hit = ((direction == "LONG" and low <= stop_px) or
                    (direction == "SHORT" and high >= stop_px))
        target_hit = ((direction == "LONG" and high >= target_px) or
                      (direction == "SHORT" and low <= target_px))

        if stop_hit:  # stop wins same-day double hit (signal_replayer.py:186-203)
            _emit_stop(card, eval_bar, day_n, eval_date, writer, seq_alloc, counters)
            return None
        if target_hit:
            _emit_target(card, eval_bar, day_n, eval_date, writer, seq_alloc, counters)
            return None

        if day_n == HOLDING_DAYS:
            _emit_expired(card, eval_bar, eval_date, writer, seq_alloc, counters)
            return None
        # else: card stays ACTIVE; no events this call

    return None


# ============================================================
# Public API
# ============================================================

def evaluate_open_cards(eval_date: date,
                        run_dir: Path,
                        cache_dir: Path = DEFAULT_CACHE_DIR,
                        run_data_ingest: bool = False) -> LifecycleResult:
    """Advance every open trade card in run_dir by exactly one trading day's
    state changes. See module docstring."""
    t0 = time.monotonic()
    eval_iso = eval_date.isoformat()
    run_dir = Path(run_dir)

    if run_data_ingest:
        daily_data_ingest(end_date=eval_date, cache_dir=cache_dir)

    reader = JournalReader(run_dir)
    writer = JournalWriter(run_dir)

    all_cards = reader.all_trade_cards()
    open_cards: List[TradeCard] = [c for c in all_cards
                                    if _current_state(c, reader) in OPEN_STATES]

    counters: Dict[str, int] = {
        "entries": 0, "stops": 0, "targets": 0, "expired": 0,
        "d6_win": 0, "d6_loss": 0, "d6_flat": 0,
    }
    seq_alloc = _SeqAllocator()
    skipped: List[Tuple[str, str]] = []
    had_per_card_error = False

    for card in open_cards:
        try:
            reason = _advance_one_card(card, eval_date, reader, writer,
                                       cache_dir, seq_alloc, counters)
            if reason:
                skipped.append((card.card_id, reason))
        except DuplicateEventIdError:
            raise  # idempotency guard
        except Exception as e:
            skipped.append((card.card_id, f"error:{type(e).__name__}:{e}"))
            had_per_card_error = True

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    status = "PARTIAL" if had_per_card_error else "OK"
    n_transitions = (counters["entries"] + counters["stops"]
                     + counters["targets"] + counters["expired"])

    return LifecycleResult(
        eval_date=eval_iso,
        run_dir=str(run_dir),
        n_open_cards_at_start=len(open_cards),
        n_transitions_emitted=n_transitions,
        n_entries=counters["entries"],
        n_stops=counters["stops"],
        n_targets=counters["targets"],
        n_expired=counters["expired"],
        n_d6_win=counters["d6_win"],
        n_d6_loss=counters["d6_loss"],
        n_d6_flat=counters["d6_flat"],
        n_skipped=skipped,
        elapsed_ms=elapsed_ms,
        status=status,
    )


# ============================================================
# CLI
# ============================================================

def _main_cli() -> int:
    ap = argparse.ArgumentParser(description="shadow_ops lifecycle evaluator")
    ap.add_argument("--eval-date", type=str, default=None,
                    help="YYYY-MM-DD; defaults to today UTC")
    ap.add_argument("--run-dir", type=str, required=True,
                    help="path to a daily_scan run directory")
    ap.add_argument("--no-data-ingest", action="store_true",
                    help="skip yfinance refresh (default; assumes parquets are current)")
    args = ap.parse_args()

    if args.eval_date:
        ed = date.fromisoformat(args.eval_date)
    else:
        ed = datetime.now(timezone.utc).date()

    try:
        result = evaluate_open_cards(
            eval_date=ed,
            run_dir=Path(args.run_dir),
            run_data_ingest=not args.no_data_ingest,
        )
    except DuplicateEventIdError as e:
        print(f"[lifecycle] already processed for this eval_date "
              f"(event_id collision): {e}", file=sys.stderr)
        return 3
    except Exception:
        traceback.print_exc()
        return 2

    out = asdict(result)
    print(json.dumps(out, indent=2, default=str))
    return 0 if result.status == "OK" else 1


if __name__ == "__main__":
    sys.exit(_main_cli())
