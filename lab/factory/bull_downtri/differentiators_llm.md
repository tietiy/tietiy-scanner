# Bull DOWN_TRI Differentiator Analysis — Sonnet 4.5

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

# Bull DOWN_TRI Cell Differentiator Analysis

## 1. Direction-flip pattern verdict

**The cross-cell inversion held PERFECTLY on calendar effects.** Bull DOWN_TRI shows wk3 as the dominant winner (+8.4pp lift, baseline 51.7%), while Bull UP_TRI showed wk3 as an anti-feature (-3.3pp). Conversely, wk4 is Bull DOWN_TRI's worst performer (-5.6pp lift, 37.8% WR) while wk4 was Bull UP_TRI's best (+2.6pp). The mirror is nearly exact.

**Momentum inversion held on recency indicators but with modest magnitude.** nifty_20d_return=high shows delta=-1.6pp (n=2424) for Bull DOWN_TRI, inverting UP_TRI's strong preference for recent momentum. RSI_14=high shows delta=-3.1pp (n=287), confirming overbought conditions hurt DOWN_TRI signals. These are directionally correct but weaker than expected.

**The 200d inversion FAILED.** nifty_200d_return=high shows delta=+1.5pp (n=4996) for Bull DOWN_TRI, meaning long-term strength slightly *helps* rather than hurts. This contradicts the UP_TRI pattern where 200d=high was an anti-feature (-2.1pp). The 200d timeframe appears to operate through a different mechanism than recency-based momentum, possibly regime classification rather than momentum reversal.

## 2. Bull DOWN_TRI mechanism

**This cell represents LATE-STAGE BULL EXHAUSTION shorts against extended leaders.** The down-triangle breakout in bull markets signals distribution or rotation out of stocks that have already run. The 53.0% WR in late_bull (+9.6pp vs baseline) confirms this: these signals work when the bull market is aging and momentum leadership begins to fracture.

**Top features reveal a mean-reversion play against elevated stocks.** The strongest predictors are 52w_high_distance_pct=high (+3.8pp), ema_alignment=bear (+3.9pp), and multi_tf_alignment_score=low (+3.4pp). These describe stocks near highs breaking DOWN patterns while internal structure is already weakening. This is NOT a momentum-short; it's catching micro-structure deterioration in macro-extended names.

**Low volatility requirement confirms rotation mechanism.** nifty_vol_regime=Low (+5.9pp, n=4098) and vol_climax_flag=False (+2.9pp) are critical. This works in *orderly* late-bull conditions where money rotates methodically, not during panic or volatility spikes. The 52w_low_distance=low (+7.3pp, n=218) edge suggests it also catches falling knives that have already collapsed—small sample but clean logic.

## 3. late_bull sub-regime as primary edge zone

**late_bull is the ONLY profitable sub-regime with 53.0% WR, creating a +9.6pp spread vs baseline.** With n=10,024 lifetime signals, the sub-regime sample should be substantial (likely 2,000-3,000 signals assuming roughly even distribution). This is NOT a fragile edge—it's a structural phenomenon. recovery_bull at 35.7% (-7.7pp) and healthy_bull at 40.5% (-2.9pp) both fail, confirming the edge is regime-specific.

**The inversion from Bull UP_TRI is architecturally profound.** UP_TRI's recovery_bull delivered 60.2% WR (best sub-regime), while DOWN_TRI's recovery_bull delivers 35.7% (worst). UP_TRI's late_bull was 45.1% (worst), while DOWN_TRI's late_bull is 53.0% (best). This is a PERFECT phase-flip: buy breakdowns in early recovery, short breakdowns in late exhaustion.

**Deployment filter is MANDATORY but sample risk exists.** If late_bull represents 20-25% of bull regime time (reasonable estimate for mature expansion phases), the edge is deployable but will have long dormant periods. The risk is that BU1 detector mis-classifies late_bull early, or that 2-3 losing signals in a row cause premature abandonment. This requires conviction in the regime detector's accuracy and acceptance of infrequent deployment windows.

