# W3 Walk-Forward Stability — Sonnet 4.5 Critique

**Date:** 2026-05-03

# Walk-Forward Stability Analysis Critique

## 1. Are SURVIVOR thresholds defensible?

Your thresholds (mean_lift > 5pp, pct_positive > 70%, n≥5) are **too lenient for deployment capital**. The 5pp lift threshold allows marginal noise through—witness rule_031 at +16pp (SURVIVOR) vs rule_029 at +18pp (DEGRADER). Both clear the bar, but one is collapsing. The 70% positive threshold is reasonable for stability, but n≥5 is dangerously low for statistical confidence over 182 windows.

**Recommendation: Tighten to mean_lift > 8pp AND pct_positive > 75% AND n≥10**. This would retain rule_019 (your workhorse with n=191) and likely win_001/kill_001, while filtering out rule_031 (n=18, borderline sample) and win_007 (degrading despite +32pp mean). The 5pp threshold lets through survivors that are barely distinguishable from measurement noise in 60-day windows.

The current bar produces 5 survivors but only 3 intersect with backtest—meaning 40% of your "survivors" failed Lab's original filters. That's evidence your walk-forward bar is catching different (possibly weaker) signals than backtest intended. Tighten it.

## 2. The 3 INTERSECTION rules—genuinely high-confidence?

**kill_001 and rule_019 are defensible; win_001 is suspect**. kill_001 shows -7.1pp lift with 39% positive across 80 windows—this is a clear, stable kill signal that validates in both tests. rule_019 has n=191 mean per window over 23 matching windows, 78% positive—this is real edge with massive sample support. The lift (+17.2pp) and breadth make it your anchor rule.

win_001 is problematic. Only n=28 mean across windows, 71% positive barely clears threshold, and +8.1pp lift is marginal. The "recent_Δ +39.3pp" suggests recent strength, but this could be regime-specific (Bear×Auto×UP_TRI working only in 2024-2026 conditions). It's "in production" per your note—if it was deployed based on Lab's work, that's circular validation (backtest → production → walk-forward all using overlapping data). **Don't count win_001 as independent confirmation.**

The intersection isn't compromised by data overlap per se (walk-forward windows are honest OOS within each step), but it's compromised by **selection bias**: Lab chose rules that worked in-sample through April 2026, and your walk-forward ends April 2026. The entire 15-year span was available to Lab during rule design. True confirmation would require post-April-2026 data only.

## 3. DEGRADERS—skip or document as regime shift?

**rule_029 (Pharma hot) should be REJECTED outright, not deployed**. Mean +18pp across history is irrelevant when recent_Δ is -57.7pp—this is catastrophic regime break. The walk-forward design exists precisely to catch this: a rule that worked 2011-2023 but fails 2024-2026. Deploying it now because of historical mean would be the textbook error walk-forward prevents. Document as "regime shift detected, Pharma hot edge collapsed," and kill it.

**win_003 (IT×Bear) is already in production and degrading** (-14.1pp recent_Δ from +5.2pp mean). This demands immediate recall or capital reduction. The mean lift is barely above your survivor threshold, and the fade suggests the edge is dying. If it's live with real capital, you have 60-day evaluation protocols per Case 2—trigger them now. Don't wait for it to turn fully negative.

**win_007 (Bear BULL_PROXY hot) should not deploy despite +32.5pp mean**. Recent_Δ -10.5pp with only n=8 windows means high variance and likely overfitting to a few extreme windows early in the 15-year span. The 90% positive rate across 8 windows sounds great until you realize 8 windows is ~480 days total (60-day windows × 8)—laughably small sample. This is a **statistical artifact, not deployable edge**.

## 4. Bull rules negative lift—data deficiency or genuine refutation?

**Genuine data deficiency, not refutation of Bull edge**. Your 15-year span (2011-2026) includes the 2011-2020 bull market, 2022 bear, 2023 recovery, and 2024-2026 chop. Bull rules triggering on "bull_uptri_healthy" or "bull_uptri_late" require sustained Bull regime—but your 60-day windows are too short to capture multi-month bull runs, and the step function (30-day step) means you're sampling regime transitions, not regime midpoints.

The negative lift on rule_011 (Bull UP_TRI healthy, -5.7pp, n=180) is particularly telling: 180 windows with matches means the rule fires frequently, but lift is negative. This suggests **Bull UP_TRI is a lagging indicator**—by the time it confirms "healthy," the easy gains are gone and mean reversion begins. This isn't a data problem; it's a signal problem. Lab's Bull work may be wrong.

