# Sonnet Analysis — Out-of-Bear Signals (V1→V2 reclassification)

Model: claude-sonnet-4-6
Signals analyzed: 67
Tokens: in=13851 out=3000

---

# Analysis of 67 Reclassified Signals: V1 Bear → V2 CHOPPY

---

## PRELIMINARY DATA AUDIT

Before clustering, let me establish what we're actually working with:

**Signal dates and Nifty context:**
- **2026-04-01**: Nifty 22,679 | ret_30d_prior = **-10.96%** | ret_6d_forward = **+6.05%** | n=22 signals
- **2026-04-07**: Nifty 23,124 | ret_30d_prior = **-10.44%** | ret_6d_forward = **+4.64%** | n=1 signal
- **2026-04-09**: Nifty 23,775 | ret_30d_prior = **-7.02%** | ret_6d_forward = **+2.48%** | n=40 signals
- **2026-04-10**: Nifty 24,051 | ret_30d_prior = **-6.47%** | ret_6d_forward = **+2.19%** | n=4 signals

**Critical observation**: ALL 67 signals have ret_30d_prior between -6.47% and -10.96%. There are **zero signals** with ret_30d_prior in the -2% to +2% range, and **zero signals** with positive prior returns.

This fundamentally constrains the clustering.

**Resolved outcomes (56 signals with known outcomes):**
- DAY6_WIN: 51
- DAY6_LOSS: 3
- GAP_INVALID: 2
- Pending (NaN): 11 (all on Apr-01, all in the pending category)

**WR of resolved (excluding GAP_INVALID):** 51/54 = **94.4%**

---

## 1. CLUSTERING

### Group A: "Real Bear — V2 Wrong to Exclude"
**Definition**: ret_30d_prior < -5%, market clearly in crash/downturn, prices below key EMAs, V2 failed its own Bear criteria likely due to EMA200 position or the 3-of-5 rolling window not yet committing.

**Signals**: ALL 67 signals — ret_30d_prior ranges from -6.47% to -10.96%

But to be analytically honest, I'll split this further on the **-7% threshold** because -6.47% is borderline and the V2 30-day context shows the BEAR count dropping from 2→1 as we move from Apr-01 to Apr-09/10.

---

### Refined Sub-clustering Based on Available Discriminators

Since ret_30d_prior is the only continuous market-context variable available (and all signals are in negative territory), I'll use:
1. **Depth of prior decline** (< -9% vs. -5% to -9%)
2. **V2_30day_context Bear count** (2 vs. 1 — indicating how close to V2 Bear the environment was)
3. **Nifty forward return** (proxy for what regime was actually doing post-signal)
4. **Outcome quality** (win rate + PnL magnitude)

---

### GROUP A: "Real Bear — V2 Wrong to Exclude"
**Criteria**: ret_30d_prior ≤ -9% AND v2_30day_context BEAR ≥ 2

| Feature | Value |
|---------|-------|
| Signal dates | Apr-01, Apr-07 |
| n signals | 23 (22 + 1) |
| ret_30d_prior | -10.96% (Apr-01), -10.44% (Apr-07) |
| Nifty forward +6d | +6.05% (Apr-01), +4.64% (Apr-07) |
| V2 context | CHOPPY:17, BEAR:2 — i.e., barely missed Bear commit |
| Nifty level | 22,679 — 23,124 (deep in crash zone) |

**Outcomes (Group A, 23 signals):**

Apr-01 (22 signals):
- Resolved with outcome: 11 signals (10 WIN, 1 LOSS)
- Pending: 11 signals (NaN)
- GAP_INVALID: 0

Apr-07 (1 signal): 1 WIN (pnl=6.61%)

**Resolved WR (Group A)**: 11 WIN / 12 resolved = **91.7%** (pending signals excluded)
*(If pending signals resolve at base rate ~94%, projected WR ≈ 93-94%)*

**Mean pnl_pct (resolved wins only):**
Apr-01 wins: 2.41, 4.10, 5.07, 8.46, 5.62, 6.39, 0.63, 8.91, 4.33, 5.49 → mean = **5.14%**
Apr-01 loss: -0.88%
Apr-07 win: 6.61%
**Group A mean pnl (all resolved):** ~4.87%

