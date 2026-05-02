# Bull Regime Synthesis — Cross-Cell Consolidation

**Status:** Bull regime cell investigation complete (3 of 3 cells).
**Date:** 2026-05-03
**Branch:** `backtest-lab`
**Scope:** Consolidate findings from Bull UP_TRI, Bull DOWN_TRI, and
Bull BULL_PROXY cells into unified Bull regime understanding.

Parallel structure to Bear synthesis (`bear/synthesis.md`).

---

## A. Cell summary

| Cell | Status | Confidence | Sessions | Production verdict |
|---|---|---|---|---|
| **Bull UP_TRI** | PROVISIONAL_OFF | MEDIUM (lifetime-validated) | 1 | DEFAULT SKIP; manual enable for `recovery_bull × vol=Med × fvg_low` |
| **Bull DOWN_TRI** | PROVISIONAL_OFF | LOW | 1 | DEFAULT SKIP; manual enable for `late_bull × wk3` |
| **Bull BULL_PROXY** | PROVISIONAL_OFF | LOW | 1 | DEFAULT SKIP; manual enable for `healthy × 20d=high` |

**Headline:** All 3 Bull cells investigated via lifetime-only
methodology (no live Bull data exists during current Lab/scanner
operational window). Each cell produced a provisional filter with
meaningful lifetime evidence; none has live validation. All cells
default to PROVISIONAL_OFF until Bull regime activates live.

---

## B. Cross-cell feature behavior matrix (within Bull regime)

The single most important table for Bull regime architecture: same
feature behaves differently across the 3 cells, and the patterns are
mechanistically explainable.

### Feature × cell direction matrix

| Feature / level | Bull UP_TRI | Bull DOWN_TRI | Bull BULL_PROXY | Pattern |
|---|---|---|---|---|
| `nifty_20d_return_pct=high` | **+5-8pp WIN** (primary anchor) | −1.6pp mild ANTI | **+5.8pp WIN** | Bullish cells share recency anchor; bearish inverts mildly |
| `nifty_200d_return_pct=high` | **−2.1pp ANTI** | +1.5pp mild WIN | **−6.8pp ANTI** | High 200d = late-cycle = anti for bullish, mild winner for shorts |
| `nifty_200d_return_pct=low` | (recovery anchor) | (rare in Bull) | (rare in Bull) | Bull definition excludes deep negative 200d |
| `day_of_month_bucket=wk4` | +2.6pp WIN | **−5.6pp ANTI** | **+13.7pp WIN** | Calendar inversion confirmed (parallel to Bear pattern) |
| `day_of_month_bucket=wk3` | −3.3pp anti | **+8.4pp WIN** | −10.7pp anti | Mid-month winner for bearish DOWN_TRI only |
| `vol_climax_flag=True` | n/a | n/a | **−4.4pp ANTI** | Universal BULL_PROXY anti (Bear was −11.0pp; same direction, weaker magnitude) |
| `inside_bar_flag=True` | −0.1pp NEUTRAL | n/a | +1.4pp NEUTRAL | Bear's compression preference (UP_TRI +4.9pp; BULL_PROXY −9.4pp) does NOT transfer to Bull |
| `nifty_vol_regime=High` | −2.0pp anti | −3.1pp anti | **+13.1pp WIN** | UP_TRI/DOWN_TRI prefer non-high-vol; BULL_PROXY uniquely captures high-vol intra-trend spikes |
| `market_breadth_pct=high` | +3.4pp WIN | n/a | +3.3pp WIN | Both bullish Bull cells share breadth=high winner |
| `52w_high_distance_pct=low` | +6.6pp WIN | n/a | **+8.0pp WIN** | Bull BULL_PROXY INVERTS Bear's far-from-highs preference (Bear +14.4pp on =high) |
| `52w_high_distance_pct=high` | +6.6pp WIN | (top of distribution) | +0.2pp neutral | Bull UP_TRI works near 52w highs (breakout-of-resistance) |

---

## C. Architectural patterns within Bull regime

### Pattern 1: Sub-regime PERFECT 4-cell inversion (UP_TRI vs DOWN_TRI)

The strongest cross-cell architectural finding in the entire Lab
pipeline. Bull's 4 sub-regime cells flip WR direction cleanly between
UP_TRI and DOWN_TRI:

| Sub-regime | Bull UP_TRI WR | Bull DOWN_TRI WR | Inversion |
|---|---|---|---|
| recovery_bull | **60.2% (best)** | 35.7% (worst) | ✓ |
| healthy_bull | 58.4% | 40.5% | ✓ |
| normal_bull | 51.3% | 42.6% | ✓ |
| late_bull | 45.1% (worst) | **53.0% (best)** | ✓ |

