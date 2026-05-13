# 01 — Problem Statement (Regime Detector v2)

**Source files cited:**
- Current code: `scanner/main.py:get_nifty_info()` lines 257-337
- Brain consumer: `scanner/brain/brain_derive.py:_derive_regime_watch()` line 348
- Diagnostic R1: `doc/tietiy_diagnostic/04_regime_detector_mechanics.md`, `05_regime_detector_test.md`
- Diagnostic R2: `doc/tietiy_diagnostic_round2/11_weekly_intelligence_reports.md`
- Operational state: `output/brain/regime_watch.json`, `output/regime_debug.json`, `output/brain/cohort_health.json`

---

## What the current regime classifier does

From `scanner/main.py:get_nifty_info()` lines 268-286:

```
df = yf.download("^NSEI", period='3mo', auto_adjust=True)
closes     = df['Close']
ema50      = closes.ewm(span=50).mean()
slope      = ema50.diff(10) / ema50.shift(10)   # 10-bar slope of EMA50
above      = closes > ema50
last_slope = float(slope.iloc[-1])
last_above = bool(above.iloc[-1])

if last_slope > 0.005 and last_above:
    regime = 'Bull'
elif last_slope < -0.005 and not last_above:
    regime = 'Bear'
else:
    regime = 'Choppy'                            # CATCH-ALL FALLBACK
```

Three labels. One input (Nifty close). Two thresholds (±0.005). Two regime "cells" win-conditions; everything else becomes Choppy.

## Five concrete failure modes

### F1 — The Choppy catch-all collapses four distinct micro-states

In the (slope_sign, above_ema50) state space there are 2×2 = 4 cells, plus the slope-magnitude band `|slope| ≤ 0.005`. The current rule promotes only the cleanest two corners (`slope > +0.005 AND above` → Bull; `slope < −0.005 AND NOT above` → Bear). Everything else is "Choppy":

| Cell | What it likely is | Same label |
|---|---|---|
| slope < −0.005, above EMA50 | **Distribution / topping** | Choppy |
| slope > +0.005, NOT above EMA50 | **Recovery / early Bull** | Choppy |
| slope ≈ 0, above EMA50 | Bull-flat / range-in-uptrend | Choppy |
| slope ≈ 0, NOT above EMA50 | Bear-flat / range-in-downtrend | Choppy |

These four states have **different forward-return distributions** (a topping market is not the same as a recovering market). Collapsing them is measurable information loss. (Source: `doc/tietiy_diagnostic/04_regime_detector_mechanics.md` §"The Choppy bucket conflates 4 distinct micro-states".)

### F2 — Brain reads weekly snapshot, not daily compute

`brain_derive._derive_regime_watch()` line 351-354:

```
regime_block = weekly_intel.get("regime", {}) or {}
latest = regime_block.get("latest", {}) or {}
current_regime = latest.get("regime") or "Unknown"
```

The brain reads `output/weekly_intelligence_latest.json`, which is written **Sunday 20:00 IST only** (per `scanner/weekly_intelligence.py` schedule). So:

- Tuesday morning's brain run reads Sunday's regime label.
- Thursday's brain run reads the same Sunday label (3 days old).
- If the Sunday-run misses (GH schedule has historical outages — documented in `master_audit_2026-04-27.md` 2026-04-28 event), the same label propagates 10+ days.

Operational verification today (2026-05-13):
- `regime_watch.json` reports `current_regime: Choppy, days_in_current_regime: 7`, snapshot from `source_date: 2026-05-08`
- `regime_debug.json` shows Nifty: 2026-05-11 above_ema50=True ret20=+1.69 → 2026-05-13 above_ema50=False ret20=−1.94 (Nifty fell from 24176 → 23379 in 2 days, −3.3%)
- The brain still thinks the regime is the Sunday Choppy/stable label while the market has rolled over toward Bear

### F3 — Slope threshold of ±0.005 misclassifies recovery

