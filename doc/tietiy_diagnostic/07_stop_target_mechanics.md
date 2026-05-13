# 07 — Stop/Target Mechanics

Source: `scanner/scanner_core.py` (stop computation per signal type), `scanner/scorer.py` (target/exit-rule), `scanner/config.py` (constants).

## Constants

```python
STOP_MULT          = 1.0   # ATR multiplier for stop
TARGET_R_MULTIPLE  = 2.0   # live target = 2× risk
TARGET_R_MULTIPLE_SHADOW = 3.0   # shadow track only, not active
EXIT_BARS          = 6     # Day-6 forced exit (calendar/trading-day depending on caller)
ATR_PERIOD         = 14
PIVOT_LOOKBACK     = 10    # bars on each side for pivot confirmation
ZONE_ATR           = 0.50  # zone proximity ATR multiplier
BP_CLOSE_POS_MIN   = 0.60  # BULL_PROXY: close_pos >= 0.60
BP_LOWER_WICK_MIN  = 0.40  # BULL_PROXY: lower wick >= 0.40
```

## Stop computation by signal type

### UP_TRI
```
stop = pivot_low - STOP_MULT × ATR
```
ATR is taken at the pivot bar (not current bar). Sanity check: `stop < entry_est`.

### DOWN_TRI
```
stop = pivot_high + STOP_MULT × ATR
```
ATR at pivot bar. Sanity: `stop > entry_est`.

### BULL_PROXY
```
stop_z = szL - 0.5 × ATR    # szL = support zone low (built from prior pivot lows)
        OR (if szL nan)
stop_z = low_at_signal_bar - 1.0 × ATR
```
Sanity: `stop_z < current_close`.

## Target computation

`scorer.get_exit_rule(signal, regime)`:

```python
def get_exit_rule(signal, regime):
    if signal == 'UP_TRI' and regime == 'Bear':
        return 'Target2x'
    return 'Day6'
```

`scorer.calc_target(entry, stop, exit_rule)`:

```python
if exit_rule == 'Target2x':
    mult = 2.0
elif exit_rule == 'Target1_5x':
    mult = 1.5
else:
    return None     # ← Day6 returns None → no target_price written
```

| Signal × Regime | Exit rule | Target |
|---|---|---|
| UP_TRI × Bear | Target2x | `entry + 2 × risk` |
| UP_TRI × Bull | Day6 | None |
| UP_TRI × Choppy | Day6 | None |
| DOWN_TRI × any | Day6 | None |
| BULL_PROXY × any | Day6 | None |

**Only ~24% of signal-regime cells (1 of 4×3=12) carry a real target.** Everything else relies on Day-6 forced exit at next-day open.

## Live stop-width distributions (deduplicated by `id`, computed from `(stop − entry).abs() / entry × 100`)

| Signal | count | mean | p25 | p50 | p75 | p90 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| UP_TRI | 229 | 14.4% | 9.9% | 14.2% | 18.2% | 22.0% | 31.2% |
| DOWN_TRI | 32 | 11.0% | 8.5% | 12.2% | 13.4% | 13.9% | 15.3% |
| BULL_PROXY | 27 | 5.7% | 4.5% | 5.2% | 6.9% | 9.4% | 10.1% |
| DOWN_TRI_SA | 2 | 4.0% | 3.1% | 4.0% | 5.0% | 5.6% | 6.0% |

Observations:
1. **UP_TRI stops are widest** (median 14%, max 31%). Wide UP_TRI stops are mostly Bank/Energy/IT names where ATR scales tend to be 3-5% of price; pivot+1×ATR easily produces 15-20% notional stops.
2. **DOWN_TRI stops cluster around 12%** — narrower than UP_TRI in median but with much higher floor (p25 8.5% vs 9.9%). On commodity-cyclical Bank/Energy DOWN_TRIs the stops are ~13-15% wide.
3. **BULL_PROXY stops are tightest** (median 5.2%) because they reference the SUPPORT ZONE LOW (built from recent pivot lows) minus 0.5×ATR, NOT the local low minus 1×ATR. The smaller offset multiplier produces materially tighter stops.
4. **DOWN_TRI_SA (second attempt) stops are also tight** (median 4%) because the parent pivot is closer to current price by the time SA fires.

