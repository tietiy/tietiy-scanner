# Regime V2 — 5-Scheme Tradeability Validation

**Generated:** 2026-05-14  
**Source:** behavioral_diagnostic_report convergence → retune3 raw-state + Group A bypass is the candidate production tradeability gate.

## Data scope (read first)

- **Signal-level tests** (WR, mean PnL): use the full production signal universe = 372 signals across **Apr 1 – May 13, 2026** (26 trading days). The brain is new — earlier signals do not exist.
- **Regime-level tests** (coverage in stress / stable periods): use the 15-year regime parquet (2011-01-03 → 2026-05-05) since signal-level data is unavailable pre-Apr 2026. Coverage is reported as % of bars where the scheme would have flagged `bear_tradeable=True`.
- **Scheme D (V1 production)** has no historical regime series stored in the V2 module → regime-level rows for Scheme D are marked `—` and noted.

## A. Top-line table (signal-level, Apr 1 – May 13, 2026)

| Scheme | UP_TRI allowed | UP_TRI WR | UP_TRI mean PnL | BULL_PROXY allowed | BULL_PROXY WR | DOWN_TRI allowed | DOWN_TRI WR | Verdict |
|---|---|---|---|---|---|---|---|---|
| A: retune3 smoothed + bypass (current) | 64 (53 res) | 94.3% | 6.58% | 10 (10 res) | 90.0% | 20 (19 res) | 21.1% | **PASS V5 P2** |
| B: retune3 RAW + bypass (recommended) | 119 (105 res) | 88.6% | 5.41% | 19 (19 res) | 78.9% | 41 (38 res) | 26.3% | **PASS V5 P2** |
| C: retune4 smoothed + bypass | 155 (133 res) | 75.9% | 3.87% | 17 (17 res) | 88.2% | 53 (50 res) | 34.0% | **FAIL V5 P2** |
| D: V1 production | 107 (94 res) | 94.7% | 5.99% | 16 (16 res) | 87.5% | 21 (20 res) | 20.0% | **PASS V5 P2** |
| E: risk_off only (raw not BULL/BULL_RECOVERY) | 242 (201 res) | 62.7% | 2.53% | 32 (31 res) | 58.1% | 96 (54 res) | 31.5% | **FAIL V5 P2** |

DOWN_TRI WR is the validating sanity check — should be low in every scheme; high WR would indicate the scheme is letting through bear momentum signals during recoveries.

## B. Per-scheme breakdown

### A: retune3 smoothed + bypass (current)

| Signal | Allowed | Resolved | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| UP_TRI | 64 | 53 | 94.3% | 6.58% | 7.34% |
| BULL_PROXY | 10 | 10 | 90.0% | 9.57% | 10.22% |
| DOWN_TRI | 20 | 19 | 21.1% | -7.19% | -8.54% |

### B: retune3 RAW + bypass (recommended)

| Signal | Allowed | Resolved | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| UP_TRI | 119 | 105 | 88.6% | 5.41% | 5.72% |
| BULL_PROXY | 19 | 19 | 78.9% | 5.64% | 4.74% |
| DOWN_TRI | 41 | 38 | 26.3% | -4.94% | -3.81% |

### C: retune4 smoothed + bypass

| Signal | Allowed | Resolved | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| UP_TRI | 155 | 133 | 75.9% | 3.87% | 4.34% |
| BULL_PROXY | 17 | 17 | 88.2% | 6.86% | 7.11% |
| DOWN_TRI | 53 | 50 | 34.0% | -3.82% | -3.08% |

### D: V1 production

| Signal | Allowed | Resolved | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| UP_TRI | 107 | 94 | 94.7% | 5.99% | 6.28% |
| BULL_PROXY | 16 | 16 | 87.5% | 7.03% | 8.57% |
| DOWN_TRI | 21 | 20 | 20.0% | -7.28% | -8.54% |

### E: risk_off only (raw not BULL/BULL_RECOVERY)

| Signal | Allowed | Resolved | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| UP_TRI | 242 | 201 | 62.7% | 2.53% | 2.41% |
| BULL_PROXY | 32 | 31 | 58.1% | 2.89% | 3.2% |
| DOWN_TRI | 96 | 54 | 31.5% | -3.92% | -3.26% |

## C. Per-period regime-level coverage

