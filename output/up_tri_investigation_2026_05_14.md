# UP_TRI=0 Investigation — 2026-05-14

**Context:** Nifty +250 today. `scan_log.json` shows 0 UP_TRI fired and 0 UP_TRI rejected. Recent days were 0/1/9/1/2 (May 7–13).

---

## Top 5 gainers today (full top-30 in JSON)

| Rank | Symbol | Sector | % chg | Today close | 5d pivot high | 10d pivot high | Broke 5d? | Broke 10d? |
|---|---|---|---|---|---|---|---|---|
| 1 | ADANIENT.NS | Energy | +8.60% | 2712.90 | 2549.90 | 2549.90 | YES | YES |
| 2 | CIPLA.NS | Pharma | +8.22% | 1436.70 | 1379.50 | 1379.50 | YES | YES |
| 3 | ALKYLAMINE.NS | Chem | +6.92% | 1750.00 | 1783.70 | 1785.00 | YES | YES |
| 4 | GNFC.NS | Chem | +6.12% | 519.95 | 506.70 | 506.70 | YES | YES |
| 5 | ZYDUSLIFE.NS | Pharma | +5.58% | 991.70 | 963.95 | 963.95 | YES | YES |

**Universe summary (187/188 processed; LTIM.NS delisted at Yahoo):**
- Broke 5-day pivot high (today's HIGH > prior 5d max): **33 stocks**
- Broke 10-day pivot high: **30 stocks**
- Top-30 gainers that broke 5d pivot: **14**
- Top-30 gainers that broke 10d pivot: **13**

## Methodological note — the spec's test does NOT match UP_TRI

The task asked about **pivot HIGH breaks** as a proxy for UP_TRI candidates. After reading `scanner/scanner_core.py:322-377`, UP_TRI is actually a **pivot-LOW** detection (higher-low / bottoming pattern), not a pivot-high breakout:

- UP_TRI fires when at `pb = last_bar - age - LB` (LB=10, age 0-3) there is a confirmed `pivot_low` and `current_close > pivot_low - 1.0 * ATR`.
- A `pivot_low` is confirmed when `lows[pb] == min(lows[pb-10 : pb+11])` — i.e. the lowest in a 21-bar window centered on `pb`.

So I ran a second pass with the correct definition.

## Second pass — actual UP_TRI definition

Recomputed on the same universe with the scanner's geometric rule:

- **22 stocks meet the UP_TRI precondition today** (confirmed pivot_low at age 0-3, current close > stop).
- 18 of the 22 have the pivot_low at **2026-04-30** (the bottom of the recent drawdown).
- Examples: BAJAJ-AUTO.NS (entry 10451 vs stop 9138 — 14% above stop), THERMAX.NS (entry 4598 vs stop 3747), LAURUSLABS.NS (entry 1316 vs stop 1050). These have massive entry-vs-stop buffers and cannot fail any geometric check.

Full candidate list is in `output/up_tri_investigation_2026_05_14.json` under `up_tri_actual_definition.candidates`.

## What the production filters would do

Inspected `data/mini_scanner_rules.json` and `scanner/mini_scanner.py`:

- `shadow_mode: true`
- All 7 rules (`min_score`, `min_rr`, `regime_alignment`, `require_volume`, `grade_gate`, `clean_air`, `delivery_volume`) have `active: false`.
- Only `kill_001` (DOWN_TRI + Bank) and `kill_002` (DOWN_TRI universal) are active — both target DOWN_TRI exclusively.

**UP_TRI signals would face zero active filters** in production. Raw UP_TRI candidates should pass through to `scan_log.signals` directly.

`output/rejected_log.json` for today (2026-05-14): 8 entries, all DOWN_TRI, all `kill_switch`. No UP_TRI rejections anywhere — including the shadow channel.

## Verdict

**LIKELY SCANNER BUG. Needs investigation before next session.**

Three independent pieces of evidence point to this:

1. **22 valid candidates exist** per the scanner's own geometric definition (pivot_low + current close > stop). Several have an entry-to-stop buffer of >10%, so no atr-related edge case can disqualify them.
2. **There are no active filters that touch UP_TRI** — neither in mini_scanner_rules.json nor in scan_log.rejected nor in rejected_log.json.
3. **Same logic produced 9 UP_TRI on May 9** (5 trading days ago). Most of today's 22 candidates use the Apr 30 pivot_low, which also existed on May 9 — so the candidate pool wasn't structurally different.

**Possible root causes (not investigated tonight — production code untouched per task constraints):**

- `prepare(sym, period='1y')` may filter or alter recent bars (corporate-action skip, holiday handling) in a way that breaks `pivot_low` detection for the Apr 30 anchor.
- `add_indicators` ATR series (`atrS`) may differ from the 14-period rolling-mean ATR I used; an inflated ATR would push `stop = pivot_low - ATR` below the entry but a NaN/zero ATR would silently skip the signal.
- Stale OHLCV cache: if the scanner reads cached data not refreshed after the EOD close, today's bar (or recent bars) may be missing, shifting `last_bar`.

**Recommended next step:** run `scanner/deep_debugger.py` (or a single-stock trace) on BAJAJ-AUTO.NS for today. The entry/stop buffer is so large that ATR / data quirks are the only paths to suppression; either yields a clear single answer.

**Caveat:** signal-generation discrepancies between an external yfinance replay and the production scanner can also come from data-source differences (split adjustment, dividend treatment, intraday vs EOD close). Before declaring a bug, the right move is a single-stock side-by-side. But the 22-vs-0 gap is too wide for "noise."
