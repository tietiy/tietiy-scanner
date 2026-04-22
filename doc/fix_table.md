# TIE TIY Fix Table

**Purpose:** Single source of truth for all known issues, fixes, and trader-effectiveness gaps.
**Owner:** Abhishek (decisions) + Claude (execution)
**Last updated:** 2026-04-23 (post-Wave 2/3/5.1 session)
**Canonical status:** Use this file + `wave_execution_log_2026-04-23.md` for "what's on the fix list?"

> **⚠️ Reconstruction note (2026-04-23):** This file was rewritten after the Wave 2/3/5.1 session to reflect 16 VERIFIED items. Search-based reconstruction covered ~90% of original. If any H-tier row (H-01, H-02, H-10+) appears missing vs git history, reinstate from prior revision. Row integrity was preserved for all rows visible during rewrite.

-----

## Summary

- **Total items: 39**
- **🔴 Critical:** 5 items — **0 PENDING · 5 VERIFIED** ✅
- **🟠 High:** 14 items — 9 PENDING · 5 VERIFIED (H-03, H-05/D1, H-08, H-09, UX-01)
- **🟡 Medium:** 13 items — 8 PENDING · 5 VERIFIED (M-01, M-06, M-07, M-08, M-11)
- **🟢 Low:** 5 items — 4 PENDING · 1 VERIFIED (L-05)
- **⚪ Deferred design:** 2 items — awaiting discussion

**Phase state:** Phase 2 unlocked (118 live resolved, 81% WR). Intelligence loop functional end-to-end after 2026-04-23 session.

-----

## Status Legend

- **PENDING** — not started
- **IN PROGRESS** — currently being fixed
- **FIXED** — code shipped, not yet verified live
- **VERIFIED** — confirmed working in production
- **DEFERRED** — intentionally pushed to later phase
- **DROPPED** — reconsidered, not a real issue
- **SKIPPED** — user decision to not address

-----

## 🔴 CRITICAL — silently broken features (Session A) — ALL VERIFIED

|#|ID      |Title                                                                                                                                                                                                                                           |File(s)                                      |Effort|Status                              |
|-|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|------|------------------------------------|
|1|**C-01**|`contra_tracker` writes to `scanner/output/` instead of repo `output/` (relative path bug, 3 constants)                                                                                                                                         |`contra_tracker.py`                          |S     |✅ VERIFIED (2026-04-21)             |
|2|**C-02**|`rule_proposer` reads/writes wrong directory — step 7 of eod_master is silent no-op                                                                                                                                                             |`rule_proposer.py`                           |S     |✅ VERIFIED (2026-04-21)             |
|3|**C-03**|Contra shadow schema mismatch — writer uses `direction`/`entry`/`stop`, reader expects `original_direction`/`inverted_direction`/`entry_est`. All shadows skip as "missing fields"                                                              |`contra_tracker.py` + `outcome_evaluator.py` |S     |✅ VERIFIED (2026-04-21, schema_v2)  |
|4|**C-04**|`approve_proposal` returns tuple but `/approve_rule` handler calls `.get()` → AttributeError every call. Human approval gate broken                                                                                                             |`rule_proposer.py` + `telegram_bot.py`       |S     |✅ VERIFIED (2026-04-21, dict return)|
|5|**C-05**|`eod_prices.json` schema mismatch — writer produces `{date, results:[]}`, three readers assume `{sym:{date:{ohlc}}}`. EOD1 primary-source optimization is dead code — always falls back to yfinance (same fragility that caused Apr 17 incident)|`outcome_evaluator.py` + `chain_validator.py`|M     |✅ VERIFIED (2026-04-21, schema_v2 + reader adapter)|

-----

## 🟠 HIGH — affects results or trader effectiveness (Session A + B)

### H tier — code/logic bugs

