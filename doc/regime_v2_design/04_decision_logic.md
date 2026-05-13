# 04 — Decision Logic

## Methodology choice: rule-based, NOT ML

Why rule-based:
1. **Auditable** — every label is explained by which gate fired. The user (and consultant) can read the rule and verify.
2. **No training set required** — ML needs labeled history; we have 281 resolved signals but no ground-truth regime labels independent of the current broken classifier.
3. **Operationalize constraint (1-of-6)** — adding ML adds an opaque dependency, model versioning, calibration drift, retraining schedule. None of which the user has demonstrated capacity to maintain.
4. **Consultant alignment** — the consultant treats regime as a discrete state with thresholds (Bear/sub_regime=hot per `round_09_phase3_vp_fix.pdf §1`). Rule-based v2 is the natural extension of that framing.
5. **Reversibility** — a rule-based classifier is one config change away from v1 in case of failure.

Hybrid (rule + ML refinement) is **deferred to v3** once we have:
- 6+ months of v2 labels + outcomes
- Ground-truth regime labels (operator-tagged or consultant-tagged) for backfill

## The 5-gate decision tree (priority order)

Evaluated top-down. **First match wins.**

### Gate 1: Bull (most restrictive)

```pseudocode
if (above_ema50 = True)
   AND (above_ema200 = True)
   AND (slope_10d_ema50 > 0.005)
   AND (ret20_pct > 0)
   AND (india_vix < 18):
    return "Bull"
```

Five conditions. All must hold. The strictest gate — only fires in clean, steady-state Bull.

### Gate 2: Bear (most restrictive)

```pseudocode
if (above_ema50 = False)
   AND (above_ema200 = False)
   AND (slope_10d_ema50 < -0.003)
   AND (ret20_pct < -2.0)
   AND (india_vix > 18):
    return "Bear"
```

Five conditions. Mirror of Bull. Note: slope threshold relaxed from `-0.005` (v1) to `-0.003` based on `cohort_health.json` showing 96 UP_TRI×Bear signals in cohort_health — these fired in a stretch where slope hovered around -0.003 to -0.005. v1's `-0.005` may have missed some legitimate Bear days. The cohort preservation test (§05) will confirm this calibration.

### Gate 3: Bull-Recovery

```pseudocode
if (above_ema50 = True)
   AND (slope_10d_ema50 > 0)
   AND (slope_10d_ema50 <= 0.005)         # not yet at Bull threshold
   AND (ret20_pct > 3.0)
   AND (india_vix < 20):
    return "Bull-Recovery"
```

The transition state when price has cleared EMA50 but slope hasn't accelerated. The +7.38% ret20 case from the Apr-26 weekly snapshot maps cleanly here (vs v1's Choppy).

### Gate 4: Bear-Recovery

```pseudocode
if (above_ema50 = False)
   AND (slope_10d_ema50 > 0)              # rising slope from below EMA50
   AND (ret20_pct > 0):
    return "Bear-Recovery"
```

Three conditions. Less restrictive than Bull-Recovery because the price-below-EMA50 condition does most of the work.

### Gate 5: Choppy (residual)

```pseudocode
return "Choppy"
```

If none of Bull, Bear, Bull-Recovery, Bear-Recovery match, fall through to Choppy. This is now a true residual: high-vol-no-direction OR genuinely-flat OR mid-EMA-with-mixed-signals.

## Persistence layer (anti-whipsaw)

The gate evaluation produces a **proposed regime**. The actual regime label requires confirmation per `02_state_space.md §"Persistence rules"`:

```pseudocode
# Pseudocode for daily classifier run
proposed_regime = run_5_gate_tree(today_features)

if proposed_regime == prior_label:
    # No change: just update last_seen
    output.regime = prior_label
    output.regime_pending = None
    output.confidence_pending = None
    output.days_in_current_regime += 1

elif proposed_regime is a Recovery state:
    # 2-day confirmation
    days_pending = days_since_change_proposed(proposed_regime)
    if days_pending >= 2:
        output.regime = proposed_regime
        output.regime_pending = None
        output.days_in_current_regime = 0
    else:
        output.regime = prior_label
        output.regime_pending = proposed_regime
        output.confidence_pending = days_pending / 2

else:  # Bull or Bear or Choppy
    # 3-day confirmation
    days_pending = days_since_change_proposed(proposed_regime)
    if days_pending >= 3:
        output.regime = proposed_regime
        output.regime_pending = None
        output.days_in_current_regime = 0
    else:
        output.regime = prior_label
        output.regime_pending = proposed_regime
        output.confidence_pending = days_pending / 3
```

Whipsaw guard (P3 from §02):
```pseudocode
# After computing output.regime
recent_10d_transitions = count_transitions_in_window(history, days=10)
if recent_10d_transitions >= 3:
    output.regime = "Choppy"
    output.regime_pending = None
    output.warning = "whipsaw_lockdown_5d"
    # Lock in Choppy for next 5 days regardless of gate matches
```

## Allowed transitions check

After determining `output.regime`, verify the transition is in the allowed set per `02_state_space.md`:

```pseudocode
allowed = {
  "Bull": {"Bull-Recovery"},
  "Bull-Recovery": {"Bull", "Choppy", "Bear-Recovery"},
  "Choppy": {"Bull-Recovery", "Bear-Recovery"},
  "Bear-Recovery": {"Bear", "Bull-Recovery", "Choppy"},
  "Bear": {"Bear-Recovery", "Choppy"}
}

if prior_label != output.regime and output.regime not in allowed[prior_label]:
    # Disallowed transition — force through an intermediate state
    intermediate = find_path(prior_label, output.regime)[0]
    output.regime = intermediate
    output.warning = f"forced_transition_via_{intermediate}"
```

