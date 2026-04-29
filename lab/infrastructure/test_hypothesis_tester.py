"""
MS-4 unit tests — hypothesis_tester correctness verification.

Per PROMOTION_PROTOCOL.md Gate 3 thresholds: each tier S/A/B threshold
must fire correctly on synthetic cohorts with known WR/n.

ALL TESTS MUST PASS before MS-4 marked complete (T4 tripwire).

Run:
    .venv/bin/python -m pytest lab/infrastructure/test_hypothesis_tester.py -v
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

# Path setup — allow relative import of hypothesis_tester
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hypothesis_tester import (  # noqa: E402
    compute_cohort_stats,
    train_test_split,
    evaluate_boost_tier,
    evaluate_kill_tier,
    evaluate_hypothesis,
    filter_cohort,
    wilson_lower_bound_95,
    binomial_p_value_vs_50,
)


# ── Helper: synthetic signals_df builder ─────────────────────────────

def _build_synthetic_signals(n_win: int, n_loss: int, n_flat: int = 0,
                              n_open: int = 0,
                              signal: str = "UP_TRI",
                              sector: str = "Bank",
                              regime: str = "Choppy",
                              start_date: str = "2020-01-01") -> pd.DataFrame:
    """Build a synthetic signals DataFrame with controlled outcome counts."""
    rows = []
    base = pd.Timestamp(start_date)
    idx = 0
    for _ in range(n_win):
        rows.append({"scan_date": (base + pd.Timedelta(days=idx)).date().isoformat(),
                      "symbol": f"S{idx}", "signal": signal, "sector": sector,
                      "regime": regime, "outcome": "DAY6_WIN"})
        idx += 1
    for _ in range(n_loss):
        rows.append({"scan_date": (base + pd.Timedelta(days=idx)).date().isoformat(),
                      "symbol": f"S{idx}", "signal": signal, "sector": sector,
                      "regime": regime, "outcome": "DAY6_LOSS"})
        idx += 1
    for _ in range(n_flat):
        rows.append({"scan_date": (base + pd.Timedelta(days=idx)).date().isoformat(),
                      "symbol": f"S{idx}", "signal": signal, "sector": sector,
                      "regime": regime, "outcome": "DAY6_FLAT"})
        idx += 1
    for _ in range(n_open):
        rows.append({"scan_date": (base + pd.Timedelta(days=idx)).date().isoformat(),
                      "symbol": f"S{idx}", "signal": signal, "sector": sector,
                      "regime": regime, "outcome": "OPEN"})
        idx += 1
    return pd.DataFrame(rows)


# ═════════════════════════════════════════════════════════════════════
# Group 1: cohort_stats (3 tests)
# ═════════════════════════════════════════════════════════════════════

def test_cohort_stats_empty():
    """Empty cohort returns zero counts; wr None."""
    df = pd.DataFrame()
    stats = compute_cohort_stats(df, cohort_filter={})
    assert stats["n_total"] == 0
    assert stats["wr_excl_flat"] is None
    assert stats["wilson_lower_95"] is None


def test_cohort_stats_single_signal():
    """Single WIN cohort: WR=1.0; n_resolved=1; n_win=1."""
    df = _build_synthetic_signals(n_win=1, n_loss=0)
    stats = compute_cohort_stats(df, cohort_filter={})
    assert stats["n_total"] == 1
    assert stats["n_win"] == 1
    assert stats["n_loss"] == 0
    assert stats["wr_excl_flat"] == 1.0


def test_cohort_stats_large_cohort():
    """Large cohort 70W/30L/5F/3O: n_total=108; WR=0.7; flats/opens excluded from wr."""
    df = _build_synthetic_signals(n_win=70, n_loss=30, n_flat=5, n_open=3)
    stats = compute_cohort_stats(df, cohort_filter={})
    assert stats["n_total"] == 108
    assert stats["n_win"] == 70
    assert stats["n_loss"] == 30
    assert stats["n_flat"] == 5
    assert stats["n_open"] == 3
    assert stats["n_resolved"] == 105
    assert stats["wr_excl_flat"] == 0.7  # 70 / (70 + 30)
    assert stats["wilson_lower_95"] is not None
    assert 0.6 < stats["wilson_lower_95"] < 0.75  # sanity range


# ═════════════════════════════════════════════════════════════════════
# Group 2: train_test_split (2 tests)
# ═════════════════════════════════════════════════════════════════════

def test_train_test_split_chronological():
    """Verify chronological split + row count preservation."""
    rows = []
    # 5 rows in 2022 (train), 3 in 2024 (test)
    for i in range(5):
        rows.append({"scan_date": f"2022-0{i + 1}-01", "symbol": f"A{i}",
                      "signal": "UP_TRI", "outcome": "DAY6_WIN"})
    for i in range(3):
        rows.append({"scan_date": f"2024-0{i + 1}-01", "symbol": f"B{i}",
                      "signal": "UP_TRI", "outcome": "DAY6_LOSS"})
    df = pd.DataFrame(rows)

    train, test = train_test_split(df, split_date="2023-01-01")
    assert len(train) == 5
    assert len(test) == 3
    assert all(pd.to_datetime(train["scan_date"]) < pd.Timestamp("2023-01-01"))
    assert all(pd.to_datetime(test["scan_date"]) >= pd.Timestamp("2023-01-01"))


def test_train_test_split_empty_input():
    """Empty input returns empty splits; no exceptions."""
    df = pd.DataFrame()
    train, test = train_test_split(df)
    assert train.empty and test.empty


# ═════════════════════════════════════════════════════════════════════
# Group 3: evaluate_boost_tier (5 tests — one per tier + 2 reject cases)
# ═════════════════════════════════════════════════════════════════════

def test_boost_tier_S():
    """Tier S boost: train WR 0.80 n=120; test WR 0.70 n=40; drift=0.10. Lock S."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=96, n_loss=24), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=28, n_loss=12), cohort_filter={})
    # Verify inputs match expected
    assert train["wr_excl_flat"] == 0.8
    assert test["wr_excl_flat"] == 0.7
    # Drift = 0.10; Tier S allows < 0.10 (strict), so this should fail S → A
    tier = evaluate_boost_tier(train, test)
    # WR delta exactly 0.10 fails Tier S strict drift; should fall to Tier A
    assert tier == "A", f"Expected A (drift=0.10 fails Tier S strict <0.10); got {tier}"


