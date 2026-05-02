# Bear DOWN_TRI Differentiator Mechanism Analysis

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

# Bear DOWN_TRI Feature Differentiator Analysis

## 1. Why does Bear DOWN_TRI INVERT? (Live 18.2% vs Lifetime 46.1%)

The -28pp inversion is **not actually selection bias in reverse** — it's **adverse selection without a quality filter**. Bear UP_TRI and Choppy F1 had Phase-5 validated combos that screened for higher-quality setups, creating positive bias. Bear DOWN_TRI has **zero Phase-5 winners**, meaning all 19 combos are WATCH — the live sample represents **unfiltered raw signal output** hitting unfavorable market conditions.

The mechanism: **descending triangles in Bear markets are highly regime-sensitive**. When Bear regime persists with follow-through, the 46% baseline holds. But if Bear regime **stalls or chops** (which 2026 April likely did), these breakdown-shorts get squeezed. The live losers show **ema=bull or MACD=bull** flags (5 of 6 top losers have bullish EMA or MACD) — these are Bear-classified stocks showing **internal divergence**, which kills the short thesis.

The 2 live winners (IPCALAB, VINATIORGA) both show **vol_regime=High** and are from top-tier sectors (Pharma, Chem). This suggests the lifetime edge requires **high volatility + sector quality + alignment** to work. The 18.2% live result is what happens when you short Bear DOWN_TRI **without these quality gates** in a non-trending environment.

**Key insight**: The inversion isn't mysterious — it's **absence of validation creating unprotected exposure**. Phase-5 validation acts as a quality screen; without it, you get raw beta to regime continuation, which failed in live period.

## 2. Mechanism for Bear DOWN_TRI at Lifetime (46.1% WR)

A descending triangle in a Bear market is a **continuation pattern** signaling that sellers control the lows (flat support) while buyers can't sustain rallies (lower highs). The short thesis: when support breaks, **trapped longs capitulate** and momentum shorts pile in. The 46% lifetime WR suggests this works slightly better than coin-flip, capturing breakdown momentum in confirmed Bear regimes.

The mediocre 46% (vs stronger cells at 50-55%) reveals **two failure modes**: (1) Bear regimes often **consolidate rather than cascade** — triangles resolve sideways or squeeze higher when macro fear eases, and (2) the pattern is **widely recognized**, so front-running and stop-hunts are common. The short wins when Bear regime has **persistent negative catalysts** (sector rotation, macro deterioration) that prevent any relief bounce.

The lifetime feature differential supports this: **wk2/wk3 timing** (+15pp/+6.7pp) suggests monthly cycle matters — likely avoiding month-end window dressing or liquidity squeezes. **Higher_highs_intact=True** (+4pp winner feature, paradoxically) may indicate stocks that briefly recover then fail again, creating better short entries than steady grinders. **Vol_regime=High** (+2.1pp) confirms the pattern needs volatility to generate follow-through.

**Bottom line**: This captures **bear market continuation breakdowns** when volatility and timing align. It's not a strong edge because triangles are ambiguous and regime-dependent. The 46% baseline is "works sometimes when Bear actually follows through."

## 3. Should kill_001 Extend to Auto/Energy/Metal?

**No immediate extension recommended**, but flag for **sector-combo watch**. Auto (40.4%), Energy (40.7%), Metal (41.4%) are clearly weak vs baseline 46.1%, but the gap (-5 to -6pp) is **smaller than Bank's live 0/6 wipeout**. The lifetime sample sizes are meaningful (n=276-340), so these aren't noise — they're genuinely harder sectors for this pattern.

The live data offers a clue: **ADANIGREEN (Energy) lost** with ema=mixed/MACD=bull, showing internal divergence. But we only have 1 Energy live loser vs 6 Bank losers — insufficient to confirm systematic failure. The lifetime differential suggests these sectors may have **higher short-squeeze risk** (cyclicals with volatility) or **regime decorrelation** (Energy/Metal often counter-trend to broader market Bear).

