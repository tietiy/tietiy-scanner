"""Smoke tests for shadow_ops/daily_report.py.

Each test seeds a temp run_dir with synthetic events, calls
generate_daily_report, and asserts on the returned markdown.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import List

import pytest

from shadow_ops.daily_report import (
    REPORTS_SUBDIR,
    default_report_path,
    generate_daily_report,
)
from shadow_ops.journal import JournalWriter
from shadow_ops.schemas import (
    CandidateSignal,
    FillSimulation,
    LifecycleEvent,
    ScanEvent,
    TradeCard,
)


# ============================================================
# Helpers
# ============================================================

def _bd(s: str) -> date:
    return date.fromisoformat(s)


def _make_scan(scan_date: str = "2018-10-26",
               regime: str = "Bear", sub_regime: str = "hot",
               n_uni: int = 73, n_post: int = 72) -> ScanEvent:
    return ScanEvent(
        event_id=f"scan_{scan_date}_001",
        event_type="scan_event",
        timestamp_utc=f"{scan_date}T16:00:00+00:00",
        scan_date=scan_date,
        regime=regime,
        sub_regime=sub_regime,
        sub_regime_inputs={"feat_nifty_vol_percentile_20d": 0.78,
                           "nifty_close_latest_date": scan_date},
        n_signals_universe=n_uni,
        n_signals_post_filter=n_post,
        scan_status="OK",
        scan_duration_ms=4521,
        git_commit_sha="abc123def456",
        data_versions={"rules_path_sha256": "deadbeef" * 8},
    )


def _make_card(card_id: str, symbol: str = "TEST.NS",
               scan_date: str = "2018-10-26",
               proposed_entry: float = 100.0,
               proposed_stop: float = 95.0,
               proposed_target: float = 110.0) -> TradeCard:
    return TradeCard(
        event_id=f"card_snap_{scan_date}_{symbol}_001",
        event_type="trade_card",
        timestamp_utc=f"{scan_date}T10:35:44+00:00",
        card_id=card_id,
        scan_event_id=f"scan_{scan_date}_001",
        candidate_signal_id=f"cand_{scan_date}_{symbol}_001",
        symbol=symbol,
        sector="Pharma",
        rule_id="rule_019_bear_uptri_hot_refinement",
        rule_031_confirm=0,
        kill_001_match=False,
        scan_date=scan_date,
        proposed_entry_price=proposed_entry,
        proposed_stop=proposed_stop,
        proposed_target=proposed_target,
        atr=2.0,
        current_state="PROPOSED",
        state_history=[{"state": "PROPOSED",
                        "timestamp_utc": f"{scan_date}T10:35:44+00:00",
                        "reason": "rule_019_match"}],
    )


def _make_fill(card_id: str, attempt_type: str, fill_date: str,
               fill_price: float, pnl_pct=None,
               fill_logic: str = "audit_faithful_t1_open_unconditional",
               seq: int = 1,
               wallclock_date: str = None) -> FillSimulation:
    """fill_date is the LOGICAL trading day. wallclock_date overrides timestamp_utc
    (default: same as fill_date)."""
    ts_date = wallclock_date or fill_date
    return FillSimulation(
        event_id=f"fill_{fill_date}_{card_id}_{seq:03d}",
        event_type="fill_simulation",
        timestamp_utc=f"{ts_date}T03:50:01+00:00",
        card_id=card_id,
        fill_attempt_type=attempt_type,
        fill_date=fill_date,
        fill_decision="FILLED",
        fill_price=fill_price,
        ohlcv={"open": fill_price, "high": fill_price + 1, "low": fill_price - 1,
               "close": fill_price, "volume": 1_000_000},
        fill_logic_applied=fill_logic,
        pnl_pct=pnl_pct,
        data_source="lab/cache/TEST_NS.parquet",
        data_source_sha256="abc" + "0" * 61,
    )


def _make_lc(card_id: str, from_state: str, to_state: str,
             reason: str, fill_event_id: str,
             eval_iso: str, exit_day=None,
             actual_entry_price=None, actual_entry_date=None,
             pnl_pct=None, exit_price=None,
             wallclock_date: str = None,
             seq: int = 1) -> LifecycleEvent:
    """eval_iso is the LOGICAL trading day. wallclock_date overrides timestamp_utc."""
    ts_date = wallclock_date or eval_iso
    trigger: dict = {"fill_event_id": fill_event_id}
    if actual_entry_price is not None:
        trigger["actual_entry_price"] = actual_entry_price
        trigger["actual_entry_date"] = actual_entry_date or eval_iso
    if exit_day is not None:
        trigger["exit_day"] = exit_day
        trigger["exit_price"] = exit_price
        trigger["pnl_pct"] = pnl_pct
        trigger["exit_date"] = eval_iso
    return LifecycleEvent(
        event_id=f"lc_{eval_iso}_{card_id}_{seq:03d}",
        event_type="lifecycle_event",
        timestamp_utc=f"{ts_date}T03:50:01+00:00",
        card_id=card_id,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        trigger_data=trigger,
    )


def _seed(run_dir: Path, events) -> None:
    w = JournalWriter(run_dir)
    for ev in events:
        w.write_event(ev)


def _seed_full_card(run_dir: Path, card_id: str, symbol: str,
                    scan_date: str, eval_iso: str,
                    transition: str,             # "ENTRY_ONLY" | "STOP" | "TARGET" | "EXPIRY"
                    entry_open: float = 99.5,
                    exit_price: float = None,
                    pnl_pct: float = None,
                    day_n: int = 1,
                    proposed_entry: float = 100.0,
                    proposed_stop: float = 95.0,
                    proposed_target: float = 110.0):
    """Convenience: seed PROPOSED card + ENTRY fill+lc, plus optional terminal."""
    card = _make_card(card_id, symbol, scan_date, proposed_entry,
                      proposed_stop, proposed_target)
    entry_fill = _make_fill(card_id, "ENTRY", eval_iso, entry_open, seq=1)
    entry_lc = _make_lc(card_id, "PROPOSED", "ACTIVE", "entry_t1_open",
                        entry_fill.event_id, eval_iso,
                        actual_entry_price=entry_open, seq=1)
    events = [card, entry_fill, entry_lc]
    if transition == "STOP":
        f2 = _make_fill(card_id, "STOP", eval_iso, exit_price,
                        pnl_pct=pnl_pct, fill_logic=f"stop_hit_d{day_n}", seq=2)
        lc2 = _make_lc(card_id, "ACTIVE", "HYPOTHETICAL_STOPPED",
                       f"stop_hit_d{day_n}", f2.event_id, eval_iso,
                       exit_day=day_n, exit_price=exit_price, pnl_pct=pnl_pct, seq=2)
        events += [f2, lc2]
    elif transition == "TARGET":
        f2 = _make_fill(card_id, "TARGET", eval_iso, exit_price,
                        pnl_pct=pnl_pct, fill_logic=f"target_hit_d{day_n}", seq=2)
        lc2 = _make_lc(card_id, "ACTIVE", "HYPOTHETICAL_FILLED",
                       f"target_hit_d{day_n}", f2.event_id, eval_iso,
                       exit_day=day_n, exit_price=exit_price, pnl_pct=pnl_pct, seq=2)
        events += [f2, lc2]
    elif transition == "EXPIRY":
        f2 = _make_fill(card_id, "EXPIRY", eval_iso, exit_price,
                        pnl_pct=pnl_pct,
                        fill_logic=f"day6_open_exit_{'win' if pnl_pct > 0 else 'loss' if pnl_pct < 0 else 'flat'}",
                        seq=2)
        lc2 = _make_lc(card_id, "ACTIVE", "EXPIRED", "d6_open_exit",
                       f2.event_id, eval_iso, exit_day=6,
                       exit_price=exit_price, pnl_pct=pnl_pct, seq=2)
        events += [f2, lc2]
    _seed(run_dir, events)


# ============================================================
# Tests
# ============================================================

def test_report_skeleton_for_empty_run_dir(tmp_path):
    md = generate_daily_report(tmp_path, _bd("2018-10-29"))
    assert md.startswith("# Shadow Ops Daily Report — 2018-10-29")
    # No scan summary, no transitions, no open cards
    assert "## Today's scan" not in md
    assert "## Today's transitions" not in md
    assert "## Open trade cards" not in md
    # Cumulative section is always rendered (zeros are informative)
    assert "## Cumulative cohort outcomes" in md


def test_report_includes_scan_summary_when_scan_event_exists(tmp_path):
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    md = generate_daily_report(tmp_path, _bd("2018-10-26"))
    assert "## Today's scan" in md
    assert "Scan status" in md and "OK" in md
    assert "abc123def456" in md  # git sha in header


def test_report_includes_entry_section_when_entries_today(tmp_path):
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    _seed_full_card(tmp_path, "card_2018-10-26_TEST.NS", "TEST.NS",
                    "2018-10-26", "2018-10-29", "ENTRY_ONLY",
                    entry_open=99.5)
    md = generate_daily_report(tmp_path, _bd("2018-10-29"))
    assert "### Entries (PROPOSED → ACTIVE) — 1 cards" in md
    assert "TEST.NS" in md


def test_report_includes_stop_section_when_stops_today(tmp_path):
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    _seed_full_card(tmp_path, "card_2018-10-26_TEST.NS", "TEST.NS",
                    "2018-10-26", "2018-10-29", "STOP",
                    entry_open=99.5, exit_price=95.0, pnl_pct=-5.0, day_n=1)
    md = generate_daily_report(tmp_path, _bd("2018-10-29"))
    assert "### Stops hit (ACTIVE → HYPOTHETICAL_STOPPED) — 1 cards" in md
    assert "stop_hit_d1" not in md or "TEST.NS" in md  # we render symbol/exit_day


def test_report_includes_target_section_when_targets_today(tmp_path):
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    _seed_full_card(tmp_path, "card_2018-10-26_TEST.NS", "TEST.NS",
                    "2018-10-26", "2018-10-29", "TARGET",
                    entry_open=99.5, exit_price=110.0, pnl_pct=10.0, day_n=1)
    md = generate_daily_report(tmp_path, _bd("2018-10-29"))
    assert "### Targets hit (ACTIVE → HYPOTHETICAL_FILLED) — 1 cards" in md


def test_report_includes_expiry_section_when_d6_today(tmp_path):
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    _seed_full_card(tmp_path, "card_2018-10-26_TEST.NS", "TEST.NS",
                    "2018-10-26", "2018-10-29", "EXPIRY",
                    entry_open=99.5, exit_price=102.0, pnl_pct=2.0)
    md = generate_daily_report(tmp_path, _bd("2018-10-29"))
    assert "### D6 expirations (ACTIVE → EXPIRED) — 1 cards" in md
    assert "WIN" in md  # +2.0 → WIN label


def test_report_skips_sections_with_zero_rows(tmp_path):
    # Just a card seeded, no events on eval_date
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    _seed(tmp_path, [_make_card("card_proposed_only", "TEST.NS", "2018-10-26")])
    md = generate_daily_report(tmp_path, _bd("2018-10-30"))
    # No scan, no transitions, no expiries on 2018-10-30
    assert "## Today's scan" not in md
    assert "## Today's transitions" not in md
    assert "### Stops hit" not in md
    assert "### Targets hit" not in md
    # Open-cards section IS rendered (1 PROPOSED card)
    assert "## Open trade cards" in md


def test_report_open_cards_listed_with_correct_state(tmp_path):
    _seed(tmp_path, [_make_card("card_PROP", "AAA.NS", "2018-10-26")])
    _seed_full_card(tmp_path, "card_ACTIVE", "BBB.NS", "2018-10-26",
                    "2018-10-29", "ENTRY_ONLY", entry_open=100.0)
    md = generate_daily_report(tmp_path, _bd("2018-10-30"))
    assert "## Open trade cards" in md
    assert "AAA.NS" in md and "BBB.NS" in md
    assert "PROPOSED" in md and "ACTIVE" in md


def test_report_cumulative_cohort_aggregates_correctly(tmp_path):
    """Seed mixed cohort: 1 target, 1 stop, 1 expired-win, 1 still-active."""
    _seed_full_card(tmp_path, "card_T", "T.NS", "2018-10-26", "2018-10-29",
                    "TARGET", entry_open=99.5, exit_price=110.0, pnl_pct=10.0)
    _seed_full_card(tmp_path, "card_S", "S.NS", "2018-10-26", "2018-10-29",
                    "STOP", entry_open=99.5, exit_price=95.0, pnl_pct=-5.0)
    _seed_full_card(tmp_path, "card_E", "E.NS", "2018-10-26", "2018-10-29",
                    "EXPIRY", entry_open=99.5, exit_price=102.0, pnl_pct=2.0)
    _seed_full_card(tmp_path, "card_A", "A.NS", "2018-10-26", "2018-10-29",
                    "ENTRY_ONLY", entry_open=99.5)
    md = generate_daily_report(tmp_path, _bd("2018-10-30"))
    assert "Total trade cards proposed | 4" in md
    assert "Currently open (PROPOSED + ACTIVE) | 1" in md
    assert "Closed: target hit (HYPOTHETICAL_FILLED) | 1" in md
    assert "Closed: stop hit (HYPOTHETICAL_STOPPED) | 1" in md
    assert "Closed: expired (D6) | 1" in md
    assert "Total closed | 3" in md


def test_report_cumulative_dual_win_rate_metrics(tmp_path):
    """Both pnl>0 and pnl≥0.5% audit-comparable win rates rendered."""
    _seed_full_card(tmp_path, "card_T", "T.NS", "2018-10-26", "2018-10-29",
                    "TARGET", entry_open=99.5, exit_price=110.0, pnl_pct=10.0)
    _seed_full_card(tmp_path, "card_S", "S.NS", "2018-10-26", "2018-10-29",
                    "STOP", entry_open=99.5, exit_price=95.0, pnl_pct=-5.0)
    md = generate_daily_report(tmp_path, _bd("2018-10-30"))
    assert "Win rate (pnl > 0)" in md
    assert "Win rate (pnl ≥ 0.5%, audit-comparable)" in md
    # 1 win out of 2 closed → 50.0% on both
    assert "50.0%" in md


def test_report_handles_missing_alerts_file(tmp_path):
    """No alerts.jsonl → alerts section omitted, no error."""
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    md = generate_daily_report(tmp_path, _bd("2018-10-26"))
    assert "## Alerts" not in md


def test_report_handles_missing_lifecycle_events_file(tmp_path):
    """No lifecycle_events.jsonl → no transitions section, no error."""
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    md = generate_daily_report(tmp_path, _bd("2018-10-26"))
    assert "## Today's transitions" not in md


def test_report_calls_regenerate_read_model_by_default(tmp_path):
    """By default, generate_daily_report regenerates the read model first
    so currents reflect latest events. Verify trade_cards_current.jsonl exists
    after the call."""
    _seed(tmp_path, [_make_card("card_X", "X.NS", "2018-10-26")])
    out_path = tmp_path / "trade_cards_current.jsonl"
    assert not out_path.exists()
    generate_daily_report(tmp_path, _bd("2018-10-26"))
    assert out_path.exists()


def test_report_skip_regen_with_no_regen_flag(tmp_path):
    """regenerate_read_model=False skips Step 7. trade_cards_current.jsonl
    is NOT created if it doesn't exist."""
    _seed(tmp_path, [_make_card("card_X", "X.NS", "2018-10-26")])
    generate_daily_report(tmp_path, _bd("2018-10-26"),
                          regenerate_read_model=False)
    out_path = tmp_path / "trade_cards_current.jsonl"
    assert not out_path.exists()


