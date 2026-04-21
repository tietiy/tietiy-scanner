# TIE TIY Engineering Dock

**Purpose:** Single source of truth for what’s being built, shipped, and considered.
**Owner:** Abhishek (decisions) + Claude (proposals)
**Update frequency:** Daily during active development.

-----

## 🚢 CURRENT STATE

**Last ship:** 2026-04-20 — Apr 20 intelligence bundle (contra_tracker, rule_proposer, weekly_intelligence + workflow updates). Three of five new features **silently broken** — see Open Incidents.
**Production status:** STABLE for core trading loop. **DEGRADED for intelligence/learning loop.**
**Phase:** Phase 2 UNLOCKED (118 live resolved, 81% WR, avg +4.02%/trade)
**Open incidents:** 5 critical (C-01 through C-05) — see below

-----

## 🟢 SHIPPED (last 30 days)

|Date      |Release                                                                  |Files   |Status                                                    |
|----------|-------------------------------------------------------------------------|--------|----------------------------------------------------------|
|2026-04-20|Intelligence bundle: contra_tracker + rule_proposer + weekly_intelligence|11 files|🔴 3 of 5 features broken — audit flagged C-01 through C-04|
|2026-04-19|Session 3: Kill + Contra + Proposer + Brief                              |15 files|✅ Stable (except items moved to C-series)                 |
|2026-04-19|Phase A + Phase B (Pattern Miner, eod_master)                            |14 files|✅ Stable                                                  |
|2026-04-18|recover_stuck_signals.py + workflow (manual run cleared Apr-17 backlog)  |2 files |✅ Used once, stable                                       |
|2026-04-17|V2 53/53 (cache, UI, workflows)                                          |11 files|✅ Stable                                                  |
|2026-04-10|Bugs B1-P1                                                               |8 files |✅ Stable                                                  |

-----

## 🟡 PENDING REVIEW

*Claude writes here. Abhishek approves/rejects.*

**Post-audit fix plan (approved by Abhishek 2026-04-20):**

- **Session A queued (9 items):** C-02 → C-01 → C-03 → C-04 → D1 → M-11 → L-05 → UX-01 → P-01. All size S. One sitting target.
- **Session B queued (10 items):** C-05 + unification/debt items
- **Session 4 queued:** New UI build (12 items)
- **Session C queued:** Quality + polish

Full list: see `doc/fix_table.md`.

-----

## 🔴 BLOCKED / NEEDS DISCUSSION

### Active blockers (new — from Apr 20 audit)

- **Intelligence loop non-functional** — 3 critical bugs (C-01, C-02, C-03) prevent contra_shadow + rule_proposer from producing any usable data. Human-approval gate (C-04) broken. Fix blocks Phase 3 & Phase 4 readiness.
- **`eod_prices.json` primary-source optimization is dead code** — schema mismatch (C-05) means `outcome_evaluator` silently falls back to yfinance on every resolve. This is the exact fragility that caused the Apr 17 stuck-signal incident.
- **Contra shadow zero-samples problem** — Phase 4 activation needs n≥20 resolved contra shadows. Zero have been captured to date due to C-01+C-03. Every day Session A isn’t shipped, Phase 4 schedule slips.

### Existing blockers (unchanged)

- **Regime classifier rewrite** — waiting for 7 days of regime_debug.json data. Logging started Apr 19.
- **Contra shadow activation** — waiting for n=20 samples (0 today due to C-01+C-03 — will start accumulating after Session A).
- **DOWN_TRI validation** — live WR 18% vs 87% backtest. kill_001 active on Bank sector. If patterns.json still shows <50% WR after n=20 beyond Bank, permanent kill across all sectors.

### Behavioral blocker (new)

- **P-01: Trader P&L reconciliation ritual missing** — roadmap success metric requires broker-statement correlation against scanner outcomes. Not happening yet. 90-day validation cannot complete without this. Needs 15 min/week ritual, 3-column Google Sheet.

-----

## 🎯 NEXT RELEASE CANDIDATES (not yet proposed)

*Existing list — unchanged:*

- **Auto-apply pattern rules** — currently manual via /approve_rule, could be automatic once confidence is high (requires Session A done + n≥20 validation)
- **Intraday consolidation** — intraday_master.yml absorbing ltp_updater + stop_check
- **Morning consolidation** — morning_master.yml absorbing morning_scan + scan_watchdog + open_validate
- **New UI refresh** — Session 4 plan (12 UI files, 5 new)
- **Score recalibration** — Phase 3 when n≥100 live resolved (P-03 in fix table)
- **Portfolio correlation** — Phase 3/4 when multi-position tracking needed (P-02)

-----

## 📋 DAILY CHECK-IN TEMPLATE

Copy-paste this to our chat each day:

```
Date: ____
Morning scan fired: Y/N
Brief received: Y/N
Open validator ran: Y/N
Stop alerts today: ___
EOD master succeeded: Y/N
Weekly intelligence (Sundays): Y/N

P&L reconciliation (weekly ritual):
- Signals taken this week: ___
- Scanner claimed outcomes: ___W ___L
- Actual broker P&L: ₹___
- Delta vs claimed: ____

Issues observed: ____
Working on: ____
```