|# |ID            |Title                                                                                                                                                   |File(s)                                                                                          |Effort|Status                                    |
|--|--------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|------|------------------------------------------|
|6 |**H-03**      |4 files implement their own `_is_trading_day` — F1 fix unified only 2. One holiday config change must be made in multiple places                        |`open_validator.py`, `outcome_evaluator.py`, `ltp_writer.py`, `heartbeat.py`                     |M     |✅ VERIFIED (2026-04-23, Wave 2)           |
|7 |**D1** (=H-05)|`KPIL.NS,Infrastructure,<same grade>` — literal placeholder in grade column, wrong sector string. Grade-gate never passes KPIL; sec_mom always 'Neutral'|`data/fno_universe.csv`                                                                          |S     |✅ VERIFIED (2026-04-23, Wave 3, grade=B)  |
|8 |**D3** (=H-04)|`kill_001.sector="Bank"` covers 38 stocks (banks + NBFCs + insurance + exchanges) on n=11 bank-only evidence                                            |`data/mini_scanner_rules.json` + `data/fno_universe.csv`                                         |M     |PENDING                                   |
|9 |**H-06**      |Sector taxonomy: 14 tags in CSV but only 8 tracked in `SECTOR_INDICES` — ~45 stocks always get `sec_mom='Neutral'`, never earn sec_leading bonus        |`data/fno_universe.csv` + `main.py`                                                              |M     |PENDING                                   |
|10|**H-07**      |`eod_prices_writer` + `stop_alert_writer` bypass `price_feed.py` — 5paisa swap would only be partial                                                    |`eod_prices_writer.py`, `stop_alert_writer.py`                                                   |M     |PENDING                                   |
|11|**H-08**      |`backup_manager.yml` weekday schedule (16:00 IST) overlaps `eod_master` step 1 (15:35 IST) — double backups + push contention                           |`.github/workflows/backup_manager.yml`                                                           |S     |✅ VERIFIED (2026-04-22, Saturday-only)    |
|12|**H-09**      |`date.today()` UTC used in 5+ files despite prior TB1/LW1/EP1/SA2 IST fixes elsewhere. Signal dates can drift on UTC-midnight runs                      |`main.py`, `journal.py`, `outcome_evaluator.py`, `weekend_summary.py`, `recover_stuck_signals.py`|M     |✅ VERIFIED (2026-04-23, Wave 2, 11 files) |

### UX tier — trader-effectiveness gaps (from end-to-end audit)

|# |ID       |Title                                                                                                 |Impact                                                                            |Effort        |Status                                    |
|--|---------|------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|--------------|------------------------------------------|
|13|**UX-01**|Morning brief missing open-position P&L summary — trader must run `/pnl` separately                   |One less Telegram round-trip at 8:47 AM decision moment                           |S             |✅ VERIFIED (2026-04-21, _enrich_with_pnl) |
|14|**UX-02**|Open validator gap report arrives 12 min after morning brief — trader has already placed entries      |Wrong R:R for gap-skipped signals already entered                                 |M             |PENDING                                   |
|15|**P-01** |No trader P&L reconciliation ritual — scanner claims 81% WR but no broker-statement correlation exists|Vision success metric unmeasurable. 90-day validation cannot complete without this|S (behavioral)|⚪ SKIPPED (user decision 2026-04-23)      |

-----

## 🟡 MEDIUM — technical debt + future risk (Session B + C)

### F-series (existing, from memory)

|# |ID            |Title                                                                      |File(s)               |Effort|Status       |
|--|--------------|---------------------------------------------------------------------------|----------------------|------|-------------|
|16|**F2** (=M-03)|`parent_signal_id` legacy field still written; `sa_parent_id` supersedes it|`journal.py`          |S     |DEFER V6     |
|17|**F3** (=M-04)|Stop-alert dedup — intraday re-breach after recovery currently swallowed   |`stop_alert_writer.py`|M     |DESIGN NEEDED|

### M tier — technical debt

|# |ID      |Title                                                                                                                                            |File(s)                                                                                                |Effort|Status                                          |
|--|--------|-------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|------|------------------------------------------------|
|18|**M-01**|`_load_eod_prices` / `_load_open_prices` docstrings state wrong schema                                                                           |`outcome_evaluator.py`                                                                                 |S     |✅ VERIFIED (2026-04-21, folded with C-05)       |
|19|**M-02**|Atomic-write pattern inconsistent — some writers use direct `open()`, others use `.tmp`+`os.replace`                                             |`eod_prices_writer.py`, `stop_alert_writer.py`, `ban_fetcher.py`, `open_validator.py`                  |M     |PENDING                                         |
|20|**M-05**|`chain_validator` doesn't check `proposed_rules.json` or `contra_shadow.json` → false "healthy" status                                           |`chain_validator.py`                                                                                   |M     |PENDING                                         |
|21|**M-06**|`_ist_now`/`_ist_today`/`_IST_OFFSET` duplicated in 5 files                                                                                      |`ltp_writer.py`, `stop_alert_writer.py`, `eod_prices_writer.py`, `telegram_bot.py`, `open_validator.py`|S     |✅ VERIFIED (2026-04-23, Wave 2, calendar_utils) |
|22|**M-07**|`html_builder` docstring references non-existent "Steps 17-20 write JS files"                                                                    |`html_builder.py`                                                                                      |S     |✅ VERIFIED (2026-04-21)                         |
|23|**M-08**|Telegram `_esc` escape duplicated in 4 files                                                                                                     |`telegram_bot.py`, `gap_report.py`, `deep_debugger.py`, `heartbeat.py` (+ `diagnostic.py`)             |S     |✅ VERIFIED (2026-04-23, Wave 5.1)               |
|24|**M-09**|`pattern_miner` O(n × 25 combos) will grow slow at ~2000 resolved signals                                                                        |`pattern_miner.py`                                                                                     |M     |PHASE 3                                         |
|25|**M-10**|`main.py` import block growing unwieldy (15+ journal helpers, 8 telegram helpers)                                                                |`main.py`, `journal.py`                                                                                |M     |PHASE 3                                         |
|26|**M-11**|`recover_stuck_signals` reads `TELEGRAM_BOT_TOKEN`; repo-wide convention is `TELEGRAM_TOKEN` (workflow maps correctly but script is non-standard) |`recover_stuck_signals.py` + workflow YAML                                                             |S     |✅ VERIFIED (2026-04-23, Wave 3)                 |

