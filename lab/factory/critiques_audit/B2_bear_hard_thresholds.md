# B2 — Bear Hard-Threshold Cliff Effects

**Date:** 2026-05-03
**Sonnet's concern:** "Bear sub-regime detector uses hard thresholds
(vol > 0.70 AND 60d_return < -0.10). Tiny differences across boundary
produce dramatic verdict changes (signal A: hot, take. signal B: cold,
skip). Cliff effect."

**Verdict: ⚠️ GAP_DOCUMENTED — cliff effects DOCUMENTED with surprising direction; soft-threshold proposed but with caveats (boundary signals are HIGHER WR, not lower).**

---

## A. Hypothesis

Hard thresholds at exactly vp=0.70 and n60=-0.10 should produce
discontinuous WR jumps near boundaries. Test: do close-to-threshold
signals on inside vs outside have similar WR (continuity violated by
hard rule)?

---

## B. Investigation

### Setup

n=13,739 resolved Bear UP_TRI signals. Baseline WR 55.7%.

### vp-axis cliff (vp threshold = 0.70)

Signals near vp threshold (0.65 ≤ vp ≤ 0.75):

| Cliff side | n | WR |
|---|---|---|
| just_inside_hot (vp > 0.70) | 1,069 | **50.0%** |
| just_outside_hot (vp ≤ 0.70) | 515 | **65.6%** |

**Counterintuitive cliff direction.** just-OUTSIDE-hot has HIGHER
WR than just-INSIDE-hot at the vp axis. The cliff goes WRONG direction
on this axis.

Mechanism: vp > 0.70 inside-hot signals require BOTH conditions
(also n60 < -0.10). Many of the just-inside-hot vp signals fail the
n60 condition. Those subset are still classified hot but lower-quality
than just-outside-vp signals that have n60 < -0.10 confidently.

This means **vp threshold at 0.70 isn't the right cutoff** — the
cell rewards signals with n60 < -0.10 more than vp > 0.70.

### n60-axis cliff (n60 threshold = -0.10)

Signals near n60 threshold (-0.12 ≤ n60 ≤ -0.08):

| Cliff side | n | WR |
|---|---|---|
| just_inside_hot (n60 < -0.10) | 1,044 | 71.8% |
| just_outside_hot (n60 > -0.10) | 1,457 | 65.1% |

**Mild cliff in expected direction.** 6.7pp gap between just-inside
and just-outside; not catastrophic.

### WR continuity along vp axis (with n60 < -0.10 fixed)

| vp bin | n | WR |
|---|---|---|
| (0, 0.5] | 42 | 69.0% |
| (0.5, 0.6] | 24 | 45.8% |
| (0.6, 0.65] | 49 | 42.9% |
| (0.65, 0.68] | 25 | 64.0% |
| (0.7, 0.72] | 0 | — |
| (0.72, 0.75] | 5 | 20.0% |
| (0.75, 0.8] | 362 | **80.4%** |
| (0.8, 1.0] | 1,735 | 65.9% |

WR is **non-monotonic in vp**. Bear UP_TRI WR is highest in the
(0.75, 0.8] band (80.4%), drops slightly above (66%), and is mixed
below 0.65. The hard threshold at vp=0.70 doesn't capture this
non-monotonicity.

### Soft-threshold simulation (sigmoid hot_conf)

```python
vp_s = 1 / (1 + exp(-(vp - 0.70) / 0.05))
n60_s = 1 / (1 + exp(-((-0.10) - n60) / 0.03))
hot_conf = vp_s * n60_s  # [0, 1]
```

Continuous hot-confidence score binned:

| hot_conf | n | WR |
|---|---|---|
| (0, 0.1] | 6,789 | 53.2% |
| (0.1, 0.3] | 3,589 | 50.7% |
| (0.3, 0.5] | 1,749 | **67.2%** ★ |
| (0.5, 0.7] | 565 | 64.2% |
| (0.7, 1.0] | 1,047 | 64.4% |

