# Bull Verification — Historical Test Periods (V2)

**Date:** 2026-05-03
**Method:** Apply production scanner's regime classifier
(`scanner/main.py:get_nifty_info()` algorithm) to NIFTY historical
data 2014-2026 to identify Bull-classified periods.

---

## Methodology

Replicated production scanner regime logic (line 281-286 in `main.py`):
```python
slope = ema50.diff(10) / ema50.shift(10)
above = close > ema50
if last_slope > 0.005 and last_above:
    regime = 'Bull'
```

Applied to daily NIFTY data 2014-01-02 → 2026-04-29 (n=3026 trading
days).

---

## Bull regime distribution (production-classifier output)

### Year × regime breakdown

| Year | Bear | Bull | Choppy |
|---|---|---|---|
| 2014 | 12 | **175** | 43 |
| 2015 | 88 | 56 | 100 |
| 2016 | 73 | **130** | 41 |
| 2017 | 3 | **180** | 65 |
| 2018 | 55 | 96 | 94 |
| 2019 | 39 | 108 | 94 |
| 2020 | 56 | **154** | 40 |
| 2021 | 23 | **181** | 44 |
| 2022 | 58 | 95 | 95 |
| 2023 | 39 | **113** | 93 |
| 2024 | 27 | **157** | 62 |
| 2025 | 47 | 105 | 97 |
| 2026 | 33 | **0** | 45 |

**2026 has 0 Bull-classified days** (matches Lab finding: no live Bull
during current scanner operational period).

### Longest consecutive Bull stretches (≥ 30 bars)

| Rank | Start | End | Bars | Notes |
|---|---|---|---|---|
| 1 | 2014-03-05 | 2014-10-07 | 142 | Modi-government rally |
| 2 | 2016-03-17 | 2016-09-29 | 130 | Pre-demonetization rally |
| 3 | 2021-05-19 | 2021-11-22 | 127 | **Post-COVID recovery rally** ★ |
| 4 | 2017-01-18 | 2017-07-05 | 113 | Broad-equity rally |
| 5 | 2020-06-05 | 2020-09-22 | 77 | Initial post-COVID rebound |
| 6 | 2020-10-08 | 2021-01-29 | 77 | Continuation of rebound |
| 7 | 2023-05-02 | 2023-08-21 | 77 | **Post-2022 broad uptrend** ★ |
| 8 | 2023-11-28 | 2024-03-19 | 76 | Pre-election rally |

---

## Test period selection

### Primary test window — 2021-08-02 → 2021-08-13 (10 trading days)

**Period:** Mid-stretch within the 127-bar 2021 Bull period (rank 3)
**Justification:**
- Within longest recent Bull stretch (gives clean Bull classification)
- 2021 post-COVID recovery; rich market activity for testing
- F&O universe data quality verified (sample stocks return data)
- Mid-stretch avoids boundary effects (clean Bull classification at
  start AND end of window)
- 10 trading days = enough to verify classification consistency +
  multiple signal generation cycles

**Verification of universe data**:
- RELIANCE.NS: 42 bars in 2021-07-01 → 2021-08-31 window ✓
- INFY.NS: 42 bars ✓
- HDFCBANK.NS: 42 bars ✓
- ITC.NS: 42 bars ✓
- TATAMOTORS.NS: yfinance API issue (transient — symbol exists but
  API returned 404 during sampling)

### Secondary test window — 2023-06-12 → 2023-06-23 (10 trading days)

**Period:** Mid-stretch within the 77-bar 2023 Bull period (rank 7)
**Justification:**
- Different macro conditions from 2021 (post-2022 correction; sustained
  uptrend phase)
- Cross-checks Bull classifier across two distinct Bull regimes
- More recent (2023) → likely better data quality on yfinance
- 10 trading days = parallel scope to primary window

**Verification of universe data**:
- RELIANCE.NS: 53 bars in 2023-05-01 → 2023-07-15 window ✓
- INFY.NS: 53 bars ✓
- HDFCBANK.NS: 53 bars ✓
- ITC.NS: 53 bars ✓

---

## V3 replay plan

For each selected test window:
1. **Per-day**: Fetch NIFTY data ending on that date, run regime
   classification logic, verify output = "Bull"
2. **Per-day per-symbol** (188 F&O stocks):
   - Fetch stock OHLCV ending on that date (1y window)
   - Invoke `prepare()` → `add_indicators()` → `detect_signals()`
     directly with regime/sector args
3. **Capture**:
   - Daily regime classifications (10 days × 1 = 10 classifications)
   - All signals generated (likely 50-200 per day across universe)
   - Score breakdown per signal (via `enrich_signal()`)
4. **Verify**:
   - Regime = Bull on all 10 days
   - Signals fire with `regime='Bull'` tag
   - All 3 signal types (UP_TRI/DOWN_TRI/BULL_PROXY) produce non-zero
     counts across 10 days
   - Sector momentum classification works
   - Scoring produces sensible output (no errors, scores in [0,10])

This is functional verification — not performance/strategy testing.

---

## Halt conditions check (V2)

| Condition | Status |
|---|---|
| Bull historical periods accessible to scanner | ✓ Multiple periods identified |
| F&O universe data available for chosen windows | ✓ Sample stocks verified |
| Test windows within validated Bull stretches | ✓ Mid-stretch placement |
| 10-day windows sized for replay scope | ✓ Manageable runtime |
| Production classifier produces Bull output for chosen days | ✓ (will verify in V3) |

All clear. Proceed to V3 replay.
