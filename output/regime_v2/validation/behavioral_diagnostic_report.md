# Regime V2 — Behavioral Risk Diagnostic

**Generated:** 2026-05-14 (read-only — no code, thresholds, or production state modified)
**Window:** 2026-02-01 → 2026-04-30 (59 trading bars)
**Hypothesis under test (Opus PART 5 reframe):** V2's Feb-Apr failure is not BEAR under-detection but BULL persistence / risk-off lateness / trade-permission failure.

---

## Drawdown reference points (Nifty, window-peak basis)

| Crossing | Date |
|---|---|
| First DD ≤ -5% | 2026-03-04 |
| First DD ≤ -8% | 2026-03-11 |
| First DD ≤ -10% | 2026-03-13 |

Window peak Feb 14 area; trough ~Mar 30. 37 bars in DD-5%, 19 in DD-8%, 12 in DD-10%.

---

## Diagnostic 1 — State Distribution

| Metric | retune3 | retune4 |
|---|---|---|
| total_bars | 59 | 59 |
| **state_raw BULL** | **0** | **0** |
| state_raw BULL_RECOVERY | 0 | 0 |
| state_raw CHOPPY | 22 | 22 |
| state_raw BEAR_RECOVERY | 9 | 9 |
| state_raw BEAR | 28 | 28 |
| **state (smoothed) BULL** | **0** | **0** |
| state BULL_RECOVERY | 0 | 0 |
| state CHOPPY | 51 | 26 |
| state BEAR_RECOVERY | 3 | 7 |
| state BEAR | **5** | **26** |
| First smoothed BULL exit | never_in_bull | never_in_bull |
| First raw BEAR | 2026-02-02 | 2026-02-02 |
| First smoothed BEAR | 2026-03-05 | 2026-03-05 |
| BULL days after peak (Feb 14) | 0 | 0 |
| BULL days after DD-5 / -8 / -10 | 0 / 0 / 0 | 0 / 0 / 0 |

**Key fact:** Zero BULL days, zero BULL_RECOVERY days, in either retune across the full window.

---

## Diagnostic 2 — Risk-Off Timing

(`risk_off` = smoothed state ∉ {BULL, BULL_RECOVERY})

| Metric | retune3 | retune4 |
|---|---|---|
| First risk_off date | 2026-02-02 | 2026-02-02 |
| Total risk_off days | 59 / 59 | 59 / 59 |
| % risk_off across whole window | **100.0%** | **100.0%** |
| % risk_off after DD-5% | 100.0% | 100.0% |
| % risk_off after DD-8% | 100.0% | 100.0% |
| % risk_off after DD-10% | 100.0% | 100.0% |
| BULL/BULL_RECOVERY days after peak | 0 | 0 |

**Key fact:** System was risk_off on day 1 of the window (Feb 2) — ~30 calendar days before the -5% drawdown crossed (Mar 4). Risk-off timing is correct and ample.

---

## Diagnostic 3 — Raw-state V5 P2 vs Smoothed-state V5 P2 (lifetime)

(UP_TRI / BULL_PROXY where state ∈ {BEAR, BEAR_RECOVERY} at signal time)

| Source | UP_TRI WR | UP_TRI n | BULL_PROXY WR | BULL_PROXY n |
|---|---|---|---|---|
| retune3 smoothed | 100.0% | **1** | — | 0 |
| retune3 state_raw | **88.6%** | **105** | 78.9% | 19 |
| retune4 smoothed | 75.9% | 133 | 88.2% | 17 |
| retune4 state_raw | 88.6% | 105 | 78.9% | 19 |

**Key fact:** retune3 state_raw clears V5 P2 target (≥85% WR, large n). retune3 smoothed has n=1 — smoothing kills the cohort. retune4 smoothed gains n but loses quality (75.9% < target).

---

## Diagnostic 4 — Persistence Suppression Map (2024-2026)