## 4. Cross-cell vs Bear DOWN_TRI

**Bull DOWN_TRI is MORE deployable than Bear DOWN_TRI despite lower baseline.** Bear DOWN_TRI showed 46.1% baseline with 0 Phase 5 winners and messy architecture (19 combos all WATCH, live 18.2%). Bull DOWN_TRI has 43.4% baseline BUT a clean 53.0% late_bull sub-regime edge that operates through coherent logic. A single high-conviction filter beats scattered mediocrity.

**Bear DOWN_TRI's calendar edge (wk2 +15pp) was stronger but less mechanically grounded.** The wk2 lift in Bear DOWN_TRI appeared arbitrary—calendar effects without clear macroeconomic or positioning logic. Bull DOWN_TRI's wk3 edge (+8.4pp) aligns with month-end window dressing and rebalancing patterns. The lower magnitude but clearer mechanism makes Bull DOWN_TRI more trustworthy.

**Sector differentiation favors Bull DOWN_TRI.** Bear DOWN_TRI required defensive sector filters (Pharma, Health) with a Bank kill rule. Bull DOWN_TRI shows no sector dependency in top features, suggesting the late_bull + low_vol filter is sufficient. Simpler architecture with fewer conditional branches reduces execution risk and overfitting concerns.

## 5. Both DOWN_TRI cells contrarian-short hostility

**Contrarian shorts are STRUCTURALLY harder than contrarian longs across all regimes.** Bear DOWN_TRI live 18.2%, Bull DOWN_TRI no live signals, both cells show sub-50% baselines (46.1%, 43.4%). Meanwhile UP_TRI cells show 52.0% (Bull) and stronger live performance. The asymmetry is brutal: catching falling knives (UP_TRI in Bear) works ~52-55% with filters; shorting breakdowns works <47% even with filters.

**The architectural truth is MOMENTUM PERSISTENCE beats REVERSAL TIMING.** DOWN_TRI patterns attempt to time exhaustion or reversal, requiring precise entry at inflection points. UP_TRI patterns ride established moves or catch bounces with room to run. Market microstructure favors continuation over reversal: stops cascade on breakdowns (momentum extends), while breakdowns often grind rather than V-bounce (reversals are slow).

**Short-side structural headwinds compound the difficulty.** Funding costs, hard-to-borrow fees, short squeezes, and regulatory constraints don't exist on the long side. Bull DOWN_TRI in late_bull works at 53% because it catches DISTRIBUTION (institutional selling is patient), not panic. The moment you try to short INTO panic (Bear DOWN_TRI), you fight short squeezes and volatility whipsaws. Only mechanical, patient exhaustion shorts work—and those are rare.

## 6. Production verdict for Bull DOWN_TRI

**PROVISIONAL_OFF default, with MANUAL ENABLE for late_bull + low_vol combinations.** The 53.0% late_bull WR (+9.6pp) with supporting low-vol edges (+5.9pp) creates a deployable but NARROW window. This should NOT be an always-on strategy. It requires active regime monitoring with BU1 detector confirmation that the bull market has entered late-stage maturity.

**Additional filters mandatory: wk3 calendar + 52w_high_distance=high + no vol_climax.** Combining late_bull (53.0%) with wk3 (+8.4pp) and nifty_vol_regime=Low (+5.9pp) should push theoretical WR toward 58-60%. Add 52w_high_distance=high (+3.8pp) and vol_climax_flag=False (+2.9pp) as confirmation filters. Expect 10-20 signals per year maximum. Quality over quantity.

**The alternative is SKIP ALL if late_bull detection is unreliable.** If the BU1 sub-regime detector has classification lag (only recognizes late_bull after it ends) or high false-positive rate, the edge evaporates. Given recovery_bull's catastrophic 35.7% WR, misclassification risk is existential. Before enabling, backtest the BU1 detector's late_bull precision separately. If precision <70%, defer Bull DOWN_TRI entirely until detector improvements ship. A 53% edge with 30% deployment error becomes a 45% live disaster.
