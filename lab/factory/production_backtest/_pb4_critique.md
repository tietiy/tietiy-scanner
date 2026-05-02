# PB4 Production Backtest — Sonnet 4.5 Critique

**Date:** 2026-05-03

## 1. Are deployment recommendations honest?

**8 READY_TO_SHIP is appropriately conservative.** The n≥5 threshold for production deployment is correct—you're protecting yourself from small-sample overfitting. The fact that 24 rules need live data is not a red flag; it's honest acknowledgment that April 2026 doesn't exercise Bull regimes or off-season calendar effects. Lowering the threshold to pad the READY count would be cargo-cult rigor.

**The real question is whether "READY" means anything.** If your existing production rules (kill_001, win_007) are already live and performing, then 8 additional READY rules is a meaningful expansion. If those 8 rules are minor variants of existing logic, you're just adding complexity without coverage. The deployment recommendation is honest *if* those 8 rules represent genuinely differentiated signal patterns.

**Conservative deferral is correct for now.** You'd rather under-deploy and expand coverage as new regimes arrive than over-deploy on April hot-Bear data and discover cold-Bear failure modes in production. The NEEDS_LIVE_DATA classification is doing its job.

## 2. NEEDS_REVIEW rules — should they ship despite divergence?

**No, they should not ship in Phase 1.** The 28-33pp divergence (win_003, win_005) screams selection bias. Path A's 100% WR is production signals *already filtered by human/algo triage*—you're measuring rule performance on pre-screened winners. Path B's 67-72% is closer to what the rule sees on raw signal flow. Shipping them now means you're trusting the 100% number, which is circular.

**The fact that similar rules are already live doesn't justify expansion.** kill_001 + win_007 being in production means you're *already exposed* to this pattern class. Adding win_003/005/006 without understanding the 30pp delta compounds the risk. If those existing rules are performing at 90%+ in production, it's because *production filtering* is doing heavy lifting, not because the rules themselves are magically strong.

**Flag them in logs, don't deploy.** Mark these signals in production with a "NEEDS_REVIEW—high divergence" tag. Collect 3-6 months of unfiltered outcomes to see if Path B's 70% holds or if production conditions consistently deliver 90%+. If the latter, you've discovered that your production filter creates a persistent edge; if the former, you've avoided deploying overfit rules.

## 3. TAKE WR 91-93% — credible or too good?

**It's partially circular but not invalid.** The 94.6% Bear UP_TRI live performance with "Phase-5 selection bias" is your tell—you *know* the rule was tuned on data that includes this April window. The backtest reproducing 91-93% proves the rule is internally consistent but doesn't prove it generalizes. You're essentially measuring in-sample fit with extra steps.

**The 2.1pp cross-validation delta is tight enough to be encouraging.** Path A (production-promoted) vs Path B (broader universe) gives nearly identical TAKE WRs. That suggests the rule logic itself—not just production filtering—is doing work. If Path A showed 95% and Path B showed 75%, you'd know the production filter was carrying all the weight. The narrow gap suggests real signal.

**Credibility depends on regime stability.** April 2026 is hot Bear; your lab calibration says hot Bear *should* deliver 85-95%. The backtest confirms that. The real test is whether the rules hold at 85%+ in the *next* hot Bear window (say, Q3 2026 if that materializes) or degrade to 50-58% in cold Bear. You won't know until you deploy and wait. The 91-93% is honest evidence for hot-Bear conditions only.

## 4. Production deployment risk in Step 7

**Phase 1 with 8 READY rules is defensible but fragile.** You're deploying rules that work in one sub-regime (hot Bear, April 2026). If market conditions shift to warm/cold Bear or Bull in May-June, those 8 rules will under-fire or misfire. You're betting that April's hot conditions persist long enough to accumulate evidence. That's not crazy—Bear markets can run for quarters—but it's not robust.

**Waiting for more sub-regime windows is the lower-regret path.** If you deploy now and the 8 rules fire heavily in May but WR drops to 60%, you've burned credibility and have to pull back. If you wait 2-3 months to accumulate Bull and cold-Bear data, you deploy 15-20 READY rules with broader coverage and higher confidence. The upside of early deployment (capturing May's potential hot-Bear continuation) is small compared to the downside (deploying overfit rules that fail when regime shifts).

**Phase 1 deployment makes sense only if you have aggressive monitoring.** If you can deploy the 8 READY rules with daily WR tracking, kill-switch logic for <65% WR over 20 signals, and explicit "Phase 1 experimental" labeling, then go ahead. If deployment means "these rules go live and we check back in 3 months," wait for more data. Your risk tolerance should dictate timing, not the backtest.

## 5. Single biggest risk NOT surfaced by this backtest

**Regime-shift whipsaw within the first 50 signals.** The backtest assumes April's hot-Bear regime is stable across the 290 production signals. But if the market pivoted mid-April from hot to cold Bear (or Bear to Bull), your rules trained on early-April could misfire on late-April. The backtest aggregate WR hides intra-month regime micro-shifts.

**You're not testing regime-detection latency.** The rules assume you *know* you're in hot Bear and apply sector/UP_TRI boosts accordingly. But in production, regime classification lags by days or weeks—your regime detector might call "Bear" when the market has already shifted to Choppy or Bull. If the 8 READY rules fire during that lag window, they'll apply hot-Bear logic to non-Bear conditions and eat losses before you realize the regime changed.

**Specifically: what happens to TAKE WR if the first 20 deployed signals occur during a regime you mis-classified?** The backtest doesn't simulate this because it uses ground-truth April regime labels. In production, you'll have regime uncertainty, and early losses during mis-classification could kill confidence in the entire rule set before it gets a fair test. You need a "regime confidence threshold" gate—don't fire high-precision rules unless regime detection confidence is >80%.

## 6. Should NEEDS_REVIEW be downgraded to NEEDS_LIVE_DATA?

**Yes, downgrade them.** The Path A vs B divergence (28-33pp) is too wide to trust. Calling them NEEDS_REVIEW implies they're *almost* ready pending investigation; calling them NEEDS_LIVE_DATA is more honest—they need 3-6 months of unfiltered production outcomes to see if Path B's 70% or Path A's 100% is real.

**NEEDS_REVIEW creates false urgency.** It suggests that with a bit more analysis, you could green-light these rules. But the divergence isn't an analysis problem; it's a data problem. You don't have enough unfiltered signals in the operational window to know whether production filtering is creating a 30pp edge or whether April was a lucky draw. More spreadsheet time won't resolve that.

**Downgrading removes temptation to ship them prematurely.** If they're flagged NEEDS_REVIEW, someone will push to "just ship them—we already have similar rules live." If they're flagged NEEDS_LIVE_DATA, the forcing function is time and accumulation, not debate. You'll revisit in Q3 2026 when you have 100+ unfiltered Bear UP_TRI sector signals and can measure the rule on a level playing field. That's the honest path.
