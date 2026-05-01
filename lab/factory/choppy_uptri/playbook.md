# Choppy UP_TRI Cell

## Status

- **Investigation date:** 2026-05-02
- **Evidence base:** Phase 5 outputs — 18 VALIDATED + 37 PRELIMINARY = 55 winners; 156 REJECTED. Validation rate 26% among evaluable.
- **Live signal universe:** 91 historical Choppy UP_TRI signals (29W / 54L / 8F → **34.9% baseline WR**, 8 flat excluded).
- **Confidence level:** **MEDIUM**. Filter F1 lifts WR from 35% → 58% (n=20 matched, +23pp lift). Below the 60% target but separation between matched (58%) and skipped (28%) is clean and meaningful.

---

## Setup

What market conditions create the opportunity?

- **Stock regime:** Choppy (oscillating, range-bound)
- **Signal type:** UP_TRI (ascending triangle breakout pattern)
- **Market context:** Live data window (April 2026) is uniformly `nifty_vol_regime=High` — high-volatility Choppy market. The lifetime backtest also flagged `nifty_vol_regime=High` as an anti-feature in Phase 5 outcomes; in this regime, only specific stock-level structural setups survive.

---

## Trigger

What activates this cell?

1. Scanner fires a UP_TRI signal on a stock
2. Stock's regime classification = Choppy
3. Hold horizon recommendation: **D5** (per Phase 3 baselines + Phase 5 finding that all 18 VALIDATED were D5)

---

## Filter Conditions (the unlock)

### Required features (ALL must match) — Filter F1

- `ema_alignment = bull` (price > EMA20 > EMA50 > EMA200)
- `coiled_spring_score = medium` (33-67, indicating moderate compression with bull-aligned trend)

In live data these two features **co-fire** — when ema_alignment is bull, coiled_spring_score tends to be in medium range (single-feature `ema_alignment=bull` produces identical matches).

### Disqualifying features (ANY match → SKIP) — anti-features from Phase 5

These features rejected in Phase 5 differentiator analysis (winners 0%, rejected 6-13%):

- `MACD_histogram_slope = falling` — momentum already deteriorating
- `higher_highs_intact_flag = True` — counter-intuitive but: HHs intact in Choppy regime means the stock is in a continuation setup, not a bounce; Choppy regime kills these
- `ema_alignment = mixed` — implicitly excluded by `ema_alignment=bull` requirement

### Note on `nifty_vol_regime=High`

This appeared as the strongest anti-feature in Phase 5 (0% winners, 19.2% rejected). However, the live April 2026 window has `nifty_vol_regime=High` for **100% of signals** — so this anti-feature would reject all live signals if applied verbatim. The live filter therefore omits it (treats current regime as fixed context) and relies on stock-level features to discriminate within the high-vol environment.

### Confirmation modifiers (optional bonus, smaller sample)

When F1 matches AND none of the anti-features are present (Filter F4), the matched WR climbs to **66.7% (n=6, 4W/2L)**. Sample is too small to call this a tight rule, but for high-conviction trades F4 is the more selective variant.

---

## Evidence

| Metric | F1 (recommended) | F4 (high-precision) |
|---|---|---|
| Required features | ema_bull AND coiled=medium | F1 + no falling MACD + no HHs intact |
| Live universe | 91 | 91 |
| Matched signals | **20** | 6 |
| Match rate | 22.0% | 6.6% |
| Matched W / L | 11 / 8 (+ 1 F) | 4 / 2 |
| **Matched WR (excl F)** | **57.9%** | **66.7%** |
| Skipped WR (excl F) | 28.1% (18W / 46L) | 32.5% (25W / 52L) |
| Lift over 35% baseline | **+23.0pp** | +31.7pp |
| Skipped-vs-matched gap | 29.8pp | 34.2pp |

**F1 verdict**: clean separation, meaningful sample, real edge. Falls short of 60% WR strict threshold but lift +23pp is substantive.
**F4 verdict**: best precision but n=6 too small for high-confidence claim.

### Cross-check vs Phase 5 findings

