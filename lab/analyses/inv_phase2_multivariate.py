"""
Phase 2 SUB-BLOCK 2C — Multivariate feature importance (lifetime only).

Per the adjusted cohort plan (Phase 2 critical-flag review): live cohorts
get univariate-only ranking due to small n (200 obs / 114 features = 1.75
obs/feat, severe overfit risk). Multivariate (RF + L1 logistic) runs only
on the 4 lifetime cohorts where n is large.

Outputs lab/output/multivariate_importance.json with structure:
  {cohort: {rf: [...], logistic: [...], auc_rf, auc_logistic}}

Run:
    .venv/bin/python lab/analyses/inv_phase2_multivariate.py
"""
from __future__ import annotations

import json
import sys
import time
import warnings
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
    from sklearn.ensemble import RandomForestClassifier  # noqa: E402
    from sklearn.linear_model import LogisticRegression  # noqa: E402
    from sklearn.model_selection import StratifiedKFold, cross_val_score  # noqa: E402
    from sklearn.preprocessing import StandardScaler  # noqa: E402
    from sklearn.metrics import roc_auc_score  # noqa: E402
    from sklearn.impute import SimpleImputer  # noqa: E402
except ImportError:
    print("scikit-learn required; install via "
          ".venv/bin/pip install scikit-learn",
          file=sys.stderr)
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────
LIFETIME_PARQUET = _LAB_ROOT / "output" / "enriched_signals.parquet"
OUTPUT_PATH = _LAB_ROOT / "output" / "multivariate_importance.json"

WIN_OUTCOMES_LIFETIME = ("DAY6_WIN", "TARGET_HIT")
LOSS_OUTCOMES_LIFETIME = ("DAY6_LOSS", "STOP_HIT")

# Random forest hyperparams
RF_N_ESTIMATORS = 200
RF_MAX_DEPTH = 10
RANDOM_STATE = 42

# Sample lifetime cohorts to keep RF fit time reasonable. Lifetime-universal
# has 94K rows × 114 features → ~10-15 min RF fit; sample to 25K.
LIFETIME_SAMPLE_CAP = 25_000


def _wlf_lifetime(outcome: str) -> str:
    if outcome in WIN_OUTCOMES_LIFETIME:
        return "W"
    if outcome in LOSS_OUTCOMES_LIFETIME:
        return "L"
    if outcome == "DAY6_FLAT":
        return "F"
    return "?"


def _prepare_X_y(df: pd.DataFrame, registry: FeatureRegistry) -> tuple:
    """Build feature matrix X (numeric only; categoricals one-hot encoded)
    and binary target y from a cohort DataFrame.

    Strategy for missing values: SimpleImputer with median (numeric).
    Categorical features: one-hot encoded (NaN → all-zero row).
    """
    # Filter to W/L only
    wl = df[df["wlf"].isin(["W", "L"])].copy()
    y = (wl["wlf"] == "W").astype(int).values

    feat_cols = []
    numeric_X = []
    cat_X_pieces = []
    feature_names = []

    for spec in registry.list_all():
        col = _FEAT_PREFIX + spec.feature_id
        if col not in wl.columns:
            continue
        if spec.value_type == "categorical":
            # One-hot encode
            s = wl[col].astype(str).fillna("missing")
            dummies = pd.get_dummies(s, prefix=spec.feature_id, dummy_na=False)
            cat_X_pieces.append(dummies)
            feature_names.extend(dummies.columns.tolist())
        elif spec.value_type == "bool":
            # Coerce to 0/1 numeric; NaN → median imputed later
            s = pd.to_numeric(wl[col].astype(float), errors="coerce")
            numeric_X.append(s.values.reshape(-1, 1))
            feature_names.append(spec.feature_id)
        else:
            # float / int
            s = pd.to_numeric(wl[col], errors="coerce")
            numeric_X.append(s.values.reshape(-1, 1))
            feature_names.append(spec.feature_id)
        feat_cols.append(spec.feature_id)

    # Stack numeric
    X_num = np.hstack(numeric_X) if numeric_X else np.empty((len(wl), 0))
    # Impute median per column
    if X_num.shape[1] > 0:
        imputer = SimpleImputer(strategy="median")
        X_num = imputer.fit_transform(X_num)
    # Stack categorical (already 0/1, no NaN)
    X_cat = (pd.concat(cat_X_pieces, axis=1).values
              if cat_X_pieces else np.empty((len(wl), 0)))
    X = np.hstack([X_num, X_cat])
    return X, y, feature_names


