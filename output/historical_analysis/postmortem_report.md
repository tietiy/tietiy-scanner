# 15-Year Postmortem — Three Core Detectors

**Generated:** 2026-05-14  
**Universe:** 188 F&O stocks (186 with usable 15-year history; LTIM delisted, TMPV too few bars).  
**Date range:** 2012-01-06 → 2026-05-06  
**Total signals replayed:** 102,654  
**Method:** Re-ran `scanner.scanner_core.detect_signals` logic at every scan-day across 15 years. Entry on next-day open, 6-day forward simulation, R:R 2:1 target.

**Conventions:** WR = `(pnl_pct > 0) / resolved`. Resolved = TARGET_HIT + STOP_HIT + DAY6_EXIT. GAP_INVALID excluded. Mean PnL is across resolved.

---

## Executive Summary — 5 most surprising findings

1. **UP_TRI × Bear regime** on full 15-year data: WR=52.2%, n=13074. Compare to the famous 94.7% from the 2026 slice (Apr 1 – May 13). **Does NOT hold** — the recent slice was a fluke.

2. **Raw detector ranking** (no filtering): BULL_PROXY=58.1% > others. Worst is DOWN_TRI=47.4%.

3. **Score discrimination**: UP_TRI score-bucket WR spread = 3.2 pp. Score is mostly noise.

4. **Deep-drawdown UP_TRI**: ret_30d<-10% cohort WR=61.4% on n=1328. This is the Group A capitulation pattern.

5. **Best sector cohort**: BULL_PROXY × Choppy × Energy → WR=66.5% on n=200.



## A. Raw detector performance

| Detector | Raw n | Resolved | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| UP_TRI | 75,352 | 75,279 | 49.5% | +0.25% | -0.04% |
| DOWN_TRI | 18,709 | 18,705 | 47.4% | -0.42% | -0.27% |
| BULL_PROXY | 8,593 | 8,568 | 58.1% | +1.22% | +0.90% |

## B. By year

WR for each detector by year. Cells show `wr% (n)`.

| Year | UP_TRI WR (n) | DOWN_TRI WR (n) | BULL_PROXY WR (n) |
|---|---|---|---|
| 2012 | 55.3% (4396) | 43.7% (1140) | 62.3% (467) |
| 2013 | 49.6% (4548) | 50.5% (1193) | 54.0% (439) |
| 2014 | 54.1% (4300) | 43.7% (1186) | 59.2% (730) |
| 2015 | 43.5% (5321) | 50.3% (1190) | 53.7% (508) |
| 2016 | 49.6% (4468) | 45.1% (1191) | 49.4% (474) |
| 2017 | 53.2% (5046) | 43.1% (1187) | 63.3% (711) |
| 2018 | 48.6% (5263) | 57.4% (1223) | 53.2% (427) |
| 2019 | 49.4% (5191) | 51.1% (1368) | 57.7% (463) |
| 2020 | 54.9% (4983) | 50.8% (1327) | 65.8% (573) |
| 2021 | 44.3% (5866) | 41.4% (1484) | 56.9% (882) |
| 2022 | 50.9% (5742) | 50.1% (1376) | 54.1% (540) |
| 2023 | 53.6% (5724) | 42.9% (1321) | 61.4% (707) |
| 2024 | 45.8% (6293) | 44.2% (1497) | 61.5% (950) |
| 2025 | 45.8% (6293) | 43.9% (1535) | 55.1% (506) |
| 2026 | 45.9% (1845) | 64.3% (487) | 53.4% (191) |


**Years where any detector dropped below 50% WR (18):**

- 2012 DOWN_TRI: 43.7% n=1140
- 2013 UP_TRI: 49.6% n=4548
- 2014 DOWN_TRI: 43.7% n=1186
- 2015 UP_TRI: 43.5% n=5321
- 2016 BULL_PROXY: 49.4% n=474
- 2016 DOWN_TRI: 45.1% n=1191
- 2016 UP_TRI: 49.6% n=4468
- 2017 DOWN_TRI: 43.1% n=1187
- 2018 UP_TRI: 48.6% n=5263
- 2019 UP_TRI: 49.4% n=5191
- 2021 DOWN_TRI: 41.4% n=1484
- 2021 UP_TRI: 44.3% n=5866
- 2023 DOWN_TRI: 42.9% n=1321
- 2024 DOWN_TRI: 44.2% n=1497
- 2024 UP_TRI: 45.8% n=6293