def test_boost_tier_S_strict():
    """Tier S boost STRICT: drift < 0.10 (not ≤). Train 0.78 n=120 / Test 0.71 n=40 → drift=0.07."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=94, n_loss=26), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=29, n_loss=12), cohort_filter={})
    # train_wr ≈ 0.7833; test_wr ≈ 0.7073 ; drift ≈ 0.076; both pass S thresholds
    assert train["wr_excl_flat"] >= 0.75
    assert test["wr_excl_flat"] >= 0.65
    assert (train["n_win"] + train["n_loss"]) >= 100
    assert (test["n_win"] + test["n_loss"]) >= 30
    drift = abs(train["wr_excl_flat"] - test["wr_excl_flat"])
    assert drift < 0.10
    tier = evaluate_boost_tier(train, test)
    assert tier == "S", f"Expected S; got {tier}"


def test_boost_tier_A():
    """Tier A boost: train 0.68 n=60 / test 0.58 n=25 / drift=0.10. Lock A."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=41, n_loss=19), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=15, n_loss=11), cohort_filter={})
    tier = evaluate_boost_tier(train, test)
    assert tier == "A", f"Expected A; got {tier}"


def test_boost_tier_B():
    """Tier B boost: train 0.62 n=35 / test 0.52 n=18 / drift=0.10. Lock B."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=22, n_loss=13), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=9, n_loss=8), cohort_filter={})
    tier = evaluate_boost_tier(train, test)
    assert tier == "B", f"Expected B; got {tier}"


def test_boost_reject_low_train_wr():
    """REJECT boost: train 0.55 fails Tier B floor (≥0.60)."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=22, n_loss=18), cohort_filter={})  # 0.55
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=12, n_loss=8), cohort_filter={})  # 0.60
    tier = evaluate_boost_tier(train, test)
    assert tier == "REJECT", f"Expected REJECT (low train_wr); got {tier}"


def test_boost_reject_drift_too_large():
    """REJECT boost: train 0.72 / test 0.50 → drift=0.22, fails all tiers (max=0.20)."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=72, n_loss=28), cohort_filter={})  # 0.72
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=15, n_loss=15), cohort_filter={})  # 0.50
    tier = evaluate_boost_tier(train, test)
    assert tier == "REJECT", f"Expected REJECT (drift=0.22 > all tier max); got {tier}"


def test_boost_reject_insufficient_n():
    """REJECT boost: train n=20 fails Tier B floor (≥30)."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=14, n_loss=6), cohort_filter={})  # 0.70 but n=20
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=10, n_loss=8), cohort_filter={})  # 0.55 n=18
    tier = evaluate_boost_tier(train, test)
    assert tier == "REJECT", f"Expected REJECT (train n<30); got {tier}"


