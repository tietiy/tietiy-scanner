# 02 — State Space Design

## Option evaluation

| Option | States | Pros | Cons | Verdict |
|---|---|---|---|---|
| **A. Keep 3-state** | Bull / Bear / Choppy | No code change | Documented broken (F1, F4 in 01) | ❌ |
| **B. 4-state (add Bull)** | + Bull-Recovery | Surgical, ~10 LOC, FINAL_SYNTHESIS Day 2 | Still collapses Choppy; doesn't address F1 | Stopgap, not v2 |
| **C. 5-state (this design)** | Bull / Bull-Recovery / Choppy / Bear-Recovery / Bear | Splits transitions out; auditable; minimal cohort disruption | 5 cohort cells per signal type (was 3) | ✅ **Recommended** |
| **D. 7-state grid** | + Distribution / Bear-Capitulation | Captures topping + crash | n explodes; many cells thin <10 samples; harder validation | Defer to v3 |
| **E. HMM continuous** | Posterior over states | Probabilistically sound | Not auditable by operator; ML overhead; opaque to consultant review | Defer indefinitely |

## Why 5-state and not 7 or 3

**5-state preserves the consultant's Bear-only constraint.** Per `doc/consultant_briefings/round_10_rule031_supplement.pdf §4.2`: "Pre-Audit-6 expected Bear-only sleeve: rule_019 + rule_031. Post-Audit-6 actual sleeve: rule_019 alone." All currently-deployable rules fire under regime=Bear; under v2 they map directly to `Bear` or `Bear-Recovery` cells without disruption.

**5-state captures the recovery transition** — the operational complaint that triggered this design. Bull-Recovery and Bear-Recovery are distinct from steady-state Bull/Bear because they are post-transition windows where forward returns differ structurally (recoveries see initial pullbacks before continuation; steady states see more directional persistence).

**5-state stays within sample-size envelope.** With 281 resolved signals across 3 signal types × 3 regimes = 9 cells today (avg ~31 signals/cell). Under v2: 3 × 5 = 15 cells (avg ~19 signals/cell). Still above n≥10 brain Tier threshold for most cells. A 7-state design pushes some cells below 10 immediately, making validation impossible without 2+ months more data.

**7-state is the right v3** when we have ~600+ resolved signals. Right call to defer per `doc/tietiy_2_0_design/01_module_boundaries.md` ("3-state today, 7-state next") — the design contract supports the upgrade path.

## The 5 states

### Bear
**Definition (operational):** Market actively declining. `^NSEI` below EMA50; EMA50 trending down; 20-day return negative. **This is the consultant-validated trade-enabling regime.**

**Quantitative gate (proposed):**
- `above_ema50 = False`
- `slope_10d_ema50 < −0.003` (loosened from `−0.005` — empirical recovery validation needed)
- `ret20_pct < −2.0%`

All three must hold for ≥3 consecutive trading days to confirm transition INTO Bear. (Persistence rule §3 below.)

### Bear-Recovery
**Definition:** Market still below EMA50 but slope is rising (the post-Bear rally phase). **Forward return distribution: positive but volatile.** Long-bias setups have asymmetric risk: a Bear-Recovery can reverse back to Bear quickly.

**Quantitative gate:**
- `above_ema50 = False`
- `slope_10d_ema50 > 0` (any positive slope)
- `ret20_pct > 0`

### Choppy
**Definition:** Genuine range-bound. No directional persistence. **This becomes the residual category** but its definition is now narrower: it captures only mid-EMA-with-flat-slope OR explicit volatility-driven sideways action.

**Quantitative gate (residual after others):**
- ANY of:
  - `|slope_10d_ema50| < 0.001` (genuinely flat)
  - `india_vix > 22 AND |ret20_pct| < 3.0%` (high volatility but no directional move)
- NOT matching any other state

### Bull-Recovery
**Definition:** Market above EMA50 but recovering — the mirror image of Bear-Recovery. Mid-trend pullback or post-Bear breakout that has cleared EMA50.

**Quantitative gate:**
- `above_ema50 = True`
- `slope_10d_ema50 > 0` AND `slope_10d_ema50 ≤ 0.005`
- `ret20_pct > 3.0%` (signals strong recent move)
- `india_vix < 20` (volatility compressing, confirming move sustainability)

### Bull
**Definition:** Steady-state Bull. EMA50 rising decisively, price extended above EMA50, low vol.

**Quantitative gate:**
- `above_ema50 = True`
- `slope_10d_ema50 > 0.005`
- `ret20_pct > 0`
- `india_vix < 18`

## State diagram (allowed transitions)

