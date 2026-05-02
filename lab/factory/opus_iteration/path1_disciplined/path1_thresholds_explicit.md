# Path 1 — Lab Threshold Reference (Authoritative)

**Date:** 2026-05-03
**Source:** Lab feature library JSON specs + sub-regime detector code
**Purpose:** Eliminate bucket-threshold ambiguity that caused 5 of 9
Step 3 validation failures. These are the EXACT thresholds Lab analyses
used; do not infer or substitute.

There are TWO threshold systems in Lab. They are NOT interchangeable.

---

## A. Feature library thresholds (canonical "low/medium/high" labels)

These are the global thresholds used by `combination_generator.py` and
referenced when a playbook says "feature=low" or "feature=high". Applied
to per-signal feature values.

### Continuous features

| Feature | low | medium | high |
|---|---|---|---|
| `feat_market_breadth_pct` | `<0.30` | `0.30-0.60` | `>0.60` |
| `feat_nifty_200d_return_pct` | `<-0.10` | `-0.10 to 0.10` | `>0.10` |
| `feat_nifty_60d_return_pct` | `<-0.10` | `-0.10 to 0.10` | `>0.10` |
| `feat_nifty_20d_return_pct` | `<-0.05` | `-0.05 to 0.05` | `>0.05` |
| `feat_nifty_vol_percentile_20d` | `<0.30` | `0.30-0.70` | `>0.70` |
| `feat_ROC_10` | `<-0.03` | `-0.03 to 0.03` | `>0.03` |
| `feat_RSI_14` | `<30` | `30-70` | `>70` |
| `feat_coiled_spring_score` | `<33` | `33-67` | `>67` |
| `feat_multi_tf_alignment_score` | `<1` | `1-2` | `>2` |
| `feat_range_compression_60d` | `<0.08` | `0.08-0.20` | `>0.20` |
| `feat_52w_high_distance_pct` | `<0.05` | `0.05-0.20` | `>0.20` |
| `feat_52w_low_distance_pct` | `<0.05` | `0.05-0.20` | `>0.20` |
| `feat_sector_index_20d_return_pct` | `<-0.05` | `-0.05 to 0.05` | `>0.05` |
| `feat_sector_index_60d_return_pct` | `<-0.10` | `-0.10 to 0.10` | `>0.10` |
| `feat_bank_nifty_20d_return_pct` | `<-0.05` | `-0.05 to 0.05` | `>0.05` |
| `feat_bank_nifty_60d_return_pct` | `<-0.10` | `-0.10 to 0.10` | `>0.10` |

### Integer-count features

| Feature | low | medium | high |
|---|---|---|---|
| `feat_fvg_unfilled_above_count` | `<2` | `2-5` | `>5` |
| `feat_fvg_unfilled_below_count` | `<2` | `2-5` | `>5` |
| `feat_swing_high_count_20d` | `<2` | `2-3` | `>3` |
| `feat_swing_low_count_20d` | `<2` | `2-3` | `>3` |

### Categorical features (no bucketing — pass-through values)

| Feature | Values |
|---|---|
| `feat_nifty_vol_regime` | `Low`, `Medium`, `High` (computed from p30/p70 of vol distribution) |
| `feat_consolidation_quality` | `none`, `low`, `medium`, `high` |
| `feat_ema_alignment` | `bull`, `bear`, `mixed` |
| `feat_MACD_signal` | `bull`, `bear` |
| `feat_day_of_month_bucket` | `wk1` (≤7), `wk2` (8-14), `wk3` (15-21), `wk4` (>21) |
| `feat_day_of_week` | `Mon`, `Tue`, `Wed`, `Thu`, `Fri` |
| `feat_sector_momentum_state` | per scanner enrichment |
| `feat_vol_climax_flag` | bool (True/False) |
| `feat_inside_bar_flag` | bool |
| `feat_higher_highs_intact_flag` | bool |

### Note on `feat_nifty_vol_regime` (categorical, NOT vol_percentile)

`feat_nifty_vol_regime` is a 3-bucket categorical computed from
`feat_nifty_vol_percentile_20d`:
- `Low`: vol_pct < 0.30
- `Medium`: 0.30 ≤ vol_pct ≤ 0.70
- `High`: vol_pct > 0.70

When a playbook says "vol=Medium" or "vol_regime=High", it refers to
this CATEGORICAL feature directly, NOT a tertile of vol_percentile.

---

## B. Sub-regime detector thresholds (per regime)

These are SEPARATE from feature library thresholds. They are used by
the sub-regime detectors and produce composite labels (hot/cold,
recovery_bull/healthy_bull/late_bull/normal_bull, etc.). The detectors
use DIFFERENT thresholds than the feature library for the same
underlying features.

### Bear sub-regime detector

Source: `lab/factory/bear/subregime/detector.py`