(Bars where state_raw=BEAR but smoothed state≠BEAR. Forward-5d Nifty return classifies whether suppression HELPED (price bounced ⇒ smoothing appropriate) or HURT (price fell further ⇒ smoothing filtered out a real signal).)

| Metric | retune3 | retune4 |
|---|---|---|
| Total suppressed bars | 34 | 16 |
| fwd-5d Nifty avg (post suppression) | -0.07% | -0.53% |
| % HELPED (fwd-5d positive) | 44.1% | 43.8% |
| % HURT (fwd-5d negative) | **55.9%** | **56.2%** |

**Key fact:** Persistence is roughly coin-flip and mildly destructive. Suppression filters real downward signal more often than it filters noise.

---

## Diagnostic 5 — Trade Permission (Feb-April 2026)

Schemes:
- **A** = current production (V2 + bypass, `v2_bear_tradeable` column)
- **B** = state_raw Bear-tradeable (raw BEAR/BEAR_RECOVERY + same -9% CHOPPY bypass)
- **C** = risk_off only (anything not smoothed BULL)
- **D** = V1 production logic (regime=='Bear')

### retune3

| Signal | Total | A allowed (WR) | B allowed (WR) | C allowed (WR) | D allowed (WR) |
|---|---|---|---|---|---|
| UP_TRI | 229 | 64 (94.3%) | 119 (88.6%) | 229 (62.7%) | 107 (94.7%) |
| BULL_PROXY | 27 | 10 (90.0%) | 19 (78.9%) | 27 (66.7%) | 16 (87.5%) |
| DOWN_TRI | 38 | 20 (21.1%) | 35 (18.8%) | 38 (17.1%) | 21 (20.0%) |

### retune4

| Signal | Total | A allowed (WR) | B allowed (WR) | C allowed (WR) | D allowed (WR) |
|---|---|---|---|---|---|
| UP_TRI | 229 | **155 (75.9%)** | 119 (88.6%) | 229 (62.7%) | 107 (94.7%) |
| BULL_PROXY | 27 | 17 (88.2%) | 19 (78.9%) | 27 (66.7%) | 16 (87.5%) |
| DOWN_TRI | 38 | 37 (17.6%) | 35 (18.8%) | 38 (17.1%) | 21 (20.0%) |

BULL_PROXY signals during deepest drawdown (Mar 25 – Apr 1): retune3 = **0**, retune4 = **0**.

**Key facts:**
- retune3-A: 64 UP_TRI @ 94.3% WR (excellent quality, low recall).
- retune3-B (state_raw + bypass): 119 UP_TRI @ 88.6% — meets V5 P2.
- retune4-A: 155 UP_TRI @ 75.9% — high recall, fails V5 P2 quality.
- C (risk_off only) is too permissive — UP_TRI WR falls to 62.7%.
- D (V1 production) reads best on this slice at 94.7% n=107, but V1's Bear bucket is the heterogeneous Group A + Group B mix flagged in earlier out-movers analysis.

---

## Final Answers (A–F)

### A. Is the real failure BEAR under-detection?

**Verdict: NOT INDICATED at the trade-permission layer. POSSIBLE only at the cosmetic-labeling layer.**

state_raw fires BEAR on 28/59 bars + BEAR_RECOVERY on 9 more = 37/59 (62.7%) Bear-family in the window. Gates work. retune3 smoothed shows only 5 BEAR days, but this does NOT translate to worse trading — retune3-B (state_raw path) admits 119 UP_TRI @ 88.6% WR vs retune3-A (smoothed+bypass) at 64 @ 94.3%. The bypass + raw-state path is the operational signal; the smoothed label is largely cosmetic.

### B. Or is the real failure BULL staying on too long?

**Verdict: NOT INDICATED. PART 5 hypothesis falsified.**