-----

## 🔎 AUDIT FINDINGS (2026-04-20 — new section)

Master audit of full codebase + data contracts + workflow chains completed Apr 20 2026. **32 findings → 39 after trader-journey UX layer added.**

### Critical findings (must fix — Session A)

|ID      |Problem                                                            |Impact                                                        |
|--------|-------------------------------------------------------------------|--------------------------------------------------------------|
|**C-01**|`contra_tracker.py` writes to `scanner/output/` (relative path bug)|Every contra shadow goes to disposable directory              |
|**C-02**|`rule_proposer.py` reads/writes wrong directory (same bug class)   |EOD master step 7 is silent no-op; no proposals ever generated|
|**C-03**|Contra shadow writer/reader schema mismatch                        |Every shadow skipped on resolution as “missing fields”        |
|**C-04**|`approve_proposal` returns tuple; handler calls `.get()`           |`/approve_rule` throws AttributeError on every invocation     |
|**C-05**|`eod_prices.json` schema mismatch between writer and 3 readers     |EOD1 primary-source dead; yfinance fallback on every resolve  |

### High-impact findings (Session A + B)

|ID       |Problem                                                                                     |Tier      |
|---------|--------------------------------------------------------------------------------------------|----------|
|**H-03** |Four files implement their own `_is_trading_day` logic                                      |Code      |
|**H-06** |Sector taxonomy: 14 CSV tags vs 8 tracked — ~45 stocks never earn sec_leading bonus         |Data      |
|**H-07** |`eod_prices_writer` + `stop_alert_writer` bypass `price_feed` abstraction                   |Code      |
|**H-08** |`backup_manager.yml` weekday cron overlaps `eod_master` step 1                              |Workflow  |
|**H-09** |`date.today()` UTC used in 5+ files despite prior IST fixes                                 |Code      |
|**D1**   |`KPIL.NS,Infrastructure,<same grade>` — literal placeholder in grade column                 |Data      |
|**D3**   |`kill_001.sector="Bank"` covers 38 stocks (banks+NBFCs+insurance+exchanges) on n=11 evidence|Data      |
|**UX-01**|Morning brief missing open-position P&L — trader must run /pnl separately                   |Trader    |
|**UX-02**|Gap report arrives 12 min after morning brief                                               |Trader    |
|**P-01** |No trader P&L reconciliation ritual                                                         |Behavioral|

### Cross-cutting patterns observed

- **Relative-path bug pattern** — 2 files (both Apr 20 ships) use bare-relative paths; 15+ others use `_HERE/_ROOT` correctly. Suggests a ship-checklist gap: “verify every new JSON output appears at repo root, not in scanner/”.
- **UTC-vs-IST pattern** — 5 files still use `date.today()` despite 4 prior IST-fix commits elsewhere. The fix wasn’t universalized.
- **Holiday-logic fragmentation** — 4 files have their own `_is_trading_day`; F1 unified only 2.
- **IST helper duplication** — 5 files each declare their own `_IST_OFFSET` / `_ist_now`. No shared module.
- **Dead-letter optimizations** — `outcome_evaluator` EOD1 fast path and `price_feed` 5paisa abstraction both look wired but aren’t. Two “optimizations” that optimize nothing.

Full findings: `doc/fix_table.md`.

-----

## 🧭 TRADER EFFECTIVENESS GAPS (2026-04-20 — new section)

Audit specifically asked: *does this system help a trader, and is it enough?*

### What the system does well for the trader

1. **Decision compression** — 188 stocks → 7 top setups in one morning Telegram
1. **Discipline enforcement** — fixed stop, fixed 6-day exit, no moving stop
1. **Exit memory** — Day 6 reminders, no forgotten exits
1. **Honest feedback** — real WR from real resolutions, no cherry-pick
1. **Regime awareness** — Bull/Bear/Choppy tagged, adjusts scoring
1. **Quality gates** — corporate action skip, F&O ban skip, gap skip at entry

### Gaps that reduce trader effectiveness

1. **Morning brief doesn’t include open-position P&L** — extra step at decision moment (UX-01)
1. **Open validator report arrives 12 min after brief** — trader has already entered (UX-02)
1. **EOD Telegram doesn’t surface `failure_reason`** — learning delayed to weekly (UX-03)
1. **No “target near” intraday alert** — DOWN_TRI shorts especially vulnerable to pullback (UX-04)
1. **R:R in signal card uses scan_price, not actual_open** — drifts by entry time (UX-05)
1. **No correlation / cluster-risk awareness** — 58 open positions, one regime shock could take many together (P-02)
1. **Score calibration not wired to live WR** — pattern_miner knows but scorer doesn’t learn (P-03)
1. **No order-execution deeplink to broker** — manual copy-paste friction (UX-06)

### Behavioral gap (non-code)

