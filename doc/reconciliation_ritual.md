# TIE TIY — Weekly P&L Reconciliation Ritual

**Purpose:** Validate that scanner's claimed outcomes match real trading P&L.
**Cadence:** Every Sunday, ~15 minutes.
**Started:** 2026-04-21
**Owner:** Abhishek

---

## Why this exists

The scanner tells me it has 81% WR and +4%/trade avg. That number is only trustworthy if it matches what my broker actually paid me. This ritual closes the loop between scanner claims and real P&L.

Without this ritual, the 90-day edge-validation phase (Apr 2026 → Jul 2026) cannot complete, because there is no ground truth to compare scanner outcomes against.

---

## The Sheet

A single Google Sheet titled `TIE TIY — P&L Reconciliation`. One tab per month.

### Columns

| Date | Symbol | Signal | Scanner outcome | Scanner P&L % | Broker P&L ₹ | Notes |
|---|---|---|---|---|---|---|

**One row per signal I actually took.** Not rejected. Not skipped. Only the ones where I placed a real order.

### Column rules

- **Date** — entry date (9:15 AM of Day 1)
- **Symbol** — e.g., `HDFCBANK.NS`
- **Signal** — `UP_TRI`, `DOWN_TRI`, `BULL_PROXY`
- **Scanner outcome** — one of: `TARGET_HIT`, `STOP_HIT`, `DAY6_WIN`, `DAY6_LOSS`, `DAY6_FLAT`
- **Scanner P&L %** — from the scanner's `pnl_pct` field
- **Broker P&L ₹** — net after brokerage, STT, GST. From broker statement. Rupees, not percent.
- **Notes** — anything odd: slippage, partial fill, exit delay, skipped exit, overnight gap, wrong hand

---

## The 15-minute Sunday ritual

Every Sunday evening. Pick a consistent time — 8 PM IST after the weekly_intelligence Telegram arrives.

1. **Open the scanner's Journal tab** on tietiy.github.io/tietiy-scanner/ — filter "Resolved this week"
2. **Open the broker contract notes** for the past week (Zerodha Console / 5paisa)
3. **For each signal I took that resolved this week:**
   - Find the matching broker buy + sell pair
   - Record scanner's claimed outcome and P&L%
   - Record broker's actual net P&L in ₹
   - Note anything weird
4. **Do NOT add rows for signals I did not take.** Skipped ones don't count.
5. **Sum the month totals** at the bottom of each tab

---

## What to look for (the monthly review)

First Sunday of each month, look at last month's totals:

### Green lights (edge is real)

- Scanner wins = broker wins on the same days
- Broker P&L totals to net positive
- Slippage column stays small (avg <0.5%)
- Win rate on broker side within ±5% of scanner's claim

### Red flags (edge is NOT what scanner says)

- **Scanner WR 80%+ but broker P&L flat or negative** → slippage or execution issues are eating the edge. Investigate.
- **Scanner wins but I didn't place the trade** → behavioral issue. I'm cherry-picking. That breaks the backtest.
- **Broker wins but scanner claimed flat/loss** → scanner's resolution logic is wrong. File a bug.
- **Gap days wreck the month** → entry validator or gap rule needs tightening.
- **One signal type (UP_TRI / DOWN_TRI / BULL_PROXY) consistently diverges** → that signal's live edge is different from backtest. Calibrate.

---

## Monthly one-liner I must write

At the end of each month, write one sentence in the sheet's summary cell:

> "April 2026: 12 signals taken, scanner claimed 9W/3L 75% · broker net ₹X,XXX (± Y% vs scanner claim). [One observation.]"

This becomes the Phase 5 evidence trail.

---

## What counts as a "pass" for Phase 5 exit criterion

By end of July 2026, I need:

- **Minimum 3 months of completed reconciliation** (May, June, July)
- **Broker net P&L positive** across those 3 months combined
- **Scanner WR within ±10% of broker-confirmed WR**
- **No signal type with broker WR under 50% at n≥15**

If all four pass: edge is real. Consider Phase 6 (commercial viability).
If any one fails: refine signals, do not scale.

---

## When to update this document

- If I miss a Sunday ritual → log it in engineering_dock.md under Daily Check-in
- If the 3-column structure proves insufficient → add a column, update this doc
- If I change my broker → note the switch date
- If a whole month gets skipped → acknowledge it broke the chain and restart

---

## What NOT to do

- **Do not backfill from memory.** If I didn't track it that week, leave it blank and note the gap.
- **Do not include signals I only wanted to take.** Only real orders on real money.
- **Do not adjust scanner outcomes to match broker.** They're independent records.
- **Do not stop the ritual early.** Even if early weeks look bad, 12 weeks of data beats 4 weeks of selective data.

---

## Change log

| Date | Change |
|---|---|
| 2026-04-21 | Created. Ritual starts this Sunday Apr 26. |