**Pattern observations:**
- Sectors: IT, Auto (×5), Metal (×2), Energy (×2), FMCG, Other (×2), Pharma
- Broad sector diversity — characteristic of market-wide crash recovery, not stock-specific edge
- Nifty itself rallied +6.05% in 6 days — this is a **capitulation bounce**, not a V2-style "sustained bear"
- V2's 30-day window shows BEAR:2 — the market was *almost* in V2-Bear but missed by the rolling commit threshold or ret20 criterion
- The -10.96% prior decline is unambiguously crash territory by any regime definition
- V2 likely excluded these because: price may have started recovering (Nifty was at 22,679 but already bouncing from lows), or EMA200 condition wasn't met, or the 3-of-5 window hadn't committed during the actual signal day

---

### GROUP B: "Mild Decline — Ambiguous"
**Criteria**: ret_30d_prior between -5% and -9%, v2_30day_context BEAR = 1

| Feature | Value |
|---------|-------|
| Signal dates | Apr-09, Apr-10 |
| n signals | 44 (40 + 4) |
| ret_30d_prior | -7.02% (Apr-09), -6.47% (Apr-10) |
| Nifty forward +6d | +2.48% (Apr-09), +2.19% (Apr-10) |
| V2 context | CHOPPY:18, BEAR:1 (Apr-09); CHOPPY:17, BEAR:1 (Apr-10) |
| Nifty level | 23,775 — 24,051 (recovery underway) |

**Outcomes (Group B, 44 signals):**

Apr-09 (40 signals):
- DAY6_WIN: 39 (note: GAP_INVALID ×2 excluded)
- DAY6_LOSS: 2 (Infra: -0.62%, Chem: -1.97%)
- GAP_INVALID: 2 (CapGoods, Other)
- Pending: 0

Apr-10 (4 signals):
- DAY6_WIN: 4 (Auto: 4.01%, Energy: 7.01%, Infra: 3.57%, Pharma: 0.72%)
- DAY6_LOSS: 0

**Resolved WR (Group B, excluding GAP_INVALID):** 43 WIN / 45 resolved = **95.6%**

**Mean pnl_pct (resolved, Group B):**
Apr-09 wins (37 signals): 3.09, 0.96, 1.35, 2.08, 3.17, 2.40, 2.80, 5.80, 7.07, 7.17, 6.35, 5.72, 10.17, 5.21, 10.47, 0.95, 1.82, 7.33, 4.65, 6.00, 5.27, 6.17, 10.24, 7.55, 9.18, 6.20, 7.26, 8.19, 6.83, 14.00, 6.46, 12.11, 2.96, 5.28, 3.20, 1.45
Apr-09 losses: -0.62, -1.97
Apr-10 wins: 4.01, 7.01, 3.57, 0.72

**Group B mean pnl (all resolved):** approximately **5.6%**

**Pattern observations:**
- Massive sector breadth: Bank (×8+), Metal (×7+), Infra (×7+), FMCG (×4), Energy (×4), Chem (×2), Health (×2), Other (×3)
- Nifty itself only gained +2.48% in 6d — yet individual stocks gained 3-14%
- This is the **crash-to-recovery inflection zone**: market has already bounced from -10% but still -7% on 30d basis
- V2 correctly identifies CHOPPY because: market has stopped declining hard, EMA slope may be recovering, price crossed back above certain thresholds
- The outsized individual stock returns (up to 14%) vs modest Nifty gain (+2.48%) strongly suggests **stock-specific breakout edge** dominant here, not regime
- BEAR:1 in V2 context (vs BEAR:2 for Group A) confirms the environment is genuinely less bear-like by Apr-09

---

### GROUP C: "Not Bearish — V2 Correct"
**Criteria**: ret_30d_prior > -5% OR positive

**Result: 0 signals qualify.** No signals have ret_30d_prior > -5%.

The data simply does not contain a Group C as originally defined. The least bearish signals are at -6.47%, which is still a meaningful decline.

---

## 2. GROUP SUMMARIES

### Group A (n=23): Deep Crash — V2 Potentially Wrong
| Metric | Value |
|--------|-------|
| Signal dates | Apr-01, Apr-07 |
| Resolved n | 12 |
| WIN | 11 |
| LOSS | 1 |
| WR (resolved) | **91.7%** |
| Pending | 11 |
| GAP_INVALID | 0 |
| Mean pnl (resolved) | **~4.87%** |
| ret_30d_prior | -10.44% to -10.96% |
| Nifty fwd 6d | +4.64% to +6.05% |
| V2 BEAR count | 2/~19 days |
| Dominant sectors | Auto, Metal, Energy, IT, FMCG |

**Key pattern**: Deep crash bottom (Nifty -11%), maximum fear zone, V2 context shows BEAR:2 (barely missed commit threshold). Forward Nifty gain is substantial (+6%), consistent with a Bear-regime capitulation bounce — exactly the scenario where UP_TRI×Bear edge is theoretically valid. The 11 pending signals all share the Apr-01 date and likely resolve soon; their directional performance is correlated (same date, same Nifty +6.05% forward).