def test_boost_tier_S_wilson_floor():
    """Tier S BOOST fails Wilson gate (0.55 < 0.60); falls to Tier A which passes
    (Wilson 0.55 ≥ 0.50 + p 0.04 < 0.05 + thresholds A all met)."""
    train_stats = {
        "wr_excl_flat": 0.76, "n_win": 76, "n_loss": 24, "n_flat": 0,
        "wilson_lower_95": 0.55,  # < 0.60 → S Wilson gate fails
        "p_value_vs_50": 0.04,
    }
    test_stats = {
        "wr_excl_flat": 0.66, "n_win": 20, "n_loss": 10, "n_flat": 0,
        "wilson_lower_95": 0.50, "p_value_vs_50": 0.04,
    }
    tier = evaluate_boost_tier(train_stats, test_stats)
    # S fails Wilson; A check: train_wr 0.76≥0.65 ✓, train_n 100≥50 ✓,
    # test_wr 0.66≥0.55 ✓, test_n 30≥20 ✓, drift 0.10<0.15 ✓,
    # Wilson 0.55≥0.50 ✓, p 0.04<0.05 ✓ → A
    assert tier == "A", f"Expected A (S fails Wilson; A passes); got {tier}"


def test_boost_tier_S_p_value_floor():
    """Tier S BOOST fails p-value gate (0.08 ≥ 0.05); A also fails p; falls to
    Tier B which has no Wilson/p gate."""
    train_stats = {
        "wr_excl_flat": 0.76, "n_win": 76, "n_loss": 24, "n_flat": 0,
        "wilson_lower_95": 0.65,
        "p_value_vs_50": 0.08,  # ≥ 0.05 → S+A p gate fail
    }
    test_stats = {
        "wr_excl_flat": 0.66, "n_win": 20, "n_loss": 10, "n_flat": 0,
        "wilson_lower_95": 0.55, "p_value_vs_50": 0.08,
    }
    tier = evaluate_boost_tier(train_stats, test_stats)
    # S+A fail p; B no p gate: train_wr 0.76≥0.60 ✓, train_n 100≥30 ✓,
    # test_wr 0.66≥0.50 ✓, test_n 30≥15 ✓, drift 0.10<0.20 ✓ → B
    assert tier == "B", f"Expected B (S+A fail p; B has no p gate); got {tier}"


def test_boost_tier_A_wilson_floor():
    """Tier A BOOST fails Wilson gate (0.45 < 0.50); falls to Tier B which has
    no Wilson gate."""
    train_stats = {
        "wr_excl_flat": 0.66, "n_win": 33, "n_loss": 17, "n_flat": 0,
        "wilson_lower_95": 0.45,  # < 0.50 → A Wilson gate fails
        "p_value_vs_50": 0.04,
    }
    test_stats = {
        "wr_excl_flat": 0.56, "n_win": 14, "n_loss": 11, "n_flat": 0,
        "wilson_lower_95": 0.40, "p_value_vs_50": 0.04,
    }
    tier = evaluate_boost_tier(train_stats, test_stats)
    # S fails train_wr (0.66<0.75); A fails Wilson (0.45<0.50); B no Wilson:
    # train_wr 0.66≥0.60 ✓, n 50≥30 ✓, test_wr 0.56≥0.50 ✓,
    # test_n 25≥15 ✓, drift 0.10<0.20 ✓ → B
    assert tier == "B", f"Expected B (A fails Wilson; B has no Wilson gate); got {tier}"


# ═════════════════════════════════════════════════════════════════════
# Group 4: evaluate_kill_tier (5 tests — one per tier + 2 reject cases)
# ═════════════════════════════════════════════════════════════════════

