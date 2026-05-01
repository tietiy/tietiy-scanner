"""
Pattern unifier — clusters Phase 4 surviving combinations into unified
patterns via Jaccard similarity on (feature_id, level) tuple sets.

Algorithm:
  1. Group combinations by cohort (signal_type × regime × horizon)
  2. Within each cohort, build pairwise Jaccard graph
  3. Add edge if Jaccard ≥ JACCARD_THRESHOLD (0.6)
  4. Connected components via union-find → each is one cluster
  5. Per cluster, select anchor combination:
       - max edge_pp_test
       - ties: min feature_count (broader pattern preferred)
       - ties: max Phase 4 tier (S > A > B)

Pattern_id: sha256 of canonical (cohort + sorted anchor feature-level pairs).

NO production scanner modifications. Lab-only.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

JACCARD_THRESHOLD = 0.6
TIER_ORDER = {"S": 3, "A": 2, "B": 1}


@dataclass
class UnifiedPattern:
    pattern_id: str
    anchor_combo_id: str
    supporting_combo_ids: list[str]
    cohort_signal_type: str
    cohort_regime: str
    cohort_horizon: str
    features: list[dict]  # [{feature_id, level}, ...] (anchor's features)
    feature_count: int
    anchor_tier: str  # Phase 4 tier (S/A/B)
    anchor_test_wr: float
    anchor_edge_pp: float
    cluster_size: int  # how many combos in this cluster (incl anchor)


# ── Feature-level set extraction ──────────────────────────────────────

def combo_feature_set(combo_row: dict) -> frozenset:
    """Extract (feature_id, level) tuple set from combo row."""
    pairs = []
    for slot in ("a", "b", "c", "d"):
        fid = combo_row.get(f"feature_{slot}_id")
        lvl = combo_row.get(f"feature_{slot}_level")
        if pd.notna(fid) and pd.notna(lvl):
            pairs.append((fid, lvl))
    return frozenset(pairs)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


# ── Union-find for connected components ──────────────────────────────

class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]  # path compression
            i = self.parent[i]
        return i

    def union(self, i: int, j: int) -> None:
        ri, rj = self.find(i), self.find(j)
        if ri == rj:
            return
        if self.rank[ri] < self.rank[rj]:
            ri, rj = rj, ri
        self.parent[rj] = ri
        if self.rank[ri] == self.rank[rj]:
            self.rank[ri] += 1


# ── Main unification ──────────────────────────────────────────────────

def _pattern_id(cohort: tuple, anchor_features: list[tuple]) -> str:
    """Stable pattern_id from cohort + sorted anchor (feature, level) pairs."""
    canonical = {
        "signal_type": cohort[0],
        "regime": cohort[1],
        "horizon": cohort[2],
        "features": sorted(anchor_features),
    }
    import json
    payload = json.dumps(canonical, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def unify_combinations(combinations_df: pd.DataFrame,
                          feature_id_cols: tuple = (
                              "feature_a_id", "feature_b_id",
                              "feature_c_id", "feature_d_id"),
                          feature_level_cols: tuple = (
                              "feature_a_level", "feature_b_level",
                              "feature_c_level", "feature_d_level"),
                          jaccard_threshold: float = JACCARD_THRESHOLD
                          ) -> list[UnifiedPattern]:
    """Group → Jaccard cluster → anchor selection.

    `combinations_df` should have:
      • combo_id, signal_type, regime, horizon, feature_count
      • feature_a..d_id / feature_a..d_level
      • test_wr, baseline_wr, tier (Phase 4 tier letter)
    """
    needed_cols = (
        "combo_id", "signal_type", "regime", "horizon", "feature_count",
        "test_wr", "baseline_wr", "tier",
        *feature_id_cols, *feature_level_cols,
    )
    for c in needed_cols:
        if c not in combinations_df.columns:
            raise ValueError(f"unify_combinations: missing required column {c!r}")

    patterns: list[UnifiedPattern] = []

    for cohort_key, group in combinations_df.groupby(
            ["signal_type", "regime", "horizon"]):
        group = group.reset_index(drop=True)
        n = len(group)
        if n == 0:
            continue

        # Compute feature-level sets per combo
        feature_sets = [combo_feature_set(row.to_dict())
                          for _, row in group.iterrows()]

        # Build union-find with edges where Jaccard ≥ threshold
        uf = UnionFind(n)
        for i in range(n):
            for j in range(i + 1, n):
                if jaccard(feature_sets[i], feature_sets[j]) >= jaccard_threshold:
                    uf.union(i, j)

        # Group by component
        components: dict[int, list[int]] = {}
        for i in range(n):
            root = uf.find(i)
            components.setdefault(root, []).append(i)

        # Anchor selection per component
        for root, members in components.items():
            sub = group.iloc[members]
            edge_pp = sub["test_wr"] - sub["baseline_wr"]
            sub = sub.assign(_edge_pp=edge_pp,
                             _tier_rank=sub["tier"].map(TIER_ORDER).fillna(0))
            # Sort: edge desc, feature_count asc, tier_rank desc
            sub = sub.sort_values(
                by=["_edge_pp", "feature_count", "_tier_rank"],
                ascending=[False, True, False])
            anchor = sub.iloc[0]
            anchor_features = sorted(feature_sets[
                members[group.index[group["combo_id"] == anchor["combo_id"]
                                       ].tolist()[0]]
            ]) if False else sorted(combo_feature_set(anchor.to_dict()))

            pattern_id = _pattern_id(cohort_key, anchor_features)
            patterns.append(UnifiedPattern(
                pattern_id=pattern_id,
                anchor_combo_id=anchor["combo_id"],
                supporting_combo_ids=[r["combo_id"] for _, r in
                                          group.iloc[members].iterrows()
                                          if r["combo_id"] != anchor["combo_id"]],
                cohort_signal_type=cohort_key[0],
                cohort_regime=cohort_key[1],
                cohort_horizon=cohort_key[2],
                features=[{"feature_id": fid, "level": lvl}
                              for fid, lvl in anchor_features],
                feature_count=int(anchor["feature_count"]),
                anchor_tier=str(anchor["tier"]),
                anchor_test_wr=float(anchor["test_wr"]),
                anchor_edge_pp=float(anchor["_edge_pp"]),
                cluster_size=len(members),
            ))

    return patterns


def patterns_to_dataframe(patterns: list[UnifiedPattern]) -> pd.DataFrame:
    """Flatten UnifiedPattern list to DataFrame."""
    rows = []
    for p in patterns:
        rows.append({
            "pattern_id": p.pattern_id,
            "anchor_combo_id": p.anchor_combo_id,
            "supporting_count": len(p.supporting_combo_ids),
            "cluster_size": p.cluster_size,
            "signal_type": p.cohort_signal_type,
            "regime": p.cohort_regime,
            "horizon": p.cohort_horizon,
            "feature_count": p.feature_count,
            "anchor_tier": p.anchor_tier,
            "anchor_test_wr": p.anchor_test_wr,
            "anchor_edge_pp": p.anchor_edge_pp,
            "features_json": __import__("json").dumps(p.features),
        })
    return pd.DataFrame(rows)
