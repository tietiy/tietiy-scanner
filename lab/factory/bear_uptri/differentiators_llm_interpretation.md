# Bear UP_TRI Differentiator Mechanism Analysis

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

# Bear UP_TRI Feature Differentiator Interpretation

## 1. Mechanism: Why Bear UP_TRI Works

**Bear-market compression-to-breakout reversal under stress.** Ascending triangles in Bear regimes represent forced consolidation against resistance while higher lows form—typically institutional accumulation or short-covering into defined supply. The breakout occurs when sellers exhaust at the apex, triggering capitulation reversal with defined risk (triangle base as stop).

**High volatility regime acts as catalyst, not headwind.** 100% High vol in live data suggests these patterns exploit panic exhaustion: bears overcommit into triangle resistance, breakout creates short squeeze + FOMO entry cascade. The pattern's geometry (compressed range + rising lows) creates asymmetric risk/reward that works *because* of stress, not despite it.

**S-tier dominance (45/64 winners) indicates mature, clean setups.** Unlike Bull regimes where early-stage (B-tier) patterns work, Bear UP_TRI requires institutional-grade quality—tight consolidation, volume confirmation, clear resistance. The mechanism is **forced capitulation at structural compression**, not speculative breakout.

## 2. Most Trusted Features for Filter Design

**Anchor #1: `nifty_60d_return_pct=low` (+52pp, 53% winner presence).** This is the regime anchor—confirms we're in sustained Bear weakness, not Bull correction. Differentiates true Bear capitulation setups from random triangles. Hard boundary, regime-defining, massive delta.

**Anchor #2: `consolidation_quality=none` (+13pp).** Counterintuitive but critical: winners *lack* traditional consolidation metrics, suggesting the triangle itself IS the consolidation (self-contained pattern). Avoids false positives from stocks with prior messy basing. This filters for "clean slate" breakouts where the triangle geometry is the primary structure.

**Anchor #3: `inside_bar_flag=True` (+8pp, 29% presence).** Tactical entry signal—inside bar at triangle apex signals compression extreme before breakout. High absolute presence (29%) makes it actionable. Confirms the "coiled spring" mechanism and provides entry timing, not just regime filter.

**Avoid:** `day_of_week=Thu` (calendar effect, likely noise). `ROC_10=high` (low absolute presence 13%, fragile). `ema200_distance_pct=high` (8% presence, not robust).

## 3. Anti-Feature Interpretation: What Doesn't Work

**`day_of_month_bucket=wk4` (-69pp, 0% winners, 69% WATCH) is regime timing artifact.** Week 4 may coincide with month-end rebalancing that creates false triangle breakouts or failed follow-through. Strongly avoid—this is a "dead zone" for the pattern, likely due to institutional flow dynamics that reverse breakout momentum.

**Medium regimes are pattern killers:** `nifty_vol_regime=Medium` (-12pp), `ROC_10=medium` (-9pp), `consolidation_quality=loose` (-8pp), `range_compression_60d=medium` (-7pp). Bear UP_TRI requires **extremes**—high stress OR tight compression. Medium = ambiguity = failure. The pattern needs clear capitulation (high vol) or coiled energy (tight range), not muddled conditions.

**`ema_alignment=bear` as anti-feature (-11pp) is paradoxical but revealing.** Despite Bear regime, winners have *misaligned* EMAs (mixed signals), suggesting the triangle forms at **inflection points** (regime transition), not in established downtrends. Confirms "capitulation reversal" over "bear rally continuation" mechanism.

## 4. Mechanism vs Sub-Regime: Universal or Specific Edge?

**The +38.9pp gap + 100% High vol + week-4 artifact strongly suggest SPECIFIC sub-regime edge**, not universal Bear pattern. If universal, lifetime (55.7%) would be closer to live (94.6%), and vol regime would show diversity. Current April 2026 regime appears to be sustained high-stress Bear with specific monthly flow patterns (week-4 dead zone).

**Discriminating pattern: Time-based anti-features (week-4) + uniform vol (100% High) indicate temporal clustering.** Universal edges show diverse conditions in live data. Here, *all* live winners occur in same vol regime and avoid same calendar window—classic sub-regime specialization. The mechanism works, but **current parameters are over-tuned to 2026 stress environment**.

**Feature evidence for sub-regime:** `nifty_60d_return_pct=low` (53% presence) is strong but not dominant—means 47% of winners occur *without* this. If truly universal Bear edge, regime anchor would be near 100%. The diversity within winners suggests the filter is catching a "hot regime" where multiple paths work, not a single robust mechanism.

## 5. Risk to Filter Selection: Over-Fitting Hazards

**CRITICAL RISK: `nifty_vol_regime=High` (100% live, 0% Medium/Low).** Exact parallel to Choppy case. Cannot use High vol as filter—it's a coincidence with current regime, not a causal feature. Lifetime data likely shows winners across vol regimes; current 100% is sampling artifact. **Using this filter guarantees zero signals when regime shifts to Medium vol.**

**HIGH RISK: `day_of_month_bucket=wk4` avoidance (-69pp).** While currently a strong anti-signal, this could be April 2026 artifact (earnings season? specific event?). Filtering out week-4 permanently may eliminate future signals when calendar effects normalize. Use cautiously, monitor for regime change.

**MEDIUM RISK: `consolidation_quality=none` (+13pp).** Appears mechanistic (triangle IS the consolidation) but 18% presence is low—could be measurement artifact where triangle patterns aren't detected by consolidation scanner. If scanner logic changes or regime shifts to patterns with prior basing, this filter fails. Test sensitivity: does adding `=loose` kill performance, or just reduce sample size?

**SAFE: `nifty_60d_return_pct=low` (regime anchor, expected to persist across Bear sub-regimes), `inside_bar_flag` (geometric pattern feature, not regime-dependent).**
