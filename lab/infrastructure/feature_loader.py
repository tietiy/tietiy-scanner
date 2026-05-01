"""
Feature library loader (registry pattern).

Reads `lab/feature_library/<feature_id>.json` × 114 (per spec v2.1) and exposes
a queryable registry of FeatureSpec objects.

Usage:
    from feature_loader import FeatureRegistry
    reg = FeatureRegistry.load_all()
    spec = reg.get("vol_ratio_20d")
    momentum_features = reg.list_by_family("momentum")
    cheap_features = reg.list_by_complexity("cheap")
    all_specs = reg.list_all()

Phase 1B per `lab/COMBINATION_ENGINE_PLAN.md`. NO main branch / NO scanner
modifications. Lab-only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
_DEFAULT_LIBRARY_DIR = _LAB_ROOT / "feature_library"

# Required fields per JSON schema
_REQUIRED_FIELDS = {
    "feature_id", "family", "value_type", "value_range",
    "level_thresholds", "direction", "mechanism",
    "data_source", "computation_complexity", "spec_version",
}

_VALID_FAMILIES = {
    "compression", "institutional_zone", "momentum",
    "volume", "regime", "pattern",
}

_VALID_VALUE_TYPES = {"float", "int", "categorical", "bool"}
_VALID_COMPLEXITIES = {"cheap", "medium", "expensive"}


@dataclass
class FeatureSpec:
    """Single feature definition mirroring JSON schema."""
    feature_id: str
    family: str
    value_type: str
    value_range: str
    level_thresholds: dict
    direction: str
    mechanism: str
    data_source: str
    computation_complexity: str
    spec_version: str

    @classmethod
    def from_dict(cls, d: dict) -> "FeatureSpec":
        missing = _REQUIRED_FIELDS - set(d.keys())
        if missing:
            raise ValueError(
                f"FeatureSpec from_dict: missing fields {missing} "
                f"(feature_id={d.get('feature_id', '?')!r})")
        return cls(
            feature_id=d["feature_id"],
            family=d["family"],
            value_type=d["value_type"],
            value_range=d["value_range"],
            level_thresholds=d["level_thresholds"],
            direction=d["direction"],
            mechanism=d["mechanism"],
            data_source=d["data_source"],
            computation_complexity=d["computation_complexity"],
            spec_version=d["spec_version"],
        )

    def validate(self) -> None:
        """Raise if any field has an invalid value."""
        if self.family not in _VALID_FAMILIES:
            raise ValueError(
                f"{self.feature_id}: family {self.family!r} not in {_VALID_FAMILIES}")
        if self.value_type not in _VALID_VALUE_TYPES:
            raise ValueError(
                f"{self.feature_id}: value_type {self.value_type!r} not in {_VALID_VALUE_TYPES}")
        if self.computation_complexity not in _VALID_COMPLEXITIES:
            raise ValueError(
                f"{self.feature_id}: computation_complexity "
                f"{self.computation_complexity!r} not in {_VALID_COMPLEXITIES}")
        if not isinstance(self.level_thresholds, dict):
            raise ValueError(
                f"{self.feature_id}: level_thresholds must be dict, "
                f"got {type(self.level_thresholds).__name__}")


@dataclass
class FeatureRegistry:
    """Registry of all FeatureSpec entries, queryable by id / family / complexity."""
    specs: dict[str, FeatureSpec] = field(default_factory=dict)

    @classmethod
    def load_all(cls, library_dir: Optional[Path] = None,
                  strict: bool = True) -> "FeatureRegistry":
        """Load all JSON files from library_dir into registry.

        Parameters
        ----------
        library_dir : Path
            Directory containing <feature_id>.json files. Defaults to
            lab/feature_library/.
        strict : bool
            If True (default), raise on any malformed JSON / missing field.
            If False, skip bad files and log to stderr; return partial registry.
        """
        library_dir = Path(library_dir) if library_dir else _DEFAULT_LIBRARY_DIR
        if not library_dir.exists():
            raise FileNotFoundError(f"feature library dir not found: {library_dir}")

        registry = cls()
        json_files = sorted(library_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(
                f"no JSON files in {library_dir}; run "
                f"lab/infrastructure/_generate_feature_library.py first")

        for p in json_files:
            try:
                with open(p) as fh:
                    data = json.load(fh)
            except json.JSONDecodeError as e:
                msg = f"feature_loader: {p.name} JSON parse error: {e}"
                if strict:
                    raise ValueError(msg) from e
                import sys
                print(msg, file=sys.stderr)
                continue

            try:
                spec = FeatureSpec.from_dict(data)
                spec.validate()
            except ValueError as e:
                msg = f"feature_loader: {p.name} validation error: {e}"
                if strict:
                    raise
                import sys
                print(msg, file=sys.stderr)
                continue

            if spec.feature_id != p.stem:
                msg = (f"feature_loader: filename {p.name} does not match "
                        f"feature_id {spec.feature_id!r}")
                if strict:
                    raise ValueError(msg)
                import sys
                print(msg, file=sys.stderr)
                continue

            registry.specs[spec.feature_id] = spec

        return registry

    def get(self, feature_id: str) -> FeatureSpec:
        """Return single FeatureSpec; raise KeyError if not found."""
        if feature_id not in self.specs:
            raise KeyError(
                f"feature_id {feature_id!r} not in registry. "
                f"Known feature_ids: {sorted(self.specs.keys())[:5]}…")
        return self.specs[feature_id]

    def list_by_family(self, family: str) -> list[FeatureSpec]:
        """Return all FeatureSpec entries in given family. Raises if family invalid."""
        if family not in _VALID_FAMILIES:
            raise ValueError(f"family {family!r} not in {_VALID_FAMILIES}")
        return sorted(
            (s for s in self.specs.values() if s.family == family),
            key=lambda s: s.feature_id)

    def list_by_complexity(self, level: str) -> list[FeatureSpec]:
        """Return all FeatureSpec entries with given complexity level."""
        if level not in _VALID_COMPLEXITIES:
            raise ValueError(f"complexity {level!r} not in {_VALID_COMPLEXITIES}")
        return sorted(
            (s for s in self.specs.values() if s.computation_complexity == level),
            key=lambda s: s.feature_id)

    def list_all(self) -> list[FeatureSpec]:
        """Return all 114 FeatureSpec entries sorted by feature_id."""
        return sorted(self.specs.values(), key=lambda s: s.feature_id)

    def family_counts(self) -> dict[str, int]:
        """Return count per family. Useful for verifying expected distribution."""
        out: dict[str, int] = {}
        for s in self.specs.values():
            out[s.family] = out.get(s.family, 0) + 1
        return out

    def complexity_counts(self) -> dict[str, int]:
        """Return count per complexity level."""
        out: dict[str, int] = {}
        for s in self.specs.values():
            out[s.computation_complexity] = (
                out.get(s.computation_complexity, 0) + 1)
        return out

    def validate_all(self) -> None:
        """Run validate() on every spec; raise if any invalid.

        Also enforces uniqueness of feature_ids (which load_all already does
        implicitly via dict-keying, but this is a belt-and-suspenders check
        for callers who construct registries manually).
        """
        for spec in self.specs.values():
            spec.validate()
        if len(self.specs) != len(set(self.specs.keys())):
            raise ValueError("duplicate feature_id in registry")

    def __len__(self) -> int:
        return len(self.specs)

    def __contains__(self, feature_id: str) -> bool:
        return feature_id in self.specs


# ── CLI helper for ad-hoc inspection ──────────────────────────────────

def _summarize() -> None:
    """Print summary of loaded library; useful for sanity checks."""
    reg = FeatureRegistry.load_all()
    print(f"feature library: {len(reg)} features loaded from "
          f"{_DEFAULT_LIBRARY_DIR}")
    print(f"  family counts: {reg.family_counts()}")
    print(f"  complexity counts: {reg.complexity_counts()}")
    print(f"  spec_versions: "
          f"{sorted({s.spec_version for s in reg.specs.values()})}")


if __name__ == "__main__":
    _summarize()
