# Choppy DOWN_TRI Cell

## Status

- **Investigation date:** 2026-05-02
- **Cell classification:** **DEFERRED** — data sparsity prevents filter articulation
- **Confidence level:** N/A (filter not articulated)

## Why DEFERRED

This cell cannot produce a production filter from current Lab data because two layers of evidence are insufficient:

### Layer 1 — Phase 5 tier distribution

All 25 Phase-4 surviving Choppy DOWN_TRI combinations land in **WATCH tier** in Phase 5. None are VALIDATED, PRELIMINARY, or REJECTED. The cause: per-combination live signal match counts are below the n=5 PRELIMINARY threshold.

| Phase 5 tier | Count |
|---|---|
| VALIDATED | 0 |
| PRELIMINARY | 0 |
| REJECTED | 0 |
| **WATCH** | **25** |

Without a winners-vs-rejected split in Phase 5 results, the differentiator analysis used in Choppy UP_TRI cell (computing `winners_pct − rejected_pct` per feature-level) is not possible.

### Layer 2 — Live signal sparsity

Live Choppy DOWN_TRI universe in current data window (April 2026):

| Symbol | Date | Outcome | P&L |
|---|---|---|---|
| LUPIN.NS | 2026-04-16 | DAY6_LOSS | −1.35% |
| OIL.NS | 2026-04-17 | DAY6_LOSS | −0.62% |
| ONGC.NS | 2026-04-20 | DAY6_LOSS | −1.11% |

**3 signals, all losses (0/3 = 0% WR).** Below the 8-signal HALT threshold for filter back-testing. No winners exist to validate against.

## What we know from lifetime data

The 25 Phase-4 survivors had mean lifetime test_wr **68.2%** (above baseline of ~52% for DOWN_TRI Choppy). Phase 4 walk-forward identified statistically significant Choppy DOWN_TRI patterns. Examples include features around `52w_high_distance_pct`, `coiled_spring_score`, `ROC_10`, `MACD` momentum tracks, and `day_of_month_bucket=wk3` (week-3 expiry-overhang bias surfaced in Phase 3 INV-013 confirmation).

But none of these patterns matched the 3 live signals (or matched too few to qualify for non-WATCH classification).

## Setup

(Provisional — based on Phase 4 lifetime evidence only, not live-confirmed)

- **Stock regime:** Choppy
- **Signal type:** DOWN_TRI (descending triangle break / short setup)
- **Default horizon recommendation:** D2 (per Phase 3 INV-013: D2 outperforms D6 across all DOWN_TRI cohorts; 16 of 25 Phase-4 survivors are D2)

## Production Verdict (current state)

| Condition | Action |
|---|---|
| DOWN_TRI signal fires in Choppy regime | **TAKE_SMALL or SKIP** |

Until live evidence accumulates:
- Default to **TAKE_SMALL** (half size) on any DOWN_TRI Choppy signal that triggers without obvious red flags
- Default to **SKIP** if conservative
- Monitor outcomes for the next 30+ Choppy DOWN_TRI signals; quarterly Phase 5 re-run will produce filter material

The 3 currently-resolved live signals all lost — small sample, but not encouraging. Trader should treat Choppy DOWN_TRI as an **open research question**, not a confirmed edge.

## What would unlock this cell

- Quarterly Phase 5 re-run: when live Choppy DOWN_TRI count reaches **≥15-20 signals** with at least 5 winners (or clear pattern in losses), differentiator analysis becomes feasible
- Estimated timeline: **6-12 months** of additional live data (April 2026 produced 3 Choppy DOWN_TRI signals in 23 days; rate ~3-5 per month)
- Alternative: re-run Phase 4 at `q=0.10` FDR (more permissive) to surface borderline-significant Choppy DOWN_TRI combinations and re-validate against larger lifetime population

## Cross-INV alignment

INV-013 (DOWN_TRI D2 dominance) said D2 outperforms D6 by 2-4pp WR across regimes in lifetime backtest. Choppy DOWN_TRI lifetime baseline is ~52% at D2 (per Phase 3). Phase 4 Choppy DOWN_TRI×D2 produced 16 surviving patterns (vs 9 at D1). The lifetime D2 dominance is the strongest available signal for default horizon recommendation.

## Investigation Notes

### What we tried

1. Mirrored Choppy UP_TRI cell methodology (extract, compare 4 groups, differentiate, back-test)
2. Hit data sparsity at step 1: no VALIDATED/PRELIMINARY/REJECTED to split
3. Live universe = 3 signals = below filter back-test threshold
4. Documented as DEFERRED rather than forcing a filter that doesn't exist

### What was unexpected

- Phase 4 had 25 Choppy DOWN_TRI survivors with mean lifetime test_wr 68.2% — patterns exist in backtest. But none of these were in the live data window enough times to validate. Phase 4 found patterns; Phase 5 couldn't observe them firing in 23 days of April 2026.
- All 3 live Choppy DOWN_TRI signals lost. Could be: (a) Choppy regime really is hostile to DOWN_TRI shorts in current sub-regime; (b) the 3 live signals matched LOW-quality Phase-4 patterns that didn't qualify for Tier S/A. Likely (a) given uniform losses, but n=3 isn't conclusive.