1. **P-01: P&L reconciliation ritual missing** — scanner claims 81% WR, but broker-statement reconciliation is not happening. The 90-day validation phase cannot complete without this. Needs weekly 15-min discipline.

-----

## 🎯 VISION ALIGNMENT CHECK (2026-04-20 — new section)

Current roadmap phase: **Prove Edge (Personal Use), 90-day validation, Apr 2026 – Jul 2026.**

### Phase 3 (May–Jun) readiness

|Requirement                            |Status    |Notes                                                          |
|---------------------------------------|----------|---------------------------------------------------------------|
|yfinance retry with fallback chains    |🟡 Partial |`price_feed.py` exists but 2/3 callers bypass it (H-07)        |
|Regime classifier rewrite (7 days data)|🟢 On track|Logging active since Apr 19                                    |
|Auto-apply validated patterns          |🔴 Blocked |Manual gate (/approve_rule) broken (C-04), let alone automation|
|Self-diagnostic /status command        |🟡 Partial |/health exists, /status needs building                         |

### Phase 4 (Jul) readiness — Activate Contra

|Requirement               |Status   |Notes                                                                               |
|--------------------------|---------|------------------------------------------------------------------------------------|
|Contra_shadow samples n≥20|🔴 Blocked|Currently n=0 due to C-01+C-03. Zero data accumulating per day until Session A ships|

### Phase 5 (Aug–Sep) readiness — Evaluate Commercial Viability

|Requirement                                 |Status   |Notes                                                              |
|--------------------------------------------|---------|-------------------------------------------------------------------|
|90-day P&L review with broker reconciliation|🔴 Blocked|P-01: no ritual established. Must start before 30-day window closes|

### Conclusion

Phase 3 is mechanically on track but behaviorally stalled. **Fix Session A and Phase 3 & 4 become achievable on schedule. Skip Session A and they slip a month each.** Phase 5 depends entirely on P-01 — a behavioral change, not code.

-----

## 📌 RECOMMENDED BEHAVIORAL ADDITIONS (2026-04-20 — new section)

These are habits/rituals, not code. Equally important to the codebase for vision success.

### 1. Weekly P&L reconciliation (P-01)

**Every Sunday, 15 minutes, 3-column Google Sheet:**

|Date|Scanner-claimed outcome (W/L/F + pnl_pct)|Actual broker P&L (₹)|
|----|-----------------------------------------|---------------------|

After 4 weeks, compare totals. If scanner WR 81% but actual P&L break-even — slippage or execution issues dominate. If both align — edge is real, ready for Phase 3 investment.

**Without this:** the 81% WR claim is unverified and Phase 5 cannot reach its exit criterion.

### 2. Before adding new features, check Session A status

Don’t ship new intelligence/learning features on top of C-01..C-05. The new features will be broken by the same underlying issues. Pattern: fix the loop, then extend it.

### 3. After any new JSON output file, smoke-test end-to-end

Include a checklist step: “run one scan locally, verify the new file appears at `repo/output/` (not `scanner/output/`), verify the intended consumer reads it and produces expected downstream effect.” The Apr 20 ship skipped this and shipped 3 broken features.

-----

## 🗂 SESSION HISTORY

|Session               |Scope                                                     |Items    |Status                                                  |
|----------------------|----------------------------------------------------------|---------|--------------------------------------------------------|
|Phase 2 Session 1     |Outcome resolution Day 6 open price (OE1/D6A/OE3)         |Apr 16-17|✅ Done                                                  |
|Phase 2 Session 2     |pattern_miner + chain_validator + eod_master consolidation|Apr 19   |✅ Done                                                  |
|Phase 2 Session 3     |Kill switch + contra + proposer + brief + weekly review   |Apr 19-20|🟡 Partial (3 of 5 features broken — C-01/C-02/C-03/C-04)|
|**Session A (queued)**|Unblock intelligence loop + close biggest UX friction     |9 items  |⏳ Approved, awaiting start                              |
|Session B (queued)    |C-05 + unify debt + close remaining UX gaps               |10 items |⏳ Queued                                                |
|Session 4 (queued)    |New UI build                                              |12 items |⏳ Queued (after Session B)                              |
|Session C (queued)    |Quality + polish                                          |11 items |⏳ Queued                                                |

-----

## 📎 REFERENCE DOCS

- `doc/session_context.md` — drop-in context for any new chat (read this first in a fresh session)
- `doc/fix_table.md` — 39-item execution plan grouped by session
- `doc/roadmap.md` — quarterly vision
- `doc/regression_log.md` — what broke, why, how fixed
- `doc/engineering_dock.md` — this file — living decision log

-----

## CHANGE LOG

|Date      |Change                                                                                                                                           |Author                    |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------|
|2026-04-20|Added audit findings, trader effectiveness gaps, vision alignment check, behavioral additions, session history. Preserved pre-existing structure.|Claude (post-master-audit)|
|2026-04-19|Initial creation by Abhishek                                                                                                                     |Abhishek                  |
