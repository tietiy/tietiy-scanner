# B1 + B2 Coupling Analysis

## Background

B1 (Bear warm-zone display) recommended a 4-tier confidence display
that surfaces boundary_hot vs confident_hot WR difference (71.5% vs
64.2%). B2 (Bear hard-threshold cliffs) recommended a continuous
sigmoid `hot_conf` score that smooths the same boundary effect.

Per Step 1.5+2 SUMMARY decision: **ship B1 (tiered) now; defer B2
(sigmoid) to Phase 2**. This document addresses the production gap
explicitly.

---

## 1. Production gap acknowledgment

Without B2's continuous sigmoid scoring, production retains a **cliff
effect at sub-regime boundaries**:

- Signal A: `vp=0.71, n60=-0.11` → boundary_hot (just-inside) → TAKE_FULL @ 71.5%
- Signal B: `vp=0.69, n60=-0.09` → boundary_cold (just-outside) → TAKE_SMALL @ 55-60%

A 2pp difference in vol_percentile and 2pp in 60d_return produces a
~12-15pp swing in displayed WR. This is the cliff B2 was designed to
eliminate.

B1's 4-tier display narrows the cliff (5 buckets vs 2) but does not
eliminate it. Boundary cells remain discrete buckets with hard tier
walls.

---

## 2. Trade-off analysis

### B1 (tiered) — what we ship

**Pros:**
- Aligns with existing percentile-bucket architecture (no new feature
  type to support)
- Trader sees uncertainty visibly via 4 distinct labels
  (confident_hot / boundary_hot / boundary_cold / confident_cold)
- Surfaces the counterintuitive `boundary_hot > confident_hot`
  finding directly in the UI
- Verdicts remain binary at sub-regime boundaries (TAKE_FULL vs
  TAKE_SMALL vs SKIP)

**Cons:**
- 5-tier walls retain cliff effect at each boundary (smaller cliffs
  than 2-tier, but still discrete)
- Tier labels can confuse trader (boundary_hot label sounds weaker
  than confident_hot, but is actually higher WR)
- WR estimates within a tier have no within-bucket gradient

### B2 (sigmoid) — deferred to Phase 2

**Pros:**
- Smooth WR gradient eliminates discrete cliffs entirely
- Single continuous `hot_conf` score per signal
- Future-proof for additional features (multivariate sigmoid)

**Cons:**
- Requires production support for continuous-feature scoring (rule
  schema change v4 → v5)
- Requires `bear_hot_conf` enrichment field added to scanner data
  pipeline (production engineering work)
- Sigmoid parameters (centers 0.70/-0.10, widths 0.05/0.03) are
  fitted to lifetime data; need quarterly re-fit cadence
- Verdict-bucket re-mapping needed (per B2 finding: soft TAKE_SMALL
  band has higher WR than soft TAKE_FULL band — labels need renaming)
- More complex trader briefing required

### Counter-argument

B1's binary-at-boundary verdicts may actually be operationally
preferable to B2's continuous gradient: traders make discrete TAKE/
SKIP decisions, not continuous size-up-by-X% decisions. Smooth verdict
gradient may not improve outcomes if trader translates to discrete
sizing buckets anyway.

This argues for B1 being a **stable production state**, not just an
intermediate.

---

## 3. B1-only production behavior recommendation

### Telegram tier display

Each Bear UP_TRI signal in Telegram shows tier label:

```
[BEAR · 🔥 BOUNDARY_HOT · WR 65-75%]
SIGNAL: HDFC.NS UP_TRI age=0
sub-regime: boundary_hot (vp=0.72, n60=-0.11)
Calibrated: 71.5% / Live observed: 94.6% / Sub-regime base: 71.5%

Action: TAKE_FULL
```

### 4-tier verdict mapping