def test_kill_tier_S():
    """Tier S kill: train WR 0.20 n=110 / test WR 0.27 n=35 / drift=0.07. Lock S."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=22, n_loss=88), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=10, n_loss=27), cohort_filter={})
    # train_wr=0.20 ≤ 0.25 ✓; test_wr ≈ 0.27 ≤ 0.30 ✓; drift ≈ 0.07 < 0.10 ✓
    tier = evaluate_kill_tier(train, test)
    assert tier == "S", f"Expected S; got {tier}"


def test_kill_tier_A():
    """Tier A kill: train 0.30 n=60 / test 0.37 n=25 / drift=0.07. Lock A."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=18, n_loss=42), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=10, n_loss=17), cohort_filter={})
    tier = evaluate_kill_tier(train, test)
    assert tier == "A", f"Expected A; got {tier}"


def test_kill_tier_B():
    """Tier B kill: train 0.38 n=40 / test 0.42 n=18 / drift=0.04. Lock B."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=15, n_loss=25), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=8, n_loss=11), cohort_filter={})
    tier = evaluate_kill_tier(train, test)
    assert tier == "B", f"Expected B; got {tier}"


def test_kill_reject_high_train_wr():
    """REJECT kill: train 0.45 fails Tier B ceiling (≤0.40)."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=20, n_loss=24), cohort_filter={})  # 0.45
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=8, n_loss=12), cohort_filter={})  # 0.40
    tier = evaluate_kill_tier(train, test)
    assert tier == "REJECT", f"Expected REJECT (train_wr 0.45 > 0.40 ceiling); got {tier}"


def test_kill_reject_drift_too_large():
    """REJECT kill: train 0.20 / test 0.45 → drift=0.25 > all tier max."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=22, n_loss=88), cohort_filter={})  # 0.20
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=18, n_loss=22), cohort_filter={})  # 0.45
    tier = evaluate_kill_tier(train, test)
    assert tier == "REJECT", f"Expected REJECT (drift=0.25 > all tier max); got {tier}"


def test_kill_reject_insufficient_n():
    """REJECT kill: test n=10 fails Tier B floor (≥15)."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=10, n_loss=20), cohort_filter={})  # 0.33 n=30
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=4, n_loss=6), cohort_filter={})  # 0.40 n=10
    tier = evaluate_kill_tier(train, test)
    assert tier == "REJECT", f"Expected REJECT (test n<15); got {tier}"


# ═════════════════════════════════════════════════════════════════════
# Group 5: filter_cohort + Wilson + p-value (5 tests)
# ═════════════════════════════════════════════════════════════════════

def test_filter_cohort_signal_match():
    """Cohort filter on signal column extracts only matching rows."""
    df = pd.concat([
        _build_synthetic_signals(n_win=5, n_loss=0, signal="UP_TRI"),
        _build_synthetic_signals(n_win=3, n_loss=0, signal="DOWN_TRI",
                                  start_date="2021-01-01"),
    ])
    filtered = filter_cohort(df, {"signal": "UP_TRI"})
    assert len(filtered) == 5
    assert (filtered["signal"] == "UP_TRI").all()


def test_filter_cohort_multiple_keys():
    """Multi-key filter: signal + sector + regime."""
    df = pd.concat([
        _build_synthetic_signals(n_win=5, n_loss=0, signal="UP_TRI",
                                  sector="Bank", regime="Choppy"),
        _build_synthetic_signals(n_win=4, n_loss=0, signal="UP_TRI",
                                  sector="Pharma", regime="Choppy",
                                  start_date="2021-01-01"),
    ])
    filtered = filter_cohort(df, {"signal": "UP_TRI", "sector": "Bank",
                                    "regime": "Choppy"})
    assert len(filtered) == 5
    assert (filtered["sector"] == "Bank").all()


def test_filter_cohort_none_wildcard():
    """None values in cohort_filter are wildcards (no filter applied on that key)."""
    df = pd.concat([
        _build_synthetic_signals(n_win=5, n_loss=0, signal="UP_TRI",
                                  sector="Bank"),
        _build_synthetic_signals(n_win=3, n_loss=0, signal="UP_TRI",
                                  sector="Pharma", start_date="2021-01-01"),
    ])
    filtered = filter_cohort(df, {"signal": "UP_TRI", "sector": None})
    assert len(filtered) == 8


def test_wilson_lower_bound_known_values():
    """Wilson 95% lower for 7W/26L (kill_002 cohort): ~0.27 raw → Wilson lower ~0.13."""
    n = 26
    wins = 7
    wilson = wilson_lower_bound_95(wins, n)
    # Expected approx 0.13 for 7/26 with Wilson 95% lower
    assert 0.10 < wilson < 0.20, f"Wilson lower for 7/26 should be ~0.13; got {wilson}"