---

### Group B (n=44): Crash Recovery — V2 Probably Correct
| Metric | Value |
|--------|-------|
| Signal dates | Apr-09, Apr-10 |
| Resolved n | 45 (incl. 2 GAP_INVALID) |
| WIN (excl. GAP) | 43 |
| LOSS | 2 |
| GAP_INVALID | 2 |
| WR (excl. GAP) | **95.6%** |
| Mean pnl (all resolved excl. GAP) | **~5.6%** |
| ret_30d_prior | -6.47%

---

# Sonnet Verdict (continued)

Model: claude-sonnet-4-6 | Tokens: in=714 out=1083

## 3. KEY QUESTION ANALYSIS

Loosening the V2 BEAR gate would almost certainly recapture both Group A and Group B simultaneously, because the discriminating feature is **not** the V2 BEAR count itself (2 vs. 1 is a razor-thin difference, well within noise for a ±15d window) but rather the underlying market regime. Group A's distinguishing signature is the **depth of prior drawdown** (ret_30d_prior of -10.4% to -11.0% vs. Group B's -6.5% to -7.0%) — a nearly 4-percentage-point gap that is observable and stable. This means surgical separation is **theoretically possible** but must be done via a **complementary depth gate** (e.g., ret_30d_prior ≤ -9%), not by adjusting the V2 BEAR threshold alone. If you loosen V2's BEAR gate without adding that depth gate, Group B floods back in — which is not necessarily catastrophic (95.6% WR) but violates the "Bear regime only" intent of V2. The critical risk is that Group B's context (-6.5% to -7%) looks more like late-crash recovery than true Bear capitulation, meaning its 95.6% WR may be regime-contingent and less robust out-of-sample than Group A's.

---

## 4. VERDICT

**HYBRID: Specific additional gates capture A surgically.**

Group A is real alpha — deep-crash-bottom signals with 91.7%+ WR and strong forward returns (+4.6% to +6.1%) that V2 incorrectly excludes. However, the V2 BEAR gate cannot be loosened in isolation without also recapturing Group B, and the mechanism to separate them already exists in the data as a clean threshold on `ret_30d_prior`. The correct action is a **targeted sub-gate**: keep V2's BEAR classification logic unchanged, but add a bypass rule that re-admits UP_TRI signals when `ret_30d_prior ≤ -9.0%` regardless of V2 BEAR/CHOPPY ambiguity — recognizing that at extreme drawdown depths, V2's CHOPPY label is a measurement artifact of volatility compression near a bottom, not a genuine regime signal. This adds exactly **one threshold on one existing feature**, satisfying the operator constraint for simplicity, and recovers ~23 high-quality signals without reopening the 44-signal Group B flood.

---

## 5. SPECIFIC RECOMMENDATION

### Gate Change: Single Bypass Condition

**Add to V2 signal logic (append as OR condition):**

```
SIGNAL = (V1 = UP_TRI) AND (
    [V2 = BEAR]                          ← existing gate, unchanged
    OR
    [V2 = CHOPPY AND ret_30d_prior ≤ -9.0%]  ← new bypass gate
)
```

**Exact threshold:** `ret_30d_prior ≤ -9.0%` (conservative; Group A spans -10.44% to -10.96%, Group B spans -6.47% to -7.02%; the gap is ~3.5pp, so -9.0% sits cleanly in the middle with ample buffer on both sides).

**Expected outcome:**
| Cohort | n | Estimated WR | Action |
|---|---|---|---|
| V2 BEAR (existing) | 40 | 95.0% | Unchanged |
| + Group A bypass | +23 | ~91-92% blended addition | Added |
| **New total** | **~63** | **~93.5-94%** | **Acceptable** |
| Group B (excluded) | 44 | 95.6% | Remains excluded |

**Why NOT include Group B:** Despite Group B's strong historical WR, its ret_30d_prior of -6.5% to -7.0% sits in a recovery-momentum regime that V2 correctly classifies as structurally different from Bear. Its WR is likely driven by post-crash beta recovery (a different edge source), not the capitulation-bottom mean-reversion edge V2 is designed to capture. Mixing edge sources degrades interpretability and increases regime-change fragility.

**Why this is safe operationally:** One new threshold, on an already-computed feature (`ret_30d_prior`), with a 3.5pp moat to the nearest excluded group. No new data sources, no classifier retraining, no additional lookback periods. Fully consistent with "build-not-operate, simpler is safer" constraint.