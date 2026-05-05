"""Smoke tests for shadow_ops/lifecycle.py.

Audit-faithful contract: lifecycle must mirror signal_replayer.py:
compute_d6_outcome bit-for-bit. These tests construct synthetic OHLC parquets,
synthetic TradeCards, and walk lifecycle.py forward day-by-day, asserting
the emitted events match the canonical simulator's logic.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pytest

from shadow_ops import lifecycle as lc_mod
from shadow_ops.journal import (
    DuplicateEventIdError,
    JournalReader,
    JournalWriter,
)
from shadow_ops.lifecycle import (
    LifecycleError,
    evaluate_open_cards,
)
from shadow_ops.schemas import TradeCard


# ============================================================
# Helpers
# ============================================================

def _bd(s: str) -> date:
    return date.fromisoformat(s)


def _build_ohlc(rows: List[Tuple[str, float, float, float, float, int]]) -> pd.DataFrame:
    """Build an OHLC DataFrame from (date, open, high, low, close, volume) tuples."""
    idx = pd.to_datetime([r[0] for r in rows])
    df = pd.DataFrame({
        "Open":   [r[1] for r in rows],
        "High":   [r[2] for r in rows],
        "Low":    [r[3] for r in rows],
        "Close":  [r[4] for r in rows],
        "Volume": [r[5] for r in rows],
    }, index=idx)
    df.index.name = "Date"
    return df


def _make_card(card_id: str = "card_2018-10-26_TEST.NS",
               symbol: str = "TEST.NS",
               sector: str = "Pharma",
               scan_date: str = "2018-10-26",
               proposed_entry: float = 100.0,
               proposed_stop: float = 95.0,
               proposed_target: float = 110.0,
               atr: float = 2.0) -> TradeCard:
    return TradeCard(
        event_id=f"card_snap_{scan_date}_{symbol}_001",
        event_type="trade_card",
        timestamp_utc=f"{scan_date}T10:35:44+00:00",
        card_id=card_id,
        scan_event_id=f"scan_{scan_date}_001",
        candidate_signal_id=f"cand_{scan_date}_{symbol}_001",
        symbol=symbol,
        sector=sector,
        rule_id="rule_019_bear_uptri_hot_refinement",
        rule_031_confirm=0,
        kill_001_match=False,
        scan_date=scan_date,
        proposed_entry_price=proposed_entry,
        proposed_stop=proposed_stop,
        proposed_target=proposed_target,
        atr=atr,
        current_state="PROPOSED",
        state_history=[{"state": "PROPOSED", "timestamp_utc": f"{scan_date}T10:35:44+00:00",
                        "reason": "rule_019_match"}],
    )


def _seed_card_into_run(run_dir: Path, card: TradeCard) -> None:
    JournalWriter(run_dir).write_event(card)


@pytest.fixture
def stub_ohlc(monkeypatch):
    """Stub _load_symbol_ohlc to return a per-symbol DataFrame the test sets up."""
    by_symbol: Dict[str, pd.DataFrame] = {}

    def fake_loader(symbol: str, cache_dir: Path) -> pd.DataFrame:
        if symbol not in by_symbol:
            raise lc_mod.LifecycleError(f"missing parquet for {symbol}")
        return by_symbol[symbol]

    def fake_parquet_meta(symbol, cache_dir, sha_cache):
        # Stub matches the real signature; values are deterministic placeholders.
        if symbol in sha_cache:
            return sha_cache[symbol]
        if symbol not in by_symbol:
            raise lc_mod.LifecycleError(f"missing parquet for {symbol}")
        rel = f"lab/cache/{symbol.replace('.', '_')}.parquet"
        sha = "0" * 64
        sha_cache[symbol] = (rel, sha)
        return rel, sha

    monkeypatch.setattr(lc_mod, "_load_symbol_ohlc", fake_loader)
    monkeypatch.setattr(lc_mod, "_parquet_meta", fake_parquet_meta)
    return by_symbol


def _walk_days(run_dir: Path, eval_dates: List[str]):
    """Helper: run evaluate_open_cards once per supplied date in order."""
    results = []
    for d in eval_dates:
        results.append(evaluate_open_cards(_bd(d), run_dir=run_dir,
                                            run_data_ingest=False))
    return results


# ============================================================
# 1. D1 unconditional entry
# ============================================================

def test_d1_entry_unconditional(tmp_path, stub_ohlc):
    """D1 OPEN entry happens regardless of D1 high vs proposed_entry.
    Even if D1 high < proposed_entry (no breakout), shadow still enters at
    D1 OPEN (audit-faithful: signal_replayer.py:160-162)."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)

    # D1 high (98) < proposed_entry (100) — no breakout under arch-doc model.
    # But audit-faithful: enter at D1 open=97, hold (no stop/target hit), state=ACTIVE.
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 97.0, 98.0, 96.0, 97.5, 1_000_000),
    ])

    result = evaluate_open_cards(_bd("2018-10-29"), run_dir=tmp_path)
    assert result.n_entries == 1
    assert result.n_stops == 0
    assert result.n_targets == 0

    r = JournalReader(tmp_path)
    assert JournalReader(tmp_path).latest_trade_card_state(card.card_id) == "ACTIVE"
    fills = r.all_fill_simulations()
    assert len(fills) == 1
    assert fills[0].fill_attempt_type == "ENTRY"
    assert fills[0].fill_price == 97.0
    assert fills[0].pnl_pct is None


