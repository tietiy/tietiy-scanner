# Bull Production Scanner — Architecture Discovery (V1)

**Date:** 2026-05-03
**Scope:** Map the production scanner's Bull regime pipeline, identify
replay capability, document gaps before V3 replay.

---

## A. Regime classifier

**Location:** `scanner/main.py:get_nifty_info()` (lines 257-337)

**Algorithm:**
```python
df = yf.download("^NSEI", period='3mo', auto_adjust=True)
ema50 = df['Close'].ewm(span=50).mean()
slope = ema50.diff(10) / ema50.shift(10)        # 10-day slope
above = df['Close'] > ema50
last_slope, last_above = slope.iloc[-1], above.iloc[-1]

if last_slope > 0.005 and last_above:           # rising EMA + price above
    regime = 'Bull'
elif last_slope < -0.005 and not last_above:    # falling EMA + price below
    regime = 'Bear'
else:
    regime = 'Choppy'
```

**Output:** `dict` with `{'regime': 'Bull'|'Bear'|'Choppy', 'regime_score', 'nifty_close', 'last_slope', 'last_above_ema50', ...}`

**Critical for replay:** uses `yf.download(..., period='3mo')` — fetches
**last 3 months from current date**. For historical replay we must:
- Mock yfinance, OR
- Fetch with explicit `start=`/`end=` parameters, OR
- Refactor to accept `as_of_date` (NOT a goal of this verification —
  out of scope per spec disciplines)

Replay approach for V3: build a thin wrapper that calls the same
classification logic with explicitly-fetched historical NIFTY data.

---

## B. Signal generators

**Location:** `scanner/scanner_core.py:detect_signals()` (lines 261-504)

**Critical finding: signal generators are REGIME-AGNOSTIC.**

Inputs:
- `df` — single stock OHLCV with indicators applied
- `symbol`, `sector` — metadata
- `regime`, `regime_score` — passed through (NOT used for detection)
- `sector_momentum`, `nifty_close` — context
- Returns: list of signal dicts

All 3 signal types fire based on **technical pattern conditions only**;
regime is just a tag attached to outputs:

| Signal | Trigger condition (regime-independent) |
|---|---|
| **UP_TRI** | pivot_low (10-bar lookback), age 0-3 bars from current, `entry > stop` |
| **DOWN_TRI** | pivot_high (10-bar lookback), age 0 only, `stop > entry` |
| **BULL_PROXY** | price > ema50 AND in support zone AND bullish reversal candle (`close_pos≥0.60` AND `lower_wick≥0.40` AND green) |

**Regime is NOT a gate on detection.** This is good news: Bull regime
will produce signals identical in structure to Bear/Choppy; only the
`regime` tag changes.

---

## C. Production scoring layer

**Location:** `scanner/scorer.py` + `scanner/mini_scanner.py`

### scorer.py — regime-aware scoring

```python
# Score per signal
if signal == 'UP_TRI':
    if regime == 'Bear':   score += 3        # highest conviction (lifetime)
    elif regime == 'Bull': score += 2
    else:                  score += 1
elif signal == 'DOWN_TRI':
    score += 2                                # regime-agnostic
elif signal == 'BULL_PROXY':
    if regime in ('Bull', 'Choppy'):         # Bear excluded
        score += 1
```

**Bull regime gets non-zero scores for all 3 signal types ✓**.

### mini_scanner.py — rule application

