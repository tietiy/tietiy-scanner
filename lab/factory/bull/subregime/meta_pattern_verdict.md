# Bull Regime Meta-Pattern Verdict — Sonnet 4.5

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

# Bull Regime Sub-Regime Architecture Review

## 1. Meta-pattern verdict: Was the predicted axis correct?

**Partial hit, wrong implementation.** The predicted "trend_persistence" concept was directionally correct—Bull's primary axis *does* measure trend health—but `nifty_200d_return_pct` is better characterized as **"trend maturity"** than "persistence." A 200-day return captures *how far into the Bull run* the market is, not just whether the trend is intact. The 15.1pp WR range validates this as Bull's strongest discriminator, outperforming the multi-timeframe alignment approach (12.7pp) that was closer to literal "persistence."

**Leadership concentration was directionally correct but secondary.** The `market_breadth_pct` axis does measure concentration (narrow vs. broad), and it successfully partitions Bull into meaningful sub-regimes. However, it's less powerful than predicted—the breadth axis primarily refines *within* maturity buckets rather than defining the primary structure. The recovery_bull (narrow) and healthy_bull (broad) split shows breadth matters most in mid-maturity Bull, less so at extremes.

**Revised characterization: "trend maturity × participation quality."** Bull's primary axis measures where you are in the cycle (early/recovery vs. mid-cycle vs. late). The secondary axis measures whether the advance is broad (healthy) or narrow (selective leadership in recovery, deteriorating leadership in late). This is subtly different from the Bear pattern where primary = panic intensity and secondary = oversold degree—both measure *stress*, just different flavors. In Bull, primary = cycle position, secondary = quality signal.

**Production implication:** For other regimes or future axis searches, prioritize **lookback-based return measures** (60d, 200d) over real-time state measures (multi-TF alignment, vol percentile) when the regime itself is directional. Trend regimes want maturity measures; rangebound regimes want state measures.

## 2. Tri-modal structure universality: Same shape or just "extremes matter"?

**Structure differs fundamentally, but tri-modal holds.** Choppy and Bear show clean hot/balance/cold distributions (roughly 10-20% / 70% / 10-20% split). Bull shows skewed tri-modal: two small hot cells (recovery 2.6%, healthy 12.5%), one large cold cell (late 7.1%), and a massive "normal" basin (76.4%). The meta-pattern isn't "three equal buckets" but rather **"two edges + bulk,"** where edge percentages vary by regime character. Volatile regimes (Bear, Choppy) spread signals across cells; stable regimes (Bull) concentrate in normal.

**The unifying principle: extremes carry 80%+ of the information.** In Bull, the meaningful edges are recovery_bull (60.2% WR, +8.2pp) and late_bull (45.1% WR, −6.9pp)—a 15.1pp spread. The healthy_bull cell (58.4%, +6.3pp) adds refinement but isn't strictly necessary; you could collapse it into normal and still capture most edge. Similarly, Bear's UP_TRI hot zone (68% WR) and cold zone likely span ~20pp. The tri-modal pattern is really **"identify the two tails that matter, everything else is baseline."**

**Bull's asymmetry reflects regime stability.** A Bull market *should* spend 70%+ of its time in "normal" conditions—that's what makes it a Bull. Bear markets are definitionally unstable (high vol, panic alternating with grind), so signals distribute more evenly across sub-regimes. Choppy is rangebound chaos, so vol/breadth extremes are common. The tri-modal meta-pattern adapts shape to regime: stable regimes → fat middle, volatile regimes → distributed edges.

**Revised meta-pattern statement:** All regimes are tri-modal as **"edge_positive + baseline + edge_negative,"** but the bucket sizes reflect regime volatility. Bull = 15% edge / 76% baseline / 7% edge. Bear likely ≈ 20% / 60% / 20%. Choppy probably ≈ 15% / 70% / 15%. The universal law is **"two discriminative tails exist,"** not "three equal buckets."

## 3. Recovery_bull surprise: Generalizable or Bull-specific?

