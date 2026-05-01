# ANALYZER findings (run 2026-05-01T21:27:40.975938Z)

**Total patterns:** 544

**Tier distribution:**
```
{
  "CANDIDATE": 345,
  "DORMANT_REGIME": 108,
  "DEPRECATED": 5,
  "DORMANT_DEFERRED": 6,
  "ACTIVE_WATCH": 57,
  "ACTIVE_TAKE_SMALL": 1,
  "DORMANT_INSUFFICIENT_DATA": 22
}
```

---

## Run summary

This analyzer pass identified 544 unified patterns across the trading rule portfolio. The tier distribution is heavily weighted toward CANDIDATE (345, 63%) and DORMANT_REGIME (108, 20%), with only 58 patterns in ACTIVE tiers (57 ACTIVE_WATCH, 1 ACTIVE_TAKE_SMALL). This distribution suggests an appropriately conservative approach—most patterns lack sufficient statistical evidence for live trading. The low count of ACTIVE_FULL (zero) is concerning if the goal is production deployment, but appropriate if this represents initial screening. The 5 DEPRECATED patterns indicate healthy culling of non-performers.

## Top patterns surfaced

The top-scoring pattern (score=65, ACTIVE_TAKE_SMALL) combines upward triangle breakouts in bear markets with early-month timing, extreme range compression, and weak breadth. The mechanism centers on mean reversion after weak hands capitulate during oversold periods with compressed ranges—institutional rebalancing flows in week 1 provide the catalyst. Multiple high-scoring patterns (ranks 2, 4, 5, 6) share the UP_TRI×Bear×D10-D15 structure, suggesting bear market counter-trend setups may be a genuine edge when paired with extreme oversold conditions and range compression. The mechanism of weak-hands capitulation followed by institutional accumulation appears repeatedly with high clarity (72-75), indicating this isn't post-hoc storytelling but a coherent behavioral driver.

## Mechanism clarity assessment

Only 2 patterns (0.4%) achieve high clarity (≥80), while 375 (69%) fall in the mid-range (50-79) and 167 (31%) have low clarity (<50). This distribution is honest but problematic—nearly one-third of patterns lack convincing causal stories. The high-clarity patterns in the top 10 (clarity 72-75) cluster around UP_TRI formations in bear/choppy markets with mean reversion or institutional accumulation mechanisms. The scarcity of ≥80 clarity patterns suggests the analyzer is appropriately skeptical but also that most rules remain in "statistically interesting but causally uncertain" territory. Mid-range clarity patterns dominate CANDIDATE and ACTIVE_WATCH tiers, which is appropriate staging.

## Concerns

None of the top 10 patterns exhibit the dangerous combination of high score + low clarity, which is reassuring. However, the single ACTIVE_TAKE_SMALL pattern (score=65, clarity=72) sits below the high-clarity threshold (80)—deploying capital on a 72-clarity mechanism risks overfitting to regime-specific anomalies. The DORMANT_REGIME pattern at rank 9 (score=62, nifty_vol_regime=High) matches other ACTIVE_WATCH scores, suggesting tier calibration may be overly sensitive to current regime vs fundamental pattern quality. With 167 low-clarity patterns still in the portfolio, there's risk of computational waste on patterns that are statistically noisy rather than genuinely predictive.

## Production readiness

The single ACTIVE_TAKE_SMALL pattern is borderline production-ready—the mechanism is coherent (mean reversion + institutional flows) but clarity of 72 suggests 1-2 more validation cycles are warranted. Among the 57 ACTIVE_WATCH patterns, those with clarity ≥75 and scores ≥62 (ranks 5-10) should advance to paper trading, particularly the relative-strength-in-weakness patterns (52w high during Nifty weakness). The DORMANT_REGIME pattern at rank 9 (UP_TRI×Bull×High Vol) looks promising for activation when volatility regime shifts—its clarity=72 and score=62 match current ACTIVE_WATCH standards. Before production, recommend requiring clarity ≥75 threshold for capital deployment and establishing regime-conditional activation rules for the 108 DORMANT_REGIME patterns.
---

## Cost summary

- LLM calls: 545
- Cache hits: 0
- Total cost: $1.310
