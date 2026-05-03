# My Recommended Combination

## Headline

**Replace your 10-week ramp plan with this 3-phase plan. Total elapsed time to "deployed and learning": 2 weeks. Total to "scaled with confidence": 6-9 months. The Lab pipeline as built is not the right product to ship.**

---

## Phase 0 — Stop, Test, Decide (Week 1)

### Activities, in order

1. **Walk-forward OOS test (Day 1-3).** Re-run the entire Lab synthesis using only 2010-2023 lifetime data. Apply resulting rules to 2024-2025 lifetime data as held-out OOS. This is the single highest-value action in this entire engagement and you skipped it.
2. **Rule-deletion ablation (Day 3-4).** Compute April backtest PnL with: 1 rule (Bear UP_TRI = TAKE), 5 rules, 17 rules, 37 rules. Plot marginal PnL vs rule count.
3. **Hire quant for 4-hour review (Day 4-7).** Cost: $300-500. Brief: "Tell me if this validation is circular and what to delete."
4. **Decision gate (Day 7).**

### Decision criteria at gate

- If walk-forward OOS WR is within 5pp of in-sample: proceed to Phase 1 with full 37-rule set (you've earned it).
- If walk-forward OOS WR drops 5-15pp: proceed with reduced rule set per quant guidance, probably 5-10 rules.
- If walk-forward OOS WR drops >15pp or quant flags fundamental issue: **stop. Do not deploy. Reframe.** Likely answer is: trade discretionarily with regime + sector overlay, no static rule engine.

### Risks per phase

- Walk-forward may show the lifetime data itself was overfit during Lab synthesis. This is a feature, not a bug; better to discover now.
- Quant may say "this whole approach is wrong." Listen.

---

## Phase 1 — Minimal Deploy (Week 2)

### Activities

1. Deploy whatever survived Phase 0. Likely 5-10 rules, not 37.
2. Capital constraint: 2.5%/trade for first 30 signals, not 5%. Half size while you measure.
3. **Critical instrumentation:** log per-signal predicted WR, actual outcome, regime classification confidence, sub-regime label, and rule that fired. This is the data you need for Phase 2.
4. Disable all the meta-systems for now: barcode v1, Phase-5 override, Brain reasoning gates, parallel v3-vs-v4.1 validation. You don't need them; they are layers between you and the data.
5. **Do not run Lab iterations.** No $10 dual-Opus runs. No prediction recalibration. Hands off.

### Decision criteria

- After 30 signals: WR ≥ 55% on TAKE rules, return to size 5%/trade.
- After 30 signals: WR < 55%: stop, investigate, do not scale.
- After 60 signals: rules with rule-level n≥15 and WR within 10pp of expected proceed; others get rolled into a single broad rule.

### Risks

- The 30-signal kill criterion will trigger by chance ~15% of the time even on a real edge. Accept this; the cost of trading a degraded system is higher than the cost of a false-positive stop.
- Regime is currently transitioning Bear→Choppy (per file 28). Your hot-Bear rules will be inert. Plan for low signal volume in Phase 1.

---

## Phase 2 — Honest data accumulation (Months 2-9)

### Activities

1. Accumulate ≥ 200 signals across regimes. This is the *real* validation data your Lab pipeline never had.
2. **Quarterly rule review** (not weekly, not monthly). Rolling 30-signal WR per rule. Demote rules with WR <baseline+5pp.
3. **Run Lab v2 only after 6 months of live data.** With ≥150 production signals, the Lab pipeline becomes useful. Right now it is operating on mostly synthetic/historical input.
4. Investigate Path A vs Path B divergence empirically: take 10 production-filtered signals where the scanner skipped a v4.1-matching cohort. Did skipping save money? This is the actual question, and it's answerable in production.

### Decision criteria

- At 6 months: if live aggregate WR ≥ 60% and ≥1 regime transition observed: scale capital deployment.
- At 6 months: if live aggregate WR < 55% across ≥100 signals: this approach does not have edge; stop and rethink (do not iterate Lab).

---

## What I am explicitly recommending you NOT do

- Do not deploy 37 rules with phased rollout per integration_notes_FINAL.md. The phased rollout pretends you've validated rules you haven't.
- Do not implement the barcode v1 system before deployment. Build it after you have 6 months of production data showing rules need that level of state tracking.
- Do not do Sonnet's "Week 0 dry run." It's a comfort-blanket; it doesn't surface the issues that matter.
- Do not run paper trading shadow mode for 60 days as your primary validation. Use it as monitoring on top of real deployment, not as a substitute for OOS testing.
- Do not pay for any more LLM Lab runs in 2026 H1. You are at the point of diminishing returns on AI-tool engagement; further runs add code, not insight.

---

## Realistic timeline

| Week | Milestone |
|---|---|
| Week 1 | Walk-forward OOS + rule ablation + quant review |
| Week 2 | Deploy 5-10 rules, half size |
| Week 6 | First 30-signal review |
| Month 3 | First 60-90 signals, regime transition possibly observed |
| Month 6 | First honest WR estimate per rule |
| Month 9 | Lab v2 (if warranted) with real data |
| Month 12 | Scale or stop decision |

This is slower than your 10-week plan to Phase 2. It is faster than the year you'll waste if your current 10-week plan deploys an over-engineered system that breaks on regime shift in month 3.
