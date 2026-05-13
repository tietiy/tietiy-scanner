# 04 — Regime Detector Mechanics

Source: `scanner/main.py` `get_nifty_info()` lines 257-338.

## Exact code

```python
df = yf.download("^NSEI", period='3mo', auto_adjust=True)
closes     = df['Close']
ema50      = closes.ewm(span=50).mean()
slope      = ema50.diff(10) / ema50.shift(10)   # 10-day slope of EMA50
above      = closes > ema50
last_slope = float(slope.iloc[-1])
last_above = bool(above.iloc[-1])

if last_slope > 0.005 and last_above:
    regime = 'Bull'
elif last_slope < -0.005 and not last_above:
    regime = 'Bear'
else:
    regime = 'Choppy'                            # CATCH-ALL FALLBACK
```

Also computes `ret20 = closes[-1]/closes[-20] - 1` and emits a `regime_score` ∈ {−1, 0, 1, 2} based on `ret20` thresholds — separate from the `regime` label.

## Decision table (the only three labels emitted)

| `last_slope` (10-bar EMA50 slope) | `last_above` (close > EMA50?) | Label |
|---|---|---|
| `> +0.005` | True | **Bull** |
| `< −0.005` | False | **Bear** |
| any other combo | any other combo | **Choppy** |

## The Choppy bucket conflates 4 distinct micro-states

There are 2×2 = 4 cells in the (`slope_sign`, `above_ema50`) state space, plus two slope-magnitude bands (`|slope| ≤ 0.005`, `|slope| > 0.005`). The current classifier promotes only the "clean trending up + above EMA50" → Bull and "clean trending down + below EMA50" → Bear corners, mapping ALL six remaining cells into "Choppy".

The six "Choppy" cells (the cells that all map to the same label):

| slope band | above_ema50 | What this likely is | Same-label-as |
|---|---|---|---|
| `< −0.005` | True | Distribution / topping (price above EMA50, trend rolling over) | flat-bull |
| `> +0.005` | False | Recovery / early Bull (price below EMA50, slope rising) | bear-flat |
| `≤ +0.005, ≥ −0.005` | True | Bull stable / range-in-uptrend | distribution top |
| `≤ +0.005, ≥ −0.005` | False | Bear stable / range-in-downtrend | recovery |
| `≤ +0.005, ≥ −0.005` | True | (subset of above — same outcome) | — |
| `≤ +0.005, ≥ −0.005` | False | (subset of above — same outcome) | — |

The four logically distinct micro-states **distribution-top, post-Bear recovery, Bull-flat, Bear-flat** all receive the same label "Choppy". Their forward-return distributions are quite different, so collapsing them is a measurable information loss.

## What the brain layer's regime_watch sees right now

From `output/brain/regime_watch.json` (as-of 2026-04-28):

```json
{
  "current_regime": "Choppy",
  "regime_stability": "stable",
  "days_in_current_regime": 7,
  "recent_distribution_7d": {"Choppy": 7},
  "prior_distribution_7d": {"Choppy": 2, "Bear": 5},
  "weekly_intelligence_snapshot": {
    "slope": 0.003614,
    "avg_ret20": 7.38,
    "above_ema50": true
  }
}
```

`slope = +0.0036` (positive but below +0.005 Bull threshold).
`above_ema50 = true`.
`avg_ret20 = +7.38%` (strongly positive 20-day move).

Per the decision table, this lands in the "Choppy" catch-all — even though every indicator points to **post-Bear-recovery / early Bull**. The system is acting as if the market is undirected when the market is in fact drifting up.

## Implication for signal performance

Hypothesis (testable against cohort_health, see `05_regime_detector_test.md`):
1. UP_TRI signals fired in this "Choppy" state are entering trades on transient pullbacks within a recovering market — pullbacks that fail to follow through because the market reverts upward, capping the move at Day-6 forced exit.
2. DOWN_TRI signals fired in this "Choppy" state face the same problem from the short side — they get steamrolled by the underlying upward drift.

This matches the observed live data (UP_TRI×Choppy 28.6% WR, DOWN_TRI×Choppy 0/3, all open Choppy DOWN_TRIs still pending).

## Verdict

**Regime detector needs refinement — NOT rebuild.** The signal it produces is informative when it fires Bear (correctly captures the steepest stretches of decline) but the Choppy label is too coarse. Two specific recommendations land in `MASTER_FINDINGS.md §2`.

The detector also has a **lookback / freshness concern**: 3-month yfinance pull is short for an EMA50, leaving the EMA50 itself with only ~13 bars of warmup before the slope is computed. EMA50 stabilises after ~3× span = 150 bars (~7 months). With period='3mo' (~63 bars), the EMA50 carries residual initialisation bias. This is unlikely to flip the regime label in normal use but is a code-quality issue worth flagging.
