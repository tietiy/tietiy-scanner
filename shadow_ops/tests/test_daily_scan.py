"""Smoke tests for shadow_ops/daily_scan.py.

Heavy I/O (FeatureExtractor, yfinance, lab/cache parquets) is stubbed via
monkeypatch so these tests run offline and fast. The classifier, OHLC loader,
universe loader, nifty loader, and detect_signals are all replaceable. The
flow under test is: rule-match dispatch + CandidateSignal/TradeCard/
LifecycleEvent/ScanEvent emission + scan_status accounting.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from shadow_ops import daily_scan as daily_scan_mod
from shadow_ops.daily_scan import (
    _compute_target,
    _load_active_rules,
    _load_universe_with_sectors,
    daily_scan,
)
from shadow_ops.journal import JournalReader
from shadow_ops.regime_classifier import RegimeClassification


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RULES_PATH = (
    _REPO_ROOT / "lab" / "factory" / "step5_finalization"
    / "L4_opus_output" / "unified_rules_v4_1_FINAL.json"
)
UNIVERSE_PATH = _REPO_ROOT / "data" / "fno_universe.csv"


# ============================================================
# Helpers — synthetic regime, synthetic signal dicts
# ============================================================

def _fake_classification(regime="Bear", sub_regime="hot",
                         scan_date_iso="2026-05-05") -> RegimeClassification:
    return RegimeClassification(
        scan_date=scan_date_iso,
        regime=regime,
        sub_regime=sub_regime,
        inputs={
            "feat_nifty_vol_percentile_20d": 0.78,
            "feat_nifty_60d_return_pct": -0.12,
            "feat_nifty_200d_return_pct": 0.04,
            "feat_market_breadth_pct": 0.32,
            "last_slope": -0.0061,
            "last_above_ema50": False,
            "nifty_close_latest_date": scan_date_iso,
        },
        features_sha="a" * 64,
        classified_at_utc=f"{scan_date_iso}T00:00:00+00:00",
        nifty_close_latest_date=scan_date_iso,
    )


def _make_signal(signal="UP_TRI", direction="LONG",
                 entry=100.0, stop=90.0, atr=2.0,
                 pivot_price=95.0, age=0, symbol="LUPIN.NS",
                 sector="Pharma") -> dict:
    """Mirror the dict shape returned by scanner_core.detect_signals."""
    return {
        "symbol": symbol,
        "sector": sector,
        "signal": signal,
        "direction": direction,
        "age": age,
        "attempt_number": 1,
        "pivot_date": "2026-05-04",
        "pivot_price": pivot_price,
        "entry_est": entry,
        "stop": stop,
        "atr": atr,
        "regime": "Bear",
        "regime_score": 0,
        "vol_q": "Average",
        "vol_confirm": False,
        "rs_q": "Neutral",
        "rs_strong": False,
        "sec_mom": "Neutral",
        "sec_leading": False,
        "bear_bonus": True,
        "stock_regime": "Neutral",
        "nifty_pct_today": 0.0,
        "sector_context": "Neutral",
        "is_sa": False,
        "sa_parent_id": None,
        "sa_parent_outcome": None,
    }


@pytest.fixture
def stub_io(monkeypatch):
    """Stub heavy I/O. Returns a config dict the test can mutate before
    invoking daily_scan(). Defaults: Bear+hot, 1-symbol universe, no signals."""
    cfg = {
        "regime": "Bear",
        "sub_regime": "hot",
        "universe": [("LUPIN.NS", "Pharma")],
        "signals": [],   # detect_signals returns this for ALL symbols
    }

    def fake_classify(scan_date, **kwargs):
        return _fake_classification(
            regime=cfg["regime"], sub_regime=cfg["sub_regime"],
            scan_date_iso=scan_date.isoformat(),
        )

    def fake_universe(*a, **kw):
        return list(cfg["universe"])

    def fake_ohlc(symbol, cache_dir, scan_ts):
        # 100 dummy bars — enough to satisfy MIN_BARS_FOR_DETECT
        idx = pd.date_range("2026-01-01", periods=100, freq="B")
        return pd.DataFrame({
            "Open": [100.0] * 100,
            "High": [101.0] * 100,
            "Low": [99.0] * 100,
            "Close": [100.0] * 100,
            "Volume": [1_000_000] * 100,
        }, index=idx)

    def fake_nifty(*a, **kw):
        idx = pd.date_range("2026-01-01", periods=100, freq="B")
        return pd.Series([22_000.0] * 100, index=idx)

    def fake_detect_signals(df, symbol, sector, regime, regime_score,
                            sector_momentum, nifty_close=None):
        # Re-tag each signal to the current symbol/sector so cfg can hold
        # generic templates that work across the (single-symbol) universe
        out = []
        for s in cfg["signals"]:
            sig = dict(s)
            sig["symbol"] = symbol
            sig["sector"] = sector
            sig["regime"] = regime
            out.append(sig)
        return out

    monkeypatch.setattr(daily_scan_mod, "classify_regime_for_date", fake_classify)
    monkeypatch.setattr(daily_scan_mod, "_load_universe_with_sectors", fake_universe)
    monkeypatch.setattr(daily_scan_mod, "_load_symbol_ohlc", fake_ohlc)
    monkeypatch.setattr(daily_scan_mod, "_load_nifty_close", fake_nifty)
    monkeypatch.setattr(daily_scan_mod, "detect_signals", fake_detect_signals)
    return cfg


# ============================================================
# 1. Rule loader
# ============================================================

def test_load_active_rules_returns_three_expected():
    """_load_active_rules pulls exactly rule_019, rule_031, kill_001."""
    rules = _load_active_rules(RULES_PATH)
    assert set(rules.keys()) == {
        "rule_019_bear_uptri_hot_refinement",
        "rule_031_bear_uptri_it_hot",
        "kill_001",
    }
    # Sanity-check the loaded rule shapes
    assert rules["rule_019_bear_uptri_hot_refinement"]["match_fields"]["signal"] == "UP_TRI"
    assert rules["kill_001"]["match_fields"]["signal"] == "DOWN_TRI"
    assert rules["rule_031_bear_uptri_it_hot"]["match_fields"]["sector"] == "IT"


# ============================================================
# 2. Universe loader
# ============================================================

def test_universe_loader_extracts_symbol_sector():
    """_load_universe_with_sectors yields (symbol, sector) tuples for all rows."""
    universe = _load_universe_with_sectors(UNIVERSE_PATH)
    assert len(universe) > 100  # ~188 symbols
    assert ("HDFCBANK.NS", "Bank") in universe
    # Every entry is a 2-tuple of non-empty strings
    for sym, sec in universe[:5]:
        assert isinstance(sym, str) and sym
        assert isinstance(sec, str) and sec


# ============================================================
# 3. Target computation (2R)
# ============================================================

def test_compute_target_2R_long_and_short():
    """target = entry ± 2 × |entry - stop| per scanner/main.py:427-429."""
    # LONG: entry=100, stop=90 → risk=10 → target=120
    assert _compute_target(100.0, 90.0, "LONG") == 120.0
    # SHORT: entry=100, stop=110 → risk=10 → target=80
    assert _compute_target(100.0, 110.0, "SHORT") == 80.0


# ============================================================
# 4. kill_001 match → candidate logged, no trade card
# ============================================================

def test_kill_001_match_emits_candidate_no_trade_card(stub_io, tmp_path):
    """Bear+Bank+DOWN_TRI signal → 1 candidate (SUPPRESSED), 0 trade cards."""
    stub_io["regime"] = "Bear"
    stub_io["universe"] = [("HDFCBANK.NS", "Bank")]
    stub_io["signals"] = [_make_signal(
        signal="DOWN_TRI", direction="SHORT",
        entry=100.0, stop=110.0, atr=2.0,
        symbol="HDFCBANK.NS", sector="Bank",
    )]

    result = daily_scan(date(2026, 5, 5), run_dir=tmp_path,
                        rules_path=RULES_PATH)

    assert result.n_signals_universe == 1
    assert result.n_signals_post_filter == 1
    assert result.n_candidate_signals_emitted == 1
    assert result.n_trade_cards_emitted == 0
    assert result.n_kill_001_suppressed == 1

    r = JournalReader(tmp_path)
    cands = r.all_candidate_signals()
    assert len(cands) == 1
    assert cands[0].kill_001_match is True
    assert cands[0].rule_019_match is False
    assert cands[0].trigger_disposition == "SUPPRESSED_BY_KILL_001"

    # NO trade card and NO lifecycle event
    assert r.all_trade_cards() == []
    assert r.all_lifecycle_events() == []


# ============================================================
# 5. rule_019 match → trade card with 2R target
# ============================================================

def test_rule_019_match_emits_trade_card_with_2R_target(stub_io, tmp_path):
    """Bear+hot+UP_TRI (non-IT sector) → 1 candidate + 1 trade card.
    Target = entry + 2 × (entry - stop). rule_031_confirm=0."""
    stub_io["regime"] = "Bear"
    stub_io["sub_regime"] = "hot"
    stub_io["universe"] = [("LUPIN.NS", "Pharma")]
    stub_io["signals"] = [_make_signal(
        signal="UP_TRI", direction="LONG",
        entry=1890.20, stop=1820.50, atr=23.45,
        pivot_price=1885.00,
        symbol="LUPIN.NS", sector="Pharma",
    )]

    result = daily_scan(date(2026, 5, 5), run_dir=tmp_path,
                        rules_path=RULES_PATH)

    assert result.n_trade_cards_emitted == 1
    assert result.n_kill_001_suppressed == 0
    assert result.n_rule_031_overlay_count == 0

    r = JournalReader(tmp_path)
    cards = r.all_trade_cards()
    assert len(cards) == 1
    card = cards[0]
    assert card.rule_id == "rule_019_bear_uptri_hot_refinement"
    assert card.rule_031_confirm == 0
    assert card.kill_001_match is False
    assert card.proposed_entry_price == 1890.20
    assert card.proposed_stop == 1820.50
    # 2R: 1890.20 + 2 * (1890.20 - 1820.50) = 1890.20 + 139.40 = 2029.60
    assert card.proposed_target == round(1890.20 + 2 * (1890.20 - 1820.50), 2)
    assert card.current_state == "PROPOSED"
    # state_history records the PROPOSED creation moment
    assert len(card.state_history) == 1
    assert card.state_history[0]["state"] == "PROPOSED"
    assert card.state_history[0]["reason"] == "rule_019_match"

    # No lifecycle events at creation — those are reserved for actual state
    # CHANGES (Step 5 T+1 fill simulation onward).
    assert r.all_lifecycle_events() == []


# ============================================================
# 6. rule_031 confirms rule_019 (IT sector) → confirm flag set
# ============================================================

def test_rule_031_match_sets_confirm_flag(stub_io, tmp_path):
    """Bear+hot+IT+UP_TRI → trade card with rule_031_confirm=1."""
    stub_io["regime"] = "Bear"
    stub_io["sub_regime"] = "hot"
    stub_io["universe"] = [("INFY.NS", "IT")]
    stub_io["signals"] = [_make_signal(
        signal="UP_TRI", direction="LONG",
        entry=1500.0, stop=1450.0, atr=15.0,
        symbol="INFY.NS", sector="IT",
    )]

    result = daily_scan(date(2026, 5, 5), run_dir=tmp_path,
                        rules_path=RULES_PATH)

    assert result.n_trade_cards_emitted == 1
    assert result.n_rule_031_overlay_count == 1

    r = JournalReader(tmp_path)
    cards = r.all_trade_cards()
    assert len(cards) == 1
    assert cards[0].rule_031_confirm == 1
    assert cards[0].sector == "IT"

    cands = r.all_candidate_signals()
    assert cands[0].rule_019_match is True
    assert cands[0].rule_031_match is True
    assert cands[0].trigger_disposition == "TRADE_CARD_PROPOSED"


# ============================================================
# 7. Choppy regime → no rule matches
# ============================================================

def test_choppy_regime_yields_zero_matches(stub_io, tmp_path):
    """regime=Choppy: rule_019/031 require Bear, kill_001 requires Bear.
    So a UP_TRI signal in Choppy yields zero candidates and zero trade cards.
    The ScanEvent itself is still written."""
    stub_io["regime"] = "Choppy"
    stub_io["sub_regime"] = "stress_mid"
    stub_io["universe"] = [("LUPIN.NS", "Pharma")]
    stub_io["signals"] = [_make_signal(
        signal="UP_TRI", direction="LONG",
        symbol="LUPIN.NS", sector="Pharma",
    )]

    result = daily_scan(date(2026, 5, 5), run_dir=tmp_path,
                        rules_path=RULES_PATH)

    assert result.regime == "Choppy"
    assert result.n_signals_universe == 1     # detect_signals still returns it
    assert result.n_signals_post_filter == 0  # no rule matched
    assert result.n_trade_cards_emitted == 0
    assert result.n_candidate_signals_emitted == 0

    r = JournalReader(tmp_path)
    assert r.all_candidate_signals() == []
    assert r.all_trade_cards() == []
    assert r.all_lifecycle_events() == []
    # ScanEvent still emitted
    scans = r.all_scan_events()
    assert len(scans) == 1
    assert scans[0].regime == "Choppy"


# ============================================================
# 8. ScanEvent shape
# ============================================================

def test_daily_scan_emits_scan_event_with_data_versions(stub_io, tmp_path):
    """ScanEvent has the expected counts, regime, and data_versions keys."""
    stub_io["signals"] = []  # no signals → empty universe

    result = daily_scan(date(2026, 5, 5), run_dir=tmp_path,
                        rules_path=RULES_PATH)

    r = JournalReader(tmp_path)
    scans = r.all_scan_events()
    assert len(scans) == 1
    ev = scans[0]
    assert ev.event_id == result.scan_event_id
    assert ev.scan_date == "2026-05-05"
    assert ev.regime == "Bear"
    assert ev.sub_regime == "hot"
    assert ev.scan_status == "OK"
    assert ev.n_signals_universe == 0
    assert ev.n_signals_post_filter == 0
    # data_versions includes our 3 expected keys
    assert "rules_path_sha256" in ev.data_versions
    assert "nifty_parquet_sha256" in ev.data_versions
    assert "regime_features_sha" in ev.data_versions
    assert len(ev.data_versions["rules_path_sha256"]) == 64
    # sub_regime_inputs round-trips the classifier dict
    assert "feat_nifty_vol_percentile_20d" in ev.sub_regime_inputs


# ============================================================
# 9. Re-scan same date in same run_dir → DuplicateEventIdError
# ============================================================

def test_re_scan_same_date_raises_duplicate(stub_io, tmp_path):
    """Running daily_scan twice for the same scan_date in the same run_dir
    raises on the second ScanEvent (event_id already exists)."""
    from shadow_ops.journal import DuplicateEventIdError

    stub_io["signals"] = []
    daily_scan(date(2026, 5, 5), run_dir=tmp_path, rules_path=RULES_PATH)

    with pytest.raises(DuplicateEventIdError, match="scan_2026-05-05_001"):
        daily_scan(date(2026, 5, 5), run_dir=tmp_path, rules_path=RULES_PATH)