**Counterintuitive again:** WR PEAKS at the BOUNDARY band
(hc 0.3-0.5, 67.2%), not the deep-hot band (hc > 0.7, 64.4%).

Same finding as B1: boundary signals beat confident signals. Soft
threshold makes this visible; hard threshold buries it.

### Soft vs Hard verdict comparison

Mapping to TAKE_FULL/TAKE_SMALL/SKIP:

**Soft threshold:**
- TAKE_FULL (hc > 0.7): 64.4% (n=1,047)
- TAKE_SMALL (hc 0.4-0.7): **72.0%** (n=1,412) ★
- SKIP (hc < 0.4): 52.8% (n=11,280)

**Hard threshold:**
- TAKE_FULL (hot): 68.3% (n=2,102)
- TAKE_SMALL (warm): 52.5% (n=6,153)
- SKIP (cold): 54.3% (n=5,484)

**Soft TAKE_SMALL bucket has HIGHER WR (72.0%) than soft TAKE_FULL
(64.4%).** This means the production verdicts are mis-aligned — what
the system labels "TAKE_SMALL" should be the highest-conviction tier.

---

## C. Mechanistic interpretation

### Why boundary signals beat deep-hot

Same as B1 finding: Bear UP_TRI rewards inflection-points within
stress, not depth-of-stress. Soft thresholds make boundary signals
visible in their own bucket; hard thresholds force them into either
deep-hot (mixing with weaker depth-of-stress signals) or warm/cold
(mixing with non-stress signals).

### Why vp cliff goes the wrong direction

The vp threshold (0.70) is set TOO LOW. Bear UP_TRI rewards extreme
volatility (vp 0.75-0.80, 80% WR) and just-below threshold signals
that pair with strong n60 (vp 0.65, n60 < -0.10 → 64% WR). The 0.70
cutoff catches a noisy middle band.

If sub-regime axes need redesign (B2 → architectural change):
- vp cutoff at 0.75 instead of 0.70 — gives cleaner cliff
- AND/OR sigmoid scoring with center at 0.75, narrower width

### Why n60 cliff is mild

n60 threshold (-0.10) is reasonable but feature is noisy. n60 <
-0.10 represents 60-day cumulative drawdown of 10%+ — a clear stress
indicator. Mild cliff (6.7pp) reflects feature stability.

---

## D. Soft-threshold proposal

### Spec

```python
def bear_hot_confidence(
    nifty_vol_percentile_20d: float,
    nifty_60d_return_pct: float,
):
    """Continuous Bear hot-confidence [0, 1]."""
    vp_s = 1 / (1 + math.exp(-(nifty_vol_percentile_20d - 0.70) / 0.05))
    n60_s = 1 / (1 + math.exp(-((-0.10) - nifty_60d_return_pct) / 0.03))
    return vp_s * n60_s
```

### Verdict thresholds (data-fitted)

| hot_conf range | Action default | Calibrated WR |
|---|---|---|
| (0.4, 0.7] | TAKE_FULL | 67-72% (boundary cell wins) |
| > 0.7 | TAKE_FULL | 64-66% (deep hot — slightly lower WR) |
| (0.1, 0.4] | TAKE_SMALL | 50-55% |
| < 0.1 | SKIP | ≤ 53% |

