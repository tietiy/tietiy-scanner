# W4 Deployment — Sonnet 4.5 Final Critique

**Date:** 2026-05-03

# FINAL REVIEW — Phase 1 Deployment Critique

## 1. Kill-switch thresholds: defensible or noise-prone?

**The proposed thresholds are too aggressive and will trigger on noise.** Your PB4 Wilson score analysis showed that 13/20 has a lower bound of 45% — which means even a *true* 65% WR rule can legitimately produce 7 losses in 20 trials. Your "WR < 50% over 20 signals → halt" threshold will fire ~30% of the time on a good rule just from binomial variance. The "< 60% over 30 signals" is slightly better but still noise-prone for a 71% expected-WR rule (Wilson lower bound on 18/30 is ~42%).

**Revised kill-switches that respect statistical reality:**
- **Per-rule:** WR < 40% over 30 signals (Wilson lower at 12/30 = 25%; this catches genuine disasters, not noise)
- **Aggregate Phase 1:** WR < 50% over 50 signals (gives you ~3 months of data before hard stop)
- **Drawdown-based:** 10% drawdown threshold is appropriate — it's capital-preservation, not statistical, so you *want* it sensitive

**The "reduce to 12.5%" middle tier is useless.** Either the rule works or it doesn't. Cutting position size mid-stream just guarantees you won't collect enough data to know. Replace with: at 30 signals, if WR 40-55%, extend evaluation another 30 signals at full Phase 1 size (25%); if still < 55% at 60 signals, halt.

## 2. Is 25% capital honest sizing for learning?

**25% is appropriate *for the experimental framing* but undersized for statistical power.** At 1.25% per signal and ~10 signals/month expected, you're risking ~12.5% of capital per month. With 71% WR and ~2:1 RR (assumed), expected monthly return is ~1.5-2% — but standard error on 10 trials is ±15pp WR, so you could easily see -1% to +5% in month 1 from pure variance.

**The real problem: 60 days may produce only 20-30 total signals.** That's not enough to distinguish a 71% rule from a 55% rule with any confidence (Wilson intervals overlap heavily). You're setting up a scenario where you *can't learn* what you need to know in the timeframe specified. Either:
- Accept that 60 days is a "no disasters" check, not a validation (probably honest), OR
- Extend to 90 days / 50+ signals before the scale-up decision, OR
- Increase to 50% capital (2.5% per signal) to get more signals in 60 days (but this contradicts "experimental")

**Recommendation:** Keep 25%, but reframe the 60-day gate as "disaster check + early warning" rather than "validation." Real validation happens at 90 days / 50 signals. Don't promise statistical certainty you can't deliver.

## 3. rule_019 hot sub-regime gating: what if Bear detector misfires?

