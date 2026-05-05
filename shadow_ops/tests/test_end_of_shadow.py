"""Smoke tests for shadow_ops/end_of_shadow.py."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

import pytest

from shadow_ops.alerts import emit_alert
from shadow_ops.end_of_shadow import (
    HISTOGRAM_BAR_WIDTH,
    REVIEW_FILENAME,
    RULE_019,
    RULE_031,
    _binomial_se_pp,
    _strip_timestamp_line,
    generate_review,
    write_review,
)
from shadow_ops.journal import JournalWriter
from shadow_ops.read_model import regenerate_read_model
from shadow_ops.schemas import (
    CandidateSignal,
    FillSimulation,
    LifecycleEvent,
    ScanEvent,
    TradeCard,
)


# ============================================================
# Helpers — synthetic event factories
# ============================================================

def _make_scan(scan_date: str = "2018-10-26",
               regime: str = "Bear",
               sub_regime: str = "hot",
               status: str = "OK",
               n_uni: int = 73, n_post: int = 72) -> ScanEvent:
    return ScanEvent(
        event_id=f"scan_{scan_date}_001",
        event_type="scan_event",
        timestamp_utc=f"{scan_date}T16:00:00+00:00",
        scan_date=scan_date,
        regime=regime,
        sub_regime=sub_regime,
        sub_regime_inputs={"nifty_close_latest_date": scan_date},
        n_signals_universe=n_uni,
        n_signals_post_filter=n_post,
        scan_status=status,
        scan_duration_ms=4521,
        git_commit_sha="abc123" + scan_date.replace("-", ""),
        data_versions={},
    )


def _make_card(card_id: str, symbol: str = "TEST.NS",
               sector: str = "Pharma",
               scan_date: str = "2018-10-26",
               proposed_entry: float = 100.0,
               proposed_stop: float = 95.0,
               proposed_target: float = 110.0,
               rule_031_confirm: int = 0) -> TradeCard:
    return TradeCard(
        event_id=f"card_snap_{scan_date}_{symbol}_001",
        event_type="trade_card",
        timestamp_utc=f"{scan_date}T10:35:44+00:00",
        card_id=card_id,
        scan_event_id=f"scan_{scan_date}_001",
        candidate_signal_id=f"cand_{scan_date}_{symbol}_001",
        symbol=symbol,
        sector=sector,
        rule_id=RULE_019,
        rule_031_confirm=rule_031_confirm,
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


def _make_candidate_kill(card_id_seq: int = 1,
                          scan_date: str = "2018-10-26",
                          symbol: str = "HDFCBANK.NS") -> CandidateSignal:
    return CandidateSignal(
        event_id=f"cand_{scan_date}_{symbol}_{card_id_seq:03d}",
        event_type="candidate_signal",
        timestamp_utc=f"{scan_date}T10:35:43+00:00",
        scan_event_id=f"scan_{scan_date}_001",
        scan_date=scan_date,
        symbol=symbol,
        sector="Bank",
        signal="DOWN_TRI",
        regime="Bear",
        sub_regime="hot",
        rule_019_match=False,
        rule_031_match=False,
        kill_001_match=True,
        trigger_disposition="SUPPRESSED_BY_KILL_001",
        rule_features_snapshot={},
    )


def _seed_full_lifecycle(run_dir: Path, card: TradeCard,
                         eval_iso: str = "2018-10-29",
                         transition: str = "TARGET",
                         exit_price: float = 110.0,
                         pnl_pct: float = 10.0,
                         day_n: int = 4):
    """Seed PROPOSED card + ENTRY fill+lc + terminal fill+lc."""
    cid = card.card_id
    entry_fill = FillSimulation(
        event_id=f"fill_{eval_iso}_{cid}_001",
        event_type="fill_simulation",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=cid, fill_attempt_type="ENTRY", fill_date=eval_iso,
        fill_decision="FILLED", fill_price=99.5,
        ohlcv={"open": 99.5, "high": 100.5, "low": 99.0, "close": 100.0, "volume": 1_000_000},
        fill_logic_applied="audit_faithful_t1_open_unconditional",
        data_source="lab/cache/TEST_NS.parquet",
        data_source_sha256="a" * 64,
    )
    entry_lc = LifecycleEvent(
        event_id=f"lc_{eval_iso}_{cid}_001",
        event_type="lifecycle_event",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=cid, from_state="PROPOSED", to_state="ACTIVE",
        reason="entry_t1_open",
        trigger_data={"actual_entry_price": 99.5,
                      "actual_entry_date": eval_iso,
                      "fill_event_id": entry_fill.event_id},
    )
    if transition == "TARGET":
        atype, to_state, reason = "TARGET", "HYPOTHETICAL_FILLED", f"target_hit_d{day_n}"
        logic = f"target_hit_d{day_n}"
    elif transition == "STOP":
        atype, to_state, reason = "STOP", "HYPOTHETICAL_STOPPED", f"stop_hit_d{day_n}"
        logic = f"stop_hit_d{day_n}"
    elif transition == "EXPIRY":
        atype, to_state, reason = "EXPIRY", "EXPIRED", "d6_open_exit"
        sub = "win" if pnl_pct > 0.5 else ("loss" if pnl_pct < -0.5 else "flat")
        logic = f"day6_open_exit_{sub}"
        day_n = 6
    else:
        # ACTIVE only — no terminal
        w = JournalWriter(run_dir)
        w.write_event(card)
        w.write_event(entry_fill)
        w.write_event(entry_lc)
        return
    term_fill = FillSimulation(
        event_id=f"fill_{eval_iso}_{cid}_002",
        event_type="fill_simulation",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=cid, fill_attempt_type=atype, fill_date=eval_iso,
        fill_decision="FILLED", fill_price=exit_price,
        ohlcv={"open": 99.0, "high": 100.0, "low": 94.0, "close": 95.0, "volume": 1_000_000},
        fill_logic_applied=logic, pnl_pct=round(pnl_pct, 2),
        data_source="lab/cache/TEST_NS.parquet",
        data_source_sha256="b" * 64,
    )
    term_lc = LifecycleEvent(
        event_id=f"lc_{eval_iso}_{cid}_002",
        event_type="lifecycle_event",
        timestamp_utc=f"{eval_iso}T03:50:01+00:00",
        card_id=cid, from_state="ACTIVE", to_state=to_state,
        reason=reason,
        trigger_data={"exit_price": exit_price, "exit_date": eval_iso,
                      "exit_day": day_n, "pnl_pct": round(pnl_pct, 2),
                      "fill_event_id": term_fill.event_id},
    )
    w = JournalWriter(run_dir)
    for ev in [card, entry_fill, entry_lc, term_fill, term_lc]:
        w.write_event(ev)


def _read_review(run_dir: Path) -> str:
    return (run_dir / REVIEW_FILENAME).read_text()


# ============================================================
# Tests
# ============================================================

def test_review_for_empty_run_dir(tmp_path):
    """Empty run_dir → header + footer; minimal content; no errors."""
    md = generate_review(tmp_path)
    assert md.startswith("# Shadow Ops End-of-Run Review")
    assert "<!-- review_generated_at:" in md
    # No data sections
    assert "## Scan summary" not in md
    assert "## Trade card cohort summary" not in md
    assert "## Outcomes by rule" not in md
    # Recommendation flags always rendered
    assert "## Recommendation flags" in md


def test_review_for_single_scan_no_cards(tmp_path):
    """One Choppy scan, no cards (regime=Choppy → no rule matches)."""
    JournalWriter(tmp_path).write_event(
        _make_scan(scan_date="2026-05-05", regime="Choppy",
                   sub_regime="stress_mid", n_post=0))
    md = generate_review(tmp_path)
    assert "## Scan summary" in md
    assert "Total scans" in md and "1" in md
    assert "Choppy" in md
    # No cohort section, no outcomes
    assert "## Trade card cohort summary" not in md
    assert "## Outcomes by rule" not in md


def test_review_for_single_scan_with_cards(tmp_path):
    """Bear+hot scan, 2 cards (1 target hit, 1 stop hit)."""
    JournalWriter(tmp_path).write_event(_make_scan())
    c1 = _make_card("card_T", "AAA.NS", scan_date="2018-10-26")
    _seed_full_lifecycle(tmp_path, c1, "2018-10-29", "TARGET",
                         exit_price=110.0, pnl_pct=10.0, day_n=4)
    c2 = _make_card("card_S", "BBB.NS", scan_date="2018-10-26")
    _seed_full_lifecycle(tmp_path, c2, "2018-10-29", "STOP",
                         exit_price=95.0, pnl_pct=-5.0, day_n=3)
    md = generate_review(tmp_path)
    assert "## Outcomes by rule" in md
    # Two cards, both closed
    assert "rule_019 (all)" in md
    assert "## Sector distribution of outcomes" in md
    assert "## realized_R distribution" in md


def test_review_aggregates_multiple_scans(tmp_path):
    """Multiple scans across days — header derives campaign window."""
    w = JournalWriter(tmp_path)
    w.write_event(_make_scan(scan_date="2018-10-26"))
    w.write_event(_make_scan(scan_date="2018-10-29"))
    w.write_event(_make_scan(scan_date="2018-10-30"))
    md = generate_review(tmp_path)
    assert "Campaign start" in md and "2018-10-26" in md
    assert "Campaign end" in md and "2018-10-30" in md
    assert "Total trading days scanned: 3" in md


def test_review_outcomes_by_rule_table_correct(tmp_path):
    """3-row outcomes table with subset slicing."""
    JournalWriter(tmp_path).write_event(_make_scan())
    # 2 with rule_031_confirm=1 (IT sector), 3 without (other sectors)
    for i, sym in enumerate(["IT_A.NS", "IT_B.NS"]):
        c = _make_card(f"card_IT_{i}", sym, sector="IT",
                       rule_031_confirm=1)
        _seed_full_lifecycle(tmp_path, c, "2018-10-29", "TARGET",
                              exit_price=110.0, pnl_pct=10.0, day_n=4)
    for i, sym in enumerate(["P_A.NS", "P_B.NS", "P_C.NS"]):
        c = _make_card(f"card_P_{i}", sym, sector="Pharma",
                       rule_031_confirm=0)
        _seed_full_lifecycle(tmp_path, c, "2018-10-29", "STOP",
                              exit_price=95.0, pnl_pct=-5.0, day_n=3)
    md = generate_review(tmp_path)
    # All 3 row labels present
    assert "rule_019 (all)" in md
    assert "rule_019 + rule_031_confirm=1" in md
    assert "rule_019 + rule_031_confirm=0" in md
    # Per-row card counts: 5 / 2 / 3
    # We can check by parsing the rule_019 (all) row
    assert "| 5 | 5 |" in md or "rule_019 (all) | 5" in md


def test_review_sector_distribution_correct(tmp_path):
    JournalWriter(tmp_path).write_event(_make_scan())
    for i in range(3):
        c = _make_card(f"card_P_{i}", f"P{i}.NS", sector="Pharma")
        _seed_full_lifecycle(tmp_path, c, "2018-10-29", "TARGET",
                              exit_price=110.0, pnl_pct=10.0, day_n=4)
    c = _make_card("card_IT", "IT.NS", sector="IT")
    _seed_full_lifecycle(tmp_path, c, "2018-10-29", "STOP",
                          exit_price=95.0, pnl_pct=-5.0, day_n=3)
    md = generate_review(tmp_path)
    assert "## Sector distribution" in md
    # Pharma row first (3 cards), IT row second (1 card)
    pharma_idx = md.find("Pharma")
    it_idx = md.find("\n| IT |") if "\n| IT |" in md else md.find("IT |")
    assert 0 < pharma_idx < it_idx


def test_review_R_histogram_buckets_correct(tmp_path):
    """All bucket labels present; counts make sense."""
    JournalWriter(tmp_path).write_event(_make_scan())
    # One target hit (R≈+2), one stop hit (R≈-1), one D6 win (R≈+0.5)
    c1 = _make_card("card_T", "A.NS")
    _seed_full_lifecycle(tmp_path, c1, "2018-10-29", "TARGET",
                          exit_price=110.0, pnl_pct=10.0, day_n=4)
    c2 = _make_card("card_S", "B.NS")
    _seed_full_lifecycle(tmp_path, c2, "2018-10-29", "STOP",
                          exit_price=95.0, pnl_pct=-5.0, day_n=3)
    c3 = _make_card("card_E", "C.NS")
    _seed_full_lifecycle(tmp_path, c3, "2018-10-29", "EXPIRY",
                          exit_price=102.5, pnl_pct=2.5, day_n=6)
    md = generate_review(tmp_path)
    assert "## realized_R distribution" in md
    # All bucket labels present
    assert "[+1.5, +2.0]" in md
    assert "[-1.0, -0.5)" in md
    # N=3
    assert "N=3" in md


def test_review_alerts_summary_includes_acks(tmp_path):
    JournalWriter(tmp_path).write_event(_make_scan())
    a1 = emit_alert(tmp_path, "CRITICAL", "SCAN_ERROR", "daily_scan",
                    "test", logical_date="2018-10-26")
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_PARTIAL", "data_ingest",
               "warn1", logical_date="2018-10-26")
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_PARTIAL", "data_ingest",
               "warn2", logical_date="2018-10-26")
    from shadow_ops.alerts import acknowledge_alert
    acknowledge_alert(tmp_path, a1.alert_id, reason="investigated")
    md = generate_review(tmp_path)
    assert "## Alerts summary" in md
    assert "CRITICAL" in md
    assert "1 / 1" in md  # 1 of 1 critical acked
    # All critical acked → no H3 "Unacknowledged CRITICAL alerts" subsection
    # (the row label "Unacknowledged CRITICAL alerts" in flags is unrelated)
    assert "### Unacknowledged CRITICAL alerts" not in md


def test_review_data_quality_issues_aggregated(tmp_path):
    JournalWriter(tmp_path).write_event(
        _make_scan(scan_date="2018-10-26", status="PARTIAL"))
    JournalWriter(tmp_path).write_event(_make_scan(scan_date="2018-10-29"))
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE", "data_ingest",
               "two failed",
               context={"failed_symbols": [["LTIM.NS", "404"], ["X.NS", "timeout"]]},
               logical_date="2018-10-29")
    emit_alert(tmp_path, "WARNING", "DATA_INGEST_FAILURE", "data_ingest",
               "again",
               context={"failed_symbols": [["LTIM.NS", "404"]]},
               logical_date="2018-10-30")
    md = generate_review(tmp_path)
    assert "## Data quality issues" in md
    assert "Scans with PARTIAL status" in md and "1" in md
    # LTIM.NS appears twice in DATA_INGEST_FAILURE contexts
    assert "LTIM.NS (2)" in md


def test_review_audit_comparison_uses_unified_rules_json(tmp_path):
    """Audit expected_wr=71% is pulled from real rules JSON."""
    JournalWriter(tmp_path).write_event(_make_scan())
    c = _make_card("card_T", "A.NS")
    _seed_full_lifecycle(tmp_path, c, "2018-10-29", "TARGET",
                          exit_price=110.0, pnl_pct=10.0, day_n=4)
    md = generate_review(tmp_path)
    # rule_019's audit expected_wr is 71.0% from real JSON
    assert "71.0%" in md
    # n_audit = 240 from evidence.n
    assert "240" in md


def test_review_recommendation_flags_correct(tmp_path):
    """Single scan, low card count → 'below threshold' labels."""
    JournalWriter(tmp_path).write_event(_make_scan())
    # 1 card only → below cards threshold
    c = _make_card("card_T", "A.NS")
    _seed_full_lifecycle(tmp_path, c, "2018-10-29", "TARGET",
                          exit_price=110.0, pnl_pct=10.0, day_n=4)
    md = generate_review(tmp_path)
    assert "## Recommendation flags" in md
    assert "below threshold" in md  # trading_days = 1 and total cards = 1
    assert "clean" in md             # 0 open + 0 unacked critical


def test_review_idempotent_modulo_timestamp(tmp_path):
    """Run twice → bodies (excluding timestamp comment) byte-identical."""
    JournalWriter(tmp_path).write_event(_make_scan())
    c = _make_card("card_T", "A.NS")
    _seed_full_lifecycle(tmp_path, c, "2018-10-29", "TARGET",
                          exit_price=110.0, pnl_pct=10.0, day_n=4)
    md1 = generate_review(tmp_path)
    md2 = generate_review(tmp_path)
    body1 = _strip_timestamp_line(md1)
    body2 = _strip_timestamp_line(md2)
    assert body1 == body2
    # Full SHA may differ (timestamp); body SHA must match
    assert (hashlib.sha256(body1.encode()).hexdigest()
            == hashlib.sha256(body2.encode()).hexdigest())


def test_review_handles_missing_run_config(tmp_path):
    """run_config.json absent → 'not present' in metadata; no error."""
    JournalWriter(tmp_path).write_event(_make_scan())
    md = generate_review(tmp_path)
    assert "run_config.json: not present" in md


def test_review_writes_to_default_path_when_no_out(tmp_path):
    JournalWriter(tmp_path).write_event(_make_scan())
    res = write_review(tmp_path)
    assert Path(res.review_path) == tmp_path / REVIEW_FILENAME
    assert (tmp_path / REVIEW_FILENAME).exists()
    sidecar = tmp_path / (REVIEW_FILENAME + ".checksum")
    assert sidecar.exists()
    assert sidecar.read_text().strip() == res.review_sha256


# ============================================================
# CC additions
# ============================================================

def test_review_includes_open_cards_banner_when_open_gt_zero(tmp_path):
    JournalWriter(tmp_path).write_event(_make_scan())
    # ACTIVE-only card (no terminal transition)
    c = _make_card("card_OPEN", "A.NS")
    _seed_full_lifecycle(tmp_path, c, "2018-10-29", "ACTIVE_ONLY")
    md = generate_review(tmp_path)
    assert "⚠ 1 cards still open" in md


def test_review_omits_open_cards_banner_when_zero_open(tmp_path):
    JournalWriter(tmp_path).write_event(_make_scan())
    c = _make_card("card_T", "A.NS")
    _seed_full_lifecycle(tmp_path, c, "2018-10-29", "TARGET",
                          exit_price=110.0, pnl_pct=10.0, day_n=4)
    md = generate_review(tmp_path)
    # Banner uses ⚠ glyph; absence of that glyph means no banner
    assert "⚠" not in md
    assert "review reflects partial cohort" not in md


def test_review_kill_001_section_separated_from_outcomes(tmp_path):
    """kill_001 suppressions render as a separate section, not in the
    outcomes-by-rule table (which only covers rule_019 cohort)."""
    JournalWriter(tmp_path).write_event(_make_scan())
    # Seed 2 kill_001 candidates (no trade card)
    JournalWriter(tmp_path).write_event(_make_candidate_kill(1, symbol="HDFCBANK.NS"))
    JournalWriter(tmp_path).write_event(_make_candidate_kill(2, symbol="ICICIBANK.NS"))
    md = generate_review(tmp_path)
    assert "## kill_001 suppressions" in md
    assert "Total suppressions across run: **2**" in md
    # Should NOT appear in outcomes table
    outcomes_section = md.split("## Outcomes by rule")[1].split("##")[0] if "## Outcomes by rule" in md else ""
    assert "kill_001" not in outcomes_section


def test_review_binomial_se_pp_computation_matches_formula(tmp_path):
    """SE = sqrt(p*(1-p)/n)*100. Compare to manual computation."""
    p_audit = 0.71
    n = 71
    expected_se = math.sqrt(p_audit * (1 - p_audit) / n) * 100
    actual = _binomial_se_pp(p_audit, n)
    assert actual == pytest.approx(expected_se, abs=1e-9)
    # Edge cases
    assert _binomial_se_pp(None, 71) is None
    assert _binomial_se_pp(0.71, 0) is None
    assert _binomial_se_pp(0.71, -1) is None
    assert _binomial_se_pp(1.5, 71) is None  # invalid p


def test_review_writes_checksum_sidecar(tmp_path):
    """Sidecar SHA matches actual file content."""
    JournalWriter(tmp_path).write_event(_make_scan())
    res = write_review(tmp_path)
    review_bytes = (tmp_path / REVIEW_FILENAME).read_bytes()
    expected_sha = hashlib.sha256(review_bytes).hexdigest()
    sidecar_sha = (tmp_path / (REVIEW_FILENAME + ".checksum")).read_text().strip()
    assert expected_sha == sidecar_sha == res.review_sha256
