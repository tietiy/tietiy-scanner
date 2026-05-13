# 07 — Bull Setup Validation Framework

5 new Bull-regime setups from L99 research. Validation pipeline + per-setup feasibility.

## Pipeline (same for every setup)

```
1. Code the detector (interface: SignalDetector)
       ↓
2. Backtest on 5-year NSE F&O data (110-188 stock universe)
       ↓ minimum sample: n ≥ 60 trades for statistical significance
3. Purged-CPCV with embargo (Lopez de Prado)
       - 5 outer folds × 5 inner folds
       - 5-bar embargo between train and test
       - per-fold WR / avg_pnl / Sharpe
       ↓ pass: WR>baseline+10pp AND Sharpe>0.5 AND no fold WR<40%
4. Per-regime stratified analysis (7 regimes from §03)
       ↓ pass: must be net-positive in at least its intended regimes
5. Paper trading (4 weeks live)
       ↓ pass: cumulative R > 0 with max DD < 3R
6. Small-live (1% risk per trade, 4 weeks)
       ↓ pass: same criteria
7. Full-live (5% risk per trade per existing rule)
```

A setup that fails at any step is documented but not deployed.

## Per-setup feasibility

### 1. VCP Breakout

**Encodable in current data?** Yes. All inputs computable from OHLCV:
- close > SMA50 > SMA150 > SMA200 (need 200-bar history; existing universe has it)
- SMA200 rising (slope > 0)
- Volatility contraction: each pullback ≤ 0.6 × previous; final contraction range < 8%
- Volume dry-up < 0.7 × 20-bar avg
- Trigger: close > pivot AND volume > 1.5 × 20-bar avg
- Stop: structural low of final contraction − 0.25 × ATR(14)
- Targets: Fib 1.272 / 1.618 of (pole top − last-contraction low)

**Additional data needed?** None beyond OHLCV. Volume profile (HVN) is helpful but not required.

**Expected sample on 5-year × 188 stocks:** ~150-250 VCPs total (sparse but adequate).

**Estimated regime distribution:** Mostly Stable-Bull. Some Inflecting-Bear→Bull during recovery.

**Estimated build effort:** 16 hours (detector + backtest harness + per-regime stratify).

**Estimated end-to-end validation time:** 10 weeks (1 week build + 1 week backtest + 4 weeks paper + 4 weeks small-live).

### 2. EMA20 Pullback ("Bone Zone") — highest signal frequency

**Encodable?** Yes. All from OHLCV.
- EMA stack: EMA9 > EMA20 > EMA50 (all from `add_indicators` in scanner_core).
- EMA20 slope positive (10-bar diff/shift).
- Pullback: 3-7 days declining + touch EMA20 + hold EMA50.
- Trigger: bullish candle closes back above EMA9.

**Additional data?** None.

**Expected sample on 5-year × 188 stocks:** **High** — likely 800-1500 fires. (L99 specifically flags this as "highest signal frequency".)

**Regime distribution:** Stable-Bull + Inflecting-Bear→Bull.

**Estimated build effort:** 8 hours.

**Validation time:** 8 weeks (smaller backtest window since sample is large, faster paper).

### 3. Bull Flag / High-Tight Flag

**Encodable?** Yes. Pole detection (≥4×ATR move in 5-10 bars with volume ≥1.3×50-day avg) is a windowed feature.

**Additional data?** None.

**Expected sample:** 300-500 across 5 years.

**Regime distribution:** Stable-Bull (continuation) and post-Inflecting-Bear→Bull.

**Estimated build effort:** 12 hours.

**Validation time:** 10 weeks.

### 4. Darvas Box Breakout — already validated on Nifty Midcap 50 (Patil et al. 2024)

**Encodable?** Yes, but **52-week new high** + box-tightness require 252-bar history per stock. Doable.

**Additional data?** None.

**Expected sample:** Sparse — maybe 60-100 fires across 5 years (Darvas requires genuine 52-week-high stocks).

**Regime distribution:** Stable-Bull predominantly.

**Estimated build effort:** 14 hours.