# ============================================================
# 2. D1 intraday stop hits same day as entry
# ============================================================

def test_d1_intraday_stop_hits_same_day_as_entry(tmp_path, stub_ohlc):
    """D1 OPEN entry then D1 LOW <= stop → two transitions, two fills on T+1."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    # D1 low=94 < stop=95 → STOP_HIT D1
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 99.0, 99.5, 94.0, 94.5, 1_000_000),
    ])

    result = evaluate_open_cards(_bd("2018-10-29"), run_dir=tmp_path)
    assert result.n_entries == 1
    assert result.n_stops == 1
    assert result.n_transitions_emitted == 2

    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_STOPPED"
    fills = r.all_fill_simulations()
    assert [f.fill_attempt_type for f in fills] == ["ENTRY", "STOP"]
    assert fills[1].fill_price == 95.0  # exits at stop_price level (no gap-fill)
    # PnL: (95 - 100) / 100 * 100 = -5.0
    assert fills[1].pnl_pct == -5.0
    assert fills[1].fill_logic_applied == "stop_hit_d1"


# ============================================================
# 3. D1 intraday target hits same day as entry
# ============================================================

def test_d1_intraday_target_hits_same_day_as_entry(tmp_path, stub_ohlc):
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    # D1 high=112 > target=110, low=99 > stop=95
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.5, 112.0, 99.0, 111.0, 1_000_000),
    ])

    result = evaluate_open_cards(_bd("2018-10-29"), run_dir=tmp_path)
    assert result.n_entries == 1 and result.n_targets == 1 and result.n_stops == 0

    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_FILLED"
    fills = r.all_fill_simulations()
    assert fills[1].fill_attempt_type == "TARGET"
    assert fills[1].fill_price == 110.0
    assert fills[1].pnl_pct == 10.0  # (110 - 100) / 100 * 100
    assert fills[1].fill_logic_applied == "target_hit_d1"


# ============================================================
# 4. Stop wins on same-day double hit
# ============================================================

def test_d1_both_stop_and_target_hit_stop_wins(tmp_path, stub_ohlc):
    """If D1 bar has BOTH low <= stop AND high >= target, stop wins
    (signal_replayer.py:186-222 checks stop first)."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 112.0, 94.0, 100.0, 1_000_000),
    ])

    result = evaluate_open_cards(_bd("2018-10-29"), run_dir=tmp_path)
    assert result.n_stops == 1 and result.n_targets == 0

    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_STOPPED"


