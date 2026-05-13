# 03 — Input Features

## Summary table

| # | Feature | Source | Lookback | Update cadence | Required? | Effort to add |
|---|---|---|---|---|---|---|
| F1 | Nifty close | yfinance `^NSEI` | 6 months | Daily EOD | **REQUIRED** | 0 (exists) |
| F2 | Nifty EMA50 slope (10-bar) | derived from F1 | 10 bars | Daily | **REQUIRED** | 0 (exists) |
| F3 | Nifty above EMA50 (bool) | derived from F1 | 1 bar | Daily | **REQUIRED** | 0 (exists) |
| F4 | Nifty ret20% | derived from F1 | 20 bars | Daily | **REQUIRED** | 0 (exists) |
| F5 | Nifty above EMA20 (bool) | derived from F1 | 20 bars | Daily | **REQUIRED** | <1h |
| F6 | Nifty above EMA200 (bool) | derived from F1 (needs 1y lookback) | 200 bars | Daily | **REQUIRED** | 1h (extend lookback) |
| F7 | Nifty realized 20-day volatility | derived from F1 | 20 bars | Daily | **REQUIRED** | 1h |
| F8 | India VIX level | yfinance `^INDIAVIX` | 1 bar | Daily EOD | **REQUIRED** | 1h |
| F9 | India VIX 10-day change | derived from F8 | 10 bars | Daily | **REQUIRED** | <1h |
| F10 | Bank Nifty relative strength | yfinance `^NSEBANK` + F1 | 20 bars | Daily | optional (v2.1) | 2h |
| F11 | USDINR | yfinance `INR=X` | 20 bars | Daily | optional (v3) | 3h |
| F12 | 10Y bond yield | external API (RBI / TradingView) | 20 bars | Daily | DEFERRED | 8h+ |
| F13 | Breadth (A/D line) | manual / external | 20 bars | Daily | DEFERRED | 12h+ |
| F14 | FII/DII flow | external (NSE/scraping) | 5 bars | Daily | DEFERRED | 16h+ |
| F15 | Global market context (S&P, Nasdaq) | yfinance `^GSPC`, `^IXIC` | 5 bars | Daily | DEFERRED | 4h |

## Required features (F1-F9) — what v2 actually uses

The decision logic in `04_decision_logic.md` uses **9 features**: F1 through F9. All are derivable from two yfinance pulls (`^NSEI`, `^INDIAVIX`) plus simple pandas math. No external data dependencies.

### F1-F6: Nifty trend/position features

**F1 — `nifty_close`:** Latest daily close from `yfinance.download("^NSEI", period='1y', ...)`. Required period change: extend `'3mo'` → `'1y'` to give EMA200 enough warmup. EMA50 will also stabilize properly.

**F2 — `slope_10d_ema50`:** `ema50.diff(10) / ema50.shift(10)` (current calculation).

**F3 — `above_ema50`:** `close > ema50` (current).

**F4 — `ret20_pct`:** `(close[-1] / close[-20] - 1) * 100` (current).

**F5 — `above_ema20`:** new. EMA20 slope provides a faster signal than EMA50; cross of close above/below EMA20 marks short-term momentum shifts.

**F6 — `above_ema200`:** new. EMA200 is the long-cycle filter. Position vs EMA200 distinguishes structural Bull (well above) from cyclical Bull (just above) from Bear-Recovery in long-cycle bear (still below). Critical for distinguishing Bull from Bull-Recovery in the v2 state space.

### F7: Realized vol

**F7 — `realized_vol_20d`:** `(log_returns.rolling(20).std() * sqrt(252) * 100)` — annualized 20-day realized vol of Nifty as percentage.

Used to disambiguate Choppy (high vol no direction) from Bull-Recovery (vol compressing as direction takes hold). Also serves as a cross-check on F8 (VIX) — if VIX and realized vol disagree, regime is in transition.

### F8-F9: India VIX

**F8 — `india_vix`:** Latest daily close from `yfinance.download("^INDIAVIX", period='1y', ...)`.

VIX has its own regimes:
- VIX < 15: "complacent" — usually means a Bull regime sustaining
- 15 ≤ VIX ≤ 22: "normal" — could be any regime
- 22 < VIX ≤ 30: "stressed" — typically Bear or Choppy with directional churn
- VIX > 30: "panic" — typically Bear-Capitulation (not in v2 state space, mapped to Bear)