## C. By V1 regime

| Detector | Regime | n | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| BULL_PROXY | Bear | 1,084 | 52.8% | +0.62% | +0.29% |
| BULL_PROXY | Bull | 4,721 | 59.8% | +1.43% | +1.04% |
| BULL_PROXY | Choppy | 2,763 | 57.3% | +1.11% | +0.81% |
| DOWN_TRI | Bear | 3,084 | 48.3% | -0.11% | -0.14% |
| DOWN_TRI | Bull | 9,642 | 46.8% | -0.58% | -0.35% |
| DOWN_TRI | Choppy | 5,979 | 47.8% | -0.33% | -0.20% |
| UP_TRI | Bear | 13,074 | 52.2% | +0.65% | +0.26% |
| UP_TRI | Bull | 36,678 | 48.7% | +0.19% | -0.13% |
| UP_TRI | Choppy | 25,527 | 49.4% | +0.13% | -0.04% |

**Key checks:**
- UP_TRI × Bear (the famous 94.7% on 2026 slice): WR=52.2% on n=13074
- DOWN_TRI × Bull: WR=46.8% on n=9642

## D. By score bucket

| Detector | Score | n | WR | Mean PnL |
|---|---|---|---|---|
| BULL_PROXY | 0-3 | 2,570 | 55.8% | +1.02% |
| BULL_PROXY | 4-5 | 5,637 | 59.3% | +1.33% |
| BULL_PROXY | 6-7 | 361 | 56.2% | +1.01% |
| DOWN_TRI | 4-5 | 9,711 | 47.4% | -0.36% |
| DOWN_TRI | 6-7 | 8,930 | 47.4% | -0.49% |
| DOWN_TRI | 8-10 | 64 | 46.9% | -0.79% |
| UP_TRI | 0-3 | 35,452 | 48.5% | +0.15% |
| UP_TRI | 4-5 | 28,863 | 50.0% | +0.28% |
| UP_TRI | 6-7 | 10,424 | 51.7% | +0.52% |
| UP_TRI | 8-10 | 540 | 51.7% | +0.46% |

## E. By age

| Detector | Age | n | WR | Mean PnL |
|---|---|---|---|---|
| BULL_PROXY | 0 | 4,318 | 59.1% | +1.29% |
| BULL_PROXY | 1 | 4,250 | 57.1% | +1.16% |
| DOWN_TRI | 0 | 18,705 | 47.4% | -0.42% |
| UP_TRI | 0 | 18,872 | 50.6% | +0.34% |
| UP_TRI | 1 | 18,851 | 50.3% | +0.32% |
| UP_TRI | 2 | 18,799 | 49.1% | +0.22% |
| UP_TRI | 3 | 18,757 | 48.1% | +0.14% |

## F. By sector (top 12 by n per detector)


### UP_TRI
| Sector | n | WR | Mean PnL |
|---|---|---|---|
| Bank | 13,859 | 48.9% | +0.20% |
| Energy | 7,416 | 47.5% | +0.11% |
| FMCG | 6,898 | 51.2% | +0.34% |
| Pharma | 6,580 | 48.8% | +0.19% |
| Chem | 6,080 | 50.0% | +0.38% |
| Metal | 5,946 | 49.3% | +0.35% |
| Auto | 5,746 | 50.7% | +0.33% |
| Infra | 5,618 | 49.5% | +0.11% |
| IT | 5,401 | 52.6% | +0.39% |
| CapGoods | 4,906 | 49.7% | +0.39% |
| Other | 4,700 | 47.6% | +0.09% |
| Health | 1,580 | 49.4% | +0.22% |

### DOWN_TRI
| Sector | n | WR | Mean PnL |
|---|---|---|---|
| Bank | 3,463 | 48.0% | -0.25% |
| Energy | 1,744 | 46.7% | -0.41% |
| FMCG | 1,726 | 48.6% | -0.33% |
| Pharma | 1,613 | 48.0% | -0.20% |
| Chem | 1,589 | 46.6% | -0.57% |
| Metal | 1,451 | 46.7% | -0.60% |
| Auto | 1,416 | 44.1% | -0.66% |
| IT | 1,382 | 46.0% | -0.48% |
| Infra | 1,369 | 47.7% | -0.59% |
| CapGoods | 1,239 | 47.4% | -0.54% |
| Other | 1,184 | 49.2% | -0.33% |
| Health | 401 | 50.1% | -0.34% |