```python
HOT_VOL_THRESHOLD = 0.70       # nifty_vol_percentile_20d > 0.70
HOT_RETURN_THRESHOLD = -0.10   # nifty_60d_return_pct < -0.10

def detect_bear_subregime(vp, n60):
    is_hot = (vp > 0.70 AND n60 < -0.10)
    return "hot" if is_hot else "cold"
```

Bear UP_TRI playbook adds `warm` per S2 critique:
- `hot`: vp > 0.70 AND n60 < -0.10 (15% lifetime, 68.3% WR)
- `warm`: vp > 0.70 AND -0.10 ≤ n60 < 0 (added in S2; live evidence
  95.2% on n=42)
- `cold`: everything else (~85% lifetime, ~49-55% WR)

### Bull sub-regime detector

Source: `lab/factory/bull/subregime/detector.py` (predicted_v2 axes)

```python
def detect_bull_subregime(p_200d, breadth):
    # 200d level
    p_level = "low" if p_200d < 0.05 else ("high" if p_200d > 0.20 else "mid")
    # breadth level
    s_level = "low" if breadth < 0.60 else ("high" if breadth > 0.80 else "mid")

    if p_level == "low" and s_level == "low":
        return "recovery_bull"   # 60.2% WR, n=972 (2.6%)
    if p_level == "mid" and s_level == "high":
        return "healthy_bull"    # 58.0% WR, n=4,764 (12.5%)
    if p_level == "mid" and s_level == "low":
        return "late_bull"       # 45.1% WR, n=2,699 (7.1%)
    return "normal_bull"          # 51.3% WR, n=29,110 (76.4%)
```

**CRITICAL:** Bull detector breadth thresholds are 0.60/0.80, NOT the
feature library's 0.30/0.60. recovery_bull "low breadth" means
breadth < 0.60, not breadth < 0.30.

**CRITICAL:** Bull detector 200d_return thresholds are 0.05/0.20, NOT
the feature library's -0.10/0.10. recovery_bull "low 200d" means
200d_return < 0.05 (not < -0.10).

### Choppy sub-regime detector (current 2-axis, pre-C1)

Source: `lab/factory/choppy/subregime/detector_design.py`

```python
QUIET_MAX = 0.30          # vol_percentile < 0.30
STRESS_MIN = 0.70         # vol_percentile > 0.70
BREADTH_LOW_MAX = 0.30
BREADTH_HIGH_MIN = 0.60
```

Vol-axis tiers:
- `quiet`: vp < 0.30
- `stress`: vp > 0.70
- `equilibrium`: 0.30 ≤ vp ≤ 0.70

Breadth-axis tiers:
- `low`: breadth < 0.30
- `high`: breadth > 0.60
- `mid`: 0.30 ≤ breadth ≤ 0.60

Choppy detector breadth thresholds match feature library (0.30/0.60).

### Choppy sub-regime detector V2 (3-axis, per C1 critique)

Adds momentum axis using `nifty_20d_return_pct`. C1 found tertile
splits work; **but C1 used 33/67 percentile splits, while feature
library uses fixed thresholds (-0.05/0.05).** Path 1 should use the
**feature library thresholds** (-0.05/0.05) for consistency.

---

## C. How to apply thresholds in rule conditions

When generating rules, conditions referencing feature buckets MUST use
the feature library thresholds. The validation harness will apply them
with operators:

```json
{"feature": "feat_market_breadth_pct", "value": 0.30, "operator": "lt"}
```

means "market_breadth_pct < 0.30" (i.e., breadth=low per library).

Equivalent shorthand using bucketed comparison:
```json
{"feature": "feat_market_breadth_pct_bucket", "value": "low", "operator": "eq"}
```

Path 1 conventions: **prefer numeric thresholds over bucket labels**
when generating rules. Numeric thresholds are unambiguous and don't
depend on the harness's bucketing logic.

For sub-regime gating (recovery_bull, hot, etc.), use:
```json
{"feature": "sub_regime", "value": "recovery_bull", "operator": "eq"}
```

`sub_regime` is computed at runtime per the detector specs above.

---

## D. Threshold mismatches that broke Step 3 validation

Step 3 validation harness used 33/67 tertile splits for ALL continuous
features. This produced incorrect populations:

| Feature | Lab threshold | Step 3 harness | Impact |
|---|---|---|---|
| `market_breadth_pct` low | <0.30 | <0.456 | recovery_bull n=199 vs Lab 972 (5x undercount) |
| `swing_high_count_20d` low | <2 | ≤1 | rule_012 0 matches |
| `fvg_unfilled_above_count` low | <2 | ≤1 | rule_003 0 matches |
| `nifty_20d_return` high | >0.05 | >+0.0072 | rule_004 wrong population |

Path 1 explicit-threshold mandate: USE THE LAB THRESHOLDS DOCUMENTED
HERE. Do not infer; do not substitute tertiles; do not invent.

Validation harness for Path 1 will be updated to use these exact
thresholds. Predictions Opus produces will be evaluated against the
corrected harness.
