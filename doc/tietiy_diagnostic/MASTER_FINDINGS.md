# TIE TIY Deep Diagnostic — Master Findings

Generated 2026-05-13 by read-only forensic of `~/code/tietiy-scanner/`. Sub-reports `00_repo_inventory.md` through `07_stop_target_mechanics.md` carry the detailed evidence; this is the consolidation.

## TL;DR

1. **DOWN_TRI verdict: KILL** (or REHABILITATE_AS_EXIT_SIGNAL_FOR_LONGS).  No subset at n≥10 in the live data is profitable. The geometry is structurally broken: no target, no ages 1-3 detection, no regime discrimination in score, and Day-6 forced exits cap upside while stops realise full −1R.
2. **Regime detector verdict: NEEDS_REFINEMENT, not REBUILD.** Bear is empirically well-calibrated (UP_TRI×Bear posts 94.7% WR). Choppy is a catch-all for 4 distinct micro-states and is currently swallowing the entire post-Bear recovery window — which is where 100% of the live portfolio is currently exposed at 28.6% UP_TRI×Choppy WR.
3. **Brain layer is fully shipped backend (7/7 Wave 5 steps).** It already produced the correct analyses. 3 PENDING proposals from 2026-04-29 expired on 2026-05-06 without trader approval because production-fire infrastructure (GH secret + 2 cron-job.org entries) was never completed. **The blocker is delivery, not analysis.**
4. **Stop/target mechanics: target-hit path exists for only 1 of 12 signal×regime cells (UP_TRI×Bear).** 89% of resolved signals exit at Day 6. Fib-based stops are feasible for UP_TRI / BULL_PROXY; adding targets to BULL_PROXY is the highest-leverage single change.

---

## 1. DOWN_TRI

### Mechanics (from `02_down_tri_mechanics.md`)

- Triggered by a confirmed `pivot_high` at age=0 only (no ages 1-3 like UP_TRI).
- Stop = `pivot_high + 1.0 × ATR` (STOP_MULT=1.0, ATR_PERIOD=14).
- Target = **None** (`scorer.get_exit_rule` returns `Day6` for all non-UP_TRI×Bear cases).
- Score = +2 flat across all regimes (no Bear/Bull/Choppy discrimination).
- `bear_bonus` is hard-coded to False on all DOWN_TRI dicts.

### Sub-population evidence (from `03_down_tri_subpopulations.md`)

n=34 DOWN_TRI rows in `signal_history.json`; 23 resolved.

| Cohort | n | WR | Σ pnl | avg R | Verdict |
|---|---:|---:|---:|---:|---|
| All DOWN_TRI resolved | 23 | 17.4% | −148.78 | −0.54 | ❌ |
| × Bear (the failure regime) | 23 | 17.4% | −145.70 | −0.64 | ❌ |
| × Bank (kill_001 cohort) | 12 | 0.0% | −122.27 | −0.81 | ❌ |
| × Energy | 6 | 0.0% | −27.99 | −0.56 | ❌ (n<10) |
| × Pharma | 3 | 66.7% | +0.92 | −0.10 | n too small |
| × Chem | 4 | 66.7% | +5.00 | +0.07 | n too small |
| × score=5 / 6 / 7 | 12 / 17 / 3 | 18/15/n.a. | negative | negative | ❌ |
| × vol_confirm=True | 15 | 18% | −82.46 | (neg) | ❌ |
| × rs_strong=True | 0 | — | — | — | N/A — never fires for DOWN_TRI |

**No cell at n≥10 is profitable.** DOWN_TRI MFE median = 0.00% — most trades never showed any favorable bar. STOP_HIT events all cluster in Bank/Energy/Bear (the Apr 6-8 short squeeze documented in `INV-01`).

### Verdict

**KILL** within the current "take the trade as posted" framework. Defensible upgrade path is **REHABILITATE_AS_EXIT_SIGNAL**: when a DOWN_TRI fires on a symbol/sector where you hold UP_TRI / BULL_PROXY longs, treat it as a heads-up to tighten or close those longs. Don't take the short trade. This preserves the pattern's information value without the lopsided geometry.

---

## 2. Regime Detector

### Mechanics (from `04_regime_detector_mechanics.md`)

`main.py:get_nifty_info()` lines 257-338. Three labels emitted:

```
slope = 10-day slope of 50-day-EMA of Nifty closes
above_ema50 = (last close > EMA50)

if slope > +0.005 AND above_ema50:  Bull
elif slope < −0.005 AND NOT above_ema50: Bear
else:                                    Choppy   ← catch-all
```

The Choppy bucket collapses 4 distinct micro-states (post-Bear recovery, distribution top, Bull-flat, Bear-flat). Today's regime per `regime_watch.json`: Choppy, but slope = +0.0036, above_ema50 = true, ret20 = +7.38%. **This is post-Bear recovery, not chop** — the label is misclassifying.

### Live cross-reference (from `05_regime_detector_test.md`)

| Cohort | n | WR | Verdict on label |
|---|---:|---:|---|
| UP_TRI × **Bear** | 96 | 94.7% | Label is gold |
| BULL_PROXY × **Bear** | 16 | 87.5% | Label is gold |
| UP_TRI × **Choppy** | 35 | 28.6% | Label is anti-predictive |
| BULL_PROXY × **Choppy** | 8 | 25.0% | Label is anti-predictive |
| DOWN_TRI × **Bear** | 21 | 20.0% | Bear doesn't save DOWN_TRI |

### Verdict

**NEEDS_REFINEMENT.** Surgical fix (Option A in sub-report 5): add a `Bull` label that fires when `slope > 0 AND above_ema50 = true AND ret20 > 3`. This pulls "post-Bear recovery" out of the Choppy bucket and gives the brain a new cohort axis to mine. ~10 lines of code in `main.py:get_nifty_info` plus minor `scorer.py` updates. Backward-compatible with all existing boost_patterns (Bear cohorts unchanged).

The EMA50 lookback initialization (period='3mo' = ~63 bars for a 50-day EMA) is a code-quality concern but unlikely to flip labels in normal use.

---

## 3. Brain Layer

### Status (from `06_brain_layer_state.md`)

- Backend 7/7 SHIPPED 2026-04-29 (commits `76a85f4`, `8e5be29`, `c047fd2`, `05570fb`, `1e1c786`, `d874180`).
- Workflows `brain.yml` (22:00 IST) + `brain_digest.yml` (22:05 IST) shipped.
- **Production fire blocked** on user-side actions: `ANTHROPIC_API_KEY` GH secret + 3 cron-job.org dashboard entries (brain.yml, brain_digest.yml, eod.yml).
- Step 8 PWA Monster tab DEFERRED to Wave UI.

### Operational insights already produced

`output/brain/` carries the brain's existing analyses:

- **`cohort_health.json`**: Identifies Tier W (BULL_PROXY×Bear, UP_TRI×Auto, UP_TRI×FMCG), Tier M (UP_TRI×Bear, UP_TRI×Metal), and Tier Candidate cohorts. DOWN_TRI×Bear sits in Candidate at −0.58 R. Carries explicit metadata warning `r_multiple_under_day6_dominance` (35/36 of 2026-04-27 resolutions were Day-6 forced exits).
- **`regime_watch.json`**: Currently sees Choppy/stable for 7 days, with prior 7-day window 5/7 Bear → Choppy. Snapshot slope +0.0036, ret20 +7.38, above_ema50=true.
- **`portfolio_exposure.json`**: Flags 100% Choppy + 95% UP_TRI + UP_TRI×Choppy×Bank 23.75% (above 20% cell threshold). Open positions: 80.
- **`unified_proposals.json`** (2026-04-29): 3 PENDING proposals (UP_TRI×Bear boost-promote, UP_TRI×Metal boost-promote, exposure-warn for Choppy concentration). All expired 2026-05-06 — no /approve, no /reject.
- **`reasoning_log.json`**: 4 LLM gate decisions from 2026-04-29 brain run, all coherent and evidence-grounded, total cost $0.10.
- **`decisions_journal.json`**: Empty (231 bytes). No trader decisions ever recorded.
- **`ground_truth_gaps.json`**: 0 thin rules, 0 thin patterns.

### Verdict

**The brain has already done the diagnostic.** The intelligence layer is operational, but its outputs have not been delivered to the trader (workflows not yet scheduled) and the 3 proposals it produced 2026-04-29 expired without action. Recommended use: **finish production-fire (the user-side actions) before designing any new brain modules.** The brain is currently doing more useful inference than the rest of the diagnostic chain has consumed.

---