def test_report_writes_to_default_path_when_no_out_specified(tmp_path):
    """default_report_path resolves to <run_dir>/reports/<eval_date>.md."""
    eval_date = _bd("2018-10-29")
    p = default_report_path(tmp_path, eval_date)
    assert p == tmp_path / REPORTS_SUBDIR / "2018-10-29.md"


def test_report_writes_to_out_path_when_specified(tmp_path):
    """generate_daily_report itself returns text; CLI handles --out."""
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    md = generate_daily_report(tmp_path, _bd("2018-10-26"))
    target = tmp_path / "custom" / "report.md"
    target.parent.mkdir(parents=True)
    target.write_text(md)
    assert target.exists()
    assert "Shadow Ops Daily Report" in target.read_text()


def test_report_data_lineage_section_includes_sha(tmp_path):
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    _seed_full_card(tmp_path, "card_X", "X.NS", "2018-10-26", "2018-10-26",
                    "ENTRY_ONLY", entry_open=100.0)
    md = generate_daily_report(tmp_path, _bd("2018-10-26"))
    assert "## Data lineage check" in md
    assert "abc123def456" in md  # git sha
    assert "lab/cache/TEST_NS.parquet" in md  # sample fill data_source


def test_report_rounds_prices_to_2_decimals_in_tables(tmp_path):
    """Prices stored at full precision (parquet float) render as 2 decimals
    in the markdown for human readability. Underlying JSON is unchanged."""
    _seed(tmp_path, [_make_scan(scan_date="2018-10-26")])
    _seed_full_card(tmp_path, "card_PRICE", "P.NS",
                    "2018-10-26", "2018-10-29", "EXPIRY",
                    entry_open=100.123456789, exit_price=1234.5678901,
                    pnl_pct=2.34)
    md = generate_daily_report(tmp_path, _bd("2018-10-29"))
    # entry_price shown as 100.12 (not 100.123456789)
    assert "100.12" in md
    assert "100.123456789" not in md
    # exit_price shown as 1234.57 (banker's rounding from 1234.5678... → 1234.57)
    assert "1234.57" in md
    assert "1234.5678901" not in md