# ============================================================
# 5. NEW: D1 open at or below stop → entry then stop, both on D1
# ============================================================

def test_d1_open_equals_stop_emits_both_entry_and_stop(tmp_path, stub_ohlc):
    """Volatile-market edge: D1 OPEN <= stop level. Audit-faithful sim
    enters at D1 open then stops out on the same bar (low <= open <= stop).
    Two transitions on T+1."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    # D1 OPEN = 95.0 (= stop), low = 94.5 < stop → entry then immediate stop
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 95.0, 95.5, 94.5, 94.8, 1_000_000),
    ])

    result = evaluate_open_cards(_bd("2018-10-29"), run_dir=tmp_path)
    assert result.n_entries == 1
    assert result.n_stops == 1

    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_STOPPED"
    fills = r.all_fill_simulations()
    assert [f.fill_attempt_type for f in fills] == ["ENTRY", "STOP"]
    assert fills[0].fill_price == 95.0     # entered at open
    assert fills[1].fill_price == 95.0     # exited at stop level
    # PnL anchored to PROPOSED entry (100), not actual fill (95)
    assert fills[1].pnl_pct == -5.0


# ============================================================
# 6. D2-D5 intraday stop
# ============================================================

def test_d2_d5_intraday_stop(tmp_path, stub_ohlc):
    """No D1 hit; D3 intraday stop. State progresses ACTIVE through D2 then
    HYPOTHETICAL_STOPPED on D3."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),  # D1 entry, no hit
        ("2018-10-30", 101.0, 102.5, 99.5, 100.5, 1_000_000),  # D2 no hit
        ("2018-10-31", 100.0, 100.5, 94.0,  95.5, 1_000_000),  # D3 stop hit (low=94)
    ])

    _walk_days(tmp_path, ["2018-10-29", "2018-10-30", "2018-10-31"])
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_STOPPED"
    lcs = r.all_lifecycle_events()
    assert [(lc.from_state, lc.to_state) for lc in lcs] == [
        ("PROPOSED", "ACTIVE"), ("ACTIVE", "HYPOTHETICAL_STOPPED")
    ]
    fills = r.all_fill_simulations()
    stop_fill = [f for f in fills if f.fill_attempt_type == "STOP"][0]
    assert stop_fill.fill_logic_applied == "stop_hit_d3"
    assert stop_fill.fill_date == "2018-10-31"


# ============================================================
# 7. D2-D5 intraday target
# ============================================================

def test_d2_d5_intraday_target(tmp_path, stub_ohlc):
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),  # D1
        ("2018-10-30", 101.0, 105.0, 100.0, 104.0, 1_000_000),  # D2
        ("2018-10-31", 104.0, 108.0, 103.0, 107.0, 1_000_000),  # D3
        ("2018-11-01", 107.0, 112.0, 106.0, 111.5, 1_000_000),  # D4 target hit
    ])

    _walk_days(tmp_path, ["2018-10-29", "2018-10-30", "2018-10-31", "2018-11-01"])
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_FILLED"
    target_fill = [f for f in r.all_fill_simulations() if f.fill_attempt_type == "TARGET"][0]
    assert target_fill.fill_logic_applied == "target_hit_d4"
    assert target_fill.pnl_pct == 10.0


# ============================================================
# 8-10. D6 W/L/F band
# ============================================================