## 4. Stop/Target Logic

### Current state (from `07_stop_target_mechanics.md`)

- Stops: `pivot ± 1.0×ATR` (UP_TRI, DOWN_TRI); `szL − 0.5×ATR` (BULL_PROXY).
- Targets: **only UP_TRI × Bear** has a real target (`Target2x` at `entry + 2 × risk`). All other signal×regime cells exit at Day 6 close.

Median stop widths: UP_TRI 14%, DOWN_TRI 12%, BULL_PROXY 5%, DOWN_TRI_SA 4%.

Live target-hit rates among resolved: UP_TRI 2.2%, BULL_PROXY 16.7%, **DOWN_TRI 0.0%**.

### Fib viability

| Signal | Stop refactor | Target add | Notes |
|---|---|---|---|
| UP_TRI | HIGH feasibility | Already has Bear target; add Bull/Choppy target | Anchor swing-low → recent high; 0.5 or 0.618 Fib stop |
| BULL_PROXY | HIGH feasibility | **High leverage** — many DAY6_WINs would have hit a Fib target | Tight stops already make this compatible |
| DOWN_TRI | Limited value alone | Adding a target alone doesn't solve regime/Day-6/no-MFE problems | Out of scope unless DOWN_TRI is rehabilitated first |

### Verdict

**Fib stops + targets are feasible for the long signals.** The single highest-leverage change is **adding a `Target2x` exit rule for BULL_PROXY**. BULL_PROXY's 16.7% target-hit rate at Day-6 is already 7× higher than UP_TRI's — a fraction of those Day-6 winners would convert to 2R target-hits with the rule. BULL_PROXY×Bear cohort already sits at +1.01 R; this could push it to +1.3-1.5 R territory.

---

## 5. Surgical Fix Plan

**Ranked by impact (highest first):**

### Fix 1 — Complete brain production-fire (HIGHEST IMPACT, 0 code)

Three user-side actions, no code touch:
- Add `ANTHROPIC_API_KEY` to GitHub Settings → Secrets → Actions.
- Add cron-job.org dashboard entry: `brain.yml` daily at 22:00 IST (16:30 UTC).
- Add cron-job.org dashboard entry: `brain_digest.yml` daily at 22:05 IST (16:35 UTC).
- (Also outstanding: `eod.yml` at 16:15 IST per M-15.)

Effect: The 3 PENDING brain proposals from 2026-04-29 don't expire silently again. The portfolio_exposure warning, regime-shift alerts, and boost-promotion candidates land in Telegram for `/approve` action. The exposure-warn alone would have flagged today's 100% Choppy concentration risk.

### Fix 2 — Hard-block DOWN_TRI broadly (HIGH IMPACT, small code change)

Extend `kill_001` from `signal=DOWN_TRI, sector=Bank` to `signal=DOWN_TRI` (sector=null = any). Evidence: `cohort_health.json` shows DOWN_TRI baseline at 17.4% WR / −6.20% avg / Candidate tier. Per the user's own confidence gates (n≥20, confidence≥85%, WR gap≥15% vs baseline), DOWN_TRI fails on every gate as a positive cohort and passes on every gate as a negative cohort.

- File: `data/mini_scanner_rules.json`
- Change: add new kill_pattern (or widen kill_001):
```json
{
  "id": "kill_002",
  "active": true,
  "signal": "DOWN_TRI",
  "sector": null,
  "reason": "Baseline 17.4% WR, -6.20% avg pnl on n=24 resolved. No sub-population at n>=10 is profitable. Bank+Energy account for 87% of bleed.",
  "added_date": "2026-05-13",
  "source": "tietiy_diagnostic_2026-05-13",
  "evidence": { "wr": 0.174, "n": 24, "avg_pnl": -6.20, "tier": "validated" },
  "contra_shadow_tracked": true
}
```
- Reversibility: 1-line flip of `active` to `false`.

(Defer the `kill_001` narrowing — it becomes redundant if `kill_002` lands.)

### Fix 3 — Add Bull label to regime classifier (HIGH IMPACT, ~10 LOC)