- Phase 5 found 18 VALIDATED + 37 PRELIMINARY across 91-style live evaluable cohort (deduped)
- Phase 5 baseline: 33% (matches our 34.9% calculation)
- F1's 22% match rate × 91 signals = 20 matches — consistent with Phase 5's 18 VALIDATED + ~5-10 of the 37 PRELIMINARY at the strictest discriminating features

---

## Production Verdict

| Filter outcome | Action | Sizing |
|---|---|---|
| F1 matches AND F4 matches | **TAKE_FULL** | full position (highest conviction) |
| F1 matches but F4 disqualifier triggers | **TAKE_SMALL** | half position |
| F1 doesn't match | **SKIP** | no entry |
| Any anti-feature triggers without F1 match | **SKIP** | no entry |
| Triangle structural KILL (per analyzer KILL barcode) | **REJECT** | filter out at scanner |

---

## Sample Trades (F1 matched, n=20)

20 historical Choppy UP_TRI signals from April 2026 that matched filter F1:

| Symbol | Date | WLF | P&L | Notes |
|---|---|---|---|---|
| ABB.NS | 2026-04-17 | W | +4.71% | ✓ |
| BEL.NS | 2026-04-17 | L | −3.94% | |
| BSE.NS | 2026-04-17 | L | −2.21% | |
| PFC.NS | 2026-04-17 | W | +0.86% | ✓ |
| TATAPOWER.NS | 2026-04-21 | W | +6.67% | ✓ |
| SIEMENS.NS | 2026-04-21 | W | +3.64% | ✓ |
| SHRIRAMFIN.NS | 2026-04-21 | L | −8.10% | worst |
| POWERGRID.NS | 2026-04-21 | W | +0.53% | ✓ |
| NTPC.NS | 2026-04-21 | W | +3.21% | ✓ |
| NAVINFLUOR.NS | 2026-04-21 | W | +4.57% | ✓ |
| MOTHERSON.NS | 2026-04-21 | W | +0.98% | ✓ |
| JINDALSTEL.NS | 2026-04-21 | L | −1.39% | |
| TORNTPOWER.NS | 2026-04-21 | W | +8.87% | best |
| GLENMARK.NS | 2026-04-21 | W | +8.75% | ✓ |
| BANDHANBNK.NS | 2026-04-21 | W | +6.06% | ✓ |
| BAJAJ-AUTO.NS | 2026-04-21 | L | −2.71% | |
| AXISBANK.NS | 2026-04-21 | L | −5.54% | |
| APLAPOLLO.NS | 2026-04-21 | L | −5.83% | |
| LUPIN.NS | 2026-04-21 | F | +0.40% | flat |
| TVSMOTOR.NS | 2026-04-21 | L | −6.12% | |

**11 wins / 8 losses / 1 flat** = 57.9% WR (excluding flat). Average winner +4.4%; average loser −4.6%. R-multiple roughly 1:1.

Sector breakdown of winners: utilities/power (TATAPOWER, NTPC, POWERGRID, TORNTPOWER) + financials (PFC, BANDHANBNK) + capital goods (ABB, SIEMENS) + pharma (GLENMARK) + chemicals (NAVINFLUOR) + auto components (MOTHERSON). Diverse — not sector-conditioned.

---

## Investigation Notes

### What worked

1. **Two features dominate winner-vs-rejected differentiation**: `ema_alignment=bull` (+40pp) and `coiled_spring_score=medium` (+36pp) are clear discriminators in Phase 4-5 lifetime data. Their independence/co-firing was the only surprise.
2. **Structural filters fell out for free**: 100% of VALIDATED were D5 horizon (not D6) and 100% of winners were Phase-4 Tier B (not Tier S/A). The high-tier patterns over-fit.
3. **Anti-features matter equally**: `MACD_histogram_slope=falling`, `higher_highs_intact_flag=True`, `nifty_vol_regime=High` cleanly separate losers.
4. **Filter performance is real**: F1 matched 22% of live signals at 58% WR vs 28% on skipped — 30pp gap is the strongest signal in this analysis.

### What was unexpected