The slope threshold for Bull is `> +0.005`. From the Apr-26 weekly snapshot: `slope=+0.0036, above_ema50=true, avg_ret20=+7.38%`. By any visual market-state assessment, this is a clear post-Bear recovery — yet the slope is **just below** the +0.005 threshold, so the label is Choppy. The +7.38% 20-day return tells you the market is moving up substantively; the EMA50 slope simply hasn't caught up because the early phase of a recovery has a flat-then-steep slope curve. (Source: `04_regime_detector_mechanics.md` "What the brain layer's regime_watch sees right now".)

### F4 — Asymmetric Bear vs Choppy predictive power

From `output/brain/cohort_health.json` (n=281 resolved as of 2026-05-12):

| Cohort | n | WR | Verdict |
|---|---:|---:|---|
| UP_TRI × **Bear** | 96 | **94.7%** | Label is gold |
| BULL_PROXY × **Bear** | 16 | **87.5%** | Label is gold |
| UP_TRI × **Choppy** | 107 | **34.6%** | Label is **anti-predictive** |
| BULL_PROXY × **Choppy** | 14 | 28.6% | Anti-predictive |
| DOWN_TRI × **Choppy** | 25 | 24.0% | Anti-predictive (everything-in-Choppy loses) |

**Bear is highly informative** (the validated 92.7% WR edge correlates 1:1 with this label). **Choppy is anti-informative** — every signal type loses money in Choppy. This is the smoking gun that Choppy is too coarse: either it's hiding pockets of edge that should be relabeled, or it's a "don't trade" signal but the system still trades anyway because shadow_mode is on.

(Source: `05_regime_detector_test.md` "Live cross-reference".)

### F5 — Single-input, single-bar classification