def test_p_value_significant_vs_50():
    """p-value should be significant (< 0.05) for 70W/30L (clear edge above 50%)."""
    p = binomial_p_value_vs_50(70, 100)
    assert p < 0.05, f"Expected p < 0.05 for 70/100; got {p}"


# ═════════════════════════════════════════════════════════════════════
# Group 6: test_hypothesis end-to-end (2 tests)
# ═════════════════════════════════════════════════════════════════════

def test_hypothesis_end_to_end_boost():
    """End-to-end: boost hypothesis on synthetic train+test split passes Tier A."""
    train_rows = []
    for i in range(60):
        train_rows.append({
            "scan_date": f"2020-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"X{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Bear",
            "outcome": "DAY6_WIN" if i < 42 else "DAY6_LOSS",  # 42/60 = 0.70
        })
    test_rows = []
    for i in range(25):
        test_rows.append({
            "scan_date": f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"Y{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Bear",
            "outcome": "DAY6_WIN" if i < 15 else "DAY6_LOSS",  # 15/25 = 0.60
        })
    df = pd.DataFrame(train_rows + test_rows)
    result = evaluate_hypothesis(df, {"signal": "UP_TRI", "sector": "Bank",
                                    "regime": "Bear"},
                              hypothesis_type="BOOST")
    # train WR=0.70 n=60; test WR=0.60 n=25; drift=0.10 — Tier A criteria
    assert result["tier"] == "A", (
        f"Expected Tier A; got {result['tier']}; "
        f"train={result['train_stats']}; test={result['test_stats']}")


def test_hypothesis_end_to_end_kill():
    """End-to-end: kill hypothesis on synthetic train+test split passes Tier A."""
    train_rows = []
    for i in range(60):
        train_rows.append({
            "scan_date": f"2020-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"X{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Choppy",
            "outcome": "DAY6_WIN" if i < 18 else "DAY6_LOSS",  # 18/60 = 0.30
        })
    test_rows = []
    for i in range(25):
        test_rows.append({
            "scan_date": f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"Y{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Choppy",
            "outcome": "DAY6_WIN" if i < 9 else "DAY6_LOSS",  # 9/25 = 0.36
        })
    df = pd.DataFrame(train_rows + test_rows)
    result = evaluate_hypothesis(df, {"signal": "UP_TRI", "sector": "Bank",
                                    "regime": "Choppy"},
                              hypothesis_type="KILL")
    # train WR=0.30 n=60; test WR=0.36 n=25; drift=0.06 — Tier A KILL criteria
    assert result["tier"] == "A", (
        f"Expected Tier A; got {result['tier']}; "
        f"train={result['train_stats']}; test={result['test_stats']}")


# ═════════════════════════════════════════════════════════════════════
# Group 7: FILTER routing (BLOCK 2 — filter_parent_type disambiguation)
# ═════════════════════════════════════════════════════════════════════

def test_filter_with_kill_parent():
    """FILTER hypothesis on a kill-parent sub-cohort routes to evaluate_kill_tier.
    Sub-cohort has low WR (kill-tier-shaped); BOOST evaluator would REJECT
    while KILL evaluator returns Tier A."""
    train_rows = []
    for i in range(60):
        train_rows.append({
            "scan_date": f"2020-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"X{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Choppy", "subsector": "PSU",
            "outcome": "DAY6_WIN" if i < 18 else "DAY6_LOSS",  # 18/60 = 0.30
        })
    test_rows = []
    for i in range(25):
        test_rows.append({
            "scan_date": f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"Y{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Choppy", "subsector": "PSU",
            "outcome": "DAY6_WIN" if i < 9 else "DAY6_LOSS",  # 9/25 = 0.36
        })
    df = pd.DataFrame(train_rows + test_rows)
    result = evaluate_hypothesis(
        df, {"signal": "UP_TRI", "sector": "Bank", "regime": "Choppy",
             "subsector": "PSU"},
        hypothesis_type="FILTER", filter_parent_type="KILL")
    # train_wr=0.30 ≤ 0.35 ✓, n=60 ≥ 50 ✓; test_wr=0.36 ≤ 0.40 ✓, n=25 ≥ 20 ✓;
    # drift=0.06 < 0.15 ✓ → KILL Tier A
    assert result["tier"] == "A", (
        f"Expected Tier A via KILL evaluator; got {result['tier']}; "
        f"train={result['train_stats']}; test={result['test_stats']}")
    assert result["filter_parent_type"] == "KILL"


def test_filter_default_backward_compat():
    """FILTER without filter_parent_type routes to BOOST (current behavior).
    Verifies existing callers passing only hypothesis_type='FILTER' still work."""
    train_rows = []
    for i in range(60):
        train_rows.append({
            "scan_date": f"2020-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"X{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Bull",
            "outcome": "DAY6_WIN" if i < 42 else "DAY6_LOSS",  # 42/60 = 0.70
        })
    test_rows = []
    for i in range(25):
        test_rows.append({
            "scan_date": f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
            "symbol": f"Y{i}", "signal": "UP_TRI", "sector": "Bank",
            "regime": "Bull",
            "outcome": "DAY6_WIN" if i < 15 else "DAY6_LOSS",  # 15/25 = 0.60
        })
    df = pd.DataFrame(train_rows + test_rows)
    # No filter_parent_type → defaults to None → BOOST evaluator (backward-compat)
    result = evaluate_hypothesis(
        df, {"signal": "UP_TRI", "sector": "Bank", "regime": "Bull"},
        hypothesis_type="FILTER")
    # Boost-shaped: train_wr=0.70 n=60; test_wr=0.60 n=25; drift=0.10 → Tier A
    assert result["tier"] == "A", (
        f"Expected Tier A via BOOST evaluator (backward-compat); got {result['tier']}; "
        f"train={result['train_stats']}; test={result['test_stats']}")
    assert result["filter_parent_type"] is None


# ═════════════════════════════════════════════════════════════════════
# Group 8: Tier drift-boundary edge cases (BLOCK 3)
# Strict-< behavior: drift exactly at threshold must FAIL that tier.
# ═════════════════════════════════════════════════════════════════════

def test_boost_tier_A_to_B_drift_boundary():
    """Boost: drift=0.15 exactly fails Tier A (strict <0.15); falls to Tier B.
    train 42/60 = 0.70; test 11/20 = 0.55; drift = abs(0.70 - 0.55) = 0.15."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=42, n_loss=18), cohort_filter={})  # 0.70 n=60
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=11, n_loss=9), cohort_filter={})   # 0.55 n=20
    assert train["wr_excl_flat"] == 0.70
    assert test["wr_excl_flat"] == 0.55
    # Wrap in round() to match production drift rounding semantics; raw abs(0.7 - 0.55)
    # = 0.15000000000000002 due to IEEE-754 FP noise (won't equal 0.15 without rounding).
    assert round(abs(train["wr_excl_flat"] - test["wr_excl_flat"]), 4) == 0.15
    tier = evaluate_boost_tier(train, test)
    # Tier S fails (train_wr<0.75); Tier A fails drift<0.15 strict;
    # Tier B: train_wr 0.70≥0.60, n 60≥30, test_wr 0.55≥0.50, test_n 20≥15,
    # drift 0.15<0.20 → B
    assert tier == "B", f"Expected B (drift=0.15 fails A strict <); got {tier}"


def test_boost_tier_B_to_REJECT_drift_boundary():
    """Boost: drift=0.20 exactly fails Tier B (strict <0.20) → REJECT.
    train 21/30 = 0.70; test 10/20 = 0.50; drift = abs(0.70 - 0.50) = 0.20."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=21, n_loss=9), cohort_filter={})   # 0.70 n=30
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=10, n_loss=10), cohort_filter={})  # 0.50 n=20
    assert train["wr_excl_flat"] == 0.70
    assert test["wr_excl_flat"] == 0.50
    # Wrap in round(); raw abs(0.7 - 0.5) = 0.19999999999999996 due to IEEE-754 FP noise.
    assert round(abs(train["wr_excl_flat"] - test["wr_excl_flat"]), 4) == 0.20
    tier = evaluate_boost_tier(train, test)
    # Tier B fails drift<0.20 strict → REJECT
    assert tier == "REJECT", f"Expected REJECT (drift=0.20 fails B strict <); got {tier}"


def test_kill_tier_S_drift_boundary():
    """Kill: drift=0.10 exactly fails Tier S (strict <0.10); falls to Tier A.
    train 20/100 = 0.20; test 9/30 = 0.30; drift = abs(0.20 - 0.30) = 0.10."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=20, n_loss=80), cohort_filter={})  # 0.20 n=100
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=9, n_loss=21), cohort_filter={})   # 0.30 n=30
    assert train["wr_excl_flat"] == 0.20
    assert test["wr_excl_flat"] == 0.30
    # Wrap in round(); raw abs(0.2 - 0.3) = 0.09999999999999998 due to IEEE-754 FP noise.
    assert round(abs(train["wr_excl_flat"] - test["wr_excl_flat"]), 4) == 0.10
    tier = evaluate_kill_tier(train, test)
    # Tier S fails drift<0.10 strict; Tier A: train_wr 0.20≤0.35, n 100≥50,
    # test_wr 0.30≤0.40, test_n 30≥20, drift 0.10<0.15 → A
    assert tier == "A", f"Expected A (drift=0.10 fails S strict <); got {tier}"


def test_kill_tier_A_to_B_drift_boundary():
    """Kill: drift=0.15 exactly fails Tier A (strict <0.15); falls to Tier B.
    train 15/50 = 0.30; test 9/20 = 0.45; drift = abs(0.30 - 0.45) = 0.15."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=15, n_loss=35), cohort_filter={})  # 0.30 n=50
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=9, n_loss=11), cohort_filter={})   # 0.45 n=20
    assert train["wr_excl_flat"] == 0.30
    assert test["wr_excl_flat"] == 0.45
    # Wrap in round(); raw abs(0.3 - 0.45) = 0.15000000000000002 due to IEEE-754 FP noise.
    assert round(abs(train["wr_excl_flat"] - test["wr_excl_flat"]), 4) == 0.15
    tier = evaluate_kill_tier(train, test)
    # Tier S fails (train_wr 0.30>0.25); Tier A fails drift<0.15 strict;
    # Tier B: train_wr 0.30≤0.40, n 50≥30, test_wr 0.45≤0.45, test_n 20≥15,
    # drift 0.15<0.20 → B
    assert tier == "B", f"Expected B (drift=0.15 fails A strict <); got {tier}"


