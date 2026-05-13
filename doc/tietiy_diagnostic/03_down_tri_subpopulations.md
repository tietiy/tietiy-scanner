# 03 — DOWN_TRI Sub-Population Analysis

Source: `output/signal_history.json` (290 records, schema v5, file mtime 2026-05-04, date range 2026-04-01 → 2026-04-29). Loaded via pandas, deduplicated by `id`.

## Sample

- 34 DOWN_TRI rows total (32 DOWN_TRI + 2 DOWN_TRI_SA).
- 23 resolved (outcome ∉ {OPEN, GAP_INVALID}).
- Date range of DOWN_TRI signals: 2026-04-01 → 2026-04-29.

The user's task brief cited "90 signals / −217 P&L" from dashboard. The live file shows 34 records / −148.78 sum PnL. Either the dashboard counts archives + duplicates (the V6 prop_005 shadow rows are mostly stripped after dedup), or it includes signals not in the current truth file. The numbers below are what `output/signal_history.json` says today.

## Overall DOWN_TRI outcome

| Outcome | n |
|---|---:|
| STOP_HIT | 11 |
| DAY6_LOSS | 8 |
| DAY6_WIN | 4 |
| OPEN | 8 |
| GAP_INVALID | 3 |
| **TARGET_HIT** | **0** |

| Metric | Value |
|---|---:|
| Resolved | 23 |
| Σ pnl_pct | −148.78 |
| avg pnl_pct | −6.47 |
| Σ r_multiple | −7.61 |
| avg r_multiple | −0.54 |
| **WR (pnl > 0)** | **17.4%** |

## A. DOWN_TRI × regime

| regime | n | resolved | Σ pnl | avg pnl | WR | avg R |
|---|---:|---:|---:|---:|---:|---:|
| **Bear** | 23 | 23 | **−145.70** | −6.34 | 17.4% | **−0.64** |
| Choppy | 11 | 3 | −3.08 | −1.03 | 0.0% | −0.18 |

98% of DOWN_TRI bleed comes from Bear-regime signals. Eight Choppy DOWN_TRI signals are still OPEN — they were precisely the prop_001 decisive test (LUPIN/OIL/ONGC + others). Three of them resolved as losses; the other eight have not.

## B. DOWN_TRI × sector

Resolved-only:

| sector | n | Σ pnl | avg pnl | WR | avg R |
|---|---:|---:|---:|---:|---:|
| **Bank** | 12 | **−122.27** | −10.19 | **0.0%** | **−0.81** |
| **Energy** | 6 | −27.99 | −4.66 | 0.0% | −0.56 |
| Other | 3 | −4.44 | −2.22 | 0.0% | −0.39 |
| Auto | 4 | 0.00 | (open) | — | — |
| CapGoods | 1 | 0.00 | (open) | — | — |
| IT | 1 | 0.00 | (open) | — | — |
| Pharma | 3 | +0.92 | +0.31 | 66.7% | −0.10 |
| Chem | 4 | +5.00 | +1.67 | 66.7% | +0.07 |

- Bank+DOWN_TRI is exactly the `kill_001` cohort (n=11 in `cohort_health` because one is open). Live evidence: 0/12 WR, −122.27 pnl. The cohort the kill rule blocks already destroyed itself before the rule activated.
- Energy+DOWN_TRI is the next-worst: 0/6 WR, −27.99 pnl, all Bear-regime.
- Pharma + Chem combined: 7 trades, +5.92 pnl, ~67% WR — but n=7 is below the n≥10 threshold for "profitable sub-population" candidacy.

## C. DOWN_TRI × stop width

stop_width_pct = `|stop − entry| / entry × 100`. DOWN_TRI distribution:

| stat | value |
|---|---:|
| count | 32 |
| mean | 10.98% |
| median | 12.16% |
| p25 / p75 | 8.54 / 13.42 |
| min / max | 3.44 / 15.33 |

Correlation `stop_width_pct vs pnl_pct`: −0.36 (wider stop → worse outcome). All-cohort bucketed:

| stop_bucket | n | Σ pnl | avg pnl | WR |
|---|---:|---:|---:|---:|
| 0-4% | 1 | −1.35 | −1.35 | 0% |
| 4-6% | 1 | 0.00 | (open) | — |
| 6-8% | 3 | −1.11 | −1.11 | 0% |
| 8-10% | 7 | −50.34 | −7.19 | 0% |
| 10-12% | 4 | −4.66 | −1.55 | 0% |
| 12-20% | 16 | −91.32 | −7.61 | 33% |

DOWN_TRI stops are all ATR-driven (`pivot_high + 1.0 × ATR`). 3-17% range is purely a function of the stock's ATR scale at signal time. There is no per-stock stop-width override. The negative correlation with outcome partly reflects that high-ATR stocks (typically Bank/Energy) have wider stops AND were the ones in the Apr 6-8 short-squeeze.

## D. DOWN_TRI × score & score components

| score | n | Σ pnl | avg pnl | WR |
|---|---:|---:|---:|---:|
| 5 | 12 | −64.59 | −5.87 | 18% |
| 6 | 17 | −84.19 | −6.48 | 15% |
| 7 | 3 | 0.00 | (open) | — |