Example: if v1 said `Bull` yesterday and gate-tree says `Bear` today, the disallowed-jump triggers force the label to `Bull-Recovery` for one day before allowing further descent. This is rare in practice (real markets don't jump) but acts as a final sanity check.

## Worked examples

### Example 1: Today's situation (2026-05-13)

Features (from `regime_debug.json` 2026-05-13):
- nifty_close: 23379.55
- above_ema50: False
- above_ema200: ? (need to compute — current code doesn't store)
- slope_10d_ema50: +0.001079
- ret20_pct: -1.94
- india_vix: ? (not currently captured)

Assume placeholder: above_ema200 = True (Nifty 23379 vs likely EMA200 around 22500), vix = 19.

Gate evaluation:
- Gate 1 (Bull): FAIL (above_ema50=False)
- Gate 2 (Bear): FAIL (above_ema200=True; slope > -0.003)
- Gate 3 (Bull-Recovery): FAIL (above_ema50=False)
- Gate 4 (Bear-Recovery): SLOPE > 0 ✓; above_ema50=False ✓; ret20 > 0 → FAIL (ret20=-1.94)
- Gate 5 (Choppy): FALL THROUGH

→ Proposed: Choppy. (Matches diagnostic finding of "stale Choppy persists.")

But wait — slope just turned positive (+0.001 from prior days). If tomorrow's slope stays positive AND ret20 turns positive AND price still below EMA50, Gate 4 fires → Bear-Recovery (pending, day 1).

After 2 days of Bear-Recovery gate matching, Bear-Recovery label commits.

This is the **transition-aware** behavior v1 lacks. v1 stays in Choppy forever.

### Example 2: The Apr-26 weekly snapshot case

Features (per `04_regime_detector_mechanics.md`):
- above_ema50: True
- slope_10d_ema50: +0.0036
- ret20_pct: +7.38
- (assume) above_ema200: True, india_vix: 18

Gate evaluation:
- Gate 1 (Bull): slope=0.0036 ≤ 0.005 → FAIL
- Gate 2 (Bear): above_ema50=True → FAIL
- Gate 3 (Bull-Recovery): above_ema50 ✓; slope > 0 ✓; slope ≤ 0.005 ✓; ret20 > 3 ✓; vix < 20 ✓ → **MATCH** → Bull-Recovery

v1 said Choppy here. v2 says Bull-Recovery. The visual market state was post-Bear recovery. v2 is correct.

### Example 3: Hypothetical pure Bear day

- above_ema50: False
- above_ema200: False
- slope_10d_ema50: -0.008
- ret20_pct: -6.5
- india_vix: 24

Gate 2: all conditions hold → **Bear**.

Same as v1. Cohort preservation works.

## Edge cases

**Insufficient EMA200 warmup:** if the yfinance pull is missing days needed for EMA200 (e.g., very recent IPO, but Nifty index won't have this), force `above_ema200` to a known-good default (True) and log a warning.

**VIX missing:** Gates 1 and 3 require `india_vix`. If missing, downgrade the gate match:
- Gate 1 without VIX: requires `slope > 0.008` (tighter slope to compensate) to fire as Bull. Else fall through.
- Gate 3 without VIX: cannot fire. Falls through to Choppy.

**slope is NaN:** if the EMA50 calculation produces NaN at the start of the lookback window, return `regime: Unknown`.

## Why these specific thresholds

The thresholds chosen here are **calibrated initial estimates**. They will be tuned during validation (`05_validation.md`) against the cohort preservation test. The candidates:

| Threshold | Initial value | Justification |
|---|---|---|
| slope > 0.005 (Bull) | +0.005 | Matches v1; preserve Bull-cohort definition |
| slope < -0.003 (Bear) | -0.003 | Loosened from -0.005; v1 may have under-captured Bear days |
| slope ≤ 0.005 (Bull-Recovery upper) | 0.005 | Caps below Bull threshold |
| ret20 > 3.0 (Bull-Recovery) | +3.0% | Apr-26 snapshot (+7.38%) was clearly recovery; lower threshold to catch earlier recovery |
| ret20 < -2.0 (Bear) | -2.0% | One-month declines of 2%+ are statistically meaningful |
| vix < 18 (Bull) | 18 | Long-run India VIX median is ~16-17; below 18 is "complacent" |
| vix < 20 (Bull-Recovery) | 20 | Slightly looser for recovery state |
| vix > 18 (Bear) | 18 | Bear typically coincides with elevated vol |

**Threshold tuning protocol** (during validation):
- Run classifier with initial values on last 12 months of Nifty data.
- Re-label all 281 resolved signals.
- Measure UP_TRI×Bear cohort: WR, n.
- If WR < 90% (degraded from 94.7%), loosen Bear gate slightly (e.g., slope threshold -0.003 → -0.004).
- If n < 80 (5 of original 96 dropped), check which days were de-classified.
- Iterate up to 5 cycles before declaring threshold space exhausted.

## What the classifier does NOT do

- Does not produce intraday labels. Classifier runs once per morning_scan; the label holds for the trading day.
- Does not predict future regime. It classifies the current state given today's features.
- Does not output continuous regime probabilities (deferred — option E in §02).
- Does not consider sector-specific regimes (each stock might be in a different micro-regime). v2 emits one market-wide regime label. Sector context is handled by existing `sector_momentum` field on signals.

## Output schema

`output/regime_features.json` (rewritten each scan):

```json
{
  "schema_version": 2,
  "as_of_date": "YYYY-MM-DD",
  "regime": "Bear-Recovery",
  "regime_pending": null,
  "confidence_pending": null,
  "days_in_current_regime": 5,
  "prior_label": "Bear",
  "transition_date": "2026-05-15",
  "gate_fired": "bear_recovery_gate",
  "features": {
    "nifty_close": 23379.55,
    "slope_10d_ema50": 0.001079,
    "above_ema50": false,
    "above_ema20": false,
    "above_ema200": true,
    "ret20_pct": -1.94,
    "realized_vol_20d_pct": 18.4,
    "india_vix": 19.2,
    "vix_change_10d_pct": 6.3
  },
  "warnings": []
}
```

This is the file brain + bridge + telegram + PWA should read for regime info post-v2.