The classifier uses only `^NSEI close`. It does not consult:
- Volatility (India VIX, realized vol)
- Breadth (advance/decline, sector participation)
- Cross-asset (Bank Nifty, USDINR, 10Y yield)
- Momentum confirmations (Nifty's position vs EMA20 AND EMA200)
- Regime-of-regime (is volatility itself elevated, suggesting a regime-transition window?)

The 50-day EMA's slope is one indicator. A real-world swing trader looks at 5-10 inputs to read regime. The classifier is operating with 1/10 the information.

Also: `period='3mo'` (~63 trading bars) is barely enough for a 50-day EMA. EMA50 needs ~3× span = 150 bars to fully stabilize. The current pull gives ~13 bars of warmup before slope is measured — initialization bias is non-trivial. (Source: `04_regime_detector_mechanics.md` final paragraph.)

---

## Operational impact today (2026-05-13)

**Today's measured state:**
- Nifty closed Mon 24176, Tue 23815, Wed 23379. -3.3% in 2 trading days.
- `above_ema50` flipped True → False on 2026-05-12.
- `ret20_pct`: +1.69 → −0.98 → −1.94 (decisive turn negative).
- Brain's regime_watch: `Choppy, stable for 7 days` — unchanged.
- Bridge state banner: `LIVE — partial data, 8 validated, no reclassifications` (DEGRADED).
- Today's 8 signals: all SKIP, because no boost rule matches `Choppy` regime gates.
- **Position state**: 80 PENDING signals (50 DOWN_TRI, 28 UP_TRI, 2 BULL_PROXY). All bucketed in `Choppy`. None in `Bear` (the regime where UP_TRI is the proven 94.7% edge).

The market has likely transitioned into Bear (or at minimum a Bear-recovery phase). UP_TRI signals firing this week, if accurately tagged as Bear, would route through `win_001..win_006` boost rules — the trader-actionable cohort. Instead they are tagged Choppy and bucketed SKIP.

**Direct cost:** the system has been holding a mis-labeled book for an unknown stretch. Every day this persists, the operator loses some fraction of the 94.7% WR opportunity the brain has been waving at them for 14 days running (today's `prop_unified_2026-05-12_001` is the same boost_promote proposal emitted on every brain run since 2026-04-29).

---

## Why Stage 2 Day 2 (add Bull label) + Day 3 (daily refresh) from FINAL_SYNTHESIS are insufficient

The `doc/FINAL_SYNTHESIS.md` Stage 2 plan proposes:

- **Day 2:** Add a fourth `Bull` regime label to `scanner/main.py:get_nifty_info()` (~10 LOC) per diagnostic R1 §5 Fix 3 (`slope > 0 AND above_ema50 AND ret20 > 3`).
- **Day 3:** Refresh regime daily — point `brain_derive._derive_regime_watch()` at `regime_debug.json` (daily) instead of `weekly_intelligence_latest.json` (weekly).

These are correct **emergency patches** but do not solve the structural problem:

1. **Day 2 (Bull label) adds one new label to a still-3-bin-grid system.** It does not address F1 (Choppy still collapses 4 micro-states), F4 (still no edge attribution beyond Bull/Bear). It also doesn't resolve when to use the new Bull label vs Choppy at the boundary (a noisy 4-bar window of recovery → Bull → false signal → reverts to Choppy → operator whipsaw).

2. **Day 3 (daily refresh) fixes staleness but not granularity.** Reading regime_debug daily gives you a daily classification — still using the same broken 3-state grid + ±0.005 thresholds. The brain will now whipsaw between Choppy and Bull as the slope wobbles around +0.005.

3. **Neither fix addresses F5 (single-input).** A daily-refreshed Bull label, computed from one indicator, is still less robust than a weekly label computed from five indicators. A multi-indicator classifier with weekly cadence may even outperform a single-indicator daily classifier — the right question is "what features + what cadence."

4. **Neither fix addresses transition detection.** A regime label tells you the current state; it does not tell you "the regime probably just changed; signals from yesterday onwards may have different forward distributions." Trading near a regime transition is a different risk profile than trading mid-regime. The current classifier emits states without confidence bands or transition markers.

5. **Neither fix is validated against cohort preservation.** Today's `win_001..win_006` boost rules are pinned to `regime=Bear`. If Day 2's Bull label re-attributes some of the 96 UP_TRI×Bear historical signals to "Bull-recovery" (because they fired during a slope-positive moment within a Bear regime), the cohort preservation breaks silently — the n=96 base shrinks, the WR shifts, the brain's boost_promote proposal logic gets garbled. A surgical patch without re-running the cohort attribution can quietly corrupt the only validated edge in the system.

**Verdict:** Day 2 + Day 3 are correct short-term moves that should land alongside this v2 effort, **NOT** as alternatives to it. They are the visibility fix; this design is the structural fix.

---

## Why this is the foundational layer to fix

The user's framing: "every signal cohort's WR/edge analysis depends on correct regime labels."

This is exactly right. The system today has:
- 11 active rules in `mini_scanner_rules.json`, of which **6 of 7 boost rules and 1 of 1 watch rule** are gated by regime (`regime=Bear` or `regime=Choppy`).
- Brain's `cohort_health.json` cohort axis: **signal+regime is 1 of 2 axes** the brain uses (signal+sector being the other).
- Bridge `bucket_engine.py` Gate 4 (evidence consensus) reads regime to fetch regime-baseline cohort stats.
- Every UP_TRI signal entering the daily pipeline is tagged with regime; every outcome resolution stores that tag in `signal_history.json`.

**The regime label is the most-used single feature in the system.** Every downstream metric (cohort_health WR, brain proposals, mini_scanner gates, bridge bucket decisions, telegram brief categorization) depends on it.

If the label is wrong on day-of-detection, the signal's downstream attribution is wrong forever. The label is stored at scan time; it does not retro-update when better classification becomes available. So historical mis-labels are baked into `signal_history.json` and cohort_health derivatives.

**Implication for v2:** the v2 classifier is not just a label generator — it requires a **historical relabeling protocol** for the 281 resolved signals (and 80 PENDING) so the existing cohort attributions can be re-computed under the new state space. This is the validation harness, not an optional add.
