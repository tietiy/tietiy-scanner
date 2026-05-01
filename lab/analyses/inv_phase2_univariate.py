"""
Phase 2 SUB-BLOCK 2B — Univariate feature importance analysis.

For each of 114 features, measures how strongly it differentiates wins from
losses across 10 cohorts (6 live + 4 lifetime). Produces ranked features per
cohort with edge_pp / p_value / effect_size statistics.

Cohorts:
  Live (n=200 from live_signals_with_features.parquet):
    1. universal-live (n=200)
    2. Bear-live      (n=98)
    3. Choppy-live    (n=102)
    4. UP_TRI-live    (n=165)
    5. DOWN_TRI-live  (n=14)   — borderline
    6. BULL_PROXY-live(n=21)   — borderline
  Lifetime (from enriched_signals.parquet, OPEN excluded):
    7. lifetime-universal (n≈105,781)
    8. lifetime-Bear      (n=17,828)
    9. lifetime-Bull      (n=45,262)
   10. lifetime-Choppy    (n=31,553)

Splits:
  numeric features → median split (low / high quantile)
  categorical features → per-category WR + chi-square
  bool features → True vs False WR

Run:
    .venv/bin/python lab/analyses/inv_phase2_univariate.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_LAB_ROOT = _HERE.parent
sys.path.insert(0, str(_LAB_ROOT / "infrastructure"))

from feature_loader import FeatureRegistry  # noqa: E402
from feature_extractor import _FEAT_PREFIX  # noqa: E402

try:
    from scipy import stats  # noqa: E402
except ImportError:
    print("scipy required; install via .venv/bin/pip install scipy",
          file=sys.stderr)
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────
LIVE_PARQUET = _LAB_ROOT / "output" / "live_signals_with_features.parquet"
LIFETIME_PARQUET = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _LAB_ROOT / "output" / "univariate_importance.json"

WIN_OUTCOMES_LIFETIME = ("DAY6_WIN", "TARGET_HIT")
LOSS_OUTCOMES_LIFETIME = ("DAY6_LOSS", "STOP_HIT")


def _wlf_lifetime(outcome: str) -> str:
    if outcome in WIN_OUTCOMES_LIFETIME:
        return "W"
    if outcome in LOSS_OUTCOMES_LIFETIME:
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def _is_nan(v) -> bool:
    if isinstance(v, str):
        return False
    try:
        return pd.isna(v)
    except Exception:
        return False


# ── Per-feature analysis ──────────────────────────────────────────────

def _analyze_numeric(values: pd.Series, wlf: pd.Series) -> dict:
    """Median-split univariate. Returns wr_low, wr_high, edge_pp, p_value,
    effect_size (Cohen's d), n_low, n_high."""
    valid = values.notna() & wlf.isin(["W", "L"])
    v = pd.to_numeric(values[valid], errors="coerce")
    y = wlf[valid]
    valid2 = v.notna()
    v = v[valid2]; y = y[valid2]
    if len(v) < 10 or v.std() == 0:
        return {"wr_low": None, "wr_high": None, "edge_pp": 0.0,
                "p_value": 1.0, "effect_size": 0.0,
                "n_low": 0, "n_high": 0, "method": "numeric_median_split"}
    median = float(v.median())
    low_mask = v <= median
    high_mask = ~low_mask
    n_low = int(low_mask.sum()); n_high = int(high_mask.sum())
    if n_low < 5 or n_high < 5:
        return {"wr_low": None, "wr_high": None, "edge_pp": 0.0,
                "p_value": 1.0, "effect_size": 0.0,
                "n_low": n_low, "n_high": n_high,
                "method": "numeric_median_split"}
    wins_low = int((y[low_mask] == "W").sum())
    losses_low = int((y[low_mask] == "L").sum())
    wins_high = int((y[high_mask] == "W").sum())
    losses_high = int((y[high_mask] == "L").sum())
    wr_low = wins_low / max(1, wins_low + losses_low)
    wr_high = wins_high / max(1, wins_high + losses_high)
    edge_pp = abs(wr_high - wr_low)
    # t-test on feature value between W and L
    v_w = v[y == "W"]; v_l = v[y == "L"]
    if len(v_w) >= 2 and len(v_l) >= 2 and v_w.std() > 0 and v_l.std() > 0:
        t_stat, p_value = stats.ttest_ind(v_w, v_l, equal_var=False)
        # Cohen's d
        pooled_std = np.sqrt(((len(v_w) - 1) * v_w.var()
                                + (len(v_l) - 1) * v_l.var())
                               / (len(v_w) + len(v_l) - 2))
        effect_size = (
            float((v_w.mean() - v_l.mean()) / pooled_std)
            if pooled_std > 0 else 0.0)
    else:
        p_value = 1.0
        effect_size = 0.0
    return {
        "wr_low": float(wr_low),
        "wr_high": float(wr_high),
        "edge_pp": float(edge_pp),
        "p_value": float(p_value) if not pd.isna(p_value) else 1.0,
        "effect_size": float(effect_size),
        "n_low": n_low,
        "n_high": n_high,
        "method": "numeric_median_split",
    }


def _analyze_categorical(values: pd.Series, wlf: pd.Series) -> dict:
    """Per-category WR + chi-square + Cramér's V."""
    valid = values.notna() & wlf.isin(["W", "L"])
    v = values[valid].astype(str)
    y = wlf[valid]
    if len(v) < 10:
        return {"wr_per_value": {}, "edge_pp": 0.0,
                "p_value": 1.0, "effect_size": 0.0,
                "method": "categorical_chi2"}
    # Contingency table
    crosstab = pd.crosstab(v, y).reindex(columns=["W", "L"], fill_value=0)
    if crosstab.shape[0] < 2 or crosstab.values.sum() < 10:
        return {"wr_per_value": {}, "edge_pp": 0.0,
                "p_value": 1.0, "effect_size": 0.0,
                "method": "categorical_chi2"}
    wr_per_value = {}
    for cat in crosstab.index:
        w = int(crosstab.loc[cat, "W"])
        l = int(crosstab.loc[cat, "L"])
        if w + l > 0:
            wr_per_value[str(cat)] = w / (w + l)
    if not wr_per_value:
        return {"wr_per_value": {}, "edge_pp": 0.0,
                "p_value": 1.0, "effect_size": 0.0,
                "method": "categorical_chi2"}
    edge_pp = max(wr_per_value.values()) - min(wr_per_value.values())
    try:
        chi2, p_value, dof, exp = stats.chi2_contingency(crosstab.values)
        n = crosstab.values.sum()
        # Cramér's V
        min_dim = min(crosstab.shape) - 1
        cramer_v = (
            float(np.sqrt(chi2 / (n * min_dim)))
            if (n * min_dim) > 0 else 0.0)
    except Exception:
        p_value = 1.0
        cramer_v = 0.0
    return {
        "wr_per_value": wr_per_value,
        "edge_pp": float(edge_pp),
        "p_value": float(p_value) if not pd.isna(p_value) else 1.0,
        "effect_size": float(cramer_v),
        "method": "categorical_chi2",
    }


def _analyze_bool(values: pd.Series, wlf: pd.Series) -> dict:
    """True/False WR + chi-square."""
    valid = values.notna() & wlf.isin(["W", "L"])
    v = values[valid]
    y = wlf[valid]
    # Coerce to bool — treat truthy/1 as True, falsy/0 as False
    try:
        vb = v.astype(bool) if v.dtype != object else v.apply(
            lambda x: bool(x) if not pd.isna(x) else False)
    except Exception:
        return {"wr_true": None, "wr_false": None, "edge_pp": 0.0,
                "p_value": 1.0, "effect_size": 0.0, "method": "bool_chi2"}
    n_true = int(vb.sum()); n_false = int((~vb).sum())
    if n_true < 5 or n_false < 5:
        return {"wr_true": None, "wr_false": None, "edge_pp": 0.0,
                "p_value": 1.0, "effect_size": 0.0,
                "n_true": n_true, "n_false": n_false,
                "method": "bool_chi2"}
    wins_t = int((y[vb] == "W").sum())
    losses_t = int((y[vb] == "L").sum())
    wins_f = int((y[~vb] == "W").sum())
    losses_f = int((y[~vb] == "L").sum())
    wr_true = wins_t / max(1, wins_t + losses_t)
    wr_false = wins_f / max(1, wins_f + losses_f)
    edge_pp = abs(wr_true - wr_false)
    crosstab = np.array([[wins_t, losses_t], [wins_f, losses_f]])
    try:
        chi2, p_value, _, _ = stats.chi2_contingency(crosstab)
        n = crosstab.sum()
        cramer_v = float(np.sqrt(chi2 / n)) if n > 0 else 0.0
    except Exception:
        p_value = 1.0
        cramer_v = 0.0
    return {
        "wr_true": float(wr_true),
        "wr_false": float(wr_false),
        "edge_pp": float(edge_pp),
        "p_value": float(p_value) if not pd.isna(p_value) else 1.0,
        "effect_size": float(cramer_v),
        "n_true": n_true,
        "n_false": n_false,
        "method": "bool_chi2",
    }


# ── Cohort-level driver ────────────────────────────────────────────────

def analyze_cohort(df: pd.DataFrame, registry: FeatureRegistry,
                     cohort_name: str) -> list[dict]:
    """Run univariate analysis on a cohort. Returns list of feature stats."""
    if "wlf" not in df.columns:
        raise ValueError(f"{cohort_name}: missing 'wlf' column")
    n_w = int((df["wlf"] == "W").sum())
    n_l = int((df["wlf"] == "L").sum())
    if n_w + n_l < 10:
        print(f"  {cohort_name}: too small (n_w={n_w}, n_l={n_l}); skipping")
        return []

    results = []
    for spec in registry.list_all():
        col = _FEAT_PREFIX + spec.feature_id
        if col not in df.columns:
            continue
        if spec.value_type == "categorical":
            stat = _analyze_categorical(df[col], df["wlf"])
        elif spec.value_type == "bool":
            stat = _analyze_bool(df[col], df["wlf"])
        else:  # float / int
            stat = _analyze_numeric(df[col], df["wlf"])
        result = {
            "feature_id": spec.feature_id,
            "family": spec.family,
            "value_type": spec.value_type,
            "n_w": n_w,
            "n_l": n_l,
            **stat,
        }
        results.append(result)

    # Sort by edge_pp descending
    results.sort(key=lambda r: -r["edge_pp"])
    return results


# ── Main ──────────────────────────────────────────────────────────────

def build_cohorts() -> dict:
    """Build the 10-cohort dict {cohort_name: DataFrame}."""
    cohorts = {}

    # Live cohorts
    print("Loading live_signals_with_features...")
    live = pd.read_parquet(LIVE_PARQUET)
    cohorts["universal-live"] = live
    cohorts["Bear-live"] = live[live["regime"] == "Bear"].copy()
    cohorts["Choppy-live"] = live[live["regime"] == "Choppy"].copy()
    cohorts["UP_TRI-live"] = live[live["signal"] == "UP_TRI"].copy()
    cohorts["DOWN_TRI-live"] = live[live["signal"] == "DOWN_TRI"].copy()
    cohorts["BULL_PROXY-live"] = live[live["signal"] == "BULL_PROXY"].copy()

    # Lifetime cohorts
    print("Loading enriched_signals (lifetime)...")
    lifetime = pd.read_parquet(LIFETIME_PARQUET)
    lifetime = lifetime[lifetime["outcome"] != "OPEN"].copy()
    lifetime["wlf"] = lifetime["outcome"].apply(_wlf_lifetime)
    lifetime = lifetime[lifetime["wlf"].isin(["W", "L", "F"])].copy()
    cohorts["lifetime-universal"] = lifetime
    cohorts["lifetime-Bear"] = lifetime[lifetime["regime"] == "Bear"].copy()
    cohorts["lifetime-Bull"] = lifetime[lifetime["regime"] == "Bull"].copy()
    cohorts["lifetime-Choppy"] = lifetime[lifetime["regime"] == "Choppy"].copy()
    return cohorts


def main():
    print("─" * 72)
    print("Phase 2 SUB-BLOCK 2B — Univariate feature importance analysis")
    print("─" * 72)

    t0 = time.time()
    registry = FeatureRegistry.load_all()
    cohorts = build_cohorts()

    print()
    output: dict = {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "cohorts": {},
    }

    # Print cohort sizes upfront
    print("Cohort sizes:")
    for name, df in cohorts.items():
        n_w = int((df["wlf"] == "W").sum())
        n_l = int((df["wlf"] == "L").sum())
        n_f = int((df["wlf"] == "F").sum())
        print(f"  {name:<25} n={len(df):>7}  W={n_w:>6}  L={n_l:>6}  F={n_f:>5}")

    print()
    print("Running univariate analysis...")
    for cohort_name, df in cohorts.items():
        t_c0 = time.time()
        n_w = int((df["wlf"] == "W").sum())
        n_l = int((df["wlf"] == "L").sum())
        results = analyze_cohort(df, registry, cohort_name)
        elapsed = time.time() - t_c0
        output["cohorts"][cohort_name] = {
            "n": len(df),
            "n_w": n_w,
            "n_l": n_l,
            "n_features_ranked": len(results),
            "ranked_features": results,
        }
        print(f"  {cohort_name:<25} {len(results):>4} features in "
              f"{elapsed:.2f}s")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as fh:
        json.dump(output, fh, indent=2, default=str)
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {OUTPUT_PATH} ({size_kb:.1f} KB)")
    print(f"Total runtime: {time.time() - t0:.1f}s")

    # Surface top 5 per cohort for sanity check
    print()
    print("═" * 72)
    print("TOP 5 FEATURES PER COHORT (by edge_pp)")
    print("═" * 72)
    for cohort_name, c in output["cohorts"].items():
        n_w, n_l = c["n_w"], c["n_l"]
        warn = " ⚠" if n_l < 20 else ""
        print(f"\n{cohort_name} (n_w={n_w}, n_l={n_l}){warn}:")
        if not c["ranked_features"]:
            print("  (no features ranked)")
            continue
        print(f"  {'rank':<5}{'feature_id':<40}{'family':<22}"
              f"{'edge_pp':>10}{'p':>10}{'effect':>10}")
        for i, r in enumerate(c["ranked_features"][:5], 1):
            edge = r.get("edge_pp", 0)
            p = r.get("p_value", 1)
            eff = r.get("effect_size", 0)
            print(f"  {i:<5}{r['feature_id']:<40}{r['family']:<22}"
                  f"{edge:>10.3f}{p:>10.4f}{eff:>10.3f}")


if __name__ == "__main__":
    main()
