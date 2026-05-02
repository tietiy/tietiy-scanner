# L1 Win_* Recalibration — Sonnet 4.5 Critique

**Date:** 2026-05-03
**Model:** `claude-sonnet-4-5-20250929`

# L1 Win_* Recalibration Critique

## 1. Are recalibrated values defensible?

**Yes, but document the regime shift explicitly.** The 13-19pp WR drop from live (72-74%) to lifetime (53-60%) is honest accounting. Live samples were 13-21 trades in a hot Bear microclimate (April 2026); lifetime samples are 1,000-1,300 trades across 15 years. The recalibration is mathematically correct, but you're conflating two different questions: (a) "What WR should we predict for **this specific rule in production**?" vs (b) "What's the defensible lifetime baseline?" If current regime persists, you're under-predicting; if regime reverts, you're right-sized.

**The real issue: regime stationarity assumption.** You chose broad-match + lifetime baseline, which implicitly bets that April 2026 is an outlier and mean reversion is coming. If the current regime (post-COVID volatility, sector rotation dynamics, whatever structural change caused the hot Bear) is the **new normal**, then 53-60% predictions will systematically undercount wins and erode trust. You need a third data cut: **last 24-36 months WR** as a sanity check. If recent-regime WR ≈ lifetime WR, you're safe. If recent-regime WR is 65-70%, you've overcorrected and should weight recent data more heavily or add regime filters.

**Recommendation:** Add a "regime-aware expected_wr" field (e.g., `expected_wr_bear_hot=0.68`, `expected_wr_lifetime=0.58`) and let the deployment layer choose which to display. Document the assumption: "We predict 58% WR conservatively; if current Bear regime persists, actual may run 10pp higher."

## 2. Should any rules NOT have been recalibrated?

**You chose wrong for win_001 and win_002.** These had **21/21 and 19/19 live records**—perfect or near-perfect in current regime—and you replaced them with 59.5% and 57.6% lifetime baselines. The correct move was to **add `sub_regime='hot'` constraints** and keep the rules narrow. A 21/21 rule is gold in live trading; broad-matching it to 15 years of noise destroys signal. You're now telling the trader "this 100% rule is actually 59%"—that's not recalibration, that's rule replacement.

**The test: forward predictive power.** If win_001 continues to hit 90%+ WR in the next 50 trades (because hot Bear persists), you've undermined trust for no reason. If it reverts to 60%, you were right to recalibrate. But you don't **know** yet, and the live sample (21/21) is screaming "this regime is different." The rational hedge: keep win_001/win_002 as `regime='Bear' AND sub_regime='hot'` with `expected_wr=0.70` and `n_pred=50-100` (narrow, high-confidence), and create **new** broad-match variants (win_001_broad) with `expected_wr=0.59` and `n_pred=500-700`. Deploy both; let the data decide which regime we're in.

**Rules win_003 through win_006 are borderline defensible** (live WR was 68-87%, not 100%), so recalibrating to 53-58% is less violent. But win_001/win_002 were **statistical anomalies in the live sample**—you don't average anomalies away, you isolate and monetize them.

## 3. Production trader expectation shift

**You're about to destroy trust, and you need a communication plan yesterday.** The trader has been seeing 95% live WR on win_* rules and making position-sizing decisions accordingly (e.g., 3x leverage on "sure things"). Production now says "actually 58% WR"—the trader will either (a) ignore the new predictions and keep using gut feel, or (b) assume the system is broken and stop trading the rules entirely. Neither outcome is acceptable.

**The shift is honest, but the framing is incomplete.** You need to present three WR numbers side-by-side: **Live-to-date** (95%), **Lifetime baseline** (58%), and **Regime-adjusted estimate** (68-72%, if you calculate recent-regime WR). The trader then understands: "Live has been exceptional, lifetime is 58%, but given current regime we expect ~70% going forward with high uncertainty." This is honest and actionable. Presenting only the 58% without context looks like the system regressed, even though the **prediction got better**.

**Concrete action:** Add a dashboard section called "Expectation Recalibration" that shows (a) old live-sample stats, (b) new lifetime baseline, (c) regime-conditional prediction, and (d) a confidence interval ("we're 80% confident WR will be 55-75% in next 100 trades"). Frame it as "improved calibration" not "downgrade." If the trader pushes back, offer a 30-day shadow period where both old and new predictions run in parallel so they can see convergence in real-time.

## 4. Five remaining FAILs

**rule_007 is a prediction-band tuning problem, not a rule problem.** Actual WR is 32.4% (perfect match to expectation), but actual count was 42 vs predicted 120-200. The rule is **working as intended**; the count prediction was wrong. This is a PASS with a bad count model, not a FAIL. Fix: loosen count bands to ±60% (from ±40%?) for low-n rules (n<100), or switch to a probabilistic count model (e.g., "90% CI: 20-180"). Don't penalize a rule for correct WR prediction when only count is off.

**rule_011, rule_020, rule_022, rule_025 are structural.** rule_011 (n=1748 vs 700-1100 predicted) is a regime shift—DOWN_TRI in Bear is firing 50% more than historical. Mark it WARNING with a note "rule over-indexing in current regime; monitor for reversion." The three Path 2 rules are described as "structural issue" with no detail—if they're broken logic (e.g., mutually exclusive conditions), fix them in L2. If they're regime-shifted like rule_011, recalibrate count and move to WARNING.

**Recommendation for L2:** Split validation into WR accuracy and count accuracy. A rule can PASS on WR and FAIL on count (like rule_007). Loosen count bands by 20-30% for rules with n<200, because count variance is high in small samples. For structural FAILs (Path 2 rules), either fix the rule logic or mark them as deprecated and create replacement rules.

## 5. Is the Lab pipeline done at 86.5% PASS+WARNING?

**No, because you haven't tested second-order failure modes.** 86.5% PASS+WARNING means individual rules are statistically sound in isolation, but you haven't validated: (a) **rule overlap/correlation** (do win_001 and win_002 fire on the same trades, creating hidden concentration risk?), (b) **regime-conditional performance** (do all win_* rules fail simultaneously in a Bull regime, creating portfolio drawdown?), or (c) **count accuracy in aggregate** (does the portfolio predict 5,000 trades but deliver 8,000, breaking position-sizing assumptions?). The validation harness is a unit test; you need integration tests.

**Deployment risk is unquantified.** You recalibrated 6 rules based on lifetime data, but if the current regime persists for 6 more months, those rules will systematically under-predict WR and the trader will override the system. The pipeline should output a **regime sensitivity report**: "If current regime continues, expect win_* rules to outperform predictions by 10-15pp; if regime reverts, predictions are accurate." Without this, you're shipping a model with a hidden regime-stationarity assumption that no one is monitoring.

**What's missing:** (1) Rule correlation matrix (flag rules with >0.7 correlation as redundant), (2) regime-conditional backtests (Bull/Bear/Sideways WR splits for all rules), (3) portfolio-level count prediction (does sum of rule predictions match historical total trade volume?), and (4) a living calibration monitor (weekly dashboard showing predicted vs actual WR/count for each rule, with auto-flagging when divergence >10pp for 3+ weeks). The Lab pipeline validated the rules; now you need a **production monitoring pipeline** to catch drift before the trader does.
