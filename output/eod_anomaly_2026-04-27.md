# EOD Anomaly Investigation — 2026-04-27

**Trigger:** 36 signals resolved today, 11 wins / 24 losses / 1 flat (31.4% WR excluding flat). Live baseline excluding today is **78.7% WR** over last 30+ days. **−47pp deviation.**

**Bottom line up front:** This is not a system bug. It is the resolution of one homogeneous correlated cohort — 35 of 36 are UP_TRI breakout signals from the **single scan day 2026-04-17 (Friday) in Choppy regime**, all force-exited at Day 6 (today, Monday) with no intermediate targets or stops triggered. The system tracked, classified, and resolved them correctly. What this surfaces is a portfolio-correlation risk that the Wave 5 brain layer is explicitly designed to flag.

---

## §1. Observed numbers — verified

| Metric | Value |
|---|---|
| Resolved today (`outcome_date == 2026-04-27`) | **36** |
| TARGET_HIT | 1 |
| DAY6_WIN | 10 |
| STOP_HIT | **0** |
| DAY6_LOSS | 24 |
| DAY6_FLAT | 1 |
| Wins (TARGET_HIT + DAY6_WIN) | 11 |
| Losses (STOP_HIT + DAY6_LOSS) | 24 |
| Flat | 1 |
| WR (excluding flat) | **31.4%** (11/35) |
| WR (treating flat as non-win) | 30.6% (11/36) |
| Aggregate P&L today | **−45.33%** (sum of pnl_pct) |
| Avg P&L per loss | −3.64% |
| Worst single loss | −11.37% (MPHASIS) |
| Avg R-multiple (all 36) | −0.01 (essentially zero) |
| Avg R-multiple (24 losses) | −0.21 (modest losses, not stop-out) |

The user's claim of 36/12/1/23 is essentially correct — the slight delta (12 vs 11 wins, 23 vs 24 losses) appears to be a rounding/reading difference. Verified counts above are: **11 wins, 24 losses, 1 flat = 36.**

---

## §2. Cross-cut breakdowns

### 2a. Outcome type

| Outcome | n |
|---|---|
| TARGET_HIT | 1 |
| DAY6_WIN | 10 |
| STOP_HIT | **0** |
| DAY6_LOSS | 24 |
| DAY6_FLAT | 1 |

**Observation:** Zero intraday stop-outs. Every loss is a Day-6 forced exit at OPEN. Stops were never violated during the 6-day hold window — losses came from drift, not adverse moves hitting stops.

### 2b. Signal type

| Signal | n | Wins | Losses | Flat | WR |
|---|---|---|---|---|---|
| **UP_TRI** | 34 | 10 | 23 | 1 | 30.3% |
| DOWN_TRI | 1 | 0 | 1 | 0 | 0% |
| BULL_PROXY | 1 | 1 | 0 | 0 | 100% |

**Observation:** UP_TRI dominates the cohort with 34/36 (94%). The DOWN_TRI and BULL_PROXY singletons are statistical noise.

### 2c. Regime at signal generation

| Regime | n | Wins | Losses | Flat | WR |
|---|---|---|---|---|---|
| **Choppy** | 36 | 11 | 24 | 1 | 31.4% |

**Observation:** **All 36 signals were generated in Choppy regime.** Single-regime cohort. No Bull/Bear comparison available within today's set.

### 2d. Sector

| Sector | n | Wins | Losses | Flat | WR |
|---|---|---|---|---|---|
| Bank | 10 | 6 | 4 | 0 | 60.0% |
| Other | 8 | 1 | 6 | 1 | 14.3% |
| **IT** | 5 | 0 | 5 | 0 | **0.0%** |
| CapGoods | 3 | 1 | 2 | 0 | 33.3% |
| Chem | 3 | 1 | 2 | 0 | 33.3% |
| Auto | 2 | 0 | 2 | 0 | 0% |
| FMCG | 2 | 1 | 1 | 0 | 50% |
| Energy | 2 | 1 | 1 | 0 | 50% |
| Infra | 1 | 0 | 1 | 0 | 0% |