### BULL_PROXY
| Sector | n | WR | Mean PnL |
|---|---|---|---|
| Bank | 1,503 | 56.2% | +0.97% |
| FMCG | 929 | 59.3% | +1.26% |
| Pharma | 840 | 60.0% | +1.24% |
| Chem | 779 | 58.7% | +1.18% |
| Auto | 769 | 58.6% | +1.24% |
| Infra | 717 | 54.7% | +0.76% |
| Energy | 665 | 63.0% | +1.63% |
| IT | 659 | 59.5% | +1.22% |
| CapGoods | 512 | 57.6% | +1.34% |
| Metal | 505 | 56.8% | +1.38% |
| Other | 444 | 56.8% | +1.77% |
| Health | 179 | 58.1% | +1.36% |


**Potential BOOST candidates (sector × detector, n≥100, WR>60%):**

- BULL_PROXY × Energy: WR=63.0% n=665 mean_pnl=+1.63%

## G. By grade

| Detector | Grade | n | WR | Mean PnL |
|---|---|---|---|---|
| BULL_PROXY | A | 541 | 59.1% | +1.37% |
| BULL_PROXY | B | 8,027 | 58.1% | +1.21% |
| DOWN_TRI | A | 1,352 | 47.1% | -0.56% |
| DOWN_TRI | B | 17,353 | 47.4% | -0.41% |
| UP_TRI | A | 5,492 | 51.4% | +0.27% |
| UP_TRI | B | 69,787 | 49.4% | +0.25% |

## H. By vol_confirm

| Detector | vol_confirm | n | WR | Mean PnL |
|---|---|---|---|---|
| BULL_PROXY | False | 6,626 | 58.7% | +1.25% |
| BULL_PROXY | True | 1,942 | 56.2% | +1.11% |
| DOWN_TRI | False | 15,095 | 47.3% | -0.42% |
| DOWN_TRI | True | 3,610 | 47.7% | -0.43% |
| UP_TRI | False | 57,113 | 50.0% | +0.29% |
| UP_TRI | True | 18,166 | 47.9% | +0.14% |

## I. By rs_q

| Detector | rs_q | n | WR | Mean PnL |
|---|---|---|---|---|
| BULL_PROXY | Neutral | 3,847 | 58.2% | +1.18% |
| BULL_PROXY | Strong | 2,845 | 58.4% | +1.26% |
| BULL_PROXY | Weak | 1,876 | 57.6% | +1.26% |
| DOWN_TRI | Neutral | 7,630 | 47.3% | -0.36% |
| DOWN_TRI | Strong | 5,529 | 47.5% | -0.46% |
| DOWN_TRI | Weak | 5,546 | 47.3% | -0.47% |
| UP_TRI | Neutral | 29,260 | 49.6% | +0.23% |
| UP_TRI | Strong | 21,409 | 50.1% | +0.26% |
| UP_TRI | Weak | 24,610 | 48.9% | +0.27% |

## J. By sec_mom

**Limitation:** sec_mom was computed as 'Neutral' for every historical signal (sector momentum series not reconstructed). All rows below will be 'Neutral'; this slice has no variation in this run.

| Detector | sec_mom | n | WR | Mean PnL |
|---|---|---|---|---|
| BULL_PROXY | Neutral | 8,568 | 58.1% | +1.22% |
| DOWN_TRI | Neutral | 18,705 | 47.4% | -0.42% |
| UP_TRI | Neutral | 75,279 | 49.5% | +0.25% |

## K. Score × Regime interaction

Score bucket WR within each regime. The interesting question: does score keep adding edge AFTER regime is known?

