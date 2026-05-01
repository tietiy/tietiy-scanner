# Choppy BULL_PROXY Cell

## Status

- **Investigation date:** 2026-05-02
- **Cell classification:** **KILL** (with documented narrow-exception hypothesis for future)
- **Confidence level:** HIGH for KILL verdict on current scanner output; UNTESTED for compression-variant exception
- **Production verdict:** REJECT all Choppy BULL_PROXY signals from current scanner

## Evidence Base

### Phase 4 + Phase 5 outputs

| Tier | Count | Lifetime test_wr | Edge_pp |
|---|---|---|---|
| VALIDATED | 0 | — | — |
| PRELIMINARY | 0 | — | — |
| REJECTED | 96 | 64.0% | +15.5pp |
| WATCH | 79 | 65.5% | +16.2pp |

**0% validation rate** — none of the 175 Phase-4 backtest survivors validated in live data.

### Live universe (8 signals)

All 8 signals fired in 2026-04-20 → 2026-04-23 (3 trading days). Outcome: **2W / 6L = 25% WR**.

| Symbol | Date | Outcome | P&L |
|---|---|---|---|
| ALKEM.NS | 2026-04-20 | STOP_HIT | −6.33% |
| EICHERMOT.NS | 2026-04-20 | DAY6_LOSS | −1.24% |
| **★INDUSINDBK.NS** | 2026-04-20 | **TARGET_HIT** | **+3.96%** |
| SBILIFE.NS | 2026-04-20 | STOP_HIT | −1.07% |
| SUNDARMFIN.NS | 2026-04-20 | STOP_HIT | −4.24% |
| **★VOLTAS.NS** | 2026-04-20 | **DAY6_WIN** | **+5.36%** |
| MFSL.NS | 2026-04-21 | STOP_HIT | −3.19% |
| HINDZINC.NS | 2026-04-23 | STOP_HIT | −2.99% |

**Critical**: Feature audit shows all 8 signals have **identical feature values**:
- `ema_alignment = mixed` (not bull)
- `coiled_spring_score ≈ 25` (low compression)
- `market_breadth_pct ≈ 0.72-0.75` (high)

The 2 winners (INDUSINDBK, VOLTAS) and 6 losers cannot be separated by any of our 114 features. The win/loss split is feature-blind in current data.

## Why KILL — Mechanism

(Synthesized from differentiator analysis + Claude Sonnet 4.5 interpretation)

BULL_PROXY signals fail in Choppy regime because the backtest captured **momentum-follow-through behavior that doesn't exist in range-bound markets**. The 96 REJECTED patterns share a clear signature:
- `market_breadth_pct=high` in 77% of REJECTED (vs 40% of WATCH)
- `ema20_distance_pct=high` in 41% of REJECTED (vs 4% of WATCH)

These are **momentum-extended setups** — broad market strong, stock already extended. In Trending market regimes these would continue. In Choppy regime, the "continuation" gets choked off by the regime's reverting nature.

The 175 Phase-4 survivors with ~65% backtest WR likely performed well during embedded Trending micro-periods within Choppy windows in the 15-yr backtest — creating a **regime-mismatch illusion** when applied to a uniformly-Choppy live window.

The current scanner is firing exclusively the **high-breadth momentum variant** of BULL_PROXY in Choppy regime. None of the 8 live signals match the compression-coil signature that resembles Choppy UP_TRI winners.

## Production Verdict

| Condition | Action |
|---|---|
| BULL_PROXY signal fires in Choppy regime | **REJECT** |
| Even if signal has high score / Tier S in scanner | REJECT (lifetime tier is misleading) |
| Even if market_breadth_pct = high (looks bullish) | REJECT (this is the kill condition) |

This cell does not produce a TAKE rule. The scanner should explicitly suppress Choppy BULL_PROXY signals at the bridge layer.

## Narrow Exception Hypothesis (UNTESTED — for future research)

The 79 WATCH-tier Phase-4 patterns share a **different feature signature** from the 96 REJECTED:
- `coiled_spring_score=medium` in 29% of WATCH (vs 0% of REJECTED)
- `ema_alignment=bull` in 27% of WATCH (vs 0% of REJECTED)

