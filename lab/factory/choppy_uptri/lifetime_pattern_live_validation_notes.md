# Choppy UP_TRI — Lifetime Pattern Live Validation (T2)

**Date:** 2026-05-02
**Live universe:** 91 Choppy UP_TRI signals (April 2026)
**Live baseline (n=83 excl flats):** 34.9% WR

## Filters tested

### F1 (cell-derived, live-validated April 2026)
- Definition: `ema_alignment=bull AND coiled_spring_score=medium`
- Lifetime: +1.7pp lift on n=7,593 (WEAKENED at scale)
- **Live: matched n=20 (22%), WR=57.9%, lift +23.0pp**

### L3 strict (lifetime-derived)
- Definition: `market_breadth_pct=medium AND nifty_vol_regime=High AND MACD_signal=bull`
- Lifetime: +10.2pp lift on n=3,318 (62.5% WR)
- **Live: matched n=0 (0%), WR=0.0%, lift -34.9pp**

### L3 relaxed (2-feat anchor only, drop MACD)
- Definition: `market_breadth_pct=medium AND nifty_vol_regime=High`
- Lifetime: +7.9pp lift on n=4,546 (60.1% WR)
- **Live: matched n=0 (0%), WR=0.0%, lift -34.9pp**

## Filter overlap

| Cell | n | WR (excl flat) |
|---|---|---|
| BOTH (L3 ∩ F1) | 0 | 0.0% |
| L3 only (not F1) | 0 | 0.0% |
| F1 only (not L3) | 20 | 57.9% |
| EITHER (L3 ∪ F1) | 20 | 57.9% |
| NEITHER | 71 | 28.1% |

## Sub-regime context (per T1 detector)

All 91 live Choppy UP_TRI signals classify as **stress sub-regime** (100%).

Subtype distribution:
- `stress__high_breadth`: n=91 (100%) — F1 sweet spot
- `stress__med_breadth`:  n=0 (0%) — L3 lifetime sweet spot

## Verdict

**L3_INSUFFICIENT_MATCHES — current live regime (stress__high_breadth dominant) doesn't produce L3 matches; pattern is balance-sub-regime activator awaiting regime shift**

## Production posture decision

The live data is dominantly `stress__high_breadth`, but the L3 lifetime
pattern was derived predominantly from `stress__med_breadth` lifetime
data. The mismatch between live subtype distribution and lifetime
filter-derivation subtype is the central finding.

| Posture option | Recommendation |
|---|---|
| Deploy L3 strict as TAKE_FULL | NO — insufficient live evidence |
| Deploy L3 strict as TAKE_SMALL | NO |
| Hold L3 as "balance-sub-regime activator" | YES — pattern is sub-regime-specific; await regime shift |
| Continue F1 as live filter | YES — F1 lifts +23.0pp on live, this is the dominant live edge |

## Open questions

1. If we get a balance-sub-regime trading day in 2026, will L3 fire and
   match its lifetime expectations?
2. Should the production scanner switch filters per detected sub-regime,
   or run all filters in parallel and pick the highest-confidence?
3. The BOTH cell (L3 ∩ F1) at n=0 is too small to characterize.
   Does the intersection produce stronger edge?
