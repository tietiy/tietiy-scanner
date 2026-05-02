# Bull UP_TRI Stratification — Sonnet 4.5 Analysis

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

# Bull UP_TRI Cell Stratification Analysis

## 1. Bullish architecture parallel/divergence

Bull UP_TRI **diverges meaningfully** from Bear UP_TRI on key structural anchors. Bear UP_TRI's top predictor was `nifty_60d_return=low` (+14.1pp), signaling mean-reversion strength in compressed markets. Bull UP_TRI's `H1_high200d` test shows **delta=-2.1pp**, suggesting high 200d returns *hurt* performance—opposite to Bear's reversion logic. The calendar anchor `wk4` shows +3.6pp lift in Bull UP_TRI vs +7.5pp in Bear UP_TRI, preserving directional agreement but at **half the magnitude**.

The `ema_alignment=bull` filter adds only +1.6pp in Bull UP_TRI, while `multi_tf_alignment_score=high` contributes +2.2pp. These are **trend-following confirmations**, not mean-reversion setups. Bear UP_TRI leaned on compression + `inside_bar=True` (+4.9pp); Bull UP_TRI shows `inside_bar=False` at +0.1pp (neutral) and `inside_bar=True` at -0.1pp. The **narrative splits**: Bear UP_TRI is a coiled spring in oversold regimes; Bull UP_TRI is a momentum continuation setup requiring alignment but penalized by over-extension (high 200d returns).

The `higher_highs_intact=True` flag contributing **-1.2pp** is counterintuitive—it suggests Bull UP_TRI wins when structure is *broken*, not intact. This aligns with a **regime-transition signature**: UP_TRI in Bull contexts may be flagging late-stage exhaustion or consolidation before continuation, where fresh breakouts (no prior higher-highs) outperform stale uptrends. This is architecturally **opposite** to Bear UP_TRI's compression-into-breakout logic.

Cross-cell architecture is **non-parallel**: Bear UP_TRI = mean-reversion in oversold; Bull UP_TRI = selective momentum with anti-overextension filters.

---

## 2. Direction-flip pattern in Bull regime

The direction-flip pattern **partially replicates but with weaker signal**. In Bear regime, `nifty_60d_return=low` was a +14.1pp anchor in Bear UP_TRI but inverted to -4.1pp in Bear DOWN_TRI—a **18.2pp swing** confirming regime-anchor dependency. Bull UP_TRI's `H1_high200d` test at **-2.1pp** suggests overextension hurts, but there's no Bear DOWN_TRI-equivalent Bull DOWN_TRI test provided for symmetric validation.

The `H2_high200d_DOWN_TRI` cross-cell test shows **+1.5pp**, indicating Bull UP_TRI setups *with DOWN_TRI geometry on 200d-high anchors* perform slightly better. This is a **muted inversion** compared to Bear's 18pp swing. The `H3_high_breadth` test at +3.4pp suggests breadth-driven Bull UP_TRI setups outperform, implying that Bull UP_TRI benefits from **broad participation** rather than narrow leader extension—again, an anti-overextension signature.

Calendar inversion is present but asymmetric: Bear DOWN_TRI showed wk2 +15pp / wk4 -17.5pp (32.5pp spread). Bull UP_TRI shows wk4 +3.6pp / wk2 -0.7pp—only a **4.3pp spread**. The direction agrees (wk4 bullish, wk2 neutral-to-weak) but magnitude collapses. This suggests Bull UP_TRI's calendar dependency is **real but second-order**, not a primary edge driver.

**Conclusion**: Direction-flip logic holds conceptually (regime anchors matter, overextension inverts) but Bull UP_TRI expresses it at 1/4 to 1/8 the magnitude of Bear cells. The Bull regime compresses predictive variance.

---

## 3. Recovery_bull's 60.2% WR cell

This **likely contains real edge but suffers from classification lag and entry ambiguity**. `recovery_bull` represents only 2.55% of samples (n=972) with 60.2% WR and +8.2pp lift—the strongest sub-regime. The trader narrative is "early Bull regime before 200d smoothing confirms strength," where UP_TRI geometry catches **leadership rotation into cyclicals and small-caps before broad indices validate**. The WR exceeds `healthy_bull` (58.4%) despite recovery_bull being *earlier* in the cycle.

The artifact risk is **regime classification leakage**: if `recovery_bull` is labeled using forward-looking data (e.g., SPY crosses 200d MA *after* the signal date), then signals tagged "recovery" may include hindsight knowledge of subsequent strength. The +8.2pp lift vs base 51.4% (normal_bull) suggests the classifier is isolating **true early-phase momentum**, but operational deployment requires the regime classification to be **real-time computable** without forward peeking.