| Detector | Regime | Score | n | WR | Mean PnL |
|---|---|---|---|---|---|
| BULL_PROXY | Bear | 0-3 | 609 | 51.4% | +0.51% |
| BULL_PROXY | Bear | 4-5 | 471 | 54.1% | +0.72% |
| BULL_PROXY | Bear | 6-7 | 4 | 100.0% | +4.10% |
| BULL_PROXY | Bull | 0-3 | 1,320 | 56.8% | +1.13% |
| BULL_PROXY | Bull | 4-5 | 3,229 | 61.0% | +1.54% |
| BULL_PROXY | Bull | 6-7 | 172 | 61.0% | +1.58% |
| BULL_PROXY | Choppy | 0-3 | 641 | 57.9% | +1.29% |
| BULL_PROXY | Choppy | 4-5 | 1,937 | 57.8% | +1.12% |
| BULL_PROXY | Choppy | 6-7 | 185 | 50.8% | +0.42% |
| DOWN_TRI | Bear | 4-5 | 1,300 | 48.3% | +0.08% |
| DOWN_TRI | Bear | 6-7 | 1,769 | 48.3% | -0.24% |
| DOWN_TRI | Bear | 8-10 | 15 | 53.3% | -1.74% |
| DOWN_TRI | Bull | 4-5 | 5,401 | 47.3% | -0.50% |
| DOWN_TRI | Bull | 6-7 | 4,214 | 46.2% | -0.68% |
| DOWN_TRI | Bull | 8-10 | 27 | 37.0% | -1.10% |
| DOWN_TRI | Choppy | 4-5 | 3,010 | 47.2% | -0.31% |
| DOWN_TRI | Choppy | 6-7 | 2,947 | 48.5% | -0.35% |
| DOWN_TRI | Choppy | 8-10 | 22 | 54.5% | +0.24% |
| UP_TRI | Bear | 0-3 | 2,835 | 48.7% | +0.42% |
| UP_TRI | Bear | 4-5 | 4,871 | 51.4% | +0.56% |
| UP_TRI | Bear | 6-7 | 4,873 | 55.2% | +0.89% |
| UP_TRI | Bear | 8-10 | 495 | 50.9% | +0.48% |
| UP_TRI | Bull | 0-3 | 16,476 | 47.9% | +0.14% |
| UP_TRI | Bull | 4-5 | 15,359 | 49.5% | +0.24% |
| UP_TRI | Bull | 6-7 | 4,798 | 48.5% | +0.22% |
| UP_TRI | Bull | 8-10 | 45 | 60.0% | +0.21% |
| UP_TRI | Choppy | 0-3 | 16,141 | 49.1% | +0.11% |
| UP_TRI | Choppy | 4-5 | 8,633 | 49.9% | +0.19% |
| UP_TRI | Choppy | 6-7 | 753 | 49.4% | -0.01% |

## L. Drawdown cohorts (ret_30d_prior of Nifty at signal date)

| Detector | DD bucket | n | WR | Mean PnL | Median PnL |
|---|---|---|---|---|---|
| BULL_PROXY | -10..-5% | 470 | 51.9% | +0.51% | +0.15% |
| BULL_PROXY | -5..0% | 2,267 | 56.6% | +0.93% | +0.72% |
| BULL_PROXY | 0..+5% | 3,717 | 58.4% | +1.36% | +0.90% |
| BULL_PROXY | <-10% | 63 | 63.5% | +2.62% | +3.74% |
| BULL_PROXY | >+5% | 2,051 | 60.7% | +1.42% | +1.17% |
| DOWN_TRI | -10..-5% | 1,439 | 45.3% | -0.27% | -0.46% |
| DOWN_TRI | -5..0% | 4,860 | 48.9% | -0.25% | -0.09% |
| DOWN_TRI | 0..+5% | 7,667 | 47.3% | -0.46% | -0.29% |
| DOWN_TRI | <-10% | 218 | 50.9% | +0.82% | +0.18% |
| DOWN_TRI | >+5% | 4,521 | 46.3% | -0.66% | -0.37% |
| UP_TRI | -10..-5% | 5,153 | 49.6% | +0.26% | -0.03% |
| UP_TRI | -5..0% | 20,255 | 50.3% | +0.22% | +0.04% |
| UP_TRI | 0..+5% | 31,977 | 48.1% | +0.06% | -0.17% |
| UP_TRI | <-10% | 1,328 | 61.4% | +2.86% | +2.04% |
| UP_TRI | >+5% | 16,566 | 50.3% | +0.46% | +0.04% |

## M. Back-to-back signals (≤5 trading days from prior of same type)