- File: `scanner/main.py` lines 281-286
- Change:
```python
if last_slope > 0.005 and last_above:
    regime = 'Bull'
elif last_slope > 0 and last_above and ret20 > 3:    # NEW: post-recovery
    regime = 'Bull'
elif last_slope < -0.005 and not last_above:
    regime = 'Bear'
else:
    regime = 'Choppy'
```
(Need to compute `ret20` before the if-tree; currently it's computed after.)

- Companion: `scanner/scorer.py` — UP_TRI×Bull already scores +2, BULL_PROXY×Bull already scores +1, DOWN_TRI is regime-agnostic. No score breakage from adding the label.
- Effect: Today's 7-day "Choppy" stretch reclassifies to Bull. Brain can now mine UP_TRI×Bull cohorts independently. UP_TRI×Choppy cohort shrinks to genuinely-flat windows (where boost_patterns should remain conservative).

### Fix 4 — Add `Target2x` exit rule for BULL_PROXY (MEDIUM IMPACT, 1-line)

- File: `scanner/scorer.py` line 111-114
- Change:
```python
def get_exit_rule(signal, regime):
    if signal == 'UP_TRI' and regime == 'Bear':
        return 'Target2x'
    if signal == 'BULL_PROXY':
        return 'Target2x'             # NEW
    return 'Day6'
```
- Effect: BULL_PROXY's existing 4 TARGET_HIT events at +2.22R already exist. With a target rule active for all BULL_PROXY, more of the DAY6_WIN cohort (n=12, avg +0.86R) will convert. BULL_PROXY×Bear cohort tier moves from W to potentially S.

### Fix 5 — Mark expired brain proposals and re-run brain.yml after Fix 1 (MEDIUM IMPACT)

After Fix 1 lands, manually trigger `brain.yml` once (workflow_dispatch). The 3 expired proposals will be regenerated against current-day signal_history (which now includes the Apr 27-29 Choppy DOWN_TRI resolutions that prop_001 was gated on). New proposals may include kill_002 extension OR keep kill_001 narrow — let the brain decide on current data.

---

## 6. What I Could NOT Determine

1. **The user's dashboard "90 signals, −217 P&L" claim for DOWN_TRI.** Live `signal_history.json` shows 34 records / 23 resolved / −148.78 pnl for DOWN_TRI. Either the dashboard is querying archived data not in the current truth file, or it's including V6 prop_005 shadow rows that I deduplicated. The numbers in my report are from the current truth file as of 2026-05-04 mtime.

2. **Day-by-day Nifty path Apr 1 → May 12 2026.** Spec called for an empirical regime classification per day. I substituted the brain-layer cohort_health cross-reference, which is downstream of the same regime label. The substitution is informative for verdict purposes but doesn't constitute an independent regime-test. A fresh yfinance pull + per-day classification remains to be done if the user wants to independently verify the regime-shift transition timestamp.

3. **Whether the 8 currently-OPEN Choppy DOWN_TRI signals (LUPIN/OIL/ONGC and others) ultimately validated or refuted prop_001.** These signals fired Apr 24-29 and were still OPEN at the file's last mtime (2026-05-04). prop_001 was explicitly gated on their resolution. Until they resolve, the answer to "does DOWN_TRI work in Choppy?" cannot be empirically grounded — current 3/3 losses in Choppy is suggestive but underpowered.

4. **Per-trade MFE/MAE distribution for UP_TRI×Choppy DAY6 outcomes.** Adding it would tell us whether a target rule would help that cohort. Not in this run; would require a per-trade walk through OHLCV for the 35 Choppy UP_TRI resolutions.

5. **The lab/factory differentiator analyses (`lab/factory/bear_downtri/`, `lab/factory/bull_downtri/`, etc.)** — these directories contain sector × regime × signal differentiator extraction code. I did not read them in this diagnostic. If they carry an "edge factor I missed for DOWN_TRI", it would surface there. Worth a follow-up read before committing Fix 2 (broad DOWN_TRI block).

6. **Whether the M-13 schema oddity (8 records with `outcome=OPEN AND outcome_date` set simultaneously)** affects any of the diagnostic counts. The current EOD composer is defensive (`outcome != 'OPEN'`) but my pandas filter used the same. Probably not a count issue but documented for completeness.

7. **The user's exact intent on "Fib-based stops/targets" specification** — Fibonacci of what? Recent leg high→low? Multi-month swing? Specific level (38.2/50/61.8/127.2)? The fix in §4 above proposes targets via a simple `Target2x` extension; a true Fib refactor would parameterise the level. Surgical fix can land first, Fib refinement later as a parameter.