**Validation time:** 12 weeks (sample is small; paper-trade phase needs more wallclock).

### 5. Cup-and-Handle (handle breakout)

**Encodable?** Yes, but cup detection (12-26 week base + 12-35% depth + right-side recovery within 5%) is the most parameter-sensitive of the five.

**Additional data?** None.

**Expected sample:** Sparse — maybe 80-150 fires across 5 years.

**Regime distribution:** Stable-Bull + Inflecting-Bear→Bull.

**Estimated build effort:** 16 hours (parameter tuning + handle-detection edge cases).

**Validation time:** 14 weeks (long detection window means slow accumulation in paper phase).

## Aggregate validation time

If validated **in parallel** (which is feasible — they're independent detectors):

```
Week  0:  Build all 5 detectors (66 hours of detector code)
Weeks 1-2: Backtest harness + per-regime stratify
Weeks 3-6: Paper trading (4 weeks for all)
Weeks 7-10: Small-live (4 weeks for all)
Week 10:  First subset ready for full-live
```

**Aggregate: ~10 weeks for the EMA20-pullback + bull flag + VCP to be ready.** Darvas and cup-handle finish later (12-14 weeks total).

If validated **sequentially** (one at a time, building confidence):

```
Setup 1 (EMA20 pullback, fastest):       8 weeks
Setup 2 (VCP):                            10 weeks
Setup 3 (bull flag):                      10 weeks
Setup 4 (Darvas):                         12 weeks
Setup 5 (cup-handle):                     14 weeks
TOTAL sequential:                        ~54 weeks (~13 months)
```

**Most realistic: parallel build, sequential graduate-to-live.** Each new setup goes live one at a time after passing all 7 stages, so confidence accumulates without correlated catastrophic failure. **~14 weeks until all 5 are live.**

## Critical caveat — purged-CPCV time

**Purged-CPCV with embargo (5×5 folds) on 5-year × 188 stocks is non-trivial compute.** Per the L99 spec, this is Lopez de Prado methodology. Estimated runtime:

- 5-year OHLCV × 188 stocks ≈ 230k bars.
- 5×5 folds = 25 train/test pairs per setup.
- Per pair: detection + simulation + statistics = ~5-30 minutes depending on detector complexity.
- **Total per setup: 2-12 hours of pure compute.**
- 5 setups × 8 hours mean = **40 hours of compute** for the initial purged-CPCV pass alone.

User has Macbook Air M5 per `fix_table.md` workflow state. Should handle it but slowly. Cloud compute may be desirable.

## Risk: 60+ trades for statistical significance, sparse setups

Darvas (60-100 fires across 5 years) and cup-handle (80-150) struggle to clear the n=60 bar for any individual stock cohort. **They will only get statistical significance at the aggregate (all stocks) level.** Per-stock or per-sector subsetting kills sample size.

This is a real concern. Recommendation: **don't promote Darvas or cup-handle to per-sector boost rules until n≥30 per sector accumulates** (could take 1-2 years live).

## Effort to build validation framework (the pipeline, not the setups themselves)

| Component | Hours |
|---|---:|
| Backtest harness (event-driven, audit-faithful) | 30 |
| Purged-CPCV implementation | 20 |
| Per-regime stratification module | 8 |
| McNemar test runner (already in §04) | 0 |
| Paper-trading mode (uses shadow_ops/lifecycle.py with no broker) | 8 (extend shadow_ops) |
| Small-live infrastructure (1% risk override + journal annotation) | 6 |
| Full-live deploy pipeline (no infra change; just a "this rule is live" flag) | 2 |
| Per-setup detector × 5 | 66 (per per-setup numbers above) |
| **Total validation infra + 5 detectors** | **~140 hours** |

## Summary

- All 5 setups are encodable from OHLCV alone.
- EMA20 pullback is the fastest to validate (highest sample frequency).
- Darvas and cup-handle have sparse-fire risk.
- Aggregate time-to-deployable: ~14 weeks for all 5 (parallel build, sequential graduate-to-live).
- 140 hours of build effort (validation infra + 5 detectors).