This signature is **identical to the Choppy UP_TRI cell's winning signature** (F1 filter from UP_TRI cell). Hypothesis: a "compression-coil BULL_PROXY" — bullish EMA stack + medium compression — might survive Choppy regime as a range-breakout play (analogous to UP_TRI bounces) rather than a momentum continuation.

**This hypothesis cannot be tested** with current data because:
1. None of the 8 live BULL_PROXY signals have this signature (all are momentum-extended)
2. Phase 5 didn't observe enough WATCH-cluster matches to validate

If/when scanner produces BULL_PROXY signals matching the WATCH-cluster signature in future quarters:
- Track separately
- Re-evaluate cell verdict if 5+ such signals accumulate with WR ≥50%

## Cross-cell context

Compare to Choppy UP_TRI cell (F1 filter: `ema_alignment=bull AND coiled_spring=medium`):
- F1 produced 58% WR (n=20) in Choppy UP_TRI
- The WATCH-cluster BULL_PROXY signature is **the same pattern type**
- But Choppy BULL_PROXY scanner doesn't produce signals matching this signature in current data window

This suggests the BULL_PROXY signal definition itself favors the momentum-extended subtype rather than compression-coil subtype. Scanner may need a separate "compression BULL_PROXY" detection mode for the narrow exception to surface.

## Investigation Notes

### What we found

1. **96 REJECTED + 79 WATCH cleanly differ on features** — not just sample-size-driven. They are two different pattern subtypes:
   - REJECTED = momentum-extended (high market_breadth, extended above EMA20)
   - WATCH = compression-bullish (medium coiled_spring, bull EMA stack)

2. **All 8 live signals are in the REJECTED archetype** — 100% match the dead pattern signature, 0% match the survivable signature.

3. **The 2 live winners are statistical noise** within the dead pattern, not evidence of a viable filter. Feature-indistinguishable from the 6 losers.

4. **API interpretation aligns with empirical finding**: Choppy regime kills momentum; backtest's edge came from embedded Trending sub-windows.

### What was unexpected

- We expected REJECTED and WATCH to be feature-similar (just sample-size-distinguished). They're actually feature-distinct, suggesting the analyzer might have surfaced a real exception — but live data doesn't include any of the exception type.
- Choppy UP_TRI's winning filter (F1) and Choppy BULL_PROXY's WATCH cluster have IDENTICAL signatures. Either signal type, when filtered for compression+bullish setup, may converge on the same trade — interesting cross-cell finding.

### What we don't know

- Whether the WATCH-cluster compression-coil BULL_PROXY would actually validate if scanner produced more such signals
- Whether INDUSINDBK and VOLTAS won for fundamental reasons (earnings, news) outside our feature space
- Whether the 8-signal sample is regime-transitional (early-Choppy after Bear) vs established Choppy

## Lifetime Validation (V3 — added 2026-05-02 evening)

**KILL verdict CONFIRMED at lifetime scale.**

Tested 8 candidate filters against 1,931 lifetime BULL_PROXY × Choppy signals (50% baseline WR). Best filter: F6 (`ema_bull AND coiled=medium AND market_breadth=high`) at +6.9pp lift on n=286 — MARGINAL but **below the +10pp threshold for filter promotion**.

The compression-coil narrow-exception hypothesis from C2 differentiator analysis does NOT replicate at lifetime — F1 (`ema_bull AND coiled=medium`) lifts only +0.5pp on 776 lifetime matches.

**Sector breakdown** (lifetime, n≥50): Energy 58.1% (+8.5pp), Auto 54.5%, FMCG 54.2% are above-baseline; Infra 39.6% (−10pp) and Other/IT/Pharma deeply negative. Sector-conditional approaches don't clear the +10pp bar either.

**Confidence: HIGH for KILL verdict** — both live and lifetime evidence converge.

See `lab/factory/choppy/lifetime_validation_summary.md` for full analysis.

---

## Update Log

- **v1 (2026-05-02):** Cell classified KILL based on 8 live signals (25% WR) + 0% Phase 5 validation across 96 REJECTED Phase-4 patterns. Production verdict: REJECT all Choppy BULL_PROXY signals. Compression-coil narrow exception documented as future research item.
- **v1.1 (2026-05-02 evening):** Lifetime validation tested KILL verdict against 1,931 signals. No filter beats +10pp threshold; compression-coil hypothesis +0.5pp at scale. KILL verdict CONFIRMED.