VIX level is a primary gate in 02_state_space gate definitions for Bull (`vix < 18`) and Bull-Recovery (`vix < 20`).

**F9 — `vix_change_10d`:** `(vix[-1] / vix[-10] - 1) * 100`.

Rising VIX during a Bull → Bull-Recovery transition is a confirmation signal. Falling VIX during Bear-Recovery confirms transition out of Bear.

## Optional features (F10) — recommended for v2.1

**F10 — Bank Nifty relative strength:** `(banknifty.ret20 - nifty.ret20)` in pp.

Banks lead the Indian market. If Bank Nifty is outperforming Nifty, Bull/Bull-Recovery is confirmed. If Bank Nifty is underperforming during a Nifty rally, the rally is suspect (likely Bull-Recovery → Choppy reversal pending).

Why not required for v2: adds complexity; Bank Nifty data has occasional yfinance fetch errors that complicate the pipeline.

## Deferred features (F11-F15) — v3+

**F11 — USDINR:** Indian markets are inversely correlated with USDINR strengthening. INR weakness usually precedes Bear regimes by 1-2 weeks. Useful but adds another yfinance call + correlation logic.

**F12 — 10Y bond yield:** Requires non-yfinance data source. RBI or TradingView API or scraping. 8+ hours of integration work.

**F13 — Breadth (advance/decline line):** NSE provides this but not via yfinance. Would need NSE bhavcopy scraping or alternative. Marquee feature for regime classification but expensive to build.

**F14 — FII/DII flow:** NSE / NSDL provides daily; requires bhavcopy scraping. High signal value (FII selling is a Bear precursor) but operationally heavy.

**F15 — Global context (S&P, Nasdaq):** Easy to add (yfinance `^GSPC`, `^IXIC`) but Indian regimes don't track US regimes day-to-day; correlation is loose and lag is unpredictable. Lower priority than F10.

## Data layer changes

### Current state
`scanner/main.py:get_nifty_info()` makes one yfinance call: `yf.download("^NSEI", period='3mo')`.

### v2 minimum
Three yfinance calls per scan:
1. `yf.download("^NSEI", period='1y')` — extended from 3mo
2. `yf.download("^INDIAVIX", period='1y')` — new
3. `yf.download("^NSEBANK", period='6mo')` — v2.1 optional

All three are cached daily; no intraday refetch needed. Total network cost: ~300 KB once per morning_scan.

### Failure modes
- **VIX fetch fails:** classify with F1-F7 only, fall back to Choppy when VIX is required (Bull / Bull-Recovery gates need VIX). Log alert.
- **NSEI fetch fails:** return `regime: Unknown`. Downstream consumers default-defensive.
- **NSEBANK fetch fails (v2.1):** F10 omitted from classification; regime still computable.

## Where each feature gets stored

New `output/regime_features.json` schema (proposed):

```
{
  "as_of_date": "2026-05-13",
  "as_of_time_ist": "08:50",
  "fetched_at_utc": "...",
  "features": {
    "nifty_close": 23379.55,
    "slope_10d_ema50": 0.001079,
    "above_ema50": false,
    "above_ema20": false,
    "above_ema200": true,
    "ret20_pct": -1.94,
    "realized_vol_20d_pct": 18.4,
    "india_vix": 19.2,
    "vix_change_10d_pct": +6.3,
    "banknifty_relative_strength_pp": -1.1   // v2.1
  },
  "regime_v2": "Bear-Recovery",      // classifier output
  "regime_pending": null,
  "confidence_pending": null,
  "gate_fired": "bear_recovery_gate",
  "warnings": []
}
```

This file is rebuilt every morning by morning_scan. Brain reads this instead of `weekly_intelligence_latest.json`. Bridge reads this for L1/L2/L4 brief.

## What we keep from current implementation

The existing `regime_debug.json` (written by `_log_regime_debug` in main.py) already logs `last_slope`, `above_ema50`, `ret20_pct`, `classified_as`. v2 extends this to log ALL 9 features + the v2 label + the gate that fired. No information loss; v1 fields stay in place for the side-by-side comparison period.