Score 6 marginally worse than score 5. **Score is non-monotonic for DOWN_TRI** — adding bonuses doesn't filter for outcome.

By score component:

| component | n_true | Σ pnl true | avg pnl true | WR true |
|---|---:|---:|---:|---:|
| vol_confirm | 15 | −82.46 | −7.50 | 18% |
| sec_leading | 7 | −1.73 | −0.86 | 0% (but mostly open) |
| rs_strong | **0** | — | — | — |
| grade_A | 1 | 0.00 | (open) | — |

- `vol_confirm` slightly HURTS — high-volume DOWN_TRIs lose more on average.
- `rs_strong` was never triggered on any DOWN_TRI (all 32 had `rs_strong=False`). The relative-strength gate is asymmetric: it identifies stocks **outperforming** Nifty (= strong stocks). A "strong stock pivot-high reversal short" doesn't fit the signal's premise.
- `sec_leading` cohort (n=7) is too small to judge.

## E. DOWN_TRI × age

All 32 DOWN_TRI are age=0. (Confirmed: scanner_core only emits age=0 DOWN_TRI.) No age sub-population exists.

## F. DOWN_TRI gap_pct distribution

13 records have `gap_pct` set (others were never validated at 9:27 open).

| stat | value |
|---|---:|
| median | +0.51% |
| 25 / 75 | −0.51 / +0.98 |
| max | +6.84 |

For SHORT signals, **positive gap = adverse**. 7 signals had `gap_pct > 0.5%` (adverse gap). Their combined pnl was only −1.35% — so gap is not the major loss driver. The damage happens during the holding period, not at the open.

## G. DOWN_TRI MFE vs MAE (resolved only)

| Metric | mean | median |
|---|---:|---:|
| mfe_pct | **0.85** | **0.00** |
| mae_pct | 6.07 | 2.97 |

**Median DOWN_TRI MFE = 0.00.** Most trades never even had a single bar of favorable excursion. They start going against immediately and the question is just how far before stop or Day 6.

Distribution of resolved DOWN_TRI by outcome:

| outcome | n | avg r_multiple | avg mfe | avg mae |
|---|---:|---:|---:|---:|
| STOP_HIT | 11 | −0.98 | 0.11 | 7.4 |
| DAY6_LOSS | 8 | −0.31 | 0.45 | 5.2 |
| DAY6_WIN | 4 | +0.09 | 2.50 | 0.7 |

DAY6_WIN events have MFE ~2.5% but the cap is Day 6 close, so the system never realises a larger move. Even the wins are tiny.

## H. Profitable sub-population search

Criteria from spec: n≥10 AND positive total_pnl AND avg_r > +0.3.

Searched cells:

| Cell | n | total_pnl | avg_r | Passes? |
|---|---:|---:|---:|:--:|
| DOWN_TRI × Bear | 23 | −145.70 | −0.64 | ❌ |
| DOWN_TRI × Choppy | 3 (resolved) | −3.08 | −0.18 | ❌ (n too small) |
| DOWN_TRI × Bank | 12 | −122.27 | −0.81 | ❌ |
| DOWN_TRI × Energy | 6 | −27.99 | −0.56 | ❌ (n too small) |
| DOWN_TRI × Pharma | 3 | +0.92 | −0.10 | ❌ (n too small, avg_r not >+0.3) |
| DOWN_TRI × Chem | 4 | +5.00 | +0.07 | ❌ (n too small) |
| DOWN_TRI × score=5 | 12 | −64.59 | (negative) | ❌ |
| DOWN_TRI × score=6 | 17 | −84.19 | (negative) | ❌ |
| DOWN_TRI × vol_confirm=True | 15 | −82.46 | (negative) | ❌ |
| DOWN_TRI × sec_leading=True | 7 | −1.73 | — | ❌ (n too small) |
| DOWN_TRI × rs_strong=True | 0 | — | — | N/A |

**No subset at n≥10 is profitable.**

The closest hint of a useful sub-population is DOWN_TRI × non-Bank/Energy/Bear-regime sectors (Pharma + Chem + Other niches), combined n=10, +1.48 pnl. But:
- Pharma+Chem alone: n=7 wins+losses combined, +5.92 pnl. Below the n≥10 floor.
- The wins here are tiny (max +4.09); the strategy still has no target-hit path.

## Verdict on DOWN_TRI rehabilitatability

**Verdict: KILL** — no profitable sub-population at n≥10 exists; the structural mechanics (no target, ages 0 only, no regime score discrimination) make it geometrically lopsided; the brain layer has implicitly confirmed this by NOT promoting DOWN_TRI to any cohort tier above Candidate.

A defensible alternative is **REHABILITATE_AS_EXIT_SIGNAL_FOR_LONGS** — i.e., when a DOWN_TRI fires, that's evidence to tighten or close existing UP_TRI / BULL_PROXY positions in the same stock/sector. This treats the pattern as information without taking the short trade. But that's a use-case redesign, not a fix to the current DOWN_TRI signal type.

Within the existing "take the trade as posted" framework, **DOWN_TRI should be retired or hard-blocked across all sectors** until a structural redesign (target rule, regime gating, or pattern refinement) gives it a positive-edge path.