UP_TRI's BEST cell is DOWN_TRI's WORST. UP_TRI's WORST is DOWN_TRI's
BEST. Mechanism: late_bull (mid 200d × low breadth = narrowing
leadership topping) is exactly when DOWN_TRI shorts work; recovery_bull
(low 200d × low breadth = early-cycle quality leadership) is exactly
when DOWN_TRI shorts get squeezed.

This is a CLEANER inversion than anything found in Bear regime. Bull
sub-regime gating is the dominant structural feature for these cells.

### Pattern 2: Direction-alignment between bullish cells (UP_TRI vs BULL_PROXY)

Both bullish Bull cells share architecture (3/4 sub-regimes aligned):

| Sub-regime | Bull UP_TRI WR | Bull BULL_PROXY WR | Direction |
|---|---|---|---|
| recovery_bull | 60.2% (best) | 57.4% (best) | ✓ same direction |
| healthy_bull | 58.4% | 53.4% | ✓ same direction |
| normal_bull | 51.3% | 51.5% | technical near-baseline |
| late_bull | 45.1% (worst) | 43.6% (worst) | ✓ same direction |

Both bullish cells prefer recovery > healthy > normal > late.
Direction is shared; magnitude differs (UP_TRI's edge cells are
stronger lifts).

### Pattern 3: Calendar inversion across direction within Bull

| Week | UP_TRI lift | BULL_PROXY lift | DOWN_TRI lift |
|---|---|---|---|
| wk3 | −3.3pp anti | −10.7pp anti | **+8.4pp WIN** |
| wk4 | +2.6pp WIN | **+13.7pp WIN** | −5.6pp anti |

Bullish setups prefer wk4; bearish prefers wk3. Mechanism: month-end
institutional flows favor longs; mid-month flows favor short-side
rotations. Same pattern as Bear (Bear bullish prefers wk4; bearish
prefers wk2 — different mid-month bucket per regime).

### Pattern 4: Universal `vol_climax × BULL_PROXY` anti-feature

Confirmed in 2 of 3 regimes (Bear and Bull):
- Bear BULL_PROXY: −11.0pp anti
- Bull BULL_PROXY: −4.4pp anti (same direction, weaker)

Mechanism: capitulation events break support structure that
BULL_PROXY's reversal mechanism depends on. This is a universal
BULL_PROXY-specific anti-feature.

### Pattern 5: Bull architecturally distinct from Bear (despite shared bullish direction)

Bear UP_TRI's top winner patterns DO NOT transfer to Bull UP_TRI:

| Test | Bear UP_TRI lifetime | In Bull UP_TRI? |
|---|---|---|
| `wk4 × swing_high_count=low` | 63.3% on n=3,374 (+7.6pp) | 54.7% on n=9,284 (only +2.6pp; below qualifying threshold) |
| `breadth=low × ema50_slope=low` | +6.2pp (n=4,555) | 0 matches in Bull (ema50_slope=low rare in Bull) |
| `nifty_60d_return=low × swing_high=low` | +7.5pp | 0 matches in Bull (60d=low rare in Bull) |

**0/3 Bear UP_TRI top patterns qualify in Bull UP_TRI.** Each cell +
regime combination has its own architectural signature.

### Pattern 6: "Recovery_bull" cell — analog to Bear's "warm" zone

Bull UP_TRI's best sub-regime (recovery_bull, 60.2% on n=972) has a
counterintuitive definition: low 200d_return AND low breadth. This
captures Bull regime classified AFTER Bear-to-Bull transition while
lagging indicators (200d) still catching up.

Mechanism parallels Bear UP_TRI's "warm" zone (borderline-cold
sub-regime, live 95% on n=42): both are TRANSITIONAL ZONES with
QUALITY LEADERSHIP. Stocks that emerge first from regime change
exhibit narrow but high-conviction edge.

This may be a universal architectural pattern across regimes —
worth dedicated cross-regime test in future synthesis.

---

## D. Sub-regime distribution across Bull cells

Bull regime sub-regime structure (per BU1 detector — `nifty_200d_return ×
market_breadth`):

```
Bull sub-regime: TRI-MODAL with skewed distribution
  recovery_bull: low 200d AND low breadth
                 ~2.6-3.2% of lifetime (smallest)
                 quality leadership concentrating in early cycle

  healthy_bull:  mid 200d AND high breadth
                 ~11.6-12.5% of lifetime
                 sustained broad uptrend

  normal_bull:   everything else
                 73.0-76.4% of lifetime (largest — bulk basin)
                 baseline-or-near-baseline WR

  late_bull:     mid 200d AND low breadth
                 7.1-10.8% of lifetime
                 narrowing leadership topping
```

**Distribution consistent across all 3 Bull cells** (same regime →
same sub-regime distribution). Sub-regime detector reuse validated
across cells.

Sub-regime distribution comparison to other regimes:
- **Bull**: 76% normal, 23% edges (skewed; bulk normal)
- **Bear**: ~60% normal, 40% edges (evenly distributed)
- **Choppy**: ~70% normal, 30% edges (similar to Bull)