Operationally, the trader should **wait for live Bull regime classification before activating recovery_bull filters**. If the regime detector flags "recovery_bull" in real-time (e.g., SPY >50d MA, <200d MA, advancing breadth, etc.), then UP_TRI setups get a +8pp edge allocation. If the regime is classified post-hoc, this cell is **research-only** and cannot be traded. The n=972 sample is sufficient for statistical weight if the classification is clean.

**Activation criteria**: Regime detector must fire "recovery_bull" signal in real-time; UP_TRI geometry + sector filters (IT/Health) + wk4 timing. Treat as **high-conviction, narrow-window setup** (2.5% of Bull opportunities).

---

## 4. Bull vs Bear UP_TRI sector ranking

Bull UP_TRI is **led by growth/defensive hybrids**, not pure cyclicals. IT (+4.7pp, n=3015) and Health (+3.4pp, n=853) are top performers—these are **earnings-growth sectors** with defensive characteristics (IT exports, Health demand inelasticity). Bear UP_TRI was led by CapGoods/Auto/Other (defensives + cyclicals recovering from oversold)—a **mean-reversion basket**. The sector divergence confirms the architectural split: Bear UP_TRI = reversion in beaten-down cyclicals; Bull UP_TRI = momentum in quality growth.

FMCG (+1.5pp, n=3425) and Chem (+0.7pp) are mid-tier, showing **defensive participation** in Bull UP_TRI but without explosive lift. Auto (0.0pp) and CapGoods (-0.6pp)—Bear UP_TRI's stars—are **neutral to negative** in Bull UP_TRI. This suggests these sectors *lag* in Bull UP_TRI contexts, likely because Bull regimes pull capital into growth (IT/Health) while cyclicals (Auto/CapGoods) need **valuation compression (Bear setups)** to outperform on mean-reversion.

Bank (-0.5pp, n=6993) underperforms despite large sample size, indicating **sector-timing risk**: Banks may be overextended or facing regulatory/rate headwinds in Bull UP_TRI windows. The sector lift map suggests Bull UP_TRI traders should **overweight IT/Health, neutral FMCG/Chem, underweight Financials/Cyclicals**—the inverse of Bear UP_TRI's cyclical-reversion playbook.

**Implication**: Sector rotation is **regime-dependent at the cell level**. Bull UP_TRI = quality growth leaders; Bear UP_TRI = cyclical mean-reversion. Portfolio construction must flip sector tilts based on regime + triangle geometry.

---

## 5. Production posture for PROVISIONAL Bull UP_TRI cell

**Default behavior: DISABLED with manual override pathway**. No live Bull data exists (n=38,100 lifetime-only), meaning the cell has **zero forward validation**. The base WR is 51.4% (normal_bull, 76% of samples)—only 130bps above coin-flip—with sub-regime edges concentrated in recovery_bull (2.5% of signals, +8.2pp) and healthy_bull (12.5%, +6.3pp). These sub-regimes together cover only **15% of Bull UP_TRI signals**, leaving 85% in normal_bull/late_bull/unknown with marginal-to-negative edges.

**Activation criteria for provisional deployment**: (1) Live Bull regime confirmed for ≥60 days; (2) regime classifier flags `recovery_bull` or `healthy_bull` in real-time; (3) sector filter = IT/Health/Consumer; (4) calendar = wk4; (5) `ema_alignment=bull` + `multi_tf_alignment_score=high`; (6) `higher_highs_intact=False` (broken structure favored). This stacks **all positive filters** to isolate the 15% high-WR sub-regimes. Signals outside these filters are **logged but not traded** until live validation accrues n≥500.

**Risk guardrails**: Max 2% portfolio allocation per signal; max 3 concurrent Bull UP_TRI positions; stop-loss at -1.5% (tighter than base -2% due to provisional status). After 6 months or n=200 live signals, compare live WR to lifetime WR (51.4% base, 58-60% filtered). If live WR undershoots by >3pp, **demote to research-only**. If live WR matches or exceeds, promote to standard rotation with 5% portfolio allocation.

**Operational summary**: Bull UP_TRI is a **conditional, high-filter cell** requiring regime + sub-regime + sector + calendar alignment. Default is off; activation is surgical. Treat as **alpha research** until live data validates the 60% WR claim in recovery/healthy sub-regimes.
