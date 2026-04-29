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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
