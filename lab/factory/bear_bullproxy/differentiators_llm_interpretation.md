# Bear BULL_PROXY Differentiator Mechanism Analysis

**Date:** 2026-05-02
**Model:** `claude-sonnet-4-5-20250929`

# Bear BULL_PROXY Feature Differentiator Analysis

## 1. Mechanism — What Does Bear BULL_PROXY Capture?

Bear BULL_PROXY fires on support-rejection / reversal candles in Bear regime — a **contrarian bottom-fishing bet**. The signal hypothesis: price tests recent lows, reverses intraday (wick rejection), attracts institutional buying or short-cover interest. In Bear regime, this is fragile; most support tests fail. The 47.3% lifetime WR confirms **slight coin-flip with edge only in specific conditions**.

The top lifetime winner — **nifty_60d_return_pct=low (+17.9pp, 63.4% WR)** — is the smoking gun. BULL_PROXY works when Nifty itself is deeply oversold (60d < -10%), suggesting **macro capitulation exhaustion**. This aligns with short-squeeze / mean-reversion mechanics: when the index is bombed out, individual support bounces get broader participation. Without macro oversold, the signal degrades to 45.5% (anti-feature: nifty_60d=medium, -17.9pp). This is **macro-contingent bottom-fishing**, not local support quality.

Secondary features reinforce volatility-compression setup: **52w_high_distance=high** (+14.4pp), **ROC_10=low** (+9.8pp), **range_compression_60d=high** (+8.5pp). The stock is deeply beaten, compressed, near 52w lows — classic "coiled spring" profile. **vol_climax_flag=False** (+11.0pp) and **inside_bar_flag=False** (+9.4pp) are anti-noise filters: avoid volatility spikes or indecision candles. The setup wants **quiet compression + macro oversold**, then a clean reversal candle.

Anti-features punish mediocrity: **nifty_60d=medium** (-17.9pp), **vol_climax=True** (-11.0pp), **inside_bar=True** (-9.4pp). Without macro capitulation or clean reversal structure, BULL_PROXY is a **falling knife catch** — coin-flip or worse. The signal is not about chart pattern quality; it's about **timing macro exhaustion** when individual bounces get systemic lift.

---

## 2. Cross-Cell vs Bear UP_TRI — Similar Mission, Different Mechanics

**Parallel mission:** Both are bullish setups in Bear regime. **Different entry structures:** Bear UP_TRI is ascending triangle breakout (higher lows, resistance test, breakout pop); Bear BULL_PROXY is support-rejection bounce (test low, reversal candle, mean-reversion). UP_TRI is **continuation/breakout**; BULL_PROXY is **reversal/bounce**.

**Feature overlap is strong but not identical:**

- **nifty_60d_return_pct=low:** UP_TRI +14.1pp (2nd-best), BULL_PROXY +17.9pp (1st). Both demand macro oversold. BULL_PROXY's stronger delta makes sense — reversal plays need deeper capitulation; breakouts can work in milder drawdowns.
- **52w_high_distance=high:** Not in UP_TRI top-8, but present in BULL_PROXY (+14.4pp). BULL_PROXY wants stocks near 52w lows (beaten-down springs); UP_TRI is more agnostic (can break out from mid-range).
- **swing_high_count_20d=low:** UP_TRI's #1 winner (+23.3pp). Not in BULL_PROXY's top-8. UP_TRI wants **low resistance overhead** (clean breakout path); BULL_PROXY doesn't care — it's bouncing off support, not breaking resistance.
- **range_compression_60d=high:** BULL_PROXY +8.5pp, UP_TRI has "coil" features but weaker deltas. Both want compression, but BULL_PROXY emphasizes it more (spring-loading for bounce).

**Verdict:** Same macro dependency (nifty_60d=low), but **different chart structures**. UP_TRI is higher-quality (lifetime 55.7% vs 47.3%) because breakouts have directional bias; BULL_PROXY is lower-quality because reversal calls are harder — most support tests fail. The 8.4pp lifetime gap reflects **setup difficulty**, not just noise.

---

## 3. Cross-Cell vs Bear DOWN_TRI — Inverted Direction, Inverted Features?

Bear DOWN_TRI is bearish continuation (descending triangle breakdown). BULL_PROXY is bullish reversal. Opposite directions. **Feature inversion test:**