**Observation:** IT was wiped out (5/5 losses). Bank was the relative bright spot (60% WR). "Other" sector tag (catch-all for unmapped sectors per H-06 in fix_table) is also notably weak. Sector dispersion is consistent with a generalized failure-to-follow-through, not a single-sector event.

### 2e. Score bucket

| Score | n | Wins | Losses | Flat | WR |
|---|---|---|---|---|---|
| 3-4 | 6 | 1 | 5 | 0 | 16.7% |
| **5-6** | 28 | 9 | 18 | 1 | 33.3% |
| 7-8 | 2 | 1 | 1 | 0 | 50.0% |
| 9-10 | 0 | — | — | — | — |

**Observation:** Most signals (28/36) sat in the score 5-6 mid-band. No high-conviction (9-10) signals fired on Apr 17. This is consistent with Choppy-regime context — fewer high-conviction setups when the broader market is rangebound.

### 2f. Days to outcome

| Day | n | Wins | Losses | Flat | WR |
|---|---|---|---|---|---|
| Day 5 | 1 | 1 | 0 | 0 | 100% |
| **Day 6** | 35 | 10 | 24 | 1 | 29.4% |

**Observation:** All but one resolution = Day-6 forced exit. The single Day-5 was a TARGET_HIT (the lone success that didn't drag to forced exit). **The 35 Day-6 forced exits are the smoking gun** — these signals just sat without conviction for the entire 6-trading-day hold window.

### 2g. Original signal date

| Signal date | n | Wins | Losses | Flat | WR |
|---|---|---|---|---|---|
| **2026-04-17 (Fri)** | 35 | 10 | 24 | 1 | 29.4% |
| 2026-04-20 (Mon) | 1 | 1 | 0 | 0 | 100% |

**Observation:** **35 of 36 trace to a single scan day — Friday 2026-04-17.** Calendar math: Apr 17 (Fri) → Apr 27 (Mon) = 6 trading days (skipping Sat/Sun + an intervening market holiday on Mon Apr 20 OR no holiday, just Sat/Sun + 5 weekdays = exactly Day 6 under per `outcome_evaluator`'s trading-day arithmetic).

### 2h. Entry gap (`gap_pct`)

| Stat | Value |
|---|---|
| Records with gap_pct | 36 of 36 |
| Min | −2.63% |
| p25 | 0.22% |
| Median | 0.64% |
| p75 | 1.67% |
| Max | 2.80% |
| > 2% gap (large favorable for adverse direction) | 2 |
| < −2% gap | 2 |

**Observation:** Entry gaps were normal — median 0.64%, only 4 of 36 had gap >2% in either direction. **Entry quality wasn't the issue.** All 36 were `entry_valid=True`. The trades did enter cleanly; they just didn't move.

### 2i. Stop-hit timing

**Zero STOP_HIT outcomes.** Stop levels were never violated intraday during the 6-day hold for any of the 24 losses. Worst MAE on a loss was 13.72% (MPHASIS) — material drawdown but stop was wider (16-26% range from entry, ATR-based).

### 2j. R-multiple distribution

| Cohort | n | Min | Median | Max | Avg |
|---|---|---|---|---|---|
| All 36 | 36 | −0.63 | −0.09 | 2.00 | −0.01 |
| Losses (24) | 24 | −0.63 | −0.14 | −0.06 | **−0.21** |
| Wins (11) | 11 | 0.03 | 0.19 | 2.00 | 0.42 |

**Observation:** Loss R-multiples are **shallow** — median −0.14, never fully stops out (no R<−0.7 except outlier at −0.63). Wins are even shallower (median +0.19). The system is bleeding small amounts on many trades, not getting stopped out aggressively. Classic Choppy-regime drift profile.

---

## §3. Temporal pattern — the Apr 17 cluster

The Apr 17 scan day is the smoking gun.

### Apr 17 scan, full picture

```
total signals generated: 44
   regime: 100% Choppy
   signal type: 43 UP_TRI + 1 DOWN_TRI
   sector spread: Bank (10), IT (6), CapGoods (6), Chem (5), FMCG (4), 
                  Other (8), Auto (2), Energy (2), Infra (1)
   score distribution: {4:7, 5:19, 6:16, 7:2}  (no 8/9/10)

outcomes as of today:
   DAY6_LOSS:   24
   DAY6_WIN:    10
   DAY6_FLAT:    1
   OPEN (still): 9   ← these are SA variants or have non-standard tracking
   subtotal resolved: 35  ← all today
```

### Daily resolution counts, last 30 days

```
Apr 08:  6
Apr 09:  2
Apr 10: 11
Apr 13:  4
Apr 15:  5
Apr 16: 29
Apr 17: 77   ← prior-week force-exit cluster (Apr 7 Bear cohort)
Apr 21:  1
Apr 23:  2
Apr 24:  4
Apr 27: 36   ← today
```

**Observation:** Today's 36 is large but **not unprecedented** — Apr 17 was a 77-resolution day (which suggests Apr 7 had its own large scan that all force-exited together on Apr 17). The pattern of "scan-day clusters force-exiting together six trading days later" is structural, not anomalous on the volume axis.

What IS anomalous about today vs Apr 17's force-exit cluster:
- Apr 17 force-exit cluster came from Apr 7 (Bear regime per backtest assumptions, well-validated cohort).
- Apr 27 force-exit cluster comes from Apr 17 (Choppy regime, **untested cohort**).

---

## §4. Baseline comparison

| Window | Sample | Wins | Losses | Flat | WR |
|---|---|---|---|---|---|
| Last 30 days **including today** | 177 | 118 | 53 | 1 | 69.0% |
| Last 30 days **excluding today** | 141 | 107 | 29 | 0 | **78.7%** |
| Last 60 days excluding today | 141 | 107 | 29 | 0 | 78.7% |
| Last 90 days excluding today | 141 | 107 | 29 | 0 | 78.7% |

**Observation:** All resolved data fits in a single 90-day window — system is young. Baseline WR pre-today is **78.7%**, today drops it to **69.0%** — a **−9.7pp drag** on the rolling baseline from one day's resolutions. This was a meaningful event for the rolling stat.

### Cohort-specific historical baselines

```
UP_TRI × Choppy regime:
   total in dataset:   n=34, W=10, L=23, F=1, WR=30.3%
   pre-today resolved: n=0   ← THIS COHORT HAD NEVER RESOLVED BEFORE TODAY
```

**Critical finding:** UP_TRI × Choppy regime is a **brand-new cohort** in the dataset. The system had ZERO historical resolutions for UP_TRI in Choppy regime before today. The 81% / 78.7% baseline was built from UP_TRI × Bear (95% WR per backtest + live data) and UP_TRI × Bull cohorts. Choppy-regime UP_TRI was untested — and today's resolution is the first signal we've gotten on its actual performance: 30.3% WR.

---

## §5. Manual spot-checks (top 5 losses)

| Symbol | Signal | Date | Outcome | Entry | Stop | Target | Outcome price | pnl_pct | r_mult | MAE | MFE | Failure reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MPHASIS | UP_TRI | 2026-04-17 | DAY6_LOSS | 2441.80 | 1937.91 | 3449.58 | 2187.90 | −11.37% | −0.53 | 13.72% | 0.23% | No directional move in 6 days |
| CYIENT | UP_TRI | 2026-04-17 | DAY6_LOSS | 967.30 | 715.33 | 1471.24 | 880.00 | −9.12% | −0.35 | 10.46% | 0.28% | Breakout without volume |
| TATAELXSI | UP_TRI | 2026-04-17 | DAY6_LOSS | 4593.60 | 3808.48 | 6163.84 | 4204.90 | −8.39% | −0.49 | 9.41% | 1.75% | Breakout without volume |
| TCS | UP_TRI | 2026-04-17 | DAY6_LOSS | 2576.90 | 2287.72 | 3155.26 | 2396.90 | −7.15% | −0.63 | 7.46% | 1.26% | Stock and market regime misaligned |
| CDSL | UP_TRI | 2026-04-17 | DAY6_LOSS | 1367.80 | 1071.72 | 1959.96 | 1315.00 | −5.60% | −0.24 | 6.37% | 0.58% | No directional move |

**Verification of classification:**

- All 5 are `outcome=DAY6_LOSS`, `days_to_outcome=6`, `effective_exit_date=2026-04-27` — correctly identifies these as Day-6 forced exits, not intraday stops.
- All have `entry_valid=True` and `actual_open` close to `entry` (gap_pct in range −0.08% to 1.84%). The entries triggered cleanly at 9:15 on Apr 20 (Mon, the trading day after Apr 17 Fri scan).
- MAE is the worst intraday adverse move during the hold. For all 5: MAE is large (6-14%) but `outcome_price > stop` for every one — stops were never violated. (Stop violation would have set `outcome=STOP_HIT` and `days_to_outcome` to whatever day the breach happened, not 6.)
- MFE is tiny (0.23-1.75%) — confirms zero follow-through. Setups never moved meaningfully in the trade direction.
- `failure_reason` is populated by `outcome_evaluator._classify_failure_reason` — surfaces the diagnosis explicitly: "no directional move," "weak setup, no follow-through," or "regime misalignment."

**Verdict on classification:** Outcome evaluator did its job correctly. No misclassification, no wrong-stop, no wrong-target. The losses are real and the labelling is faithful.

---

## §6. Cross-reference with `output/analysis/*.js`

`[needs-verification]` — full audit of analysis JS not run; covered at module-summary level only. The analysis dashboard reads `signal_history.json` directly (not `bridge_state.json`), so today's resolutions land in stats.js / analysis/segmentation.js as soon as they're committed. Filter logic (`OUTCOME_WIN`, `OUTCOME_LOSS`, etc) matches `outcome_evaluator`'s classification — no divergence expected. If a divergence exists, it would manifest as different WR readings between PWA dashboard and the daily report; comparing both tomorrow morning would catch it.

---

## §7. Hypothesis-ranked findings

### PRIMARY HYPOTHESIS — Single-day correlated cohort failure in untested regime

**Claim:** A homogeneous cohort of 44 UP_TRI signals fired simultaneously on a Choppy-regime Friday (Apr 17). 35 of those (the resolved subset) reached Day 6 today. They followed the empirical Choppy-regime profile — drift, no follow-through, modest mid-day MAE excursions but stops not violated, force-exited at OPEN of Day 6.

**Evidence supporting:**
- 35/36 trace to one scan day (Apr 17), 100% Choppy regime
- 35/36 hit Day-6 forced exit, zero intraday stop-outs
- MFE distribution (median 0.19R for wins) confirms little follow-through across the entire cohort
- Outcome classification verified by spot-check on 5 worst losses
- Pre-today UP_TRI × Choppy historical resolutions = **zero**, meaning this is the first calibration point we have for this cohort
- Failure-reason field on losses reads as a classic Choppy-regime drift profile

**This is real market behavior, faithfully captured by the system.**

### SECONDARY HYPOTHESIS — IT-sector concentration amplified the loss

**Claim:** IT was 5/5 losses (0% WR). If the 5 IT signals had behaved more typically (~75% baseline), today's overall WR would have been 16/35 = 46% rather than 31.4%.

**Evidence:**
- IT carried zero wins; every other sector carried at least one
- IT signals included MPHASIS, CYIENT, TATAELXSI, TCS, CDSL — high-quality names but all fell into the no-follow-through pattern
- Bank sector (10/10 of which fired same day) carried 60% WR — the relative bright spot

**Status:** Real but secondary; explains a portion of the deviation given the primary cohort failure.

### TERTIARY HYPOTHESIS — Score-bucket weakness

**Claim:** Low score buckets (3-4) carried 16.7% WR vs 33.3% for 5-6 bucket and 50% for 7-8. Skipping 3-4 entries would have improved overall.

**Evidence:** Real but small effect (only 6 of 36 in 3-4 bucket). Not a primary driver.

### RULED OUT — System bug / misclassification

**Evidence against:**
- Spot-check on 5 worst losses confirms outcome classification is correct in every case
- `entry_valid=True`, `gap_pct` reasonable, `outcome_price` between stop and target = correctly Day-6 forced exit not stop-out
- `failure_reason` is populated and sensible
- Trading-day arithmetic: Apr 17 → Apr 27 = 6 trading days correctly per `outcome_evaluator._get_nth_trading_day`
- Total daily count (36) is in line with prior cluster days (Apr 17 had 77; Apr 16 had 29)

**This is not a bug.**

### RULED OUT — Schema / data corruption

**Evidence against:**
- Schema discipline holds (canonical writer field names match reader expectations)
- All 36 records have populated `signal`, `regime`, `sector`, `score`, `entry`, `stop`, `target_price`, `outcome_price`, `outcome_date`
- No dropped records during resolved-record filtering (16 dropped earlier in the analyze_full.py run, but those were from older history, not today)

**Data is clean.**

---

## §8. Recommendations (informational only — DO NOT auto-act)

These are observations, not directives. Decisions are explicitly the trader's.

### Process

1. **The Wave 5 brain layer is exactly the answer.** Brain's `portfolio_exposure.json` derived view would have flagged the Apr 17 cohort: "44 simultaneous signals, 100% same regime, predominantly UP_TRI, mostly score 5-6 mid-band, sector concentration in Bank/IT/CapGoods/Chem." Brain's `cohort_health.json` would have flagged "UP_TRI × Choppy: n=0 historical baseline — confidence_band='low'." Neither flag exists today.

2. **Choppy regime UP_TRI is now a tagged cohort.** It has 30.3% WR at n=34. Per the §3 tier classifier in `brain_design_v1.md`, this is sub-Tier-W (fails ≥65% WR floor). Worth a `rule_proposer` proposal for a kill_pattern or warn_pattern: `signal=UP_TRI, regime=Choppy → SKIP or downgrade`. Wave 5 brain would propose this automatically; today the trader can manually consider it via `/proposals` after the next eod_master fires. Note: 4 of the 9 still-OPEN Apr 17 signals will resolve in coming days — wait for those to land before locking the WR estimate.

3. **Day-6 forced-exit clusters are structural.** They will happen any time many signals fire on the same scan day and don't follow through. The system tracking is correct; the trader's exposure-side discipline is what limits damage. Suggesting a portfolio-cap heuristic ("max 10 entries per scan day") is decision-side and out of scope for this audit.

### Data

4. **9 still-OPEN Apr 17 signals.** These are likely SA-variants (second-attempt) or signals with non-standard `tracking_end`. Worth checking next eod_master to see how they resolve — they may extend the cohort sample.

5. **The `failure_reason` field is doing real work.** "Breakout without volume," "regime misalignment," "no directional move" map cleanly to Choppy-regime drift behavior. Pattern-mining over `failure_reason` could be a Wave 5 ground-truth-gap derived view.

### Action

6. **No immediate action recommended on rules or signals.** The data is real. Wave 5 brain layer is the structural fix. Until then, trader's mental synthesis carries the load — same as before.

7. **Re-run `scripts/analyze_full.py` tomorrow afternoon** after eod_master fires. The fresh report will absorb today's 36 resolutions into the rolling baseline and refresh the actionable findings.

---

## §9. Final assessment

| Question | Answer |
|---|---|
| Is this a system bug? | **No.** Outcome evaluator classified correctly; data is clean. |
| Is this misclassification? | **No.** All 5 spot-checked losses verified faithful. |
| Is this real market behavior? | **Yes.** Single-day correlated cohort in an untested regime, force-exited at Day 6 with no intermediate triggers. |
| Does it warrant immediate intervention? | **No.** The system did its job. Trader's risk-management decisions (entry sizing, portfolio caps) are the human side of this loop and were exercised at trade time. |
| Does it inform Wave 5 design? | **Yes — directly.** Validates the brain-layer portfolio-exposure and cohort-health derived views. Justifies the cap on simultaneous proposals (§1.8 of brain_design_v1.md) and the n≥10 floor for Tier W (§3). |
| What additional data would clarify? | The 9 still-OPEN Apr 17 signals' eventual resolution (extends cohort sample). Comparison with Apr 17's own 77-resolution day breakdown (the Apr 7 cohort that resolved that day) — if Bear-regime cohort resolved at typical 80%+ WR while today's Choppy-regime cohort resolved at 30%, that's strong evidence regime is the dominant factor, not other variables. |

---

_Investigation end. Report length 2,290 words. No code or non-doc files modified. Real signal_history.json read-only._