def _seed_six_day_walk(tmp_path, stub_ohlc, d6_open: float):
    """Helper: 6 trading days with no intraday stop or target hit; D6 open = supplied."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),  # D1 entry
        ("2018-10-30", 101.0, 102.5, 99.5, 100.5, 1_000_000),  # D2
        ("2018-10-31", 100.5, 103.0, 99.5, 102.0, 1_000_000),  # D3
        ("2018-11-01", 102.0, 103.5, 100.5, 102.5, 1_000_000), # D4
        ("2018-11-02", 102.5, 104.0, 101.0, 103.0, 1_000_000), # D5
        ("2018-11-05", d6_open, d6_open + 0.5, d6_open - 0.5, d6_open, 1_000_000),  # D6 exit
    ])
    return card


def test_d6_open_exit_win(tmp_path, stub_ohlc):
    """D6 open = 102 → pnl = +2.0% > 0.5% threshold → DAY6_WIN."""
    card = _seed_six_day_walk(tmp_path, stub_ohlc, d6_open=102.0)
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30", "2018-10-31",
                          "2018-11-01", "2018-11-02", "2018-11-05"])
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "EXPIRED"
    expiry = [f for f in r.all_fill_simulations() if f.fill_attempt_type == "EXPIRY"][0]
    assert expiry.fill_price == 102.0
    assert expiry.pnl_pct == 2.0
    assert expiry.fill_logic_applied == "day6_open_exit_win"


def test_d6_open_exit_loss(tmp_path, stub_ohlc):
    """D6 open = 98 → pnl = -2.0% → DAY6_LOSS."""
    card = _seed_six_day_walk(tmp_path, stub_ohlc, d6_open=98.0)
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30", "2018-10-31",
                          "2018-11-01", "2018-11-02", "2018-11-05"])
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "EXPIRED"
    expiry = [f for f in r.all_fill_simulations() if f.fill_attempt_type == "EXPIRY"][0]
    assert expiry.pnl_pct == -2.0
    assert expiry.fill_logic_applied == "day6_open_exit_loss"


def test_d6_open_exit_flat(tmp_path, stub_ohlc):
    """D6 open = 100.4 → pnl = +0.4% → |pnl|<0.5 → DAY6_FLAT."""
    card = _seed_six_day_walk(tmp_path, stub_ohlc, d6_open=100.4)
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30", "2018-10-31",
                          "2018-11-01", "2018-11-02", "2018-11-05"])
    r = JournalReader(tmp_path)
    expiry = [f for f in r.all_fill_simulations() if f.fill_attempt_type == "EXPIRY"][0]
    # pnl_pct rounds to 0.4 (still <0.5 → flat)
    assert expiry.pnl_pct == 0.4
    assert expiry.fill_logic_applied == "day6_open_exit_flat"


# ============================================================
# 11. Idempotency via event_id uniqueness
# ============================================================

def test_idempotent_rerun_raises_duplicate(tmp_path, stub_ohlc):
    card = _make_card()
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),
    ])

    evaluate_open_cards(_bd("2018-10-29"), run_dir=tmp_path)
    # Second invocation for same eval_date: card is now ACTIVE, so the second
    # advance call is a no-op intraday-check (no event emission) — that won't
    # collide. To truly test idempotency, we re-run the FIRST D1 — which would
    # require a fresh PROPOSED card. Simpler: directly check that the writer
    # rejects re-emission of the same event_id.
    from shadow_ops.schemas import FillSimulation
    w = JournalWriter(tmp_path)
    fill = FillSimulation(
        event_id=f"fill_2018-10-29_{card.card_id}_001",
        event_type="fill_simulation",
        timestamp_utc="2018-10-29T10:00:00+00:00",
        card_id=card.card_id,
        fill_attempt_type="ENTRY",
        fill_date="2018-10-29",
        fill_decision="FILLED",
        fill_price=100.0,
        ohlcv={"open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 1_000_000},
        fill_logic_applied="audit_faithful_t1_open_unconditional",
    )
    with pytest.raises(DuplicateEventIdError):
        w.write_event(fill)


# ============================================================
# 12. NO_FILL never auto-emitted
# ============================================================

def test_no_fill_state_never_emitted(tmp_path, stub_ohlc):
    """Walk a card from D1 through D6 with various scenarios; verify
    NO_FILL never appears as a to_state."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),
        ("2018-10-30", 101.0, 102.5, 99.5, 100.5, 1_000_000),
        ("2018-10-31", 100.5, 103.0, 99.5, 102.0, 1_000_000),
        ("2018-11-01", 102.0, 103.5, 100.5, 102.5, 1_000_000),
        ("2018-11-02", 102.5, 104.0, 101.0, 103.0, 1_000_000),
        ("2018-11-05", 103.0, 103.5, 102.5, 103.0, 1_000_000),
    ])
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30", "2018-10-31",
                          "2018-11-01", "2018-11-02", "2018-11-05"])
    states = [(lc.from_state, lc.to_state) for lc in JournalReader(tmp_path).all_lifecycle_events()]
    assert all(s != "NO_FILL" for fr, s in states)
    assert all(s != "SKIPPED" for fr, s in states)