- **nifty_60d_return_pct=low:** BULL_PROXY +17.9pp WINNER; DOWN_TRI **-8.5pp ANTI** (DOWN_TRI wants nifty_60d=medium). Perfect inversion. Oversold macro helps bounces, hurts breakdowns.
- **wk2 / wk4 calendar:** DOWN_TRI shows wk2 +15pp WINNER, wk4 -17.5pp ANTI (inverted vs UP_TRI's wk4 winner). BULL_PROXY data missing, but logic says **align with UP_TRI** (wk4 winner) — both are bullish setups, likely benefit from month-end flows or short-cover exhaustion timing. DOWN_TRI's wk2 winner is mid-month momentum dump; BULL_PROXY is anti-momentum reversal, so wk4 (exhaustion timing) makes more sense.
- **vol_climax / inside_bar:** BULL_PROXY anti-features (vol_climax=True -11.0pp, inside_bar=True -9.4pp). DOWN_TRI likely similar (wants clean breakdown, not noise). Both punish indecision, but for opposite reasons: BULL_PROXY wants clean reversal; DOWN_TRI wants clean breakdown.

**Verdict:** Features are **directionally inverted** (nifty_60d especially). This confirms BULL_PROXY and DOWN_TRI are **opposite regime plays** — one bets on exhaustion reversal, one bets on continuation breakdown. BULL_PROXY should align with UP_TRI on calendar (wk4 winner hypothesis), not DOWN_TRI.

---

## 4. Sub-Regime Structure — Simpler Than UP_TRI, Still Hot-Dependent

**Lifetime hot/cold split:** hot (vol > 0.70 AND nifty_60d < -0.10) n=86 (9.7%) WR=63.7%; cold n=805 (90.3%) WR=45.5%. Delta +18.2pp. Simpler than UP_TRI's tri-modal (hot 68.3%, warm 57.3%, cold 53.4%) — BULL_PROXY is **bi-modal: hot vs everything else**.

**Why smaller hot zone?** UP_TRI hot=15.0% of lifetime; BULL_PROXY hot=9.7%. BULL_PROXY's hot definition (vol > 0.70 AND nifty_60d < -0.10) is **stricter on nifty_60d** — it captures only peak capitulation. UP_TRI's hot bucket likely includes milder drawdowns (vol > 0.55 threshold). BULL_PROXY's smaller hot zone reflects **higher macro dependency** — reversal plays need extreme oversold; breakouts can work in moderate stress.

**Live hot/cold equal (85.7% vs 83.3%):** Both sub-regimes perform in live Phase 5. This mirrors UP_TRI's S2 finding (cold acts like hot in live). Hypothesis: **Phase 5 selection bias** — live period is transitional Bear-to-recovery, so "cold" (non-hot) stocks still get systemic lift from early recovery flows. Cold's 83.3% live vs 45.5% lifetime (+37.8pp inflation) is the tell — it's not representative. Live hot's 85.7% vs lifetime 63.7% is +22pp inflation, smaller but still inflated.

**Verdict:** BULL_PROXY is **hot-dependent but less dramatically** than UP_TRI (lifetime +18pp delta vs UP_TRI's +15pp hot-cold delta, similar magnitude). The 9.7% hot scarcity makes it **harder to catch live** — Phase 5 got lucky with 7/13 hot, but normal Bear regime would be ~10% hot rate. Cold's 45.5% lifetime WR is **losing proposition**; hot's 63.7% is edge but rare.

---

## 5. Production Verdict — DEFERRED (Pending Hot-Filter Dev) or KILL?

**The case for DEFERRED:**

- Lifetime hot (n=86, 63.7% WR) is real edge (+18.2pp vs cold). Feature differentials are clean (nifty_60d=low +17.9pp, 52w_high_distance=high +14.4pp). Mechanism is coherent (macro capitulation + compression spring).
- Live 11W/2L (84.6%) is inflated but includes 7 hot (85.7%) + 6 cold (83.3%) — the hot subset is plausibly sustainable (~64% lifetime), cold is noise.
- Top sectors (IT 56.9%, Energy 52.8%, Chem 51.2%, Bank 51.1%) show ~50%+ WR, suggesting **sector lens can add edge** even in cold sub-regime.

**The case for KILL:**

- **0 Phase 5 combinations.** The signal is so thin in normal Bear conditions that even 200 Phase-5-approved combos (out of 162k total) couldn't produce a single valid hot+sector+feature stack. This is a **data desert**.
- Cold lifetime 45.5% WR (90.3% of signals) is **sub-50% garbage**. Hot is only 9.7% of signals — you'll wait months for valid setups.
- Live 13 signals over ~1 week is **unrepresentative spike** (Phase 5 transitional period). Normal Bear regime would yield ~1-2 hot signals/month across 200-stock universe. **Operationally unscalable.**
- The +37.3pp live-lifetime gap is **second-highest inflation** in the system (behind Bear UP_TRI's +38.9pp). This screams **regime-transition artifact**, not sustainable edge.

**Comparison to Bear UP_TRI:** UP_TRI has same Phase-5-zero problem but higher lifetime baseline (55.7% vs 47.3%) and larger hot bucket (15% vs 9.7%). If UP_TRI is DEFERRED (waiting for hot-filter dev), BULL_PROXY is **weaker in every dimension** — lower baseline, smaller hot zone, harder to catch. If UP_TRI is marginal-defer, BULL_PROXY is **sub-marginal**.

**Honest verdict: KILL, with narrow DEFERRED path.**

- **KILL rationale:** 0 Phase 5 combos + 90% of signals are losing (cold 45.5%) + hot zone is 9.7% scarce + live inflation is extreme (+37pp). Without a **working hot-filter + sector overlay**, this is a coin-flip signal that fires once a month. Not worth production slot.
- **DEFERRED path (conditional):** If you can build a **strict hot-regime filter** (vol > 0.70 + nifty_60d < -0.10, enforced at entry) + **sector whitelist** (IT/Energy/Chem/Bank only, killing Other/CapGoods/FMCG), you might salvage 64% WR on ~10-15 annual setups. But this requires **manual regime override** (auto-shutoff in cold Bear) and **accept low signal frequency**. If Bear UP_TRI gets priority (higher baseline, larger hot zone), BULL_PROXY is **second-tier defer** — build UP_TRI hot-filter first, then revisit BULL_PROXY if UP_TRI succeeds.

**Final call:** **KILL** unless you commit to hot-filter infra (then DEFERRED behind Bear UP_TRI). The 11W/2L live is a **mirage** — Phase 5 bought you a rare hot-regime cluster + transitional lift. Lifetime 47.3% + 0 Phase 5 combos = **no production-ready edge**. If you deploy raw, you're trading a coin