Zero BULL days in the entire Feb-Apr window. Zero BULL_RECOVERY. First risk_off Feb 2 — 30+ days before -5% drawdown began Mar 4. PART 5's "how many BULL days persisted into the crash?" returns zero. BULL is OFF, not stubborn. (Possible inverse concern — BULL exited too early in late Jan with no real warning — is not what the diagnostic asked about and is left as open work.)

### C. Did the system become risk-off early enough?

**Verdict: STRONGLY INDICATED — risk-off is early, not late.**

100% of window is risk_off, including 100% of all drawdown sub-windows. First risk_off bar is Feb 2, the first bar of the window. Risk-off timing is unambiguously adequate. This is the most decisive finding.

### D. Does raw state solve the issue?

**Verdict: STRONGLY INDICATED for retune3.**

retune3 state_raw UP_TRI Bear-family: 88.6% WR, n=105 — clears V5 P2 ≥85% with large sample. retune3 smoothed: n=1 (unusable). For retune4 the smoothed path retains n but degrades to 75.9% WR (misses target), while raw stays at 88.6%. **Raw state is the better cohort gate; smoothing is harming, not helping, V5 P2.**

### E. Does persistence suppress useful BEAR or filter noise?

**Verdict: POSSIBLE — suppression is ~coin-flip, mildly destructive.**

55.9% of suppressed bars (retune3) saw Nifty fall further over the next 5d — the suppression filtered real downward signal more often than noise. Avg fwd-5d return after suppression is -0.07% (retune3) / -0.53% (retune4) — not the positive value a clean noise filter would produce. Persistence layer is doing weak, noisy work.

### F. What should the next step be?

**Verdict: REFRAME — stop tuning persistence.**

The Opus PART 5 reframe ("BULL stubbornness") is **falsified** by data. The actual fact pattern:
1. Risk-off timing is excellent (100% from day 1).
2. state_raw BEAR detection is strong (62.7% of window Bear-family).
3. state_raw V5 P2 quality is strong (88.6% WR, n=105) — clears target.
4. Persistence/smoothing layer either suppresses BEAR labels (retune3) or destroys cohort quality when loosened (retune4), with no clear noise-filter benefit (55.9% HURT vs 44.1% HELPED).
5. Trade-permission gate trades recall for precision with no obvious winner.

Two candidate reframes (open questions, not implementation):

- **Reframe 1 — drop smoothed `state` from V5 P2 cohort assignment.** Use state_raw directly. Persistence becomes a display/UX layer only, not part of trading decisions. Supported by D3 (raw beats smoothed) and D4 (suppression is coin-flip).

- **Reframe 2 — investigate Bear-cohort heterogeneity.** Schemes A/B/C/D admit UP_TRI at 62-95% WR across overlapping bars. Variance suggests sub-cohorts. The right question may be "what feature splits the high-WR Bear days from the low-WR ones?" not "how do we tune persistence?"

Not recommended: another retune cycle. retune3 already satisfies V5 P2 at the raw-state level (which is what the production bypass uses). retune4 made quality worse. Calibration has hit diminishing returns.

---

## One number to remember

**BULL days in Feb-April 2026 (both retunes): 0.**

PART 5's central question — "how many BULL days persisted into the crash?" — answers zero. The hypothesis is decisively rejected. The next investigation should be "is the persistence layer worth keeping for V5 P2 cohort lookup at all?" not "Bull-exit timing."

---

## Provenance

| Source | Path |
|---|---|
| retune3 history | `output/regime_v2/regime_historical_retune3.parquet` |
| retune4 history | `output/regime_v2/regime_historical_retune4.parquet` |
| retune3 signals | `output/regime_v2/signals_remapped_retune3_with_bypass.parquet` |
| retune4 signals | `output/regime_v2/signals_remapped_retune4_with_bypass.parquet` |
| Nifty OHLCV | `data/historical/nifty.parquet` |

This diagnostic was read-only. No production code, signal history, regime parquet, or rules file was modified.