| Detector | Cohort | n | WR | Mean PnL |
|---|---|---|---|---|
| UP_TRI | back_to_back (≤5d) | 56,598 | 49.2% | +0.22% |
| UP_TRI | solo (>5d gap or first) | 18,681 | 50.7% | +0.35% |
| DOWN_TRI | back_to_back (≤5d) | 231 | 44.6% | -0.54% |
| DOWN_TRI | solo (>5d gap or first) | 18,474 | 47.4% | -0.42% |
| BULL_PROXY | back_to_back (≤5d) | 4,247 | 57.1% | +1.15% |
| BULL_PROXY | solo (>5d gap or first) | 4,321 | 59.2% | +1.29% |

## N. Surprises / outliers (signal × regime × sector, n≥200)

### Top 20 best WR cohorts

| Detector | Regime | Sector | n | WR | Mean PnL |
|---|---|---|---|---|---|
| BULL_PROXY | Choppy | Energy | 200 | 66.5% | +1.88% |
| BULL_PROXY | Bull | Pharma | 429 | 65.5% | +1.67% |
| BULL_PROXY | Choppy | Chem | 239 | 64.0% | +1.57% |
| BULL_PROXY | Bull | IT | 346 | 63.6% | +1.68% |
| BULL_PROXY | Bull | FMCG | 500 | 62.2% | +1.51% |
| BULL_PROXY | Bull | Energy | 379 | 61.7% | +1.42% |
| BULL_PROXY | Bull | Other | 257 | 60.7% | +2.13% |
| BULL_PROXY | Bull | CapGoods | 246 | 60.6% | +1.41% |
| BULL_PROXY | Choppy | Auto | 221 | 59.7% | +1.31% |
| BULL_PROXY | Bull | Auto | 473 | 59.2% | +1.36% |
| BULL_PROXY | Bull | Infra | 408 | 58.8% | +1.36% |
| BULL_PROXY | Choppy | FMCG | 310 | 58.7% | +1.14% |
| UP_TRI | Bear | Auto | 934 | 56.9% | +1.33% |
| BULL_PROXY | Bull | Chem | 433 | 56.8% | +1.20% |
| BULL_PROXY | Bull | Metal | 310 | 56.8% | +1.50% |
| BULL_PROXY | Bull | Bank | 833 | 56.7% | +1.06% |
| DOWN_TRI | Bear | Pharma | 280 | 56.1% | +0.61% |
| BULL_PROXY | Choppy | Bank | 492 | 55.7% | +0.87% |
| UP_TRI | Bear | Chem | 1,085 | 55.4% | +0.79% |
| UP_TRI | Bear | Metal | 1,082 | 55.1% | +1.01% |

### Top 20 worst WR cohorts

| Detector | Regime | Sector | n | WR | Mean PnL |
|---|---|---|---|---|---|
| DOWN_TRI | Bear | Metal | 257 | 41.6% | -1.25% |
| DOWN_TRI | Bear | Auto | 231 | 43.3% | -0.71% |
| DOWN_TRI | Bull | Auto | 729 | 43.3% | -0.75% |
| DOWN_TRI | Choppy | Pharma | 509 | 43.8% | -0.42% |
| DOWN_TRI | Bear | Energy | 284 | 44.4% | -0.61% |
| DOWN_TRI | Bull | Other | 589 | 45.2% | -0.73% |
| DOWN_TRI | Choppy | IT | 451 | 45.2% | -0.71% |
| DOWN_TRI | Choppy | Metal | 417 | 45.3% | -0.58% |
| DOWN_TRI | Bull | IT | 697 | 45.5% | -0.66% |
| DOWN_TRI | Bull | Infra | 706 | 45.5% | -0.92% |
| DOWN_TRI | Choppy | Auto | 456 | 45.8% | -0.48% |
| UP_TRI | Bull | Energy | 3,651 | 45.8% | +0.01% |
| DOWN_TRI | Bull | FMCG | 898 | 45.9% | -0.76% |
| UP_TRI | Bear | Health | 272 | 46.0% | -0.32% |
| UP_TRI | Bull | Other | 2,240 | 46.2% | +0.05% |
| DOWN_TRI | Bear | Chem | 267 | 46.4% | -0.66% |
| DOWN_TRI | Bull | Chem | 850 | 46.4% | -0.66% |
| UP_TRI | Bull | CapGoods | 2,378 | 46.5% | +0.10% |
| DOWN_TRI | Bull | Energy | 919 | 46.6% | -0.57% |
| DOWN_TRI | Bear | Bank | 564 | 47.0% | +0.09% |