### UX/P tier — trader effectiveness (from audit)

|# |ID       |Title                                                                                         |Impact                                                               |Effort|Status           |
|--|---------|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------|------|-----------------|
|27|**UX-03**|EOD Telegram doesn't surface `failure_reason` — learning delayed to weekly intelligence report|Trader learns 4+ days slower than possible                           |S     |PENDING          |
|28|**UX-04**|No "target near" intraday alert — trader may miss early exit on target approach               |DOWN_TRI shorts especially vulnerable to pullback before close       |M     |PENDING          |
|29|**UX-05**|R:R shown in signal card uses `scan_price`, not `actual_open` — drifts after gap              |Trader sees stale R:R at entry time                                  |M     |PENDING          |
|30|**P-02** |Correlation blindness — 58 open positions, no sector-cluster risk check                       |One Nifty drop could take out 15+ correlated positions simultaneously|M     |PHASE 3/4        |
|31|**P-03** |Score calibration not wired to live WR — pattern_miner findings don't feed scorer formula     |UP_TRI Age 0 Bear scores same whether live WR is 60% or 98%          |L     |PHASE 3 Session 7|

-----

## 🟢 LOW — polish (Session C)

|# |ID      |Title                                                                                       |File(s)                             |Effort|Status                                |
|--|--------|--------------------------------------------------------------------------------------------|------------------------------------|------|--------------------------------------|
|32|**L-01**|`TELEGRAM_CHAT_ID` default hardcoded to `'8493010921'` in source                            |`telegram_bot.py`                   |S     |PENDING                               |
|33|**L-02**|Memory mentions `nightly_ops.yml` / `weekly_ops.yml` — only `weekly_intelligence.yml` exists|memory / `engineering_dock.md`      |S     |DOC ONLY                              |
|34|**L-03**|Many `"NEW (Session 3)"` markers now stale                                                  |multiple files                      |S     |PENDING                               |
|35|**L-04**|`master_check.yml` title claims counts that differ from reality                             |`.github/workflows/master_check.yml`|S     |PENDING                               |
|36|**L-05**|Workflow filename typo — `recover_struck_signals.yml` should be `recover_stuck_signals.yml` |`.github/workflows/`                |S     |✅ VERIFIED (2026-04-23, already correct in repo)|

-----

## ⚪ DEFERRED — Design Decisions (not bugs)

|# |ID       |Question                                                                                     |Needs                                                                |
|--|---------|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
|37|**D6**   |Grade refresh cadence — grades frozen since initial backtest. When/how to refresh?           |Decision on cadence (quarterly? after n≥N resolved?) + refresh script|
|38|**D7**   |Dynamic grading via `pattern_miner` — replace CSV grades with data-driven grades from live WR|Phase 3/4 — needs n≥50 per stock before viable                       |
|39|**UX-06**|Order-execution deeplink to broker (Zerodha/5paisa) — reduce copy-paste friction             |Needs broker API research — liability/scope decision first           |

-----

## Execution Plan

### Session A — Unblock intelligence loop + fix UX friction — ✅ COMPLETE

All 9 items shipped. P-01 skipped by user decision (2026-04-23).

|Order|ID   |Status                                       |
|-----|-----|---------------------------------------------|
|1    |C-02 |✅ VERIFIED                                   |
|2    |C-01 |✅ VERIFIED                                   |
|3    |C-03 |✅ VERIFIED                                   |
|4    |C-04 |✅ VERIFIED                                   |
|5    |D1   |✅ VERIFIED                                   |
|6    |M-11 |✅ VERIFIED                                   |
|7    |L-05 |✅ VERIFIED (never had typo)                  |
|8    |UX-01|✅ VERIFIED                                   |
|9    |P-01 |⚪ SKIPPED (user decision)                    |

### Session B — Unify technical debt + close remaining UX gaps — 🟡 PARTIAL (8 of 10)