# ============================================================
# 13. Gap-through-stop exits at stop, NOT at gap-down OPEN
# ============================================================

def test_gap_through_stop_exits_at_stop_not_open(tmp_path, stub_ohlc):
    """signal_replayer.py:192 — exit_price = float(stop_price), regardless of
    how far the bar gapped down past stop."""
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    # D2 gaps to 80 (way past stop=95), low=78
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),
        ("2018-10-30",  80.0,  82.0, 78.0,  79.0, 1_000_000),
    ])
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30"])
    stop_fill = [f for f in JournalReader(tmp_path).all_fill_simulations()
                 if f.fill_attempt_type == "STOP"][0]
    assert stop_fill.fill_price == 95.0  # NOT 80.0 (gap-down OPEN)
    assert stop_fill.pnl_pct == -5.0     # PnL anchored to proposed entry, exit at stop


# ============================================================
# 14. Gap-through-target exits at target, NOT gap-up OPEN
# ============================================================

def test_gap_through_target_exits_at_target_not_open(tmp_path, stub_ohlc):
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),
        ("2018-10-30", 130.0, 135.0, 128.0, 132.0, 1_000_000),  # gap to 130, target=110
    ])
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30"])
    target_fill = [f for f in JournalReader(tmp_path).all_fill_simulations()
                   if f.fill_attempt_type == "TARGET"][0]
    assert target_fill.fill_price == 110.0  # NOT 130.0
    assert target_fill.pnl_pct == 10.0


# ============================================================
# 15. SHORT direction stop logic (high >= stop_price)
# ============================================================

def test_short_direction_stop_logic(tmp_path, stub_ohlc):
    """SHORT: stop is above entry; stop hit when high >= stop (gap-up against)."""
    # SHORT: target < entry < stop
    card = _make_card(proposed_entry=100.0, proposed_stop=105.0, proposed_target=90.0)
    _seed_card_into_run(tmp_path, card)
    # D2 high=106 >= stop=105
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0,  101.0,  99.0,  100.5, 1_000_000),
        ("2018-10-30", 102.0,  106.0, 101.0,  105.5, 1_000_000),
    ])
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30"])
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_STOPPED"
    stop_fill = [f for f in r.all_fill_simulations() if f.fill_attempt_type == "STOP"][0]
    assert stop_fill.fill_price == 105.0
    # SHORT pnl: (entry - exit) / entry * 100 = (100 - 105)/100 = -5
    assert stop_fill.pnl_pct == -5.0


# ============================================================
# 16. SHORT direction target logic (low <= target_price)
# ============================================================

def test_short_direction_target_logic(tmp_path, stub_ohlc):
    """SHORT: target is below entry; target hit when low <= target."""
    card = _make_card(proposed_entry=100.0, proposed_stop=105.0, proposed_target=90.0)
    _seed_card_into_run(tmp_path, card)
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 101.0, 99.0, 100.0, 1_000_000),
        ("2018-10-30",  98.0,  99.0, 88.0,  89.5, 1_000_000),  # low=88 < target=90
    ])
    _walk_days(tmp_path, ["2018-10-29", "2018-10-30"])
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "HYPOTHETICAL_FILLED"
    target_fill = [f for f in r.all_fill_simulations() if f.fill_attempt_type == "TARGET"][0]
    assert target_fill.fill_price == 90.0
    # SHORT pnl: (100 - 90) / 100 * 100 = +10
    assert target_fill.pnl_pct == 10.0


