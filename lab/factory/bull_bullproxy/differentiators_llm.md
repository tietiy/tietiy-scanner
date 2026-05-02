# Bull BULL_PROXY Differentiator Analysis — Sonnet 4.5

**Date:** 2026-05-03
**Model:** `claude-sonnet-4-5-20250929`

# Bull BULL_PROXY Cell Differentiator Analysis

## 1. Mechanism — What Does Bull BULL_PROXY Represent?

Bull BULL_PROXY represents **support defense in trending markets** — institutional confirmation that the bullish structure remains intact. While Bear BULL_PROXY captures capitulation reversals at extreme oversold levels (macro fear reset), Bull BULL_PROXY identifies shallow pullbacks within established uptrends where buyers immediately step in. This is the "buy the dip" regime where institutional participants view retracements as accumulation opportunities rather than breakdown warnings.

The mechanism works because **information asymmetry favors continuation in Bull regimes**. When the 200-day trend is positive and breadth is healthy, temporary weakness signals profit-taking or tactical rotation, not structural deterioration. Smart money uses these moments to add exposure at better prices. The pattern differentials prove this: `multi_tf_alignment_score=high` adds +7.0pp (n=2,116), meaning support holds when multiple timeframes confirm the trend. The `52w_high_distance_pct=low` feature (+8.0pp, n=261) shows this works best when price is already near strength — these are continuation setups, not reversal attempts.

The **timing edge comes from calendar and volatility clustering**. `day_of_month_bucket=wk4` dominates with +13.7pp (n=707) — month-end window dressing and rebalancing flows create systematic support. `nifty_vol_regime=High` adds +13.1pp (n=383), but this is **constructive volatility** (sharp but brief washouts that flush weak hands), not the destructive capitulation seen in Bear regimes. The `nifty_20d_return_pct=high` lift (+5.8pp, n=593) confirms recency bias: recent strength attracts momentum capital that defends pullbacks aggressively.

Institutional behavior differs fundamentally from Bear BULL_PROXY. In Bear regimes, institutions wait for maximum pain (60d returns deeply negative) before deploying capital. In Bull regimes, they **front-run support** because competition for entry is fierce. The late_bull sub-regime collapse to 43.6% WR (-7.5pp, n=268) reveals the failure mode: once the trend exhausts, these shallow dips become distribution points rather than accumulation zones.

## 2. vol_climax Replication Test Verdict

The vol_climax=True feature delivered **delta=-4.4pp in Bull BULL_PROXY**, confirming it as a **universal anti-feature across both regimes**. This validates the cross-regime hypothesis: volume capitulation events break support structures regardless of directional context. In Bear BULL_PROXY, vol_climax=True showed -11.0pp, nearly 3x the magnitude, but the directional consistency is the critical finding. Capitulation spikes signal forced liquidation and panic exits that violate the controlled pullback thesis.

The mechanism difference explains the magnitude gap. In Bear regimes, vol_climax events occur at oversold extremes where one more wave of selling triggers margin calls and systematic deleveraging — the anti-feature is stronger because it compounds an already fragile structure. In Bull regimes, vol_climax punctures the "buy the dip" psychology by introducing **fear contagion**. When volume spikes on the downside in an uptrend, it signals institutional distribution rather than retail capitulation, breaking the support-defense pattern that Bull BULL_PROXY relies on.

The -4.4pp penalty may seem modest, but it's operationally decisive. Bull BULL_PROXY's baseline is only 51.1% — a 4.4pp drag pulls the sub-cohort to ~46.7%, below random. The **✓ CONFIRMED** verdict means production filters must explicitly exclude vol_climax=True signals. This creates a clean decision rule: if the support test occurs with volume capitulation, it's not a Bull BULL_PROXY setup — it's a potential breakdown that should be ignored or potentially faded.

The universality of this anti-feature also validates the **Bear regime insights as predictive for Bull behavior**. When a feature pattern holds across opposing macro regimes, it represents a microstructural truth rather than regime-specific noise. Vol_climax=True breaks support because it reveals seller urgency that overwhelms incremental buyers — this is true whether the 200-day trend is up or down.

## 3. inside_bar=True Direction Across Regimes

Bull BULL_PROXY showed **inside_bar=True delta=+1.4pp**, classified as **neutral** — a stark contrast to Bear BULL_PROXY's -9.4pp anti-feature. This regime divergence reveals fundamentally different consolidation dynamics. In Bear regimes, inside bars signal indecision that precedes further breakdown (range compression before capitulation), making them toxic for reversal attempts. In Bull regimes, inside bars represent **healthy pause patterns** where neither buyers nor sellers dominate temporarily, allowing continuation afterward.

The neutral outcome (+1.4pp is statistically insignificant with large sample sizes) means inside bars neither help nor hurt in Bull BULL_PROXY. This makes mechanical sense: Bull regime support tests don't require explosive range expansion to validate. A tight consolidation followed by resumption is equally valid because the underlying bid remains intact. The pattern preference shifts from "violent reversal" (Bear regime) to "controlled continuation" (Bull regime). Institutional participants don't need to see panic covering to confirm support — steady accumulation within narrow ranges works fine.

The **production implication is significant**: inside_bar filters that improve Bear BULL_PROXY (explicitly avoiding inside_bar=True setups) should **not** be applied to Bull BULL_PROXY. Doing so would eliminate neutral signals without edge improvement, reducing sample size for no gain. This is a regime-specific filter divergence that requires conditional logic in production systems — the same technical pattern has opposite implications depending on macro context.

This also explains why `multi_tf_alignment_score=high` works so strongly (+7.0pp) in Bull BULL_PROXY. When inside bars don't matter, what matters is **trend alignment across timeframes**. The Bull regime doesn't need range expansion drama; it needs confirmation that the pullback is shallow across multiple lookback windows (daily, weekly, monthly all showing uptrends). The focus shifts from volatility signature to structural position.