## O. Volatility regime (Nifty 5-day realized vol quintiles)

| Detector | Vol regime | n | WR | Mean PnL |
|---|---|---|---|---|
| BULL_PROXY | calm | 1,655 | 55.8% | +1.06% |
| BULL_PROXY | mid | 5,371 | 57.6% | +1.14% |
| BULL_PROXY | volatile | 1,542 | 62.6% | +1.68% |
| DOWN_TRI | calm | 3,873 | 48.9% | -0.34% |
| DOWN_TRI | mid | 11,407 | 47.8% | -0.39% |
| DOWN_TRI | volatile | 3,425 | 44.3% | -0.61% |
| UP_TRI | calm | 16,915 | 48.7% | +0.16% |
| UP_TRI | mid | 47,802 | 48.8% | +0.14% |
| UP_TRI | volatile | 10,562 | 54.3% | +0.92% |

## P. Calendar effects

### Day of week

| Detector | DoW | n | WR | Mean PnL |
|---|---|---|---|---|
| UP_TRI | Mon | 14,810 | 49.5% | +0.21% |
| UP_TRI | Tue | 15,205 | 51.0% | +0.37% |
| UP_TRI | Wed | 15,170 | 49.2% | +0.24% |
| UP_TRI | Thu | 15,413 | 48.5% | +0.17% |
| UP_TRI | Fri | 14,563 | 49.3% | +0.24% |
| DOWN_TRI | Mon | 3,928 | 48.0% | -0.38% |
| DOWN_TRI | Tue | 3,763 | 48.0% | -0.35% |
| DOWN_TRI | Wed | 3,785 | 47.9% | -0.28% |
| DOWN_TRI | Thu | 3,564 | 48.3% | -0.40% |
| DOWN_TRI | Fri | 3,658 | 44.5% | -0.71% |
| BULL_PROXY | Mon | 1,810 | 57.6% | +1.11% |
| BULL_PROXY | Tue | 1,857 | 59.1% | +1.33% |
| BULL_PROXY | Wed | 1,675 | 56.8% | +1.04% |
| BULL_PROXY | Thu | 1,643 | 56.7% | +1.24% |
| BULL_PROXY | Fri | 1,580 | 60.4% | +1.40% |

### Month

| Detector | Month | n | WR | Mean PnL |
|---|---|---|---|---|
| UP_TRI | 1 | 6,866 | 48.3% | +0.12% |
| UP_TRI | 2 | 6,812 | 43.6% | -0.42% |
| UP_TRI | 3 | 5,971 | 54.0% | +0.73% |
| UP_TRI | 4 | 7,032 | 49.4% | +0.24% |
| UP_TRI | 5 | 5,880 | 50.4% | +0.25% |
| UP_TRI | 6 | 5,901 | 52.6% | +0.57% |
| UP_TRI | 7 | 6,453 | 50.5% | +0.19% |
| UP_TRI | 8 | 6,017 | 50.5% | +0.50% |
| UP_TRI | 9 | 5,831 | 50.1% | +0.54% |
| UP_TRI | 10 | 6,343 | 54.2% | +0.83% |
| UP_TRI | 11 | 6,058 | 48.2% | +0.01% |
| UP_TRI | 12 | 6,115 | 43.5% | -0.41% |
| DOWN_TRI | 1 | 1,726 | 53.4% | +0.22% |
| DOWN_TRI | 2 | 1,531 | 55.5% | +0.44% |
| DOWN_TRI | 3 | 1,491 | 50.8% | +0.02% |
| DOWN_TRI | 4 | 1,316 | 45.2% | -0.80% |
| DOWN_TRI | 5 | 1,678 | 45.6% | -0.70% |
| DOWN_TRI | 6 | 1,669 | 43.6% | -0.94% |
| DOWN_TRI | 7 | 1,514 | 52.8% | +0.17% |
| DOWN_TRI | 8 | 1,490 | 47.2% | -0.40% |
| DOWN_TRI | 9 | 1,545 | 47.2% | -0.33% |
| DOWN_TRI | 10 | 1,541 | 44.6% | -0.70% |
| DOWN_TRI | 11 | 1,548 | 42.1% | -0.87% |
| DOWN_TRI | 12 | 1,656 | 40.7% | -1.14% |
| BULL_PROXY | 1 | 665 | 56.4% | +1.33% |
| BULL_PROXY | 2 | 747 | 51.0% | +0.60% |
| BULL_PROXY | 3 | 637 | 59.0% | +1.14% |
| BULL_PROXY | 4 | 623 | 57.3% | +1.32% |
| BULL_PROXY | 5 | 712 | 58.1% | +1.56% |
| BULL_PROXY | 6 | 765 | 66.7% | +1.86% |
| BULL_PROXY | 7 | 716 | 60.3% | +1.50% |
| BULL_PROXY | 8 | 691 | 55.3% | +0.86% |
| BULL_PROXY | 9 | 737 | 57.3% | +1.15% |
| BULL_PROXY | 10 | 697 | 53.5% | +0.95% |
| BULL_PROXY | 11 | 645 | 54.4% | +0.58% |
| BULL_PROXY | 12 | 933 | 65.2% | +1.61% |