Bull is more stable than Bear (76% normal); Bear regimes spread
signals across cells more.

---

## E. Live-vs-lifetime gap pattern

| Cell | Live WR | Lifetime WR | Gap |
|---|---|---|---|
| Bull UP_TRI | n/a (0 live) | 52.0% | n/a |
| Bull DOWN_TRI | n/a (0 live) | 43.4% | n/a |
| Bull BULL_PROXY | n/a (0 live) | 51.1% | n/a |

**No live-vs-lifetime gap to decompose.** Bull cells are pure
lifetime; calibrated WR equals lifetime baseline directly. No Phase 5
selection bias to remove.

This is a methodological CLEAN STATE: Bull production WR expectations
are set by lifetime evidence alone, not inflated by live cherry-
picking. When Bull regime activates live and Phase 5 produces
winners, expect 20-30pp inflation to follow (parallel to Bear UP_TRI's
+38.9pp pattern).

---

## F. Methodology lessons surfaced from Bull regime

### Lesson 1: Cross-regime patterns DON'T transfer

0/3 Bear UP_TRI top patterns qualify in Bull UP_TRI. Each cell +
regime pair needs its own filter design. Cross-cell inheritance does
not work even within the same signal type across regimes.

**Implication**: future regime work cannot reuse filter rules from
prior regimes. Sub-regime detectors and methodology can be reused
(parallel structure); specific filters cannot.

### Lesson 2: Per-regime sub-regime axes are different but architecturally consistent

| Regime | Primary axis | Secondary axis | Structure |
|---|---|---|---|
| Choppy | vol_percentile | breadth | tri-modal balanced |
| Bear | vol_percentile | nifty_60d_return | tri-modal (hot/warm/cold) |
| Bull | nifty_200d_return | market_breadth | tri-modal SKEWED (recovery/healthy/normal/late) |

Universal: tri-modal structure exists; "two discriminative tails
plus baseline" pattern holds. Regime-specific: axes that define
those tails.

**"Primary axis = regime definition, secondary axis = risk flavor"**
meta-pattern (from Bear synthesis BS1) holds for Bull:
- Bull's primary axis (200d_return) = trend MATURITY (early/mid/late
  cycle)
- Bull's secondary axis (breadth) = participation quality

### Lesson 3: Cell investigations must be done per (signal_type × regime) pair

Bull UP_TRI ≠ Bear UP_TRI architecturally. Different filter anchors,
different sub-regime axes, different sector preferences, different
candle pattern preferences. Both bullish-direction cells, but
fundamentally distinct mechanisms.

### Lesson 4: Lifetime-only methodology is viable and disciplined

When live data is absent (Bull regime not active), the 5-step factory
methodology adapts to 3 steps:
1. Extract + sub-regime detector (BU1 / BD1 / BP1)
2. Differentiator analysis + cross-cell predictions (BU2 / BD2 / BP2)
3. Filter test + verdict + playbook (BU3 / BU4 / BD3 / BD4 / BP3 / BP4)

Bull regime work validated this adapted methodology cleanly across
3 cells. Producing PROVISIONAL_OFF verdict with documented filter
candidates is the appropriate outcome — neither overclaiming nor
under-claiming.

### Lesson 5: PROVISIONAL_OFF is a valid cell verdict

Three cells closed PROVISIONAL_OFF. This is more useful than KILL
(preserves real lifetime structure for future activation) and more
honest than DEPLOY (live data can't yet validate filter robustness).

Production posture: default SKIP, manual enable for shadow testing,
preserve optionality without committing capital.

---

## G. Sonnet 4.5 cross-cell architectural analysis

See [`bull/synthesis_llm_analysis.md`](synthesis_llm_analysis.md) for
the full cross-cell architectural critique generated by Sonnet 4.5
during LS1.

---

## Decision flow

See [`bull/decision_flow.md`](decision_flow.md) for the full unified
production decision flow with sub-regime gating, KILL rules, and
calibrated WR expectations per signal-type × sub-regime.

---

## Update Log

- **v1 (2026-05-03, LS1):** Initial cross-cell consolidation.
  3 Bull cells investigated; all PROVISIONAL_OFF (lifetime-only
  methodology). Architectural patterns identified: sub-regime PERFECT
  inversion (UP_TRI vs DOWN_TRI), bullish direction-alignment (UP_TRI
  + BULL_PROXY share recovery-best/late-worst), calendar inversion
  across direction (wk4 bullish / wk3 bearish), universal
  `vol_climax × BULL_PROXY` anti-feature, recovery_bull as
  transitional-quality cell analog to Bear's warm zone.

  Cross-regime: 0/3 Bear UP_TRI patterns transfer to Bull UP_TRI;
  per-regime axes different but architecturally consistent (tri-modal,
  primary = regime definition, secondary = risk flavor).
