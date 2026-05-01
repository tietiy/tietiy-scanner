"""
Unit tests for feature_loader.py.

Run:
    .venv/bin/python -m pytest lab/infrastructure/test_feature_loader.py -v
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from feature_loader import (  # noqa: E402
    FeatureRegistry,
    FeatureSpec,
    _DEFAULT_LIBRARY_DIR,
    _REQUIRED_FIELDS,
    _VALID_FAMILIES,
)


# ═════════════════════════════════════════════════════════════════════
# Group 1: load_all + counts (5 tests)
# ═════════════════════════════════════════════════════════════════════

def test_load_all_returns_114_features():
    reg = FeatureRegistry.load_all()
    assert len(reg) == 114, f"expected 114 features; got {len(reg)}"


def test_family_counts_match_spec_v2_1():
    reg = FeatureRegistry.load_all()
    expected = {
        "compression": 15,
        "institutional_zone": 22,
        "momentum": 25,
        "volume": 15,
        "regime": 20,
        "pattern": 17,
    }
    actual = reg.family_counts()
    assert actual == expected, f"family count mismatch: {actual} vs {expected}"


def test_complexity_counts_match_table():
    """Table-derived counts (73/35/6); spec narrative summary said 67/36/11
    but table is authoritative source."""
    reg = FeatureRegistry.load_all()
    expected = {"cheap": 73, "medium": 35, "expensive": 6}
    actual = reg.complexity_counts()
    assert actual == expected, f"complexity count mismatch: {actual} vs {expected}"


def test_all_specs_have_v2_1_version():
    reg = FeatureRegistry.load_all()
    versions = {s.spec_version for s in reg.specs.values()}
    assert versions == {"v2.1"}, f"unexpected spec_versions: {versions}"


def test_all_features_have_required_fields():
    reg = FeatureRegistry.load_all()
    for spec in reg.specs.values():
        for f in ("feature_id", "family", "value_type", "value_range",
                   "level_thresholds", "direction", "mechanism",
                   "data_source", "computation_complexity", "spec_version"):
            assert hasattr(spec, f), f"{spec.feature_id} missing {f}"


# ═════════════════════════════════════════════════════════════════════
# Group 2: get / list queries (4 tests)
# ═════════════════════════════════════════════════════════════════════

def test_get_known_feature_returns_spec():
    reg = FeatureRegistry.load_all()
    spec = reg.get("vol_ratio_20d")
    assert isinstance(spec, FeatureSpec)
    assert spec.feature_id == "vol_ratio_20d"
    assert spec.family == "volume"
    assert spec.value_type == "float"


def test_get_unknown_feature_raises_keyerror():
    reg = FeatureRegistry.load_all()
    with pytest.raises(KeyError):
        reg.get("nonexistent_feature_xyz")


def test_list_by_family_returns_correct_count():
    reg = FeatureRegistry.load_all()
    momentum = reg.list_by_family("momentum")
    assert len(momentum) == 25
    institutional = reg.list_by_family("institutional_zone")
    assert len(institutional) == 22


def test_list_by_complexity_returns_filtered():
    reg = FeatureRegistry.load_all()
    expensive = reg.list_by_complexity("expensive")
    assert len(expensive) == 6
    expensive_ids = {s.feature_id for s in expensive}
    # Verify ob_bullish_proximity, triangle_quality_ascending, market_breadth_pct
    # are all in the expensive bucket
    for expected in ("ob_bullish_proximity", "ob_bearish_proximity",
                       "triangle_quality_ascending", "triangle_quality_descending",
                       "market_breadth_pct", "advance_decline_ratio_20d"):
        assert expected in expensive_ids, (
            f"{expected} missing from expensive bucket; got {expensive_ids}")


# ═════════════════════════════════════════════════════════════════════
# Group 3: known-feature spec correctness (4 tests)
# ═════════════════════════════════════════════════════════════════════

def test_close_pos_in_range_spec_correct():
    """Q1 v2 addition. Verify INV-012 BTST primitive encoded correctly."""
    reg = FeatureRegistry.load_all()
    spec = reg.get("close_pos_in_range")
    assert spec.family == "volume"
    assert spec.value_type == "float"
    assert spec.value_range == "0-1"
    assert spec.level_thresholds == {"low": "<0.3", "medium": "0.3-0.7", "high": ">0.7"}
    assert "BTST" in spec.mechanism
    assert spec.computation_complexity == "cheap"


def test_accumulation_distribution_signed_collapsed():
    """Q3 v2 — verify renamed from accumulation_score_20d."""
    reg = FeatureRegistry.load_all()
    spec = reg.get("accumulation_distribution_signed")
    assert spec.family == "volume"
    assert spec.value_type == "float"
    # Verify old mirrored pair NOT present
    assert "distribution_score_20d" not in reg
    assert "accumulation_score_20d" not in reg


def test_fib_extensions_present_v2_1():
    """v2.1 additions — verify both Fib extension features present."""
    reg = FeatureRegistry.load_all()
    spec_1272 = reg.get("fib_1272_extension_proximity_atr")
    spec_1618 = reg.get("fib_1618_extension_proximity_atr")
    assert spec_1272.family == "institutional_zone"
    assert spec_1618.family == "institutional_zone"
    assert spec_1272.value_type == "float"
    assert spec_1618.value_type == "float"


def test_swing_features_present_v2_q2():
    """Q2 v2 — verify wave-count features dropped, swing features added."""
    reg = FeatureRegistry.load_all()
    # Wave features dropped
    assert "wave_count_estimate" not in reg
    assert "wave_4_complete_flag" not in reg
    # Swing features added
    for f in ("swing_high_count_20d", "swing_low_count_20d",
                "last_swing_high_distance_atr", "higher_highs_intact_flag"):
        assert f in reg, f"{f} missing"
        assert reg.get(f).family == "pattern"


# ═════════════════════════════════════════════════════════════════════
# Group 4: error handling (3 tests)
# ═════════════════════════════════════════════════════════════════════

def test_invalid_library_dir_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        FeatureRegistry.load_all(library_dir=Path("/nonexistent/dir/xyz"))


def test_empty_library_dir_raises_filenotfound(tmp_path):
    """Library dir exists but contains no JSON files."""
    with pytest.raises(FileNotFoundError) as exc_info:
        FeatureRegistry.load_all(library_dir=tmp_path)
    assert "no JSON files" in str(exc_info.value)


def test_malformed_json_strict_raises(tmp_path):
    """A malformed JSON file should raise in strict mode."""
    bad = tmp_path / "bad_feature.json"
    bad.write_text("{ not valid json")
    with pytest.raises(ValueError) as exc_info:
        FeatureRegistry.load_all(library_dir=tmp_path)
    assert "JSON parse error" in str(exc_info.value)


# ═════════════════════════════════════════════════════════════════════
# Group 5: validate_all + invariants (3 tests)
# ═════════════════════════════════════════════════════════════════════

def test_validate_all_passes_on_loaded_registry():
    reg = FeatureRegistry.load_all()
    reg.validate_all()  # should not raise


def test_feature_id_uniqueness():
    reg = FeatureRegistry.load_all()
    ids = [s.feature_id for s in reg.list_all()]
    assert len(ids) == len(set(ids)), "duplicate feature_ids found"


def test_filename_matches_feature_id():
    """Each feature_id should match its JSON filename."""
    reg = FeatureRegistry.load_all()
    for spec in reg.specs.values():
        expected_path = _DEFAULT_LIBRARY_DIR / f"{spec.feature_id}.json"
        assert expected_path.exists(), (
            f"feature_id {spec.feature_id} loaded but file "
            f"{expected_path.name} not found")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
