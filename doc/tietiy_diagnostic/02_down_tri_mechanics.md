# 02 — DOWN_TRI Mechanics (Forensic)

Source: `scanner/scanner_core.py` lines 379-430 (DOWN_TRI detection), `scanner/scorer.py` (scoring/exit-rule), `scanner/config.py` (constants).

## DOWN_TRI signal generation — exact code path

`scanner_core.py` lines 379-430:

```python
# ── DOWN TRIANGLE — age 0 only ────────────────
pb = last_bar - 0 - LB                          # PIVOT_LOOKBACK = 10
if LB <= pb < n and ph_v[pb]:                    # pivot HIGH detected at pb
    atr = atr_v[pb]
    if not (np.isnan(atr) or atr <= 0):
        pivot_px  = highs[pb]                    # the pivot-high price
        entry_est = closes[last_bar]
        stop      = round(pivot_px + STOP_MULT * atr, 2)   # STOP_MULT=1.0
        if stop > entry_est:                     # sanity: stop above entry for short
            ...
            signals.append({
                'signal':       'DOWN_TRI',
                'direction':    'SHORT',
                'age':          0,
                'pivot_price':  round(pivot_px, 2),
                'entry_est':    round(entry_est, 2),
                'stop':         stop,
                'atr':          round(atr, 2),
                ...
                'bear_bonus':   False,           # <— always False (asymmetric)
            })
```

### Trigger conditions

1. A confirmed `pivot_high` exactly at bar `last_bar - PIVOT_LOOKBACK` (i.e., the most recent confirmed pivot, lookback=10).
2. `age == 0` ONLY (no age-1/2/3 variants — unlike UP_TRI which runs ages 0-3).
3. Valid ATR.
4. Stop (= pivot_high + 1×ATR) is above current close (sanity).

No volume gate, no regime gate, no proximity-to-zone check, no momentum gate. Bare pivot detection + ATR-based stop.

### Stop & target

- Stop = `pivot_high + 1.0 × ATR` (STOP_MULT=1.0, lives in `config.py`).
- **No target.** `scorer.get_exit_rule(signal, regime)` returns `'Target2x'` ONLY when `signal=='UP_TRI' and regime=='Bear'`. Every other case (including ALL DOWN_TRI) returns `'Day6'`, and `calc_target` returns `None` for `Day6`.
- Result: DOWN_TRI trades exit ONLY via STOP_HIT or DAY6 timer. No target-hit path exists.

### Scoring

`scorer.py` line 74-76:

```python
elif signal == 'DOWN_TRI':
    score += SCORE_DOWN_ALL    # = 2, flat all regimes
    breakdown.append(f"DownAll+{SCORE_DOWN_ALL}")
```

DOWN_TRI gets:
- Age 0 → +3 (age layer)
- Regime layer → +2 flat (no Bear/Bull/Choppy discrimination)
- Quality bonuses → up to +4 (vol_confirm, sec_leading, rs_strong, grade_A)

Max DOWN_TRI score = 9 (vs 10 for UP_TRI which can also get Bear+3).

## UP_TRI vs DOWN_TRI — symmetry audit

| Aspect | UP_TRI | DOWN_TRI | Symmetric? |
|---|---|---|---|
| Detection bar | `pivot_low` at `last_bar - age - LB` | `pivot_high` at `last_bar - LB` | Mirror in price feature |
| Ages scanned | 0, 1, 2, 3 | **0 only** | **NO** — UP_TRI scans 4 ages of pivots, DOWN_TRI scans 1 |
| Stop direction | `pivot_low − 1×ATR` | `pivot_high + 1×ATR` | Mirror |
| Regime bonus in score | Bear+3, Bull+2, Choppy+1 | flat +2 all regimes | **NO** — UP_TRI score rewards Bear conviction |
| `bear_bonus` flag | `regime == 'Bear'` (drives +3) | **always False** | **NO** |
| Target rule | `Target2x` if Bear, else `Day6` | `Day6` (no target) | **NO** — DOWN_TRI never has a target |
| Quality bonuses (vol/sec/rs/grade) | same | same | Yes |

## Asymmetries that matter

### A1 — DOWN_TRI never has a 2R target

This is the single largest structural asymmetry. UP_TRI×Bear can hit target in <6 days for a clean 2R win. DOWN_TRI must reach Day 6 or get stopped. **The 11 STOP_HIT outcomes vs 0 TARGET_HIT in current data is the direct consequence of this design.**

Day-6 forced exits cap the upside on shorts. Even when a short moves in our favor (DAY6_WIN), the magnitude is small. The 4 DAY6_WIN DOWN_TRI outcomes in current data total only +7.27% pnl_pct (vs the 11 STOP_HITs at −113.61%). The geometry is one-sided.

### A2 — DOWN_TRI ages 1-3 are not detected

UP_TRI scans 4 ages worth of pivots (age 0, 1, 2, 3), giving 4 candidate triggers per bar. DOWN_TRI scans only age=0. Per the validated backtest summary in `session_context.md`: "DOWN_TRI: **Age 0 ONLY.** Edge gone at age 1+." So the asymmetry is intentional — but it also means DOWN_TRI gets only one shot per pivot-high event, with no second-chance variant.

### A3 — No regime score discrimination for DOWN_TRI

UP_TRI in Bear regime scores +3 vs +1 in Choppy. DOWN_TRI scores +2 flat regardless of regime. The score thus cannot help a downstream filter prefer "DOWN_TRI in market-aligned regime". The system has no built-in way to express "this DOWN_TRI is in a regime where it's likely to work."

(In current data, DOWN_TRI×Bear and DOWN_TRI×Choppy both fail — so a Bear-only bonus wouldn't have saved this signal type. But the asymmetry is structural and worth noting.)

### A4 — Stop multiplier identical, ATR-driven

Both signal types use `STOP_MULT = 1.0`, so stop width is purely ATR-driven. Mathematically symmetric. Empirically (next section) DOWN_TRI stops end up wider in absolute % terms because of stock-level volatility selection.

## What the live data shows

(Detail in `03_down_tri_subpopulations.md`.) The structural asymmetries above predict exactly the observed failure mode:

- 0 TARGET_HIT events (no path exists).
- 11/23 STOP_HIT events (48%) all in Bank/Energy/Bear — rally-crushing-shorts geometry.
- DOWN_TRI MFE median = **0.00%** — most trades never even moved favorably one bar.
- Wins are tiny when they occur (max +4.09% on DAY6_WIN; total across 4 wins = +7.27%).
- Losses are large and disciplined-to-stop (avg STOP_HIT pnl_pct ≈ −12%).

The mechanics are doing exactly what they're coded to do. The strategy is structurally one-sided: 1R downside cap, capped upside with no acceleration mechanism, in a market regime (Bear) where rally-mean-reversion is more common than continuation.