def _run_random_forest(X, y, feature_names: list[str]) -> dict:
    rf = RandomForestClassifier(
        n_estimators=RF_N_ESTIMATORS,
        max_depth=RF_MAX_DEPTH,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    # 5-fold cross-validated AUC
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    auc_scores = cross_val_score(rf, X, y, cv=skf, scoring="roc_auc",
                                    n_jobs=-1)
    auc_mean = float(auc_scores.mean())
    # Fit full data for feature importances
    rf.fit(X, y)
    importances = rf.feature_importances_
    # Aggregate one-hot encoded categorical importances back to feature_id
    return {"auc": auc_mean,
              "importances_per_column": importances.tolist(),
              "feature_names": feature_names}


def _run_logistic(X, y, feature_names: list[str]) -> dict:
    # Standardize numeric features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    lr = LogisticRegression(
        penalty="l1",
        solver="liblinear",
        C=0.1,  # L1 regularization strength
        class_weight="balanced",
        max_iter=1000,
        random_state=RANDOM_STATE,
    )
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    auc_scores = cross_val_score(lr, X_scaled, y, cv=skf, scoring="roc_auc",
                                    n_jobs=-1)
    auc_mean = float(auc_scores.mean())
    lr.fit(X_scaled, y)
    coefs = lr.coef_[0]
    return {"auc": auc_mean,
              "coefs_per_column": coefs.tolist(),
              "feature_names": feature_names}


def _aggregate_per_feature(importances_or_coefs: list[float],
                              feature_names: list[str],
                              registry: FeatureRegistry) -> list[dict]:
    """Aggregate per-column scores back to per-feature_id (sum for one-hot
    columns sharing the same feature_id prefix). Returns ranked list."""
    feat_id_set = {s.feature_id for s in registry.list_all()}
    agg: dict[str, float] = {fid: 0.0 for fid in feat_id_set}

    for col_name, score in zip(feature_names, importances_or_coefs):
        # Match either exact feature_id or prefix for one-hot dummies
        if col_name in feat_id_set:
            agg[col_name] += abs(float(score))
            continue
        for fid in feat_id_set:
            if col_name.startswith(fid + "_"):
                agg[fid] += abs(float(score))
                break
    # Rank by importance descending
    ranked = sorted(agg.items(), key=lambda t: -t[1])
    return [{"feature_id": fid, "importance": imp, "rank": i + 1}
              for i, (fid, imp) in enumerate(ranked)]


def _aggregate_logistic_with_signs(coefs: list[float],
                                       feature_names: list[str],
                                       registry: FeatureRegistry) -> list[dict]:
    """Like _aggregate but preserves signed coefs (we sum abs for ranking,
    track dominant sign for direction)."""
    feat_id_set = {s.feature_id for s in registry.list_all()}
    coef_signed: dict[str, float] = {fid: 0.0 for fid in feat_id_set}
    coef_abs: dict[str, float] = {fid: 0.0 for fid in feat_id_set}

    for col_name, c in zip(feature_names, coefs):
        target = None
        if col_name in feat_id_set:
            target = col_name
        else:
            for fid in feat_id_set:
                if col_name.startswith(fid + "_"):
                    target = fid
                    break
        if target is None:
            continue
        coef_signed[target] += float(c)
        coef_abs[target] += abs(float(c))

    ranked = sorted(coef_abs.items(), key=lambda t: -t[1])
    out = []
    for i, (fid, mag) in enumerate(ranked):
        sign = ("+" if coef_signed[fid] > 0
                  else "-" if coef_signed[fid] < 0 else "0")
        out.append({"feature_id": fid, "coef_magnitude": mag,
                    "coef_signed": coef_signed[fid], "coef_sign": sign,
                    "rank": i + 1})
    return out