**You cannot validate Bull rules in this dataset**. Either (a) extend windows to 120 days to capture full bull cycles, (b) regime-filter the walk-forward to test Bull rules only in Bull-labeled windows, or (c) acknowledge Bull rules are unvalidated and exclude them from deployment. Current evidence leans toward "Lab's Bull rules don't work," but the test design doesn't cleanly separate "no Bull data" from "Bull logic is bad."

## 5. rule_031 (IT hot) vs rule_029 (Pharma hot)—real edge or artifact?

**IT hot (rule_031) looks like recent-regime artifact; Pharma hot (rule_029) is historical artifact now dead**. Both are Bear×UP_TRI×hot_sector, differing only in sector. rule_031 shows +16pp mean with recent_Δ +9.5pp (strengthening), while rule_029 shows +18pp mean with recent_Δ -57.7pp (collapsing). This divergence within the same signal class (hot sectors in Bear UP_TRI) is **evidence that sector rotation dominates, not stable UP_TRI edge**.

If the Bear×UP_TRI×hot logic were sound, both sectors should show similar stability. Instead, you have one fading (Pharma) and one strengthening (IT). This suggests Lab's "hot sector" classification is either (a) backward-looking (Pharma was hot 2011-2020, IT is hot 2023-2026) or (b) the "hot" label is overfit to historical momentum that doesn't predict forward lift. The n=18 for rule_031 vs n=17 for rule_029 (both tiny) means you're drawing strong conclusions from weak samples.

**Neither should deploy**. rule_031's recent strength could be 2024-2026 AI/tech bubble momentum (IT = tech-heavy), which is precisely the regime-specific edge that fails next year. The fact that two "hot" sectors diverge this dramatically within the same rule structure is a **red flag on the entire hot-sector framework**. Lab's sector work is suspect.

## 6. Should we relax criteria for INSUFFICIENT_DATA rules?

**No. Insufficient data means insufficient evidence, full stop**. You have 182 windows over 15 years. If a rule can't accumulate n≥5 windows with matches in 15 years, it's either (a) so narrowly conditioned it will never fire enough to matter in production, or (b) the conditions are mutually exclusive by design (e.g., Bull regime + Choppy breadth). Either way, it's not deployable.

The 11 INSUFFICIENT_DATA rules include Choppy sub-regime rules (rule_014/015/016 breadth conditions) and Bull rules. For Bull rules, you've already established (Q4) that the dataset lacks clean Bull regime windows—but that's a test-design problem, not a threshold problem. Relaxing n≥5 to n≥2 would let you "validate" rules that fired twice in 15 years. That's not validation; that's **anecdote masquerading as evidence**.

If you want to rescue Bull rules specifically, **design a separate Bull-regime-only walk-forward** using only windows where market regime = Bull at window start. This would give you clean Bull-rule testing without contaminating the threshold. But don't lower the bar universally—doing so would pollute your SURVIVOR category with noise and defeat the purpose of walk-forward (filtering out overfit rules).

## 7. Lab work over-fit verdict—confirm or refute?

**Confirms Lab over-fit, but salvages 2-3 rules**. Lab delivered "8 READY_TO_SHIP" from backtest; walk-forward validates 3 (and one of those, win_001, is marginal per Q2). That's a **62% false-positive rate** in Lab's backtest process—Opus was right to flag circularity. The walk-forward evidence suggests Lab's methodology was loose, thresholds were gamed, or in-sample/out-of-sample boundaries were violated.

The 3 survivors (kill_001, win_001, rule_019) are not evidence that "Lab's overall approach works." They're evidence that **even a broken process occasionally finds real signal**. rule_019 in particular (Bear×UP_TRI×hot_refinement, n=191, +17.2pp) is a genuine workhorse that survived because it has massive sample support. But the fact that Lab's "ready_to_ship" included rule_029 (now collapsing), rule_011 (negative lift), and rule_012 (negative lift) means Lab's quality control failed.

**Phase 1 deployment should be 2 rules: kill_001 and rule_019**. Drop win_001 (borderline sample, circular production history). This is a humbling result—37 rules tested, 15 years of data, and you get 2 clean survivors—but it's honest. Deploying all 8 of Lab's rules would be **repeating Lab's over-fit mistake with walk-forward lipstick on**. Accept the 2-rule outcome, deploy with 25% capital as Case 2 prescribes, and use 60-day evaluation to decide whether to expand. The walk-forward didn't validate Lab's work; it **debugged** it.