## Foundation question — synthesis

**Q1. Is each raw detector good on its own?**

- **UP_TRI**: raw WR=49.5% mean_pnl=+0.25% → **BROKEN**.
- **DOWN_TRI**: raw WR=47.4% mean_pnl=-0.42% → **BROKEN**.
- **BULL_PROXY**: raw WR=58.1% mean_pnl=+1.22% → **MARGINAL**.

**Q2. Does regime amplify edge, or is regime the only thing producing edge?**

Compare each detector's raw WR vs its best-regime WR:
- UP_TRI: raw=49.5%, best regime=Bear 52.2% (n=13074), worst regime=Bull 48.7% (n=36678), spread=3.5 pp
- DOWN_TRI: raw=47.4%, best regime=Bear 48.3% (n=3084), worst regime=Bull 46.8% (n=9642), spread=1.5 pp
- BULL_PROXY: raw=58.1%, best regime=Bull 59.8% (n=4721), worst regime=Bear 52.8% (n=1084), spread=7.0 pp

## Top 10 actionable insights

1. **UP_TRI × Bear regime** on 15-year data: WR=52.2% (n=13074). The recent 94.7% from 2026 slice is **inflated** — long-run is much lower.

2. **DOWN_TRI raw**: WR=47.4% on n=18,705. Marginal — depends on cohort filtering.

3. **BULL_PROXY raw**: WR=58.1% on n=8,568.

4. **Score discrimination (UP_TRI)**: WR by bucket 0-3=48.5%, 4-5=50.0%, 6-7=51.7%, 8-10=51.7%.

5. **Deep-drawdown UP_TRI (ret_30d<-10%)**: WR=61.4% on n=1328. This is the strongest single-feature cohort and supports the existing Group A bypass design.

6. **UP_TRI age effect**: age 0 WR=50.6% (n=18,872) vs age 3 WR=48.1% (n=18,757). Age has limited effect.

7. **vol_confirm (UP_TRI)**: True WR=47.9% (n=18,166) vs False WR=50.0% (n=57,113). Volume gate is mostly noise.

8. **Grade A vs B (UP_TRI)**: A WR=51.4% (n=5,492) vs B WR=49.4% (n=69,787).

10. **Back-to-back UP_TRI (≤5d)**: WR=49.2% (n=56,598) vs solo WR=50.7% (n=18,681). Repetition signals fatigue.


## Open questions for follow-up

- sec_mom historical reconstruction would let us test 'sec_mom = Leading' which is part of production scoring but absent from this run.

- 6-day forward window is short for the 2:1 R:R target — most signals exit at day-6 close (94%+), so PnL is concentrated near zero. Re-running with day-15 / day-30 horizons would test trend continuation.

- Entry slippage / liquidity not modelled. Real-world entry would not always be at next-day open at the quoted price.

- Survivorship bias: the 188 stocks are TODAY's F&O universe. Stocks that exited the universe (or never joined) are not represented.

- Corporate actions (splits, bonuses) are NOT filtered by `has_recent_corporate_action` in the replay — production scanner applies that filter at scan time. Effect is small in aggregate but worth checking on individual outlier cohorts.


---
*End of report.*