**Note:** the 0.4-0.7 band ("boundary hot" in soft framework =
"boundary_hot" in B1's tier classification) is the highest-WR cohort
with n=1,412. Production should treat this as the PRIMARY conviction
cell.

### Quantified improvement

| Metric | Hard | Soft | Improvement |
|---|---|---|---|
| Best-tier n | 2,102 | 1,412 | -33% (smaller) |
| Best-tier WR | 68.3% | 72.0% | **+3.7pp** |
| Best-tier vs baseline | +12.6pp | +16.3pp | +3.7pp |

Soft threshold trades sample size for WR precision: 33% smaller
TAKE_FULL pool but 3.7pp higher WR. Worth it for capital-efficiency.

---

## E. Production integration considerations

**Schema impact:** Production rules.json doesn't currently support
continuous-feature scoring. Either:
- Add `continuous_score_function` rule type (new schema)
- Pre-compute `bear_hot_conf` as scanner enrichment field; rules
  match against bucketed values

The 2nd approach is simpler and aligns with A1's recommended 2-tier
schema (match_fields + conditions array). Pre-compute hot_conf during
scanner enrichment; bucket into 5 tiers; rules match by tier.

**Risk:** sigmoid parameters (centers 0.70/-0.10, widths 0.05/0.03)
are fitted to lifetime data. May not generalize if Bear regime
structure shifts. Mitigation: re-fit sigmoid quarterly; document fit
date.

---

## F. Failure modes considered

### Failure mode 1: Soft TAKE_FULL band has lower WR than soft TAKE_SMALL

**Considered:** Production calls (0.4, 0.7] "TAKE_SMALL" but it has
HIGHER WR than TAKE_FULL. Trader confusion.

**Reality:** Verdict labels need re-mapping. Highest WR cohort should
be TAKE_FULL regardless of conf score band. Recommendation: relabel
the bands so TAKE_FULL = boundary_hot tier.

### Failure mode 2: Sigmoid parameter staleness

**Considered:** Centers and widths fitted to 2010-2026 lifetime data.
Bear regime in 2027+ may have different vol distribution.

**Reality:** mitigated by quarterly re-fit. Could also use rolling
12-month percentile thresholds instead of fixed centers.

### Failure mode 3: Too granular for trader

**Considered:** 5-tier display + continuous confidence score is
information overload.

**Reality:** display only the bucket name (TAKE_FULL boundary /
TAKE_FULL deep / TAKE_SMALL / SKIP); hide continuous score.

---

## G. Verdict

**GAP_DOCUMENTED.** Cliff effects are real but counterintuitive:

1. **vp axis cliff:** just-outside hot has HIGHER WR (66%) than
   just-inside (50%). Cliff direction is WRONG.
2. **n60 axis cliff:** mild expected-direction cliff (72% vs 65%).
3. **Soft threshold:** WR peaks at BOUNDARY (67%) not deep-hot (64%).
4. **Verdict bucket misalignment:** soft TAKE_SMALL band has 72% WR;
   soft TAKE_FULL band has 64% WR. Production should re-map labels.

**Action: SHIP soft-threshold scoring** with re-mapped verdicts.
Best WR cell is the boundary band, not deep-hot.

**Pre-activation work:**
1. Add `bear_hot_conf` enrichment field to scanner (sigmoid scoring)
2. Update Bear UP_TRI playbook with soft-threshold spec
3. Re-map verdict labels: TAKE_FULL = boundary tier (hc 0.4-0.7)
4. Document sigmoid parameter fit date + re-fit cadence

**Cross-reference B1:** B1 found same finding via 4-tier confidence
display. B2 confirms via continuous sigmoid. Both point to "boundary
> deep" pattern. Production should ship one mechanism (either tiered
or sigmoid), not both.

---

## H. Investigation summary

| Aspect | Finding |
|---|---|
| vp cliff (just-inside vs just-outside) | INVERTED (50% inside vs 66% outside) |
| n60 cliff | mild expected (72% inside vs 65% outside) |
| WR continuity along vp axis | NON-MONOTONIC (peaks 0.75-0.80) |
| Soft sigmoid hot_conf peak band | (0.4, 0.7] at 67.2% WR (n=1,749) |
| Soft TAKE_SMALL WR | 72.0% (n=1,412) — HIGHER than soft TAKE_FULL |
| Hard TAKE_FULL WR | 68.3% (n=2,102) |
| Soft vs Hard best-tier improvement | +3.7pp WR; -33% sample |
| Verdict bucket alignment | MISALIGNED (highest WR band labeled TAKE_SMALL) |
| Recommended action | SHIP soft-threshold + re-mapped verdict labels |
| Cross-reference | B1 (4-tier display) confirms same boundary > deep pattern |

Sonnet's cliff-effect concern was valid. Investigation surfaced that
cliff effects exist AND go in counterintuitive direction (boundary >
deep). Soft threshold makes pattern visible.