```
                         ┌──────────────────┐
                         │      Bull        │
                         └──────┬───────────┘
                                │   slope drops, vix rises
                                ▼
                         ┌──────────────────┐
              ┌─────────►│  Bull-Recovery   │◄─────────┐
              │          └──────┬───────────┘          │
              │ slope             │ price falls         │
              │ persists          │ below EMA50         │
              │ positive          │                     │
              │           ┌──────▼───────────┐         │
              │           │      Choppy      │ slope    │
              │           └──┬──────────┬────┘ rises   │
              │              │          │              │
              │ slope flip   │          │ slope flip   │
              │ down + ret−  │          │ up + ret+    │
              │              ▼          │              │
              │       ┌──────────────┐  │              │
              │       │ Bear-Recovery│──┘              │
              │       └──┬───────────┘                 │
              │   slope persists negative              │
              │   AND price stays below EMA50          │
              │          ▼                              │
              │       ┌──────────────┐                  │
              └───────│     Bear     │──────────────────┘
                      └──────────────┘
                       (consultant-validated trade-enabling state)
```

**Allowed direct transitions:**

| From | Allowed next states |
|---|---|
| Bear | Bear-Recovery (slope rises), Choppy (slope flattens) |
| Bear-Recovery | Bear (reversal), Bull-Recovery (price clears EMA50), Choppy (slope rolls back) |
| Choppy | Bear-Recovery, Bull-Recovery (NOT direct to Bull or Bear — must pass through recovery state) |
| Bull-Recovery | Bull (slope strengthens), Choppy (slope flattens), Bear-Recovery (price falls below EMA50) |
| Bull | Bull-Recovery (slope weakens or vol rises) |

**Explicitly disallowed direct transitions:**
- Bull → Bear (must pass through Bull-Recovery → Choppy → Bear-Recovery sequence)
- Bear → Bull (mirror)

The reason: real markets do not jump from Bull to Bear in a single bar. Even Mar-2020 crash showed 2-3 days of Distribution → Bear-Recovery (failed) → Bear progression. Enforcing the transition graph adds a sanity check that prevents single-bar noise from flipping the regime.

## Mutual exclusivity rules

A given day's classification produces **exactly one** label. No probability distribution; no co-states. (HMM design rejected per option E above.)

If two gates would match (e.g., Bull-Recovery and Bull both have `above_ema50=True AND slope>0`), the more-restrictive state wins: Bull (which requires slope > 0.005 AND vix < 18) supersedes Bull-Recovery.

Gate priority order (evaluated top-down; first match wins):
1. Bull (most restrictive)
2. Bear (most restrictive)
3. Bull-Recovery
4. Bear-Recovery
5. Choppy (residual; assigned if no other match)

## Persistence rules (anti-whipsaw)

Without persistence, the classifier flips daily on noise. Three rules:

**P1 — Transition confirmation.** A regime change requires the new state's gate to match for **3 consecutive trading days** before the label changes. Days 1-2 of the new gate matching are logged as `regime_pending` but `regime` stays at the prior label.

**P2 — Recovery states have shorter confirmation** (2 days instead of 3) because Recovery states are themselves transition-windows and require faster response.

**P3 — Bear → Bear-Recovery → Bear oscillation guard.** If the system has flipped between Bear and Bear-Recovery 3+ times within 10 trading days, force the label to Choppy for the next 5 trading days. This prevents whipsaw-flooding the brain with regime_alert proposals.

## What "regime_pending" means for downstream consumers

When the gate has matched for 1-2 days (within the confirmation window):
- `regime` field in signal_history: still old label
- `regime_pending` field: new label (e.g., "Bear-Recovery")
- `confidence_pending`: float 0-1 (1.0 = ready to flip tomorrow if gate holds)

Bridge bucket_engine + brain Step 5 regime_shift_detector can consume `regime_pending` to surface transition warnings to the trader BEFORE the label commits. This is the "regime is shifting" alert.

## Backward compatibility with existing rules

Current `mini_scanner_rules.json` boost rules pin to `regime=Bear`. Under v2:

- `win_001..win_007` (regime=Bear) → matches v2 `Bear` only. **NOT** Bear-Recovery.
- This is intentional. The historical n=96 UP_TRI×Bear cohort fired under days that, under v2 rules, would mostly map to `Bear` (price below EMA50 + slope decisively negative). A subset (~5-15%) may map to `Bear-Recovery` and would not trigger the current boost rules. That subset's WR can be re-analyzed under v2 as a candidate cohort.

The cohort preservation test (§01 in `05_validation.md`) is the explicit verification of this.

## Edge cases

**Insufficient data (start of yfinance pull, holidays, etc.):** if any required input is missing (vix, ret20), return `regime: Unknown`. Downstream consumers must handle Unknown the same as Choppy (default-defensive).

**Market closed / weekend:** Saturday/Sunday classification reuses Friday's. Holidays use prior trading day's classification.

**Data corruption:** if `ret20_pct` is outside ±50% (clearly bad data), log alert + return `regime: Unknown`.
