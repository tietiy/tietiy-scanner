# Unconventional Alternatives

## 1. Delete 32 rules, deploy 5

**Problem solved:** Complexity-without-evidence; circular validation; data-starvation (because 5 rules need 5x less data to validate).

**The 5 rules:**
- `kill_001` (Bear Bank DOWN_TRI REJECT) — 0/11 live, no controversy.
- A single Bear UP_TRI TAKE_FULL (no sector split). Aggregate live WR is 94.7% n=96 per cohort_health.
- `rule_018` (Choppy DOWN_TRI wk4 REJECT) if calendar effect holds.
- A single Choppy UP_TRI broad WATCH (file 27 shows 28.6% WR — almost a kill).
- A single broad position-sizing rule (e.g., "in Choppy regime, all sizes halved").

**Requires:** Honesty about the fact that sub-regime, sector, and calendar segmentation in the 37-rule set is statistically unsupported at current sample sizes. Discarding 32 rules with `expected_wr` numbers feels like throwing away work. It isn't; it's removing rules whose evidence base is n<10.

**Realistic outcome:** You capture 80%+ of the observable edge with 14% of the rules. Validation is tractable. Deployment is in 1 week not 10. You will know within 3 months whether the edge is real because the n accumulates fast on broad rules.

**Feasibility:** High. The blocker is psychological (sunk cost), not technical.

---

## 2. Trade the 5-rule system for 6 months *first*, then revisit Lab work

**Problem solved:** Restart pressure (immediate); validation correctness (6 months of clean OOS data); cognitive load (5 rules vs 37).

**The play:**
- Deploy alternative #1 immediately (week 1).
- Do not run any Lab work for 6 months. Hard rule.
- After 6 months, you have ~150-300 production signals across multiple regimes. *Now* you have data to derive sub-rules.
- The Lab pipeline you already built can be re-run on this honest data.

**Requires:** Discipline to not iterate. The hardest constraint for an analytical trader.

**Realistic outcome:** Either (a) the simple system works, you have income, you have data, and Lab v2 is grounded in reality, or (b) it doesn't work and you've discovered that with 6 months instead of 5 weeks of additional engineering. Both are good outcomes; the current path doesn't produce either cleanly.

**Feasibility:** Medium. Requires you to accept that the current Lab work is *input* for a future iteration, not a finished product.

---

## 3. Hire a quant for 4 hours

**Problem solved:** AI-tool dependency; validation correctness; methodology blindspots.

**The play:** Find an experienced quant on a freelance platform (Upwork, Topcoder finance, hedge fund alumni networks). Pay $200-500 for a 4-hour code/methodology review. Show them files 06, 27, 02. Ask: "Is this circular? Does the 37-rule structure match the n? What would you delete?"

**Requires:** Willingness to receive an answer like "delete 32 rules, redo lifetime backtest with held-out 2024-25." A human quant will not be polite about overfit the way LLMs default to being.

**Realistic outcome:** $300-500 spent buys you the single most useful piece of feedback in this entire pipeline. The Lab spend was $21.41; this is 15-25× that, and worth it. **An LLM cannot give you what a human with skin-in-the-game in markets can: pattern recognition for failure modes that don't exist in their training data.**

**Feasibility:** High. The blocker is again psychological — admitting you need a non-LLM second opinion after 5 weeks of LLM-driven work.

---

## (Bonus) 4. Sell the rules, don't trade them

**Problem solved:** Capital risk; income; validation (paying customers will surface failures faster than backtest).

**The play:** Package the rule set + scanner + Telegram delivery as a paid signal service for Indian F&O retail. ₹500-2000/month per subscriber. 50 subscribers = ₹25K-100K/month income with no capital at risk on your side.

**Requires:** Marketing, customer support, regulatory awareness (SEBI investment advisor rules apply if you give specific recommendations).

**Realistic outcome:** Probably bad — the regulatory burden is real, and signal services are a saturated market. But it forces a different question: would you pay for these rules? If no, why are you risking capital on them?

**Feasibility:** Low (regulatory). Mentioned only because the thought experiment is clarifying.
