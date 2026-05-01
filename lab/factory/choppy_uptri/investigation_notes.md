# Choppy UP_TRI — Investigation Notes

Process documentation for cell 1 of the barcode factory. The analytical journey, written for future cells to learn from.

---

## Hypotheses tested

### H1: Lifetime test_wr discriminates winners from rejected

**REFUTED.** VALIDATED mean test_wr 56.3% vs REJECTED 58.1% — REJECTED is slightly higher. Phase 4 walk-forward on 15-yr data could not predict which Choppy UP_TRI patterns would survive live. Lifetime evidence alone is insufficient for Choppy.

### H2: Lifetime drift discriminates

**REFUTED.** Both groups have identical 7.7pp drift. Curve-fit-risk proxy doesn't help here either.

### H3: Phase-4 tier (S/A/B) predicts live tier

**INVERTED.** All 18 VALIDATED + 37 PRELIMINARY are Phase-4 Tier B (the lowest production tier). REJECTED contains the Tier S (27) and Tier A (9) patterns. **High-tier backtest patterns over-fit Choppy in lifetime data.** This is a major finding.

### H4: D5 vs D6 horizon matters

**STRONGLY CONFIRMED.** All 18 VALIDATED are D5. PRELIMINARY is mixed (19 D6, 18 D5). REJECTED is split (82 D5, 74 D6). D5 horizon strongly favored — likely captures bounce setups before Choppy reverts.

### H5: A few features carry most differentiation signal

**CONFIRMED.** Two features dominate:
- `ema_alignment=bull` (+40.2pp differentiator)
- `coiled_spring_score=medium` (+36.3pp differentiator)

All other features below +10pp. Long tail of mild differentiators that don't move the needle individually.

### H6: Multi-feature combinations matter (specific 2/3-feature pairs)

**REFUTED for tight combinations.** No 2-feature pair appears in ≥30% of winners. Winners are heterogeneous beyond the two anchor features.

### H7: Sector matters

**REFUTED.** Sectors distribute across winners and losers similarly. F1's matched signals span 8+ sectors (utilities, financials, capital goods, pharma, chems, autos). Not a sector-conditioned setup.

### H8: Anti-features (negative differentiators) are useful

**CONFIRMED.** `MACD_histogram_slope=falling` (0% winners, 8% rejected), `higher_highs_intact_flag=True` (0% winners, 13% rejected), `ema_alignment=mixed` (0% winners, 6% rejected) — all clean exclusion features. Adding them to F1 improved precision (F4: 67% WR) but cut sample dramatically.

### H9: nifty_vol_regime distinguishes regime sub-character

**LIFETIME-CONFIRMED, LIVE-INAPPLICABLE.** Phase 5 differentiator analysis flagged `nifty_vol_regime=High` as the strongest anti-feature (0% winners, 19.2% rejected). But April 2026 live data has 100% `nifty_vol_regime=High` — the filter would reject every live signal. Useful as historical context, useless as live filter.

### H10: A clean filter can lift Choppy UP_TRI WR from 35% to 60%+

**PARTIAL.** F1 lifts to 58% (n=20). F4 lifts to 67% (n=6). The 60% bar wasn't cleanly cleared with meaningful sample size. Real edge exists but isn't dramatic.

---

## What was found

### Mechanism interpretation

**Choppy UP_TRI bounce setup** (filter F1):
- Stock has bullish EMA stack (EMA20 > EMA50 > EMA200, price above)
- `coiled_spring_score=medium` — moderate compression with bull-aligned trend (the score formula: 0.5·compression + 0.5·trend; medium = 33-67 range)
- Triggered in Choppy regime with high market vol
- Mean: a stock with established uptrend that compressed moderately into Choppy regime, fires UP_TRI breakout, captures bounce within a 5-day window before regime mean-reverts

**Counter-pattern (the rejected setup)**:
- `ema_alignment=mixed` (uncoordinated EMA stack)
- `MACD_histogram_slope=falling` (momentum already deteriorating)
- `higher_highs_intact_flag=True` (in continuation setup, not bounce)
- These are trend-following / continuation setups that fail in Choppy regime where trends don't continue

### Structural findings (free filters)

1. **D5 horizon dominates**: All VALIDATED are D5. Production should default Choppy UP_TRI to D5 hold.
2. **Phase-4 Tier B is the surviving tier**: not Tier S/A. Higher-tier patterns over-fit. Possible explanation: highest-edge patterns in Phase 4 lifetime backtest used calendar features (`day_of_week=Tue`) or other artifacts that don't replicate in current live regime.

---

## What was surprising

1. **Lifetime evidence completely fails to predict live outcome** for Choppy UP_TRI. test_wr ~ 57% in both VALIDATED and REJECTED. The two groups are statistically indistinguishable on lifetime metrics. Live evidence is the entire signal.

2. **Phase-4 Tier S/A patterns are 100% REJECTED**. Counter to intuition that higher backtest tier = better live performance. Suggests Phase 4 walk-forward stability filter (12pp drift cap) isn't tight enough to filter out Choppy regime artifact patterns.

3. **`higher_highs_intact_flag=True` is bad for Choppy bounces**. The "trend healthy" feature predicts losers in this cohort. The mechanism is regime-coupled: HHs intact = continuation setup; continuation breaks in Choppy.

4. **`ema_alignment=bull` and `coiled_spring_score=medium` are functionally identical filters in live data** (F1 = F2 produces identical matches). The two features co-occur because in Choppy regime the only stocks with bullish EMA stack also have medium compression — extreme compression has already broken down or extended.