**Mechanically Bull-specific, but structurally generalizable as "transitional quality."** The recovery_bull definition (200d return barely positive + narrow breadth) only exists in Bull because it requires regime classification *after* a Bear-to-Bull transition while lagging indicators (200d return) are still catching up. You can't have this exact cell in Bear (by definition, Bear can't have emerging positive returns) or Choppy (Choppy doesn't have directional recovery). So the literal setup is Bull-only.

**But the *concept* of "transitional zone with quality leadership = high WR" likely generalizes.** Recovery_bull's 60.2% WR comes from narrow leadership (institutions/smart money leading) during regime transition before retail/breadth catches up. Bear's "warm zone" (UP_TRI in mid-vol, mild oversold) at 68% WR might be analogous: not full panic, not full recovery, but selective opportunities in quality names during Bear stabilization. Choppy's UP_TRI hot zone (60% WR in high vol + synchronized breadth) is different—it's opportunistic reversal, not quality leadership—so less analogous.

**The unifying principle: "early cycle + selectivity = edge."** Whether it's recovery_bull (early Bull, narrow breadth), Bear warm zone (post-panic stabilization, not yet oversold extreme), or even Choppy's rotation phases, the pattern is **"be early when the crowd hasn't arrived yet, and trade with the leaders not the laggards."** Narrow breadth in recovery_bull is a *feature* (quality leads) vs. narrow breadth in late_bull as a *bug* (distribution/topping).

**Cross-regime test recommendation:** Check if Bear UP_TRI has a "mid-panic + breadth-narrowing" cell that outperforms (quality names bottoming first). Check if Choppy UP_TRI has a "rotation-initiation" cell (breadth turning from sync to rotation). If both exist, the meta-pattern is **"transitional quality zones = highest WR"** across all regimes, just expressed differently per regime's geometry.

## 4. Production implications: Filter design for Bull UP_TRI

**TAKE_FULL in recovery_bull and healthy_bull (n=5,736, 58.7% WR composite).** These two cells represent 15.1% of Bull UP_TRI signals but deliver +6.3pp to +8.2pp edge. The composite WR across both (~58.7%) is strong enough to take full size without cascading to additional filters. Recovery_bull's small sample (n=972) might raise concerns, but 60.2% WR on 972 trades is statistically significant (>30 expected edge trades) and mechanically sound (quality leadership in early Bull).

**SKIP late_bull explicitly (n=2,699, 45.1% WR).** This is 7.1% of signals with −6.9pp edge—a trap. The definition (mid 200d return + narrow breadth) is easy to implement and catches the classic topping pattern. Skipping these saves ~7% of capital from sub-45% WR trades. This is the clearest production rule: `if nifty_200d_return_pct in [0.05, 0.15] AND market_breadth_pct < 0.60: SKIP`.

**CASCADE normal_bull (n=29,110, 51.3% WR).** This is 76% of signals at near-baseline WR (+0.3pp edge, essentially zero). Send these to the next filter layer—likely Bear/Choppy sub-regime cascade (if regime mix is ambiguous) or signal-level filters (anchoring_quality, vol context, etc.). The volume is too large and edge too thin to take blindly, but 51.3% WR isn't *bad*—it just needs refinement. A two-stage filter (Bull sub-regime → signal-level) will extract edge from this bucket.

**Implementation priority: late_bull SKIP first, then recovery+healthy TAKE.** The SKIP rule has higher ROI because it's defensive (saves 7% of capital from −7pp edge) and simpler (one rule). The TAKE_FULL rule captures +6-8pp edge on 15% of signals but requires two cell definitions. In practice: (1) add late_bull SKIP immediately, (2) add recovery+healthy TAKE after validating on Bull DOWN_TRI / BULL_PROXY to ensure the cells aren't UP_TRI-specific artifacts.

## 5. Cross-signal predictions: Bull DOWN_TRI and BULL_PROXY

**Bull DOWN_TRI (contrarian short): Expect weak edge, possible inversion.** In Bear, DOWN_TRI inverts UP_TRI (Bear DOWN_TRI's hot zone is low vol + mild oversold, opposite of UP_TRI's high vol + capitulation). In Bull, DOWN_TRI is fighting the regime, so baseline WR should be sub-50% (likely 35-45% range). **Predicted inversion:** late_bull (mid 200d + narrow breadth) should be DOWN_TRI's *best* cell (shorting into narrowing leadership), while recovery_bull should be worst (shorting quality leadership = pain). If late_bull DOWN_TRI hits 48-52% WR, it validates the sub-regime structure. If recovery_bull DOWN_TRI drops to 30-35% WR, it confirms the "quality leadership" thesis.

**Bull DOWN_TRI production rule: Only trade late_bull cell, skip rest.** If the inversion holds and late_bull delivers 48-52% WR for DOWN_TRI while other cells are 35-42%, the production filter is simple: `if Bull AND DOWN_TRI AND NOT late_bull: SKIP`. This makes DOWN_TRI a late-cycle topping tool, not a general Bull short instrument. Expected signal volume: 7% of DOWN_TRI signals in Bull qualify (matching late_bull's 7.1% of UP_TRI), so this is a rare, selective short setup.

**BULL_PROXY (support rejection): Expect alignment with UP_TRI, not inversion.** BULL_PROXY tests support in Bull regime—it's a momentum continuation setup like UP_TRI, not a contrarian signal like DOWN_TRI. **Predicted alignment:** recovery_bull and healthy_bull should also be BULL_PROXY's hot zones (bounces in quality-led or broad Bull = high WR). Late_bull should underperform (support breaks more often when leadership narrows). The WR spread might compress (UP_TRI 60%/58%/45% → BULL_PROXY 56%/54%/47%) because support tests are inherently lower-probability than breakouts, but rank order should hold.

**Cross-signal validation test: Check all three signals in recovery_bull.** If recovery_bull delivers 60% WR for UP_TRI, 55-57% for BULL_PROXY, and 32-38% for DOWN_TRI, the cell is validated as "genuine quality leadership zone" rather than UP_TRI-specific overfitting. If results are mixed (e.g., BULL_PROXY doesn't outperform in recovery_bull), the cell may be breakout-specific, and production filters need signal-level customization. Run this test on n=972 recovery_bull UP_TRI signals + equivalent DOWN_TRI/BULL_PROXY samples before deploying TAKE_FULL rules.