| Tier | Verdict | Calibrated WR | Notes |
|---|---|---|---|
| confident_hot | TAKE_FULL | 60-65% | Deep stress; depth-of-stress is mid-tier |
| **boundary_hot** | **TAKE_FULL** | **65-75%** | **Highest WR (counterintuitive); early capitulation** |
| boundary_cold | TAKE_SMALL | 55-60% | Transitional; partial ingredient match |
| confident_cold | SKIP / apply Tier 1 cascade | ≤55% | Apply wk4 × swing_high=low if available |

### Calibrated WR alongside live observed (per B3)

Production must display BOTH calibrated and live observed WR per the
B3 framework:

```
Calibrated (sub-regime gated):     71.5%   ← what to expect
Live observed (n=74):              94.6%   ← reflects Phase-5 selection bias
Phase-5 override (if applicable):  76.6%   ← override candidate
```

This honesty is critical: live 94.6% is NOT reproducible at
production scale. Trader must understand the gap. Telegram footer or
PWA tooltip explains:

> "Live WR includes selection bias from validated patterns.
> Calibrated WR is the lifetime baseline + sub-regime tier — what
> the system expects in steady-state production."

### Trader briefing items

First-deployment briefing must explain:

1. **boundary_hot > confident_hot is real, not a typo.** Mechanism:
   early-stage capitulation reversals (cusp of hot) work better than
   deep-stress reversals (already-extended downtrends with overcrowded
   shorts).

2. **Calibrated WR < Live WR is expected.** The gap (e.g., 71.5% vs
   94.6%) is selection bias. Position-size on calibrated, not live.

3. **Tier labels carry counter-intuitive ordering.** "Boundary"
   sounds weaker than "Confident" but is actually higher WR.

---

## 4. Phase-2 trigger criteria for promoting B2 sigmoid

B2 should be promoted from Phase 2 to production when ONE of:

### Criterion A: Verdict-tier mismatch frequency exceeds threshold

After 6 months live operation:
- Track per-signal: tier classification, action taken, outcome
- Compute "tier accuracy" = % of trades where tier prediction matches
  realized cohort WR within ±5pp
- If tier accuracy < 70% (i.e., >30% of cohorts perform outside
  predicted band), tier walls are too coarse → promote B2

### Criterion B: Trader-observed cliff complaints

If trader reports >5 specific instances per quarter of "this signal
just barely missed boundary_hot but performed identically to
boundary_hot signals in actual outcome" — empirical confirmation that
the cliff is operational friction → promote B2.

### Criterion C: New continuous features added

If production adds NIFTY-level continuous features that benefit from
sigmoid scoring (e.g., `nifty_drawdown_depth`, `term_structure_signal`),
the sigmoid framework becomes broadly useful → promote B2 with v5
schema migration.

### Criterion D: 6-month minimum operational time

Regardless of A/B/C, defer B2 promotion for **at least 6 months
post-v4 cutover**. Stable v4 baseline is required before measuring
cliff impact. Earlier promotion risks confounding sigmoid effect with
v4 schema migration effects.

### Recommended decision date

**Phase-2 review checkpoint: 2027-Q1** (assuming v4 ships 2026-Q3).

By 2027-Q1, production should have:
- ≥6 months of v4 operation
- ≥1000 Bear UP_TRI signals across multiple sub-regime episodes
- Tier-accuracy data
- Live + calibrated WR comparison data
- Trader feedback log

Decision matrix at checkpoint:
- All criteria A, B, C, D pass → promote B2 to v5 schema
- Only D + (A or B) → revisit at 2027-Q3
- Only D → defer indefinitely; B1 is stable production state

---

## Summary

Ship B1 (4-tier display) now. Defer B2 (sigmoid) to Phase 2 with a
2027-Q1 review checkpoint. Production gap (cliff at tier boundaries)
is acknowledged but bounded: the B1 display narrows cliffs from 2
buckets to 5 and surfaces uncertainty visibly. B2's continuous
gradient is a UX improvement that may or may not translate to better
trade outcomes given discrete trader decision-making. Six months of
v4 operational data will tell us whether B2 is worth the schema
migration cost.