**This is the single biggest deployment risk.** The walk-forward validation assumes the Bear regime detector is *always correct at signal time*. But regime detection has lag (you're using 60-day returns + 20-day vol percentile — both backward-looking). On regime transition days (Bear → Choppy, the most common exit), you could easily have:
- Regime still labeled "Bear" (60d return still negative)
- Sub-regime still "hot" (vol percentile elevated from prior week)
- But underlying market dynamics already shifted (bounce exhausted, mean-reversion edge gone)

**Walk-forward can't catch this because it validates on *already-labeled* historical data.** It doesn't test real-time classification edge cases. Your rule_019 edge depends on "capitulation bounce in Bear hot stress" — but if you're actually in early Choppy (regime just flipped), you're buying failed bounces in a directionless chop, which is poison.

**Mitigations:**
- Add a **regime confirmation lag**: only fire rule_019 if regime has been Bear for ≥5 consecutive days (prevents transition-day misfires)
- Add a **vol decay check**: sub_regime="hot" AND vol_percentile *declining* over last 3 days (confirms you're in the bounce phase, not the initial panic)
- **Kill-switch specific to regime misfire:** if rule_019 WR < 50% over first 15 signals, assume regime detector is broken and halt immediately (don't wait for 30-signal threshold)

Without these, you're effectively beta-testing your regime classifier in production with real money.

## 4. "PHASE 1 EXPERIMENTAL" label: behaviorally protective or ignored?

**It will be ignored after 2 weeks.** Humans habituate to warning labels incredibly fast — this is why "Smoking Kills" on cigarette packs doesn't work. After seeing "[PHASE 1 EXPERIMENTAL — 25% sizing]" on 10 consecutive signals, the trader's brain will pattern-match it as "normal scanner output" and the warning becomes invisible.

**Stronger behavioral alternatives:**
- **Separate Telegram channel** for Phase 1 signals (physical separation forces conscious context-switch)
- **Require manual confirmation** for each Phase 1 trade: scanner posts "rule_019 fired on SYMBOL — reply /confirm_019_SYMBOL to execute" (friction = attention)
- **Daily aggregate summary** at market open: "Phase 1 active: 3 open positions, 60% WR over 18 signals, 8 days until next review" (keeps evaluation framing salient)
- **Color-coding in PWA**: Phase 1 signals appear in amber/orange instead of green (visual distinction that doesn't habituate as fast as text)

The label is better than nothing, but if you're serious about maintaining experimental framing, you need *behavioral friction*, not just text.

## 5. win_003 RECALL: act now or wait for confirmation?

**Recall it now.** Here's why:

**The evidence for decay is not just statistical — it's structural.** Win_003 is IT × Bear × UP_TRI (no sub-regime gate). Your walk-forward shows -14.1pp recent delta, and your lab work discovered that the Bear UP_TRI edge is *concentrated in hot sub-regime* (rule_019's domain). Win_003 is likely winning during hot phases and losing during warm/cold, but because it fires on *all* Bear phases, it's net degrading as the regime mix shifts.

**Waiting for "5 more signals" is expensive confirmation bias.** If the rule is broken, those 5 signals at full 5% sizing = 25% capital at risk to confirm what you already suspect. That's not prudent risk management — it's paying for data you already have (from walk-forward).

**Action plan:**
- Immediately reduce win_003 to 1% sizing (flag as "under review")
- After 30 days / 10 signals at 1%, compare WR to rule_019 hot gated version
- If win_003 performs similarly to rule_019 (suggesting it was just catching hot sub-regime luck), deprecate it entirely
- If win_003 *outperforms* rule_019, investigate whether there's a warm/cold edge you missed

Don't throw good money at a degrading rule when you have a better replacement ready.

## 6. What could break this that walk-forward can't catch?

**Three structural blindspots in walk-forward methodology:**

### A. Regime distribution shift
Walk-forward validates rules across W1-W3 (2023-2025 data), which includes specific Bear regime characteristics (COVID recovery, inflation fears, sector rotation patterns). If 2026 Bear regimes have different *internal structure* (e.g., "hot" phases are shorter/shallower, or vol spikes don't coincide with capitulation bounces), rule_019's lift will evaporate. Walk-forward assumes the *relationship* between features and outcomes is stationary; it doesn't test for structural breaks.

### B. Signal frequency collapse
Walk-forward reports "n=191 mean per window" for rule_019, but that's an average across windows that *had* Bear hot conditions. If 2026 has longer Bull/Choppy regimes, you might see only 3-5 Bear hot signals per month instead of the expected 10-15. You'd be under-diversified (high variance on tiny n) and the 60-day evaluation would be meaningless. Walk-forward doesn't validate *signal generation rate* under different macro regimes.

### C. Scanner implementation bugs
Walk-forward validates on perfect hindsight-labeled data. Production scanner has to compute `sub_regime` in real-time with potential data feed delays, missing features (vol percentile not updated), or edge cases (market holiday affects 60d return calculation). A subtle bug that mis-labels 20% of signals as "hot" when they're actually "warm" would destroy rule_019's edge, but walk-forward never tested the *scanner's* implementation, only the rule logic.

**The last one is the killer.** You're deploying a rule that depends on correct real-time feature computation, but you haven't run a *live scanner simulation* (replay 2025 data day-by-day with production code) to verify the scanner produces the same labels walk-forward assumed.

## 7. Honest probability Phase 1 produces positive returns?

**Base case: 40% chance of meaningful positive return (>+3% over 60 days).**

### Scenario probabilities:

| Outcome | P | 60-day return | Reasoning |
|---------|---|---------------|-----------|
| **Success** | 25% | +5% to +8% | Rules work as validated; regime stays Bear or transitions gently; no implementation bugs |
| **Modest win** | 15% | +1% to +3% | Rules work but signal count low (Bull/Choppy dominates); small sample = muted returns |
| **Breakeven** | 30% | -1% to +1% | Rules perform at expected WR but variance washes out edge; or regime misfire offsets kill_001 saves |
| **Modest loss** | 20% | -2% to -5% | Scanner implementation bug OR regime detector misfires on transitions; kill-switches eventually fire |
| **Disaster** | 10% | -8% or worse | Structural break (Bear 2026 ≠ Bear 2023-25) + slow kill-switches; or catastrophic bug |

**Compared to alternatives:**

- **Full 8-rule Lab deployment:** 20% chance of success (too many unvalidated sectors; win_003/win_007 known degraders)
- **5-rule Opus deployment:** 35% chance (better than 8-rule, but no walk-forward validation; over-optimistic on sector edges)
- **Discretionary (no rules):** 50% chance (trader has 60% baseline WR, but high variance; no kill-switches)
- **No deployment (paused):** 0% return, 0% risk (but opportunity cost of scanner + lab work wasted)

**The 2-rule Phase 1 is the second-best option after discretionary**, but it's the *only* option that produces *learning* (you get validated kill-switches + regime framework tested in production). The expected value isn't just the 60-day return — it's the probability you build a durable systematic edge over 6-12 months.

**Critical assumption check:** This 40% probability assumes you implement the regime confirmation lag + vol decay check + scanner simulation pre-deployment (Q3 mitigations). Without those, success drops to 25% because regime misfire risk dominates.

---

## Final verdict: DEPLOY with modifications

**Ship rule_019 + kill_001, BUT:**

1. **Add regime confirmation lag** (Bear ≥5 days) and vol decay check to rule_019
2. **Run 30-day scanner simulation** on 2025 data with production code to verify sub_regime labeling matches walk-forward assumptions
3. **Revise kill-switches** to 40% WR floor (30 signals) and 50% aggregate floor (50 signals)
4. **Recall win_003 now** (reduce to 1% until validated against rule_019)
5. **Reframe 60-day evaluation** as "disaster check" not "validation" — true validation at 90 days / 50 signals
6. **Add behavioral friction** (separate Telegram channel or manual confirm) to maintain experimental framing

**Without these changes, deployment is premature.** With them, you have a defensible 40% shot at building something real.
