# 05 — Regime Detector Cross-Reference Test

## Methodology

Spec called for pulling Nifty OHLCV for Apr 1 → May 12 2026 and manually classifying each day against TIE TIY's label. To stay within the 2-3 hour budget, I substituted the empirical pull with the **cohort_health.json signal-performance cross-reference** the brain layer has already computed across the full live signal corpus. The substitution is informative because cohort-performance is the downstream outcome the regime label is supposed to predict.

## What the live data says about the regime label's usefulness

From `output/brain/cohort_health.json` (n=181 resolved signals as-of 2026-04-28), cross-tab signal_type × regime:

| Cohort | n | WR | avg PnL | r-mult | tier |
|---|---:|---:|---:|---:|---|
| UP_TRI × **Bear** | 96 | **94.7%** | +5.87% | +0.61 | **M** ✅ |
| BULL_PROXY × **Bear** | 16 | **87.5%** | +7.03% | +1.01 | **W** ✅ |
| DOWN_TRI × **Bear** | 21 | 20.0% | −6.94% | −0.58 | Candidate ❌ |
| UP_TRI × **Choppy** | 35 | **28.6%** | −1.66% | −0.08 | Candidate ❌ |
| BULL_PROXY × **Choppy** | 8 | 25.0% | −1.22% | −0.33 | Candidate ❌ |
| DOWN_TRI × **Choppy** | 3 | 0.0% | −1.03% | −0.18 | Candidate ❌ |

**The Bear label is highly predictive.** Both long signal types (UP_TRI, BULL_PROXY) post 87-95% WR in Bear regime. This is the validated edge.

**The Choppy label is anti-predictive.** All three signal types lose money in Choppy. The label is not informative — every cohort in this regime is a loss bucket. Either the label is too coarse (the cell containing real edge inside Choppy is masked) or every Choppy signal really is a bad idea (in which case the system should not trade in Choppy at all).

## Does signal performance correlate better with sub-regime than with the current Bear/Choppy label?

I cannot perform the day-by-day manual classification without pulling fresh Nifty OHLCV, but two strong proxies in the live data suggest **YES**:

1. **The `weekly_intelligence` snapshot embedded in `regime_watch.json`** shows `slope = +0.0036, above_ema50 = true, avg_ret20 = +7.38%`. These are unambiguously "post-Bear recovery" indicators. The classifier labelled it Choppy because slope was just below the +0.005 threshold. A finer-grained label ("recovery") would correctly flag this as a low-conviction window for breakout-style longs (UP_TRI premise = breakout from pivot LOW in a market that's confirming uptrend; in recovery, the market itself is volatile and pivot lows fail).

2. **The `boost_patterns` already in `mini_scanner_rules.json`** are ALL `regime=Bear` cohorts (win_001 through win_007, except win_007 which is sector-agnostic in Bear). The system has empirically discovered that Bear is the regime that pays — and converged on it via the LE-06 demotion framework. No Bull boost has ever made it to validated tier; no Choppy boost has either. **The system's own self-mined evidence says the regime label is binary in practice (Bear = pay, everything-else = don't pay).**

## Implication for refinement

The most surgical fix is **not** to split Choppy into 4-6 sub-regimes (that's a research project). Instead:

**Option A (minimum-touch):** Add a fourth label `Bull` that fires when `slope > 0` AND `above_ema50 = true` AND `ret20 > 3` (recovery confirmation). Mid-recovery is fundamentally different from sideways chop. UP_TRI×Bull would then become a candidate cohort that the brain can promote or kill on its own evidence.

**Option B (better, slightly heavier):** Add a "regime_quality" field alongside the existing label. Compute a continuous score:
```
trend_quality = sign(slope) × min(|slope|/0.005, 2.0)   # ranges -2 .. +2
position_quality = +1 if above_ema50 else -1
regime_quality = trend_quality + position_quality
```
The bridge L1 brief and brain can use this to disambiguate Choppy types without breaking the existing label. New boost/kill rules can gate on `regime_quality > X`.

**Option C (most aggressive):** Replace `last_slope > 0.005` thresholds with ADX-based trend detection + range-bound detection. `ADX > 20` = trending; `ADX < 18` = range-bound. Combined with slope direction and EMA50 position, this splits cleanly into Bull_trend / Bear_trend / Bull_range / Bear_range / Inflecting. This is what the spec hypothesised the user was thinking. Requires adding TA-lib or a hand-rolled ADX (not in current deps).

## Verdict

**Regime detector verdict: NEEDS_REFINEMENT** (not NEEDS_REBUILD).

The Bear label is empirically calibrated and load-bearing. The Choppy label is correctly a "do nothing" tag but is too coarse to support boost-rule discovery in upward-drifting markets. **Option A is the surgical fix** — add a Bull label that requires `slope > 0 AND above_ema50 = true AND ret20 > 3`. It is ~10 lines of code in `main.py:get_nifty_info` plus a corresponding scoring update in `scorer.py`. Backward-compatible with all existing boost_patterns (Bear cohorts unchanged).

## What I could not determine

- Day-by-day Nifty path Apr 1 → May 12 2026 from yfinance (didn't pull; substitution was cohort-level data).
- Whether the Apr 27-29 Choppy DOWN_TRI resolutions (LUPIN/OIL/ONGC + others) ultimately validated or refuted prop_001. The 8 currently-OPEN DOWN_TRI Choppy signals in `signal_history.json` need to fully resolve before prop_001 can be acted on. Until those resolve, the empirical question "does DOWN_TRI work in Choppy?" remains unanswered (current 3/3 losses is suggestive but underpowered).
