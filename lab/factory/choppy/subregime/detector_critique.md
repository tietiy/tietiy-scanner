# Choppy Sub-Regime Detector — Sonnet 4.5 Critique

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`
**Source:** `detector_design.md` + `detector_validation.json`

## Critique

# Sub-regime Detector Design Critique

## 1. Feature sufficiency

**Core gap: momentum/trend direction is completely absent.** You're classifying volatility × breadth but ignoring whether the market is falling apart (drawdown stress) vs. recovering from lows (rebound stress). A 30% vol-percentile with 25% breadth during capitulation is fundamentally different from the same metrics 3 days after a bottom when shorts are covering.

The strongest missing feature is **Nifty 20-day return or distance-from-52w-high**. Its absence matters because "stress" conflates panic-selling with explosive short-covering rallies—both high-vol, but UP_TRI signals behave oppositely. Your stress__low_breadth catastrophe (20.2% WR) likely captures falling-knife entries, while stress__med_breadth (60.1%) catches V-bottom reversals after breadth stabilizes.

Secondary gap: **cross-sectional dispersion** (stock-level vol distribution). High Nifty vol + high breadth can mean either synchronized rally or rotational churn. The 51.7% vs 60.1% WR gap between stress__high vs __med suggests this matters, but you can't diagnose it.

## 2. Threshold defensibility

**Not defensible for win-rate optimization, but defensible for interpretability and stability.** The inherited 0.30/0.70 percentile cutoffs are arbitrary tertiles, not chosen to maximize separation of your 9-cell WR distribution. You have enough data (35k signals) to optimize via:
- **Recursive partitioning on WR**: Build a decision tree with vol_percentile + breadth predicting binary W/L, extract splits.
- **Isotonic regression boundaries**: Fit monotonic WR(vol) curves separately per breadth tertile, find inflection points.

However, fixed percentile thresholds have *regime-shift stability*—they adapt as the vol distribution evolves (2020 vs 2023 "stress" means different absolute vol). Optimized absolute thresholds would drift. If you re-optimize, validate on out-of-sample crisis periods (COVID, Russia-Ukraine) to check if learned boundaries collapse when regime shifts.

The breadth 0.30/0.60 split is more suspicious—those look like round-number guesses. The balance__med vs __high UP_TRI gap (46.8% → 54.0%) suggests 0.60 might be too low; try 0.65-0.70 as the high-breadth threshold.

## 3. Edge cases that break it

**A. Post-event gap-up compression (Budget 2024 rally style):** Nifty gaps +2% on policy news, then grinds sideways for 5 days with shrinking intraday ranges. Vol-percentile decays rapidly into "balance" or "quiet," but the tight coil is pre-breakout tension, not stable equilibrium. UP_TRI signals fail because the system expects mean-reversion, but you're in a breakout setup. Detector needs recent-gap or ATR-compression flags.

**B. Sectoral rotation disguised as balance:** Nifty vol at 40th percentile (balance), breadth at 55% (med), but IT is -8% while Energy is +6%. Market *looks* calm, but stock-specific signals are in a stock-picker's regime, not Choppy mean-reversion. Cross-sectional dispersion or sector-correlation breakdown would catch this; your detector sees false calm.

**C. Friday → Monday volatility reset:** Friday closes with 85th vol-percentile (stress), Monday opens flat and trades ±0.3% (realized vol collapses). Your 20-day percentile still shows stress for 4-5 more days due to the rolling window, but the regime already flipped. Signals get stress filters when they need quiet filters. You need exponential vol or intraday range to catch regime shifts within 1-2 days.

**D. Low-liquidity holiday weeks (Diwali, year-end):** Breadth mechanically falls (many stocks don't trade daily), Nifty vol stays artificially low due to thin volumes. Detector shows quiet__low_breadth (your 65% UP_TRI hero cell), but the edge is fake—it's just calendar effect + survivor bias. Filter needs trading-days-active or turnover adjustment.

**E. VIX spike without Nifty vol (2023 HDFC Bank weight-change):** India VIX jumps on event risk, but Nifty realized vol stays low because the index is composition-stable. Your detector shows balance/quiet, but option skew and institutional positioning scream stress. Missing derivatives-based fear gauge.

## 4. The quiet__low_breadth 65.1% UP_TRI surprise

**Likely real but fragile—cluster of specific macro regimes, not a robust edge.** 359 signals over ~8 years suggests ~3-4 signals/month during those periods. Hypotheses:
- **Post-correction recovery starts:** Nifty bottoms and stabilizes (low vol), but most stocks still broken (low breadth). UP_TRI catches early-cycle leadership (Reliance, HDFC) before broad participation. This is real—it's the "narrow rally" edge.
- **Survivor bias from FII-heavy months:** Low breadth in mid/small-caps, but Nifty 50 stable. UP_TRI on large-caps works because they're in a different micro-regime. If your universe is market-cap weighted, this is real; if equal-weight, it's selection bias.

**Discriminating test:** Partition the 359 signals by Nifty's 20-day return terciles. If the edge is real, it should hold across all three (recovery thesis doesn't require specific direction). If it only works when Nifty is +4-8% over prior 20 days, it's disguised momentum, not regime structure. Also check: does median market-cap of triggered stocks differ (>₹50k crore vs <₹10k crore)? If yes, it's a cap-segment rotation artifact.

## 5. The stress__low_breadth 20.2% UP_TRI catastrophe

**Credible enough to SKIP, but add a 30-day probation sunset clause.** 372 signals with 75 wins vs 297 losses is statistically brutal (p < 0.001 vs coin-flip). This isn't noise. The regime is coherent: high stress + collapsing breadth = capitulation/cascade, and mean-reversion signals get run over by momentum.

However, n=372 over 8 years means ~1 signal/week during those periods—small enough that a single 6-month anomaly (COVID recovery, Russia-Ukraine) could dominate the sample. **Action:** Hard-SKIP the cell, but:
1. Log every skipped signal with a "would-have" P&L track.
2. After 30 live trading days OR 15 skipped signals, recompute WR. If it recovers to >40%, re-enable with caution.
3. Check if the 20.2% includes a single 2-week disaster (e.g., March 2020). If yes, it's a regime break, not a persistent edge failure.

If you have drawdown constraints, SKIP is a no-brainer. If you're in exploration mode, consider a 0.25× position-size test rather than full skip.

## 6. Production deployment risk

**Most likely failure: whipsaw hell during regime transitions, especially vol-regime flips.** Scenario: Market exits stress on Day T (vol-percentile drops to 68%), triggers balance filters, then spikes back to stress on Day T+2 (news event). Signals generated on T+1 get the wrong filter, and the rapid flip means your 20-day vol hasn't settled—you're blind for 3-5 days.

**Manifestation:** A cluster of 10-15 losing trades over 1 week, all in "transition" states your detector doesn't recognize. Post-mortem shows half were stress__med signals getting balance filters (under-hedged), half were balance signals getting stress filters (over-hedged, missed moves). Your Sharpe halves for the month because the detector lags the true regime by 2-3 days.

**Mitigation without re-engineering:** Add a **2-dayema vol supplement** alongside the 20-day percentile. If short-term vol diverges >20 percentile points from the 20-day (e.g., 20d=65th, 2d=88th), flag as "transition__unknown" and either skip or use the most conservative filter. Costs you ~5% of signals but prevents the whipsaw bleed. Alternatively, require 3 consecutive days in the same sub-regime before applying the corresponding filter (lag in exchange for stability).