**Recommendation**: Keep kill_001 as Bank-only for now, but **add Energy/Auto/Metal to Phase-4 rejection criteria** for future combos. If a new combo emerges with these sectors over-represented, reject it in Phase 4. For existing WATCH combos, let them stay WATCH but **monitor sector distribution** — if live signals skew Energy/Metal, that's a red flag for manual override.

**Rationale**: We don't have enough live evidence to ban these sectors outright (could be overfitting to lifetime), but we have enough lifetime evidence to treat them as **suspect** and avoid building combos around them.

## 4. Filter Candidates from Lifetime Data

**Filter 1 (primary): day_of_month_bucket = wk2 OR wk3**  
wk2 shows +15pp lift (58.3% presence WR), wk3 shows +6.7pp (50.9%). Together they cover n=1,556 of 3,640 (43% of samples) and avoid the toxic wk4 (-17.5pp, 34.1% WR). This timing filter likely dodges **month-end rebalancing squeezes** and **options expiry turbulence** (if relevant in Indian markets). Conservative because it's binary and large-sample.

**Filter 2 (secondary): nifty_vol_regime = High AND higher_highs_intact = True**  
Vol_regime=High shows +2.1pp (47.1% WR, n=1,745) — descending triangles need volatility to break decisively. higher_highs_intact=True shows +4pp (49.5% WR, n=566) — paradoxically, this may identify stocks that briefly recover (creating lower highs) then break, offering cleaner short entries than steady bleeders. Combined, this filters for **active breakdown candidates** rather than dead-money shorts.

**Implementation suggestion**: Start with **Filter 1 only** (timing) as a provisional rule, since it's simpler and has the largest effect size. Monitor if live signals concentrate in wk4 (which would validate the filter). Add Filter 2 if we see live losers clustered in Low vol / higher_highs=False conditions. Avoid over-layering filters given zero Phase-5 validation.

**Conservative rationale**: With n=11 live and 2W/9L, any filter is speculative. Timing-based filters (wk2/wk3) are **regime-agnostic** and less likely to overfit than technical indicator combinations. Start minimal, add only with evidence.

## 5. DEFERRED vs KILL vs FILTER — Production Verdict

**Verdict: DEFERRED with provisional filters (Filter 1: wk2/wk3 timing) and kill_001 maintained. Do not deploy to production.**

**Rationale**: Zero Phase-5 validated combos means **no live-tested quality standard exists**. The 18.2% live WR (n=11) is catastrophically bad, but sample size is too thin to definitively kill — could be regime mismatch. However, **the burden of proof is on the signal to validate**, not on us to disprove it. With 0/19 combos validated and live performance inverted vs lifetime, there is **no positive evidence** to justify production risk.

The lifetime 46.1% WR is **mediocre at best** — this is not a hidden gem, it's a marginal edge that requires perfect conditions. The feature differential shows **strong timing dependency** (wk2/wk3 vs wk4) and **sector brittleness** (Pharma/Chem work, Bank/Energy/Auto fail). Without Phase-5 validation to confirm which conditions matter in live trading, deploying this is **guessing with capital**.

**Path forward**: (1) Maintain kill_001 (Bank exclusion) as confirmed. (2) Add provisional Filter 1 (wk2/wk3 timing only) to any future Bear DOWN_TRI signals, logging as DEFERRED. (3) Require **n=20+ samples with 50%+ WR** under the filtered ruleset before reconsidering. (4) If live regime shifts back to strong Bear with follow-through, re-evaluate — this cell may be **regime-specific** and only works in trending Bear, not choppy Bear.

**Honest assessment**: This cell feels like a **weak structural edge** (descending triangle shorts in Bear) that's **highly conditional** (needs volatility, timing, sector alignment) and **not validated in live conditions** (zero Phase-5 winners). The 46% lifetime WR is "better than nothing" but not "good enough to deploy without validation." Keep it in research, don't risk real capital until it proves itself in Phase 5 or live improves dramatically with filters applied.