def test_kill_tier_B_to_REJECT_drift_boundary():
    """Kill: drift=0.20 exactly fails Tier B (strict <0.20) → REJECT.
    train 25/100 = 0.25; test 9/20 = 0.45; drift = abs(0.25 - 0.45) = 0.20."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=25, n_loss=75), cohort_filter={})  # 0.25 n=100
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=9, n_loss=11), cohort_filter={})   # 0.45 n=20
    assert train["wr_excl_flat"] == 0.25
    assert test["wr_excl_flat"] == 0.45
    # Wrap in round() for symmetry with other boundary tests (raw abs(0.25 - 0.45)
    # happens to be exact 0.20 in this case, but rounding is consistent practice).
    assert round(abs(train["wr_excl_flat"] - test["wr_excl_flat"]), 4) == 0.20
    tier = evaluate_kill_tier(train, test)
    # Tier B fails drift<0.20 strict → REJECT
    assert tier == "REJECT", f"Expected REJECT (drift=0.20 fails B strict <); got {tier}"


# ═════════════════════════════════════════════════════════════════════
# Group 9: Extreme-WR + degenerate-cohort edge cases (BLOCK 3)
# ═════════════════════════════════════════════════════════════════════

def test_extreme_wr_zero():
    """All-loss cohort (wr=0.0): Wilson lower ≈ 0.0; p-value < 0.05 (n=20)."""
    df = _build_synthetic_signals(n_win=0, n_loss=20)
    stats = compute_cohort_stats(df, cohort_filter={})
    assert stats["wr_excl_flat"] == 0.0
    assert stats["wilson_lower_95"] is not None
    # Wilson lower for 0/20 is mathematically ≥ 0 (negative possible due to rounding); should be ≈ 0
    assert stats["wilson_lower_95"] <= 0.01, f"Wilson for 0/20 should ≈ 0; got {stats['wilson_lower_95']}"
    assert stats["p_value_vs_50"] is not None
    assert stats["p_value_vs_50"] < 0.05, f"p for 0/20 should be highly significant; got {stats['p_value_vs_50']}"


def test_extreme_wr_one_hundred():
    """All-win cohort (wr=1.0): Wilson lower < 1.0 (binomial CI never reaches 1); p-value < 0.05."""
    df = _build_synthetic_signals(n_win=20, n_loss=0)
    stats = compute_cohort_stats(df, cohort_filter={})
    assert stats["wr_excl_flat"] == 1.0
    assert stats["wilson_lower_95"] is not None
    # Wilson lower for 20/20 ≈ 0.84 (below 1.0)
    assert 0.5 < stats["wilson_lower_95"] < 1.0, f"Wilson for 20/20 should be ~0.84; got {stats['wilson_lower_95']}"
    assert stats["p_value_vs_50"] is not None
    assert stats["p_value_vs_50"] < 0.05, f"p for 20/20 should be highly significant; got {stats['p_value_vs_50']}"


def test_all_flat_cohort():
    """20 signals all DAY6_FLAT: wr_excl_flat=None; both tier evaluators REJECT."""
    train = compute_cohort_stats(
        _build_synthetic_signals(n_win=0, n_loss=0, n_flat=20), cohort_filter={})
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=0, n_loss=0, n_flat=20), cohort_filter={})
    assert train["n_total"] == 20
    assert train["n_flat"] == 20
    assert train["wr_excl_flat"] is None
    assert train["wilson_lower_95"] is None
    # Both evaluators reject on None train_wr
    assert evaluate_boost_tier(train, test) == "REJECT"
    assert evaluate_kill_tier(train, test) == "REJECT"


def test_p_value_not_significant():
    """50/100 wins (random): p-value ≈ 1.0 (not significant). evaluate_boost_tier
    rejects regardless of test_wr (train_wr 0.50 fails Tier B floor 0.60 anyway)."""
    df = _build_synthetic_signals(n_win=50, n_loss=50)
    train = compute_cohort_stats(df, cohort_filter={})
    assert train["wr_excl_flat"] == 0.5
    # z = (50 - 50) / sqrt(25) = 0 → p = 1.0
    assert train["p_value_vs_50"] is not None
    assert train["p_value_vs_50"] > 0.95, f"p for 50/100 should be ≈ 1.0; got {train['p_value_vs_50']}"
    test = compute_cohort_stats(
        _build_synthetic_signals(n_win=11, n_loss=9), cohort_filter={})
    # Tier S/A/B all fail train_wr_min (≥0.75 / ≥0.65 / ≥0.60); REJECT
    assert evaluate_boost_tier(train, test) == "REJECT"


def test_split_boundary_exactly_on_split_date():
    """Signal exactly on split_date routes to test (>= cutoff per code line 221)."""
    rows = []
    for i in range(5):
        rows.append({"scan_date": "2022-12-15", "symbol": f"A{i}",
                      "signal": "UP_TRI", "outcome": "DAY6_WIN"})
    for i in range(5):
        rows.append({"scan_date": "2023-01-01", "symbol": f"B{i}",
                      "signal": "UP_TRI", "outcome": "DAY6_WIN"})
    for i in range(5):
        rows.append({"scan_date": "2023-06-15", "symbol": f"C{i}",
                      "signal": "UP_TRI", "outcome": "DAY6_WIN"})
    df = pd.DataFrame(rows)
    train, test = train_test_split(df, split_date="2023-01-01")
    # 2022-12-15 < 2023-01-01 → train (5 rows)
    # 2023-01-01 >= 2023-01-01 → test (5 rows; >= inclusive)
    # 2023-06-15 >= 2023-01-01 → test (5 rows)
    assert len(train) == 5
    assert len(test) == 10
    # Verify split_date rows are in test, not train
    assert all(pd.to_datetime(test["scan_date"]) >= pd.Timestamp("2023-01-01"))


def test_outcome_field_missing_column():
    """signals_df without 'outcome' column: cohort_stats returns zeros + None
    wr gracefully; evaluate_boost_tier rejects on None train_wr."""
    df = pd.DataFrame([
        {"scan_date": "2022-01-01", "symbol": "A", "signal": "UP_TRI"},
        {"scan_date": "2022-02-01", "symbol": "B", "signal": "UP_TRI"},
    ])
    # No 'outcome' column present
    stats = compute_cohort_stats(df, cohort_filter={})
    assert stats["n_total"] == 2  # rows present in cohort
    assert stats["n_win"] == 0
    assert stats["n_loss"] == 0
    assert stats["wr_excl_flat"] is None
    assert stats["wilson_lower_95"] is None
    test_stats = compute_cohort_stats(
        _build_synthetic_signals(n_win=10, n_loss=8), cohort_filter={})
    # train wr_excl_flat=None → evaluate_boost_tier returns REJECT immediately
    assert evaluate_boost_tier(stats, test_stats) == "REJECT"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