def main():
    print("─" * 72)
    print("Phase 2 SUB-BLOCK 2C — Multivariate (RF + L1 logistic, "
          "lifetime cohorts only)")
    print("─" * 72)

    t0 = time.time()
    registry = FeatureRegistry.load_all()

    print("Loading enriched_signals (lifetime)...")
    lifetime = pd.read_parquet(LIFETIME_PARQUET)
    lifetime = lifetime[lifetime["outcome"] != "OPEN"].copy()
    lifetime["wlf"] = lifetime["outcome"].apply(_wlf_lifetime)
    lifetime = lifetime[lifetime["wlf"].isin(["W", "L", "F"])].copy()

    cohorts = {
        "lifetime-universal": lifetime,
        "lifetime-Bear": lifetime[lifetime["regime"] == "Bear"].copy(),
        "lifetime-Bull": lifetime[lifetime["regime"] == "Bull"].copy(),
        "lifetime-Choppy": lifetime[lifetime["regime"] == "Choppy"].copy(),
    }

    # Sample large cohorts for tractable RF fit time
    rng = np.random.RandomState(RANDOM_STATE)
    sampled_cohorts = {}
    for name, df in cohorts.items():
        if len(df) > LIFETIME_SAMPLE_CAP:
            # Sample preserving W/L ratio via stratified sampling
            df_sampled = df.groupby("wlf", group_keys=False).apply(
                lambda g: g.sample(
                    n=int(LIFETIME_SAMPLE_CAP * len(g) / len(df)),
                    random_state=RANDOM_STATE),
                include_groups=False,
            )
            # The .apply drops 'wlf' column; restore it
            wlf_col = []
            for wlf_val, g in df.groupby("wlf"):
                n_take = int(LIFETIME_SAMPLE_CAP * len(g) / len(df))
                wlf_col.extend([wlf_val] * n_take)
            df_sampled["wlf"] = wlf_col[:len(df_sampled)]
            sampled_cohorts[name] = df_sampled
        else:
            sampled_cohorts[name] = df

    print()
    print("Cohort sampling (cap=" + f"{LIFETIME_SAMPLE_CAP}):")
    for name, df in sampled_cohorts.items():
        n_full = len(cohorts[name])
        n_w = int((df["wlf"] == "W").sum())
        n_l = int((df["wlf"] == "L").sum())
        print(f"  {name:<25} full_n={n_full:>7}  sampled_n={len(df):>6}  "
              f"W={n_w:>5}  L={n_l:>5}")

    output: dict = {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rf_hyperparams": {"n_estimators": RF_N_ESTIMATORS,
                            "max_depth": RF_MAX_DEPTH},
        "logistic_hyperparams": {"penalty": "l1", "C": 0.1, "solver": "liblinear"},
        "lifetime_sample_cap": LIFETIME_SAMPLE_CAP,
        "cohorts": {},
    }

    print()
    for name, df in sampled_cohorts.items():
        print(f"\n=== {name} ===")
        t_c0 = time.time()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=FutureWarning)
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            X, y, feature_names = _prepare_X_y(df, registry)
            if X.shape[0] < 50 or len(np.unique(y)) < 2:
                print("  too small or unbalanced; skipping")
                continue
            print(f"  X shape: {X.shape}  W/L: {y.sum()}/{len(y)-y.sum()}")
            print(f"  Running RandomForest (n_est={RF_N_ESTIMATORS}, "
                  f"max_depth={RF_MAX_DEPTH})...")
            rf_result = _run_random_forest(X, y, feature_names)
            print(f"    RF AUC (5-fold CV): {rf_result['auc']:.3f}")
            rf_ranked = _aggregate_per_feature(
                rf_result["importances_per_column"],
                rf_result["feature_names"], registry)

            print(f"  Running L1 LogisticRegression (C=0.1)...")
            lr_result = _run_logistic(X, y, feature_names)
            print(f"    Logistic AUC (5-fold CV): {lr_result['auc']:.3f}")
            lr_ranked = _aggregate_logistic_with_signs(
                lr_result["coefs_per_column"],
                lr_result["feature_names"], registry)

        elapsed = time.time() - t_c0
        output["cohorts"][name] = {
            "n": len(df),
            "n_w": int(y.sum()),
            "n_l": int(len(y) - y.sum()),
            "auc_rf": rf_result["auc"],
            "auc_logistic": lr_result["auc"],
            "rf": rf_ranked,
            "logistic": lr_ranked,
        }
        print(f"  cohort done in {elapsed:.1f}s")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as fh:
        json.dump(output, fh, indent=2, default=str)
    size_kb = OUTPUT_PATH.stat().st_size / 1024
    print(f"\nSaved: {OUTPUT_PATH} ({size_kb:.1f} KB)")
    print(f"Total runtime: {time.time() - t0:.1f}s")

    # Surface AUC + top 10 per cohort
    print()
    print("═" * 72)
    print("MULTIVARIATE RESULTS — TOP 10 PER METHOD PER COHORT")
    print("═" * 72)
    for name, c in output["cohorts"].items():
        print(f"\n{name} (n={c['n']}, W={c['n_w']}, L={c['n_l']}):")
        print(f"  RF AUC: {c['auc_rf']:.3f}   "
              f"Logistic AUC: {c['auc_logistic']:.3f}")
        if c['auc_rf'] < 0.55:
            print(f"  ⚠ AUC < 0.55 — signal too weak; ranking unreliable")
        print("  Top 10 RF:")
        for r in c["rf"][:10]:
            print(f"    {r['rank']:>3}. {r['feature_id']:<40} "
                  f"importance={r['importance']:.4f}")
        print("  Top 10 Logistic L1:")
        for r in c["logistic"][:10]:
            print(f"    {r['rank']:>3}. {r['feature_id']:<40} "
                  f"|coef|={r['coef_magnitude']:.3f}  sign={r['coef_sign']}")


if __name__ == "__main__":
    main()