Rules from `data/mini_scanner_rules.json` apply post-detection. Currently
all rules are in **shadow_mode** (log but don't block).

Bull-affecting rules:
- `regime_alignment`: would block SHORT signals in Bull regime if active
  (currently inactive).

### data/mini_scanner_rules.json — boost/kill patterns

**Bull-specific rules: 0**. All boost_patterns are `regime: "Bear"`:

```
win_001: UP_TRI × Auto × Bear  (21/21 WR)
win_002: UP_TRI × FMCG × Bear  (19/19 WR)
win_003: UP_TRI × IT × Bear    (18/18 WR)
win_004: UP_TRI × Metal × Bear (15/15 WR)
win_005: UP_TRI × Pharma × Bear (13/13 WR)
win_006: UP_TRI × Infra × Bear (10.5/12 WR)
win_007: BULL_PROXY × * × Bear  (~14/16 WR)
```

This is **expected and pre-documented gap**: the boost_patterns layer
was populated from live Bear data in April 2026; Bull live data
doesn't exist yet so no Bull boost_patterns have been added.

`kill_patterns`: 1 entry (`kill_001: DOWN_TRI × Bank` — regime-agnostic, will fire in Bull too).

---

## D. Historical replay capability

**No built-in replay mode.** Production scanner architecture:

- `scanner/main.py:scan_universe()` — top-level orchestrator
- `scanner/scanner_core.py:prepare(symbol, period='1y')` — uses
  `yf.download(period='1y')` from CURRENT date
- `scanner/main.py:get_nifty_info()` — uses `yf.download(period='3mo')`
- `scanner/main.py:get_sector_momentum()` — uses
  `yf.download(period='1mo')` for sector indices

**To replay historical period**, the cleanest path is:

1. **Custom replay harness** (NOT modifying production code):
   - Build a Python helper that calls `yf.download(symbol, start=..., end=...)`
     with explicit historical date range
   - For each trading day in test window:
     - Fetch NIFTY data ending on that date → run regime logic manually
     - Fetch each universe stock's data ending on that date → call
       `detect_signals()` directly with regime/sector info
     - Apply scorer.py
   - Save outputs alongside production outputs for comparison

This approach **invokes the actual production functions** unchanged
(no code modifications), passing them historical data they wouldn't
otherwise see. Verification is genuine.

The alternative (mock yfinance + invoke main.scan_universe()) is more
risky — depends on internal control flow that may have side effects
(file writes, telegram sends, etc.).

---

## E. Regime persistence / state

**Stateless regime classification.** `get_nifty_info()` is called once
per scan day; output is written to `output/regime_debug.json` (rolling
90-day log, line 246) but classification itself doesn't depend on
prior days' state.

**Implication:** historical replay is straightforward — no need to
preserve state across days; each day's regime can be classified
independently.

---

## Constants reference (from `scanner/config.py`)

```python
PIVOT_LOOKBACK   = 10           # bars on each side for pivot detection
EMA_FAST         = 20
EMA_MID          = 50
EMA_SLOW         = 200
STOP_MULT        = 1.0          # ATR mult for UP/DOWN_TRI stop
BP_CLOSE_POS_MIN  = 0.60        # BULL_PROXY close in upper 60% of bar
BP_LOWER_WICK_MIN = 0.40        # BULL_PROXY lower wick min 40% of bar
```

---

## Summary — Bull pipeline architecture

| Layer | Bull-handling status |
|---|---|
| Regime classifier (NIFTY → Bull/Bear/Choppy) | ✓ Bull is one of 3 outputs; logic is symmetric |
| Sector momentum (`get_sector_momentum`) | ✓ Regime-agnostic |
| Signal generators (UP_TRI / DOWN_TRI / BULL_PROXY) | ✓ Regime-AGNOSTIC; Bull tag passes through |
| Scorer (regime → score) | ✓ Bull explicitly handled (UP_TRI=2, BULL_PROXY=1, DOWN_TRI=2) |
| mini_scanner rules | ✓ Bull-applicable (regime_alignment etc., currently shadow) |
| boost_patterns | **GAP**: 0 Bull-specific entries (expected — no Bull live data) |
| kill_patterns | ✓ Bank × DOWN_TRI applies to Bull too |
| watch_patterns | ✓ Will fire on Bull signals matching pattern |

**Top-level verdict (V1, pre-replay):** Bull pipeline is structurally
**fully implemented** — regime classifier outputs Bull, signal
generators produce signals tagged with Bull, scorer assigns Bull
scores. Only documented gap: no Bull-specific boost_patterns (fixable
when Bull live data accumulates; not blocking).

V3 replay needed to verify functional correctness on actual Bull
historical data.

## Replay path chosen for V3

**PATH B (manual function invocation)**, per spec. Custom replay
harness invokes `detect_signals()` and regime classification logic
directly with historical data, captures outputs, runs sanity checks.

This is verification without modifying production code, exactly per
spec disciplines.

---

## Key files for V3 replay

| File | Role |
|---|---|
| `scanner/scanner_core.py` | `prepare()`, `add_indicators()`, `detect_signals()` — invoke directly |
| `scanner/main.py` (lines 257-337) | regime classification logic — replicate in harness |
| `scanner/main.py:get_sector_momentum()` | sector momentum — replicate |
| `scanner/scorer.py:enrich_signal()` | post-detection scoring — invoke |
| `scanner/config.py` | constants (PIVOT_LOOKBACK, BP_CLOSE_POS_MIN, etc.) |
| `data/mini_scanner_rules.json` | rules + boost/kill — used by mini_scanner.py |
| `data/fno_universe.csv` | 188 stocks to iterate |