1. **Lifetime test_wr is statistically identical** between VALIDATED (56.3%) and REJECTED (58.1%). REJECTED actually has slightly higher lifetime WR. Phase 4 walk-forward couldn't distinguish them; Phase 5 live did.
2. **Phase-4 Tier S/A all REJECTED in Choppy** — the highest-edge backtest patterns don't survive live. This is a strong signal that Choppy is regime-shifting and high-edge backtest combinations curve-fit historical Choppy.
3. **`higher_highs_intact_flag=True` is an anti-feature** for Choppy UP_TRI bounces. Mechanism: HHs intact = trend continuation setup; Choppy regime kills continuation. The bounce setups (HHs broken, recovering) win.
4. **`ema_alignment=bull` and `coiled_spring_score=medium` are confounded in live** (F1 = F2). Both features point to the same stock state: bullish trend with moderate compression.

### What was disappointing

1. **No filter cleared 60% WR + 10% match-rate strict bar**. Best practical filter (F1) reached 58% WR. F4 hit 67% but only n=6.
2. **High-vol regime context** can't be used as a filter because all live signals are in it. Lifetime backtest's `nifty_vol_regime=High` anti-feature is real but inapplicable to current data.
3. **Live n is small** (91 signals total, 20 F1 matches). Wilson 95% CI on 11/19 (excl flat) is roughly [37%, 76%] — the 58% point estimate has wide bands.
4. **No common 2-feature pairs ≥30%** in winners — patterns are heterogeneous; can't compress to a single canonical feature combo beyond the two anchor features.

### Open questions for future investigation

1. **Does F1 hold up over the next 50-100 Choppy UP_TRI signals?** Quarterly Phase 5 re-run will add signals; track F1 matched WR over time.
2. **Is the "Phase-4 Tier B winners over Tier S losers" finding stable across regimes**, or is it Choppy-specific? Apply same diagnostic to UP_TRI×Bear and UP_TRI×Bull when Bull live data accumulates.
3. **Why is `coiled_spring_score=medium` better than `=high`?** High compression should theoretically produce stronger breakouts, but Choppy regime apparently rewards moderate-compression setups (bounces) over extreme-compression (which become breakdowns in Choppy).
4. **Does Phase 5 evaluate all `ema_alignment=bull` signals as winners?** F1 = F2 in live. Lifetime they were correlated; live they're identical. Why?

### Data gaps that limit confidence

- Live universe is exclusively April 2026 (single regime sub-character)
- 91 signals → 20 F1 matches → wide CIs on per-filter WR
- Can't validate filter on Bull or Bear regime stocks (cohort-specific)
- Phase-4 backtest's `nifty_vol_regime=High` distinction can't be tested in live
- Sector concentration of winners isn't statistically tight (sectors distribute across both winners and losers in matched set)

---

## Lifetime Validation (V1 — added 2026-05-02 evening)

**F1 lift weakened significantly at lifetime scale.**

| Metric | Live (Apr 2026, n=91) | Lifetime (15yr, n=27,072) |
|---|---|---|
| Baseline WR | 34.9% | 52.3% |
| F1 match rate | 22.0% | 28.0% — generalizes |
| F1 matched WR | 57.9% | 54.0% |
| **F1 lift over baseline** | **+23.0pp** | **+1.7pp** |
| F4 lift over baseline | +31.7pp | +3.0pp |

**Verdict downgrade**: confidence MEDIUM → **LOW**. F1 is a regime-shift adaptive filter that exploits hostile Choppy sub-regimes (e.g., April 2026), not a structural Choppy edge. At 15-yr lifetime aggregate, F1 produces near-zero edge.

Recommended production posture:
- Deploy F1 with explicit "regime-shift adaptive" caveat; **TAKE_SMALL only** (not TAKE_FULL) until F1 lift recurs in another hostile-Choppy sub-regime
- Track per-sub-regime in quarterly Phase 5 re-runs
- See `lab/factory/choppy/lifetime_validation_summary.md` for full analysis

---

## Update Log

- **v1 (2026-05-02):** Initial reverse engineering from Phase 1-5 outputs. F1 recommended; n=20 matched, 58% WR, +23pp lift over 35% baseline.
- **v1.1 (2026-05-02 evening):** Lifetime validation surfaced regime-shift dependency. F1 lift collapses to +1.7pp at 15-yr scale. Confidence downgraded MEDIUM → LOW. Production: TAKE_SMALL only.