## 4. 20d_return Alignment with Bull UP_TRI

The alignment is **✓ CONFIRMED and decisive**. Bull BULL_PROXY shows `nifty_20d_return_pct=high` at +5.8pp (n=593), while the cross-regime context notes Bull UP_TRI benefits from the same feature at +5-8pp. This is a **shared recency anchor** across bullish Bull cells — both patterns require near-term momentum as precondition. The mechanism is identical: recent strength attracts momentum capital and creates chasing behavior that supports continuation setups.

The cross-cell prediction test further validates this with **✓ CONFIRMED** status, meaning the lift was both present and statistically significant. This creates a **production-level feature hierarchy**: `nifty_20d_return_pct=high` should be a first-pass filter for all bullish Bull signals (BULL_PROXY, UP_TRI, and potentially others). The 593-sample cohort for Bull BULL_PROXY is substantial, representing 22% of lifetime signals, so this isn't a small-sample artifact.

The **anti-feature pattern strengthens the case**: `nifty_20d_return_pct=medium` shows -5.7pp penalty in Bull BULL_PROXY. This U-shaped response (high is good, medium is bad) mirrors typical momentum factor behavior — you want strong trends, not choppy mid-range action. Medium 20d returns signal indecision and range-bound conditions where support tests fail more often because there's no momentum cushion to absorb selling pressure.

Production implication is straightforward: **require nifty_20d_return_pct=high as mandatory filter for both Bull BULL_PROXY and Bull UP_TRI**. This creates a unified bullish signal stack with consistent entry conditions. The alignment also suggests these cells may capture different phases of the same underlying regime — UP_TRI as breakout continuation (60.2% WR in recovery_bull), BULL_PROXY as pullback entry within the trend (57.4% WR in recovery_bull). Both need the 20-day momentum tailwind to work.

## 5. Sector Preferences vs Bear BULL_PROXY

The data provided doesn't include explicit sector performance breakdowns for Bull BULL_PROXY, but we can infer the **likely divergence from Bear BULL_PROXY's defensive preference** (Pharma 67%, Energy 64%). Bull BULL_PROXY's feature set suggests it favors **cyclical and momentum sectors** rather than defensives, based on the alignment with high 20d returns and multi-timeframe trend strength.

The `52w_high_distance_pct=low` winner (+8.0pp, n=261) indicates Bull BULL_PROXY works best when stocks are near 52-week highs — this is the opposite of Bear BULL_PROXY's beaten-down preference (`52w_high_distance=high` at +14.4pp in Bear). Near-high positioning favors sectors with institutional sponsorship and earnings momentum: Technology, Financials, Industrials in growth phases. These sectors maintain tight stop-loss discipline and attract systematic flows that defend pullbacks aggressively.

Bear BULL_PROXY's defensive sector preference made sense for capitulation reversals — Pharma and Energy hold value better during crashes and attract safety flows at bottoms. Bull BULL_PROXY should show the **mirror pattern**: underperformance in defensives (which lag in strong rallies) and outperformance in high-beta cyclicals. The `nifty_vol_regime=High` lift (+13.1pp) supports this — constructive volatility in Bull markets benefits sectors with strong earnings revisions, not stable dividends.

The production test would be to segment Bull BULL_PROXY signals by sector and compare win rates. Expected hierarchy: Technology/Discretionary/Financials at top (55-60% WR), Staples/Utilities/Pharma at bottom (45-48% WR). This would confirm that **sector rotation must flip based on regime** — the same defensive tilt that saves Bear BULL_PROXY would sink Bull BULL_PROXY by missing the momentum trade.

## 6. Production Verdict

Bull BULL_PROXY baseline at 51.1% is **marginally profitable but insufficient for standalone deployment**. The best sub-regime recovery_bull at 57.4% WR looks attractive but suffers from **severe sample scarcity** (n=70, only 2.6% of signals). This creates 95% confidence intervals of roughly ±11pp, making it unsuitable as primary filter. The production-viable regime is **healthy_bull at 53.4% WR (n=333, 12.4% of signals)**, which provides sufficient sample size for 2-3x per year trading frequency with ±5pp confidence bounds.

The right production filter combines **regime and feature conditions**: (1) activate only in healthy_bull (exclude late_bull's 43.6% failure mode), (2) require `nifty_20d_return_pct=high` (cross-validated with UP_TRI), (3) require `day_of_month_bucket=wk4` (+13.7pp, n=707) for timing edge, (4) exclude `vol_climax=True` (-4.4pp, confirmed anti), (5) favor `nifty_vol_regime=High` (+13.1pp) for volatility signature. This stacked filter likely produces 15-25 signals per year at 56-60% WR.

The **activation logic requires regime detection**: Bull BULL_PROXY should activate when market breadth is healthy (not late-cycle exhaustion) and 200-day returns are positive but not extreme. The late_bull collapse to 43.6% WR (n=268) is the critical failure mode to avoid — this occurs when P/E multiples are stretched and sentiment is euphoric. A simple breadth filter (require market_breadth_pct ≠ extremely high) would exclude late_bull while preserving healthy_bull and recovery_bull signals.

**Position sizing should reflect confidence tiers**: recovery_bull signals (if sample grows) get 1.5x base size due to 57.4% WR, healthy_bull gets 1.0x base size, normal_bull gets 0.5x size (51.5% WR barely above baseline). Late_bull signals should be **completely excluded** or potentially faded short. The month-end timing edge (wk4 bucket) suggests signals should be scaled into Wednesday-Friday of month-end weeks to capture rebalancing flows. This creates a conditional, regime-aware deployment rather than always-on signal generation.