### What we don't know

- Whether the 25 Phase-4 patterns will validate, reject, or stay WATCH when more live data arrives
- Whether DOWN_TRI×Choppy is structurally dead in current high-vol regime (similar to BULL_PROXY×Choppy finding) or just under-observed
- Whether D2 is genuinely the right horizon or if a finer split (D1 + D2 conditional) would better discriminate

## Comprehensive Lifetime Exploration v2 (added 2026-05-02 night)

L3 combinatorial search across **6,287 lifetime DOWN_TRI×Choppy signals**
unlocked this cell from DEFERRED to **UPGRADABLE** by surfacing a
lifetime-validated filter family that didn't require live-window
discrimination. Authoritative source:
[`../choppy/lifetime/synthesis.md`](../choppy/lifetime/synthesis.md).

### Promoted lifetime pattern (DOWN_TRI×Choppy)

| Tier | Filter | n | WR | Lift |
|---|---|---|---|---|
| **Best lifetime combo** | `market_breadth=medium AND nifty_vol=Medium AND wk3 AND bank_nifty_20d=medium` (effective via 3-feat top) | 1295 | 57.8% | **+11.7pp** |
| **Strong 2-feat anchor** | `market_breadth=medium AND nifty_vol=Medium` | 1727 | 55.2% | +9.1pp |
| Calendar variant | `wk3 × bank_nifty_20d=medium` | 1295 | 57.8% | +11.7pp |
| RSI-confirmed | `RSI=medium × vol=Medium × breadth=medium` | 1508 | 56.1% | +10.0pp |

132 qualifying combos surfaced — robust, not single-pattern fragility.

### L4 stratification surfacings

- **Vol-gating is critical.** `breadth=medium` lift breakdown:
  Low-vol −5.6pp | **Medium-vol +9.1pp** ✓ | High-vol −3.0pp
  Apply only inside `nifty_vol_regime=Medium` cohort.
- **AVOID sectors:** Pharma −4.7pp (catastrophic), Metal −1.8pp, Bank −1.3pp
- **Best sector:** Other +4.1pp
- **Calendar edges:**
  - **wk3 +9.5pp** (n=1718) — strongest weekly bucket
  - **wk4 −7.1pp** (avoid)
  - Friday −6.2pp (avoid)
  - Best month: Feb +16.2pp (n=711) — symmetric inverse of UP_TRI's Feb hostility
  - Worst month: Sep −12.7pp; Mar −10.6pp

### Revised production posture (v2)

Cell is upgraded from **DEFERRED** to **CANDIDATE** based on lifetime
evidence, even though live April-2026 data still produced only 3 signals
(all losses; small n, possibly under-observed sub-regime).

| Filter outcome | Action | Sizing |
|---|---|---|
| `breadth=medium AND vol=Medium AND wk3 AND bank_nifty=medium` AND non-Friday AND sector ∉ {Pharma, Metal} | **TAKE_FULL** | full position (new lifetime-validated) |
| `breadth=medium AND vol=Medium` AND non-Friday AND sector ∉ {Pharma, Metal} | **TAKE_SMALL** | half position |
| sector=Pharma | **SKIP** | structural mismatch (−4.7pp) |
| feat_day_of_week=Fri | **SKIP** | (−6.2pp) |
| feat_day_of_month_bucket=wk4 | **TAKE_SMALL_AT_MOST** | (−7.1pp) |
| No filter match | **SKIP** | unchanged default |

### Confidence delta

| State | v1 | v2 |
|---|---|---|
| Cell classification | DEFERRED | **CANDIDATE** (lifetime-derived filter; awaits live validation) |
| Filter availability | None | TAKE_FULL + TAKE_SMALL tiers |
| Default | TAKE_SMALL or SKIP | SKIP unless filter matches |

### What unlocks PROMOTED status

- Quarterly Phase-5 re-runs accumulate ≥15 live DOWN_TRI×Choppy×breadth=medium×vol=Medium signals
- Live matched WR ≥ 50% on those signals
- At that point: upgrade CANDIDATE → VALIDATED, deploy with full confidence

### What was unexpected

The cell looked dead at v1 (3 live losses, no Phase-5 winners). But the
lifetime data has 6,287 DOWN_TRI×Choppy signals — the cell's prior data
sparsity was an *April-2026 sub-regime* artifact, not a structural void.
The 2-feat combinatorial search bypasses the Phase-5 winners-vs-rejected
split that originally blocked filter articulation.

---

## Update Log

- **v1 (2026-05-02):** Cell classified DEFERRED. 25 Phase-4 survivors all WATCH in Phase 5; live universe of 3 signals (all losses) too sparse for filter articulation. Re-evaluate after next quarterly Phase 5 run.
- **v2 (2026-05-02 night):** L3 lifetime combinatorial search across 6,287 signals surfaced robust filter family (132 qualifying combos). Cell **upgraded DEFERRED → CANDIDATE**. New TAKE_FULL/TAKE_SMALL tiers added based on `breadth=medium × vol=Medium` lifetime pattern. Awaits live validation. See `../choppy/lifetime/synthesis.md`.