|Order|ID   |Title                                               |Status                          |
|-----|-----|----------------------------------------------------|--------------------------------|
|10   |C-05 |eod_prices schema adapter                           |✅ VERIFIED (Apr 21)             |
|11   |M-01 |Fix outcome_evaluator docstrings (fold w/ C-05)     |✅ VERIFIED (Apr 21)             |
|12   |H-03 |Centralize trading-day logic in calendar_utils      |✅ VERIFIED (Apr 23, Wave 2)     |
|13   |H-09 |Replace `date.today()` with `ist_today()` everywhere|✅ VERIFIED (Apr 23, Wave 2)     |
|14   |M-06 |Consolidate IST helpers                             |✅ VERIFIED (Apr 23, Wave 2)     |
|15   |M-07 |Fix html_builder docstring                          |✅ VERIFIED (Apr 21)             |
|16   |H-08 |Drop backup_manager weekday cron                    |✅ VERIFIED (Apr 22)             |
|17   |UX-02|Fold gap-skip summary into morning brief            |PENDING                         |
|18   |UX-03|Surface failure_reason in EOD Telegram              |PENDING                         |
|19   |UX-05|R:R recalc at actual_open in signal card            |PENDING                         |

### Session 4 — UI build (multi-sitting) — PENDING

12 UI items (UI2–UI12) per memory entry 29. New tab structure, time-aware modes, Fraunces + Geist fonts.

### Session C — Quality + polish (after UI)

|Order|ID                    |Title                               |Status                              |
|-----|----------------------|------------------------------------|------------------------------------|
|20   |D3                    |Narrow kill_001 scope               |PENDING                             |
|21   |H-06                  |Sector taxonomy unification         |PENDING                             |
|22   |H-07                  |Route eod_writers through price_feed|PENDING                             |
|23   |M-02                  |Standardize atomic-write helper     |PENDING                             |
|24   |M-05                  |Extend chain_validator coverage     |PENDING                             |
|25   |M-08                  |Consolidate Telegram _esc           |✅ VERIFIED (Apr 23, Wave 5.1 — promoted to Session B ship) |
|26   |UX-04                 |Intraday target-near alert          |PENDING                             |
|27–30|L-01, L-02, L-03, L-04|Polish items                        |PENDING                             |

### Phase 3+ — Deferred

- F2, F3 — design-decision gated
- M-09, M-10 — scale-gated
- P-02 — correlation detection (session 8)
- P-03 — score calibration (session 7)
- D6, D7 — grade refresh strategy
- UX-06 — broker integration scope decision

-----

## What NOT to fix (intentional, do not touch)

- Dual scoring constants `config.py` vs `scorer.py` — represent backtest baseline vs current weights, intentionally different.
- `mini_scanner.DEFAULT_RULES` — graceful fallback when JSON corrupt, keep.
- `parent_signal_id` + `sa_parent_id` dual-write — legacy migration safety, drop at V6.
- `eod_master.yml` + `eod_update.yml.bak` coexistence — rollback escape hatch, keep.
- `main.py` STEP numbering comments — navigation aid for 500-line function.
- `push_sender` 3-value return (True/False/None) — None signals 410 Gone for sub cleanup.
- `_already_validated_today` still triggers D6B — entries vs exits are separate concerns, keep.
- `signal_history.json.backup.json` + `backups/` dated — two recovery horizons, keep both.
- `recover_stuck_signals.yml` mapping line `TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}` — removed in Wave 3 (M-11), no longer applies.

-----

## Verification Notes

- `verify_fixes.py` + `verify_fixes.yml` do NOT exist — planned but not built. AICREDITS_API_KEY not set.
- Master Check covers Tier 1 (syntax), Tier 2 (imports), Tier 3 (safe execution + 7 inline validations) — **no logic-validation layer exists yet**.
- After each fix: run Master Check manually, confirm green. That's the current verification gate.
- **New (2026-04-23):** Automated pattern migrations run via `scripts/wave2_migration.py` + `scripts/wave5_m08_migration.py` with workflow dispatch — backup + syntax-check + rollback-on-failure built in.

-----

## Change Log

|Date      |Change                                                                                                                                                                                         |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|2026-04-20|Initial creation after master audit. 39 items locked.                                                                                                                                          |
|2026-04-23|Wave 2/3/5.1 session — 16 IDs VERIFIED (C-01..C-05, H-03, H-05/D1, H-08, H-09, M-01, M-06, M-07, M-08, M-11, L-05, UX-01). P-01 SKIPPED per user decision. Summary counts and Session A/B status tables updated. See `doc/wave_execution_log_2026-04-23.md` for canonical session record.|
