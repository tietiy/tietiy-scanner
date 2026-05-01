"""
Phase 4 input schema validator.

Validates that the artifacts from Phases 1-3 are present, well-formed, and
contain the expected structure before Phase 4 starts iterating combinations.

HALTs with explicit error if any input is missing or malformed.

Inputs validated:
  • lab/output/enriched_signals.parquet (Phase 1) — 114 feat_* + outcome
  • lab/output/feature_importance.json (Phase 2) — top 20 per cohort
  • lab/output/baselines.json (Phase 3) — signal × regime × horizon nested
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent

sys.path.insert(0, str(_HERE))
from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import _FEAT_PREFIX, _EXPECTED_FEATURE_COUNT  # noqa: E402

DEFAULT_ENRICHED_PATH = _LAB_ROOT / "output" / "enriched_signals.parquet"
DEFAULT_IMPORTANCE_PATH = _LAB_ROOT / "output" / "feature_importance.json"
DEFAULT_BASELINES_PATH = _LAB_ROOT / "output" / "baselines.json"

OUTCOME_COVERAGE_THRESHOLD = 0.95


class ValidationError(Exception):
    """Raised when input validation fails."""


def validate_enriched(path: Path = DEFAULT_ENRICHED_PATH) -> dict:
    """Confirm enriched_signals.parquet has 114 feat_* cols + outcome."""
    if not path.exists():
        raise ValidationError(f"enriched parquet not found: {path}")
    df = pd.read_parquet(path, columns=None)
    feat_cols = [c for c in df.columns
                 if c.startswith(_FEAT_PREFIX)
                 and c != _FEAT_PREFIX + "_extractor_error"]
    if len(feat_cols) != _EXPECTED_FEATURE_COUNT:
        raise ValidationError(
            f"enriched parquet has {len(feat_cols)} feat_* cols, "
            f"expected {_EXPECTED_FEATURE_COUNT}")
    if "outcome" not in df.columns:
        raise ValidationError("enriched parquet missing 'outcome' column")
    n_rows = len(df)
    n_with_outcome = df["outcome"].notna().sum()
    coverage = n_with_outcome / n_rows
    if coverage < OUTCOME_COVERAGE_THRESHOLD:
        raise ValidationError(
            f"outcome coverage {coverage:.1%} below "
            f"{OUTCOME_COVERAGE_THRESHOLD:.0%} threshold")
    # Confirm registry IDs match feat_* cols
    registry = FeatureRegistry.load_all()
    expected_ids = {s.feature_id for s in registry.list_all()}
    actual_ids = {c[len(_FEAT_PREFIX):] for c in feat_cols}
    missing = expected_ids - actual_ids
    if missing:
        raise ValidationError(f"feature_id mismatch; missing: {sorted(missing)}")
    return {"n_rows": n_rows,
              "n_features": len(feat_cols),
              "outcome_coverage": float(coverage),
              "regimes": df["regime"].dropna().unique().tolist(),
              "signal_types": df["signal"].dropna().unique().tolist()}


def validate_importance(path: Path = DEFAULT_IMPORTANCE_PATH) -> dict:
    """Confirm feature_importance.json has cohorts + ranked_features per cohort."""
    if not path.exists():
        raise ValidationError(f"feature_importance.json not found: {path}")
    with open(path) as fh:
        data = json.load(fh)
    if "cohorts" not in data:
        raise ValidationError("feature_importance.json missing 'cohorts' key")
    cohorts = data["cohorts"]
    if not isinstance(cohorts, dict) or not cohorts:
        raise ValidationError("feature_importance.json 'cohorts' empty/wrong type")
    summary = {}
    for cohort_name, cdata in cohorts.items():
        if "ranked_features" not in cdata:
            raise ValidationError(
                f"cohort {cohort_name} missing 'ranked_features'")
        rf = cdata["ranked_features"]
        if not isinstance(rf, list) or len(rf) < 20:
            raise ValidationError(
                f"cohort {cohort_name} ranked_features length "
                f"{len(rf) if isinstance(rf, list) else '?'} (need ≥20)")
        # Check first entry shape
        first = rf[0]
        for required in ("feature_id", "borda_score", "aggregate_rank",
                          "top_20"):
            if required not in first:
                raise ValidationError(
                    f"cohort {cohort_name} ranked_features[0] missing "
                    f"{required!r}")
        summary[cohort_name] = {
            "n_features_ranked": len(rf),
            "n_top_20": sum(1 for f in rf if f.get("top_20")),
        }
    return {"cohorts_present": list(cohorts.keys()),
              "summary": summary}


def validate_baselines(path: Path = DEFAULT_BASELINES_PATH) -> dict:
    """Confirm baselines.json has signal_type × regime × horizon nested
    structure with WR + Wilson interval per cell."""
    if not path.exists():
        raise ValidationError(f"baselines.json not found: {path}")
    with open(path) as fh:
        data = json.load(fh)
    if "cohorts" not in data:
        raise ValidationError("baselines.json missing 'cohorts' key")
    cohorts = data["cohorts"]
    cell_count = 0
    cells_with_wr = 0
    for sig_type, regime_dict in cohorts.items():
        if not isinstance(regime_dict, dict):
            raise ValidationError(f"baselines: {sig_type} value not dict")
        for regime, horizon_dict in regime_dict.items():
            if not isinstance(horizon_dict, dict):
                raise ValidationError(
                    f"baselines: {sig_type}/{regime} value not dict")
            for horizon, cell in horizon_dict.items():
                cell_count += 1
                if not isinstance(cell, dict):
                    raise ValidationError(
                        f"baselines cell {sig_type}/{regime}/{horizon} not dict")
                # Expected keys (some can be None for too_low cells)
                for k in ("n", "wr", "wilson_lower_95", "wilson_upper_95",
                           "confidence"):
                    if k not in cell:
                        raise ValidationError(
                            f"baselines cell {sig_type}/{regime}/{horizon} "
                            f"missing key {k!r}")
                if cell.get("wr") is not None:
                    cells_with_wr += 1
    return {"signal_types": list(cohorts.keys()),
              "n_cells": cell_count,
              "n_cells_with_wr": cells_with_wr}


def validate_all(verbose: bool = False) -> dict:
    """Run all validations. Returns combined summary or raises ValidationError."""
    enriched = validate_enriched()
    importance = validate_importance()
    baselines = validate_baselines()
    summary = {"enriched": enriched,
                 "importance": importance,
                 "baselines": baselines}
    if verbose:
        print("Phase 4 input validation:")
        print(f"  enriched: {enriched['n_rows']} rows × "
              f"{enriched['n_features']} features, "
              f"outcome coverage {enriched['outcome_coverage']:.1%}, "
              f"regimes {enriched['regimes']}, "
              f"signal_types {enriched['signal_types']}")
        print(f"  importance: {len(importance['cohorts_present'])} cohorts: "
              f"{importance['cohorts_present']}")
        print(f"  baselines: {baselines['n_cells']} cells "
              f"({baselines['n_cells_with_wr']} with WR), "
              f"signal_types {baselines['signal_types']}")
    return summary


if __name__ == "__main__":
    try:
        validate_all(verbose=True)
        print("\n✓ all validations passed")
    except ValidationError as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        sys.exit(1)