Coverage = % of bars in the window where the scheme would flag `bear_tradeable=True`. Stress windows: higher = better recall. Stable windows: lower = better precision.

### Stress windows (higher % desirable)

| Window | bars | A: r3 smooth+bypass | B: r3 RAW+bypass | C: r4 smooth+bypass | D: V1 | E: risk_off |
|---|---|---|---|---|---|---|
| 2020 COVID (Mar-Apr) | 39 | 100.0% | 97.4% | 100.0% | — | 100.0% |
| 2022 correction (Feb-Jun) | 103 | 31.1% | 65.0% | 66.0% | — | 86.4% |
| 2024 H2 corrections (Oct-Dec) | 62 | 43.5% | 43.5% | 43.5% | — | 93.5% |
| Feb-April 2026 (recent) | 59 | 28.8% | 62.7% | 55.9% | — | 100.0% |

### Stable windows (lower % desirable)

| Window | bars | A: r3 smooth+bypass | B: r3 RAW+bypass | C: r4 smooth+bypass | D: V1 | E: risk_off |
|---|---|---|---|---|---|---|
| 2017 stable bull | 248 | 2.4% | 2.0% | 2.4% | — | 26.6% |
| 2019 stable bull | 241 | 17.0% | 19.9% | 17.0% | — | 52.7% |
| 2024 H1 stable bull | 120 | 0.0% | 0.0% | 0.0% | — | 29.2% |

### Lifetime coverage (2011 → 2026, sanity check)

| Scheme | Bars bear-tradeable | % of lifetime |
|---|---|---|
| A: retune3 smoothed + bypass (current) | 728 / 3760 | 19.4% |
| B: retune3 RAW + bypass (recommended) | 898 / 3760 | 23.9% |
| C: retune4 smoothed + bypass | 838 / 3760 | 22.3% |
| D: V1 production | — | — |
| E: risk_off only (raw not BULL/BULL_RECOVERY) | 2035 / 3760 | 54.1% |

## D. Per-criterion verdicts

| Criterion | A | B | C | D | E |
|---|---|---|---|---|---|
| V5 P2 ≥85% on UP_TRI Bear-family | PASS (94.3%) | PASS (88.6%) | FAIL (75.9%) | PASS (94.7%) | FAIL (62.7%) |
| Coverage Feb-Apr 2026 (≥90% desirable) | 28.8% | 62.7% | 55.9% | — | 100.0% |
| Coverage 2020 COVID (≥80% desirable) | 100.0% | 97.4% | 100.0% | — | 100.0% |
| False-positive 2017 stable bull (≤10% desirable) | 2.4% | 2.0% | 2.4% | — | 26.6% |
| False-positive 2024 H1 (≤10% desirable) | 0.0% | 0.0% | 0.0% | — | 29.2% |

## E. Final recommendation

**A_GATE: clean.** Scheme B does not underperform Scheme A on any critical criterion.

**Recommended production candidate: Scheme B — retune3 RAW state + Group A bypass.**

Rationale (based on the tables above):

- V5 P2 UP_TRI Bear-family WR: B=88.6% vs A=94.3%. Both schemes hit V5 P2 ≥85%, but B exposes a much larger n (the cohort is usable for downstream analysis, vs A's tiny smoothed cohort).
- Stress coverage Feb-Apr 2026: B=62.7% vs A=28.8%. B re-captures the BEAR bars that retune3 smoothing was suppressing.
- 2020 COVID: B=97.4% vs A=100.0%.
- Stable bull false-positive (2017): B=2.0% vs A=2.4%.
- Scheme E (risk_off only) is too loose — UP_TRI WR=62.7% (well below V5 P2). Confirms that the bypass clause matters.
- Scheme C (retune4 smoothed + bypass) WR=75.9% — confirms retune4 is a regression.

## F. Limitations

1. Signal-level WR/PnL is restricted to Apr 1 – May 13, 2026. Conclusions about V5 P2 quality come from this slice only.
2. Period-by-period false-positive and coverage testing uses regime-bar coverage, not actual historical signals (which do not exist for those periods).
3. Scheme D (V1) has no regime parquet equivalent; only signal-level comparison is meaningful.
4. Group A bypass uses Nifty 30-day return at the bar (regime-level) or at the signal date (signal-level). The two are consistent.