---

## What was disappointing

1. **No filter cleared 60% WR with meaningful match rate.** F1 hits 58% on 22% match rate; F4 hits 67% on 6.6% match rate. The strong bar (60% AND ≥10% match rate) isn't cleared cleanly.

2. **Wide CIs on F1's 58%**: Wilson 95% on 11/19 → roughly [37%, 76%]. The point estimate is real but the bands are too wide to claim tight precision.

3. **Live n=91 limits all conclusions.** Bear and Bull cohort can't be filter-tested at all (cohort blocked or insufficient data). This cell's findings are Choppy-specific and need quarterly re-validation.

4. **Mechanism explanation cited "mean_reversion" / "weak_hands_capitulation" / "smart_money_positioning"** — plausible but not specifically tied to the two anchor features. The filter found a *what* but the *why* is somewhat post-hoc.

---

## What we still don't know

1. **Will F1 generalize beyond April 2026?** Need 2-3 more months of Choppy data. If matched WR drops below 50% over the next 50 signals, F1 was a sample artifact.

2. **Why does `coiled_spring_score=medium` win over `=high`?** Theoretical thinking says high compression → bigger breakout. Empirical finding says medium > high. Open question whether this is regime-coupled or universal.

3. **Are there hidden features (not in the 114) that would discriminate better?** This investigation only used Phase 1-5 features. Features like sector flow, options skew, or order book imbalance might separate F1 winners from losers within the matched set.

4. **Can the Phase-4 Tier S/A "loser" patterns be diagnosed?** They include high-test-WR patterns that didn't replicate. Reverse-engineering THEIR feature signatures would give us anti-patterns to actively reject — which features cause backtest curve-fit in Choppy.

5. **Does the cell scale to other (signal × regime) cells?** Method is generalizable, but each cell's filter will likely be different. UP_TRI×Bear and BULL_PROXY×Choppy need their own investigations.

---

## Methodology lessons for future cells

### Useful patterns

- **Start with descriptive comparison** (C1) before diving into features. The "lifetime stats are similar" finding shaped the entire investigation.
- **Compute differentiator score per (feature, level)** — surfaces winner features and anti-features in one pass.
- **Test 4-5 candidate filters**, not 1. F1 vs F4 trade-off (precision vs match rate) emerged from comparison.
- **Acknowledge live regime context** — the `nifty_vol_regime=High` finding from lifetime can't apply to live if all live signals are in that regime.

### Anti-patterns

- **Don't trust lifetime evidence alone** for Choppy regime. The cohort's lifetime test_wr was identical between winners and losers.
- **Don't expect strict 60% WR + 10% match-rate** without LARGE live samples. 91 signals isn't enough for precise filters.
- **Don't pick a filter just because it has highest WR** — F4 at n=6 is statistically wobbly. F1 at n=20 is the practical winner despite lower WR.
- **Don't fabricate mechanism**. Phase 4 backtest patterns can't be assigned mechanism post-hoc with high confidence; "weak_hands_capitulation" is plausible but not provable from features alone.

### What this cell can teach future cells

1. **Each (signal × regime) cohort may need different methodology.** Choppy UP_TRI worked because lifetime + live data both had ≥50 winners. UP_TRI×Bull won't work this way (no live data). DOWN_TRI×Bear won't work this way (live n=14 is too small for filter testing).

2. **Free structural filters exist.** Don't ignore them. D5 horizon and Phase-4 Tier B for Choppy UP_TRI fell out without feature analysis.

3. **Two features beat ten.** No need to overengineer. Top 2 differentiators (ema_alignment=bull, coiled_spring=medium) carried most of the signal.

4. **The investigation that fails is also valuable.** If the next cell shows no clean differentiators, document that honestly — it tells us Choppy UP_TRI is filterable but [signal × regime X] isn't.

---

## Connection to other Lab outputs

- **Phase 4 PHASE-04_combinations.md**: top UP_TRI×Choppy×D5/D6 patterns are the inputs for this analysis.
- **Phase 5 PHASE-05_live_validation.md**: tier verdicts (VALIDATED/PRELIMINARY/REJECTED) defined the winners-vs-rejected split.
- **ANALYZER barcodes.json**: ACTIVE_WATCH-tier Choppy UP_TRI patterns from analyzer should overlap heavily with F1-matched patterns. Quick cross-check: if analyzer outputs and F1 disagree substantially, both methods need calibration.
- **Phase 2 lifetime-Choppy importance**: `ema_alignment` ranked top in lifetime-Choppy Borda (rank 1). `coiled_spring_score` ranked 19. Phase 2 + this investigation converge on `ema_alignment=bull` as the single most important Choppy UP_TRI feature.

---

## Cell verdict

**Choppy UP_TRI cell v1: SHIP filter F1 with confidence MEDIUM.**

Filter F1 (`ema_alignment=bull AND coiled_spring_score=medium`) produces a real, repeatable +23pp lift over the 35% baseline on 22% of live Choppy UP_TRI signals. The lift is meaningful but the 58% WR point estimate has wide CIs.

For production:
- F1 matches → TAKE_SMALL (half size due to wide CI)
- F1 + F4 match → TAKE_FULL (high conviction, smaller subset)
- F1 doesn't match → SKIP

Re-validate quarterly. If F1 matched WR drops below 50% on next 30 signals → relegate to PRELIMINARY and investigate.