## Live target-hit rates (resolved signals only)

| Signal | n_resolved | TARGET_HIT | rate |
|---|---:|---:|---:|
| UP_TRI | 185 | 4 | 2.2% |
| BULL_PROXY | 24 | 4 | 16.7% |
| **DOWN_TRI** | 23 | **0** | **0.0%** |

Day-6 forced exits dominate everywhere. The only signal type with a meaningful target-hit rate is BULL_PROXY (1 in 6) — the tight-stop structure works in BULL_PROXY's favor.

The user is currently sitting on 8 TARGET_HIT outcomes total across 232 resolved signals (3.4%). The `cohort_health.json` warning `r_multiple_under_day6_dominance` is correct: nearly every cohort's r-multiple is dampened because the population is mostly Day-6 caps and stop-outs.

## Fib-based stop/target viability

The user's stated goal is to "add Fib-based stops/targets to upgrade UP_TRI, BULL_PROXY, and possibly rehabilitate DOWN_TRI."

**For stops (replacing `pivot ± 1×ATR`):**
- The current ATR-based stop is wide because ATR captures intraday volatility, and a 1×ATR-buffer can be 3-5% of price on its own.
- A Fib-based stop anchored to a recent swing low (UP_TRI / BULL_PROXY) or swing high (DOWN_TRI) at the 0.5 or 0.618 retracement of the most recent leg would land tighter on average AND more meaningful structurally.
- **Feasibility: HIGH for UP_TRI and BULL_PROXY.** They already use pivot-low (UP_TRI) or szL/support zone (BULL_PROXY) as anchors. Replacing the `1×ATR` offset with a Fib level computed from the prior leg (pivot_high → current low for an UP_TRI; or the szH→szL range for BULL_PROXY) is a 1-2 day refactor in scanner_core.
- **Feasibility for DOWN_TRI: LIMITED.** The signal premise is "short the pivot high." Fib retracements from the most recent prior leg (pivot_low → pivot_high) would land at logical levels above entry (38.2%, 50%, 61.8% retracement from the high). Tighter stop = better R if it holds. But the underlying problem (no target + Day-6 forced exit + adverse regime drift) is not solved by stop refinement.

**For targets (replacing `Day6` with structured exits):**
- Adding a Fib-based target at e.g., 1.272× extension of the prior leg gives DOWN_TRI a target-hit path it currently lacks.
- BULL_PROXY's tight stops already make a target structurally compatible — moving from `Day6` to `Target2x` on BULL_PROXY would convert some DAY6_WIN outcomes (avg +0.86R) into TARGET_HIT outcomes (avg +2R). The 4 existing BULL_PROXY TARGET_HITs averaged +2.22R; another ~15 BULL_PROXY DAY6_WINs could plausibly have hit 2R given their MFE/MAE distributions. Modeling required.
- UP_TRI×Choppy and UP_TRI×Bull — neither currently has a target. The Choppy cohort is losing, so a target wouldn't save it (only one in 35 was a Day-6 winner of decent size; most are flat-to-loss). UP_TRI×Bear already has a Target2x rule.

**Stop-width-vs-outcome correlation (DOWN_TRI):** Pearson `r = −0.36` between stop_width_pct and pnl_pct. Negative — wider stops fared worse in the live sample. Mostly an artefact of high-ATR Bank/Energy names being the dominant DOWN_TRI population during the Apr 6-8 short squeeze.

## What I could not determine

- The actual MFE/MAE distribution of UP_TRI×Choppy DAY6 outcomes (which would tell us whether a target would have helped) — requires deeper per-trade walk through OHLCV data, not in this run.
- Whether a Fib-based stop on BULL_PROXY would change the existing 16.7% TARGET_HIT rate up or down. Backtest required.