# ============================================================
# 17. Missing OHLC for eval_date → skip card with clear reason
# ============================================================

def test_lifecycle_with_missing_ohlc_skips_card_or_errors_clearly(tmp_path, stub_ohlc):
    """eval_date isn't a trading day for this symbol → skip with clear reason."""
    card = _make_card()
    _seed_card_into_run(tmp_path, card)
    # Symbol parquet has data up to D1 but not D2
    stub_ohlc["TEST.NS"] = _build_ohlc([
        ("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000),
    ])
    # D1 advance succeeds
    evaluate_open_cards(_bd("2018-10-29"), run_dir=tmp_path)
    # D2 — symbol parquet lacks 2018-10-30, last bar is 2018-10-29
    result2 = evaluate_open_cards(_bd("2018-10-30"), run_dir=tmp_path)
    # The card should be skipped with "no_bar_for_eval_date"
    assert len(result2.n_skipped) == 1
    card_id, reason = result2.n_skipped[0]
    assert "no_bar_for_eval_date" in reason
    # Card stays ACTIVE (no transition emitted)
    r = JournalReader(tmp_path)
    assert r.latest_trade_card_state(card.card_id) == "ACTIVE"


# ============================================================
# 18. data_source + data_source_sha256 populated (arch §6.7)
# ============================================================

def test_fill_simulation_records_data_source_path(tmp_path):
    """End-to-end with REAL parquet on disk: emitted FillSimulation has
    data_source ending in the expected filename and a valid SHA-256 hex
    matching the file's actual bytes."""
    import hashlib
    cache_dir = tmp_path / "cache"; cache_dir.mkdir()
    ohlc = _build_ohlc([("2018-10-29", 100.0, 102.0, 99.0, 101.0, 1_000_000)])
    parquet_path = cache_dir / "TEST_NS.parquet"
    ohlc.to_parquet(parquet_path)

    run_dir = tmp_path / "run"; run_dir.mkdir()
    card = _make_card()
    _seed_card_into_run(run_dir, card)

    evaluate_open_cards(_bd("2018-10-29"), run_dir=run_dir, cache_dir=cache_dir)

    fills = JournalReader(run_dir).all_fill_simulations()
    assert len(fills) == 1
    fill = fills[0]
    assert fill.data_source.endswith("TEST_NS.parquet")
    assert len(fill.data_source_sha256) == 64
    assert all(c in "0123456789abcdef" for c in fill.data_source_sha256)

    expected_sha = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    assert fill.data_source_sha256 == expected_sha


def test_fill_simulation_data_source_consistent_across_emits(tmp_path):
    """D1 entry + D1 same-day stop → 2 FillSimulations with identical
    data_source and data_source_sha256 (sha_cache works)."""
    cache_dir = tmp_path / "cache"; cache_dir.mkdir()
    # D1 OPEN=99 (above stop=95) entry, low=94 < stop → same-day stop
    ohlc = _build_ohlc([("2018-10-29", 99.0, 99.5, 94.0, 94.5, 1_000_000)])
    parquet_path = cache_dir / "TEST_NS.parquet"
    ohlc.to_parquet(parquet_path)

    run_dir = tmp_path / "run"; run_dir.mkdir()
    card = _make_card(proposed_entry=100.0, proposed_stop=95.0, proposed_target=110.0)
    _seed_card_into_run(run_dir, card)

    evaluate_open_cards(_bd("2018-10-29"), run_dir=run_dir, cache_dir=cache_dir)

    fills = JournalReader(run_dir).all_fill_simulations()
    assert len(fills) == 2
    assert [f.fill_attempt_type for f in fills] == ["ENTRY", "STOP"]
    assert fills[0].data_source == fills[1].data_source
    assert fills[0].data_source_sha256 == fills[1].data_source_sha256
    assert fills[0].data_source_sha256 != ""