def test_report_filters_by_logical_date_not_wallclock_timestamp(tmp_path):
    """Lifecycle event with timestamp_utc on a DIFFERENT day from its
    associated FillSimulation.fill_date should still be classified by
    fill_date in the report. Operator runs lifecycle late → wallclock
    is next UTC day → must not miss the transition."""
    card = _make_card("card_LATE", "L.NS", "2018-10-26")
    # Fill on logical 2018-10-29; LC emitted at 03:50 UTC on 2018-10-30 (late run)
    f1 = _make_fill("card_LATE", "ENTRY", "2018-10-29", 100.0, seq=1)
    f2 = _make_fill("card_LATE", "STOP", "2018-10-29", 95.0,
                    pnl_pct=-5.0, fill_logic="stop_hit_d1", seq=2)
    lc1 = _make_lc("card_LATE", "PROPOSED", "ACTIVE", "entry_t1_open",
                   f1.event_id, eval_iso="2018-10-29",
                   actual_entry_price=100.0,
                   wallclock_date="2018-10-30",  # late run
                   seq=1)
    lc2 = _make_lc("card_LATE", "ACTIVE", "HYPOTHETICAL_STOPPED",
                   "stop_hit_d1", f2.event_id, eval_iso="2018-10-29",
                   exit_day=1, exit_price=95.0, pnl_pct=-5.0,
                   wallclock_date="2018-10-30",  # late run
                   seq=2)
    _seed(tmp_path, [card, f1, lc1, f2, lc2])

    # Report for 2018-10-29 (the LOGICAL trading day) MUST include the entry
    # and stop, even though wallclock timestamp is 2018-10-30.
    md = generate_daily_report(tmp_path, _bd("2018-10-29"))
    assert "### Entries (PROPOSED → ACTIVE) — 1 cards" in md
    assert "### Stops hit (ACTIVE → HYPOTHETICAL_STOPPED) — 1 cards" in md
    # Report for 2018-10-30 (wallclock day) should NOT include them
    md2 = generate_daily_report(tmp_path, _bd("2018-10-30"))
    assert "## Today's transitions" not in md2
