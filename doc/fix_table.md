🎯 Full rewrite coming. Every single item, every phase, every investigation thread. This is the complete handoff doc.
One note before I write: this is going to be long — likely ~900 lines. I’m including everything so tomorrow’s fresh Claude has zero ambiguity. Single paste box below.

Full Rewrite — doc/fix_table.md
Replace the ENTIRE content of doc/fix_table.md with this:

# TIE TIY Fix Table

**Purpose:** Single source of truth for all known issues, fixes, trader-effectiveness gaps, sprint plan, and investigation threads.
**Owner:** Abhishek (decisions) + Claude (execution)
**Last updated:** 2026-04-24 (post-midnight planning session)
**Canonical status:** Use this file + `doc/wave_execution_log_2026-04-23.md` for "what's on the fix list?"

> **⚠️ Reconstruction note (2026-04-24):** This file was rewritten after Wave 2/3/5.1 session + 4-day sprint planning. Search-based reconstruction of original H-tier rows covered ~90%. If any H-01, H-02, H-10+ row existed in prior git history that is missing here, reinstate from prior revision.

-----

## Summary

- **Total items: 60** (original 42 + 18 new items from planning session)
- **🔴 Critical:** 5 items — **0 PENDING · 5 VERIFIED** ✅
- **🟠 High:** 14 items — 9 PENDING · 5 VERIFIED (H-03, H-05/D1, H-08, H-09, UX-01)
- **🟡 Medium:** 13 items — 8 PENDING · 5 VERIFIED (M-01, M-06, M-07, M-08, M-11)
- **🟢 Low:** 5 items — 4 PENDING · 1 VERIFIED (L-05)
- **🔵 AN-series (analysis GUI):** 3 items — AN-01 Day 1, AN-02 gated (Session 4), AN-03 deferred (HYDRAX)
- **🔵 MC-series (observability):** 3 items — MC-01 Day 4 framework, MC-02/03 Week 2
- **🟣 HL-series (auto-healer):** 5 items — HL-01 Day 4 framework, HL-02..05 Week 2
- **🔶 PIN-series:** 1 item — PIN-01 Day 1 diagnose, Day 2 fix
- **🟤 OPS-series (repo split):** 4 items — OPS-01..03 Day 2 execute, OPS-04 Day 3
- **🔷 TG-series:** 1 item — TG-01 Day 1 diagnose, Day 2 fix
- **🔺 BP-series:** 1 item — BP-01 Day 1 investigate, Day 2 rule if warranted
- **🟫 DQ-series (data quality):** 1 item — DQ-01 Day 2
- **🔬 INV-series (investigation threads):** 2 items — INV-01 (DOWN_TRI mystery), INV-02 (G-series catalog)
- **⚪ Deferred design:** 2 items — awaiting discussion

**Phase state:** Phase 2 unlocked (118 live resolved, 81% WR). Intelligence loop functional end-to-end after 2026-04-23 session. **4-day sprint begins 2026-04-24** to ship complete + steady + bug-free state.

-----

## Status Legend

- **PENDING** — not started
- **IN PROGRESS** — currently being fixed
- **FIXED** — code shipped, not yet verified live
- **VERIFIED** — confirmed working in production
- **DEFERRED** — intentionally pushed to later phase
- **DROPPED** — reconsidered, not a real issue
- **SKIPPED** — user decision to not address
- **GATED** — conditional on another item completing first

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
|8 |**D3** (=H-04)|`kill_001.sector="Bank"` covers 38 stocks (banks + NBFCs + insurance + exchanges) on n=11 bank-only evidence                                            |`data/mini_scanner_rules.json` + `data/fno_universe.csv`                                         |M     |PENDING (Day 2)                           |
|9 |**H-06**      |Sector taxonomy: 14 tags in CSV but only 8 tracked in `SECTOR_INDICES` — ~45 stocks always get `sec_mom='Neutral'`, never earn sec_leading bonus        |`data/fno_universe.csv` + `main.py`                                                              |M     |PENDING (Day 2)                           |
|10|**H-07**      |`eod_prices_writer` + `stop_alert_writer` bypass `price_feed.py` — 5paisa swap would only be partial                                                    |`eod_prices_writer.py`, `stop_alert_writer.py`                                                   |M     |PENDING (Week 2, pre-HYDRAX)              |
|11|**H-08**      |`backup_manager.yml` weekday schedule (16:00 IST) overlaps `eod_master` step 1 (15:35 IST) — double backups + push contention                           |`.github/workflows/backup_manager.yml`                                                           |S     |✅ VERIFIED (2026-04-22, Saturday-only)    |
|12|**H-09**      |`date.today()` UTC used in 5+ files despite prior TB1/LW1/EP1/SA2 IST fixes elsewhere. Signal dates can drift on UTC-midnight runs                      |`main.py`, `journal.py`, `outcome_evaluator.py`, `weekend_summary.py`, `recover_stuck_signals.py`|M     |✅ VERIFIED (2026-04-23, Wave 2, 11 files) |

### UX tier — trader-effectiveness gaps (from end-to-end audit)

|# |ID       |Title                                                                                                 |Impact                                                                            |Effort        |Status                                    |
|--|---------|------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|--------------|------------------------------------------|
|13|**UX-01**|Morning brief missing open-position P&L summary — trader must run `/pnl` separately                   |One less Telegram round-trip at 8:47 AM decision moment                           |S             |✅ VERIFIED (2026-04-21, _enrich_with_pnl) |
|14|**UX-02**|Open validator gap report arrives 12 min after morning brief — trader has already placed entries      |Wrong R:R for gap-skipped signals already entered                                 |M             |PENDING (Day 3)                           |
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
|19|**M-02**|Atomic-write pattern inconsistent — some writers use direct `open()`, others use `.tmp`+`os.replace`                                             |`eod_prices_writer.py`, `stop_alert_writer.py`, `ban_fetcher.py`, `open_validator.py`                  |M     |PENDING (Day 2)                                 |
|20|**M-05**|`chain_validator` doesn't check `proposed_rules.json` or `contra_shadow.json` → false "healthy" status                                           |`chain_validator.py`                                                                                   |M     |PENDING (Day 2)                                 |
|21|**M-06**|`_ist_now`/`_ist_today`/`_IST_OFFSET` duplicated in 5 files                                                                                      |`ltp_writer.py`, `stop_alert_writer.py`, `eod_prices_writer.py`, `telegram_bot.py`, `open_validator.py`|S     |✅ VERIFIED (2026-04-23, Wave 2, calendar_utils) |
|22|**M-07**|`html_builder` docstring references non-existent "Steps 17-20 write JS files"                                                                    |`html_builder.py`                                                                                      |S     |✅ VERIFIED (2026-04-21)                         |
|23|**M-08**|Telegram `_esc` escape duplicated in 4 files                                                                                                     |`telegram_bot.py`, `gap_report.py`, `deep_debugger.py`, `heartbeat.py` (+ `diagnostic.py`)             |S     |✅ VERIFIED (2026-04-23, Wave 5.1)               |
|24|**M-09**|`pattern_miner` O(n × 25 combos) will grow slow at ~2000 resolved signals                                                                        |`pattern_miner.py`                                                                                     |M     |PHASE 3                                         |
|25|**M-10**|`main.py` import block growing unwieldy (15+ journal helpers, 8 telegram helpers)                                                                |`main.py`, `journal.py`                                                                                |M     |PHASE 3                                         |
|26|**M-11**|`recover_stuck_signals` reads `TELEGRAM_BOT_TOKEN`; repo-wide convention is `TELEGRAM_TOKEN` (workflow maps correctly but script is non-standard) |`recover_stuck_signals.py` + workflow YAML                                                             |S     |✅ VERIFIED (2026-04-23, Wave 3)                 |

### UX/P tier — trader effectiveness (from audit)

|# |ID       |Title                                                                                         |Impact                                                               |Effort|Status           |
|--|---------|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------|------|-----------------|
|27|**UX-03**|EOD Telegram doesn't surface `failure_reason` — learning delayed to weekly intelligence report|Trader learns 4+ days slower than possible                           |S     |PENDING (Day 3)  |
|28|**UX-04**|No "target near" intraday alert — trader may miss early exit on target approach               |DOWN_TRI shorts especially vulnerable to pullback before close       |M     |PENDING (Week 2) |
|29|**UX-05**|R:R shown in signal card uses `scan_price`, not `actual_open` — drifts after gap              |Trader sees stale R:R at entry time                                  |M     |PENDING (Day 3)  |
|30|**P-02** |Correlation blindness — 58 open positions, no sector-cluster risk check                       |One Nifty drop could take out 15+ correlated positions simultaneously|M     |PHASE 3/4        |
|31|**P-03** |Score calibration not wired to live WR — pattern_miner findings don't feed scorer formula     |UP_TRI Age 0 Bear scores same whether live WR is 60% or 98%          |L     |PHASE 3 Session 7|

-----

## 🔵 AN tier — Analysis & Diagnostic GUI (NEW 2026-04-23)

### Full Scope for Each Stage

|# |ID       |Title                                                                                                                                              |File(s)                                        |Effort|Status |
|--|---------|---------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|------|-------|
|32|**AN-01**|**Stage 1 — SQL Query Feature on GitHub Pages.** `output/analysis.html` + `output/analysis.js`. Loads sql.js from CDN. Fetches signal_history.json from public Pages URL. Creates in-memory SQLite, INSERTs all signals into `signals` table. **Open-ended SQL textarea + Run button + results render as HTML table.** Ship as MVP brick — no presets, no charts yet.|`output/analysis.html` + `output/analysis.js`  |M     |PENDING (Day 1 ship)|
|33|**AN-02**|**Stage 2 — Preset Queries + Charts + Export.** Preset query buttons derived from Stats + Journal tab questions in Session 4 UI. WR heatmap chart (sector × regime × age). MAE/MFE distribution chart. CSV export of current query result. Query list finalized AFTER Session 4 Stats + Journal tabs ship.|same files                                     |M     |GATED (waits for Session 4 UI)|
|34|**AN-03**|**Stage 3 — HYDRAX Bridge.** Formalize schema as `analysis/schema.sql`, port queries to `analysis/queries/*.sql` folder. Queries port unchanged to HYDRAX's Postgres. Deferred until HYDRAX Phase 0 starts.|New: `analysis/` folder                        |S     |DEFERRED (HYDRAX Phase 0)|

### AN-01 Stage 1 — Technical Spec (for tomorrow's build)

**Architecture:**
- Static HTML page served from GitHub Pages (works on iPad Safari)
- `sql.js` (SQLite compiled to WebAssembly) loaded from Cloudflare CDN
- Browser fetches `signal_history.json` from public Pages URL (unchanged if repo split happens — public repo still serves)
- In-memory SQLite database created per page load
- Schema inferred from JSON record structure + declared explicitly in code

**Schema (v1 Stage 1):**
```sql
CREATE TABLE signals (
  id                    TEXT PRIMARY KEY,
  date                  TEXT,
  symbol                TEXT,
  signal                TEXT,
  direction             TEXT,
  entry                 REAL,
  stop                  REAL,
  target                REAL,
  score                 REAL,
  regime                TEXT,
  sector                TEXT,
  grade                 TEXT,
  generation            INTEGER,
  age                   INTEGER,
  vol_confirm           INTEGER,
  rs_strong             INTEGER,
  sec_leading           INTEGER,
  grade_A               INTEGER,
  is_sa                 INTEGER,
  sa_parent_id          TEXT,
  result                TEXT,
  outcome               TEXT,
  outcome_date          TEXT,
  outcome_price         REAL,
  pnl_pct               REAL,
  r_multiple            REAL,
  stop_hit              INTEGER,
  failure_reason        TEXT,
  action                TEXT,
  actual_open           REAL,
  gap_pct               REAL,
  entry_valid           INTEGER,
  mae_pct               REAL,
  mfe_pct               REAL,
  effective_exit_date   TEXT,
  data_quality          TEXT
);


UI layout:
	•	Header: “TIE TIY Analysis”
	•	Load indicator: “Loaded N signals” after JSON fetch completes
	•	Textarea: rows=6, monospace font, placeholder example query shown
	•	“Run” button
	•	Results area: HTML table with sortable headers, paginated if >100 rows
	•	Error area: red text if query errors
	•	Example seed query shown on first load: SELECT signal, result, COUNT(*) FROM signals GROUP BY signal, result ORDER BY signal, result
Non-goals for Stage 1:
	•	No preset buttons (deferred to Stage 2)
	•	No charts (deferred to Stage 2)
	•	No CSV export (deferred to Stage 2)
	•	No joins with other files (deferred — only signal_history in Stage 1)
	•	No saved query history (localStorage) (deferred)
AN-02 Stage 2 — Preset Query Library (Draft)
Once Session 4 UI ships, these become the preset buttons (list is seed, refine based on Stats tab design):
	1.	WR by signal × regime × age — the core heatmap question
	2.	Sector performance table — WR + avg P&L per sector
	3.	Worst 10 setups — largest losses, ordered by pnl_pct ascending
	4.	Best 10 setups — largest wins, ordered by pnl_pct descending
	5.	MAE / MFE distribution — histogram bins
	6.	Time-to-target histogram — how many days to target hit
	7.	Kill rule impact — would kill_001 have helped/hurt historically
	8.	Gap impact analysis — WR segmented by gap_pct buckets
	9.	Grade A vs Grade B vs Grade C performance — stock quality tier analysis
	10.	Regime transition analysis — WR during regime changes
AN-03 Stage 3 — HYDRAX Schema Bridge (Post-HYDRAX)
	•	Export schema as analysis/schema.sql (Postgres-compatible DDL)
	•	Port preset queries from JS strings to analysis/queries/*.sql files
	•	Each query file has frontmatter: description, expected columns, expected row count range
	•	Automated test harness: run each query against both TIE TIY SQLite AND HYDRAX Postgres, assert equivalent results
	•	Migration validation gate

🔵 MC tier — Ultimate Master Check (NEW 2026-04-23)
Full Scope



|# |ID       |Title                                                                                                                                                                                                                                                                                                                                                                                           |File(s)                                                                                                    |Effort|Status                   |
|--|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|------|-------------------------|
|35|**MC-01**|**Ultimate Master Check framework** — consolidate `scan_watchdog.yml` + `heartbeat.yml` + `master_check.yml` into single time-scoped workflow with 8 scopes: pre_scan (08:00 IST), post_scan (08:50), post_validate (09:30), intraday (10:00), post_eod (15:40), end_of_day (20:00), overnight (23:00), full (manual). Context-aware alerts. Retires 2 old workflows (scan_watchdog, heartbeat).|`scripts/master_check_ultimate.py` + `.github/workflows/master_check_ultimate.yml` + retire 2 old workflows|L     |PENDING (Day 4 framework)|
|36|**MC-02**|**Expand check coverage** — data integrity (well-formed records, cross-file consistency), staleness detection (file mtime vs expected cadence), workflow success tracking (last 7 days), performance metrics (each workflow’s avg runtime over 30 days).                                                                                                                                        |extends MC-01                                                                                              |M     |PENDING (Week 2)         |
|37|**MC-03**|**Daily health report** — end_of_day scope sends Telegram digest: WR today, open count, tomorrow’s exits, red flags, performance anomalies, yesterday-vs-today comparison.                                                                                                                                                                                                                      |extends MC-01                                                                                              |S     |PENDING (Week 2)         |

MC-01 Technical Spec (Day 4 framework)
File: scripts/master_check_ultimate.py
CLI: python scripts/master_check_ultimate.py --scope <scope_name>
Scopes and what each checks:



|Scope          |IST Time           |Checks                                                                                                                                |
|---------------|-------------------|--------------------------------------------------------------------------------------------------------------------------------------|
|`pre_scan`     |08:00              |Secrets present, workflows enabled, yesterday’s eod_master completed, signal_history.json parseable, no stuck workflows from yesterday|
|`post_scan`    |08:50              |morning_scan completed, Telegram brief sent, meta.json fresh (<30 min), signal count plausible (not zero unless holiday)              |
|`post_validate`|09:30              |open_validate completed, gap_pct populated for today’s signals, D6 triggers resolved for eligible signals                             |
|`intraday`     |10:00, 12:00, 14:00|ltp_updater running on schedule, stop_check running, no LTP staleness >15 min                                                         |
|`post_eod`     |15:40              |eod_master ran, outcomes populated for Day-6 signals, chain_validator clean, eod_prices.json written                                  |
|`end_of_day`   |20:00              |Full day summary: WR today, new signals, resolved outcomes, open count, tomorrow’s planned exits. Telegram digest.                    |
|`overnight`    |23:00              |Auto-analyst ran if ≥5 new resolutions, patterns.json refreshed, proposed_rules.json updated, weekly_intelligence on Sundays          |
|`full`         |Manual             |All Tier 1 (syntax) + Tier 2 (imports) + Tier 3 (safe execution + inline validations) — current master_check behavior                 |

Retires:
	•	.github/workflows/scan_watchdog.yml — absorbed into post_scan
	•	.github/workflows/heartbeat.yml — absorbed into pre_scan
Alert routing:
	•	Critical failures → immediate Telegram
	•	Warnings → accumulated, sent with end_of_day digest
	•	Performance anomalies → logged to doc/performance_log.md, Telegram only if >2σ deviation
MC-02 Expansion (Week 2)
New checks to add:
	•	Data integrity: every signal has valid id, date, symbol, entry>0, stop>0
	•	Cross-file consistency: meta.active_signals_count matches actual history count
	•	Staleness: each file has expected mtime window (e.g., ltp_prices.json <10 min during market hours)
	•	Workflow success tracking: query GitHub API for last 7 days of each workflow’s success rate
	•	Performance metrics: avg runtime per workflow, flag regressions
MC-03 Health Report (Week 2)
Telegram digest format:

📊 END OF DAY — 2026-04-24

Today: W:3 L:1 F:1 — WR 60%
Open positions: 58 (+2 from yesterday)
Tomorrow exits: 7 signals
Resolved today: 5 signals

⚠️ Anomalies:
  • BP-01 pattern holding (Bank BULL_PROXY at 45% WR live)
  • ltp_updater avg runtime 3.2s (baseline 1.1s) — investigate

Weekly: 11W/4L/2F (WR 73%) — tracking +0.5% vs 30-day baseline


🟣 HL tier — Auto-Healing Infrastructure (NEW 2026-04-23, scope reduced 2026-04-24 per screenshot discovery)
Full Scope



|# |ID       |Title                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |File(s)                                                                                               |Effort|Status                   |
|--|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|------|-------------------------|
|38|**HL-01**|**Auto-healer wiring** — Extend existing `diagnostic.py --heal` into scheduled workflow. Centralize audit log at `doc/heal_log_<ts>.md`. Trading-hours gate (NEVER runs 9:15-15:30 IST). Backup-before-write on every action. Telegram notification on every heal. Dry-run as default, `--heal` as explicit flag. **Invariant: NEVER touches trading core** (entry/stop/target/outcome/result/pnl_pct of existing signals). Existing `backfill_schema_v5()`, `backfill_generation_flags()`, `backfill_target_prices()` preserved as-is.|`scripts/auto_healer.py` + `.github/workflows/auto_healer.yml` (wrapper around existing diagnostic.py)|M     |PENDING (Day 4 framework)|
|39|**HL-02**|**Heal scope: metadata + aggregates** — meta.json, scan_log, mini_log, rejected_log regeneration from signal_history.json (truth source).                                                                                                                                                                                                                                                                                                                                                                                              |extends HL-01                                                                                         |M     |PENDING (Week 2)         |
|40|**HL-03**|**Heal scope: stuck signals + orphans + dupes** — reuse `recover_stuck_signals.py` for stuck part. Orphan outcome (outcome set but result PENDING) reconciliation. Duplicate signal ID detection (e.g., `-REJ` issue).                                                                                                                                                                                                                                                                                                                 |extends HL-01 + reuse recover_stuck_signals.py                                                        |M     |PENDING (Week 2)         |
|41|**HL-04**|**Heal scope: schema migrations** — v4→v5 forward-migration for legacy records. Backfills for `grade_A`/`sec_leading`/`rs_strong`/`is_sa`/`sa_parent_id`. (Some already exist in diagnostic.py.)                                                                                                                                                                                                                                                                                                                                       |extends HL-01                                                                                         |M     |PENDING (Week 2)         |
|42|**HL-05**|**Heal scope: Intelligence file regeneration** — contra_shadow.json, patterns.json, proposed_rules.json regenerable from resolved outcomes in signal_history.json.                                                                                                                                                                                                                                                                                                                                                                     |extends HL-01                                                                                         |M     |PENDING (Week 2)         |

HL-01 Safety Invariants (NON-NEGOTIABLE)
Files/fields that are NEVER auto-healed:
	•	signal_history.json — outcome fields (result, outcome, pnl_pct, r_multiple, outcome_date, outcome_price, stop_hit)
	•	signal_history.json — entry/stop/target of existing signals (immutable trading facts)
	•	Open position state — never modify active trade records
	•	mini_scanner_rules.json kill rules — human approval only
	•	scorer.py score weights — intentional
	•	Historical records older than 90 days — fossilized
Files/fields that CAN be auto-healed:
	•	meta.json — regenerable aggregates
	•	scan_log.json, mini_log.json, rejected_log.json — aggregates, regenerable
	•	contra_shadow.json — if missing fields, recompute from history
	•	patterns.json, proposed_rules.json — regenerable from resolved outcomes
	•	nse_holidays.json — refreshable from known source
	•	ltp_prices.json, eod_prices.json — refreshable
	•	Schema version migrations (record at v4, repo at v5) — forward-migrate
	•	Missing backfill fields (generation, target_price, sa_parent_outcome) — backfill
Operational guards:
	•	Trading hours lock: 9:15-15:30 IST = HEALER DISABLED
	•	Dry-run default: --heal requires explicit flag
	•	Per-action approval: --heal-meta, --heal-stuck, etc. — no global --heal-all unless user types it
	•	Backup before every write: quarantine/heal_<ts>/
	•	Rollback on verification failure: post-heal Master Check run, revert if fails
	•	Immutable audit trail: doc/heal_log_<ts>.md for every run
	•	Telegram notification on EVERY heal action (silent healing = silent bugs)
	•	Never re-triggers workflows: healer identifies broken workflow → Telegram to user → user triggers re-run
HL-01 Existing Foundation (from diagnostic.py)
Already present (2026-04-23 screenshot confirmed):
	•	diagnostic.py --heal mode exists (M13 feature per its header)
	•	backfill_schema_v5() function — working
	•	backfill_generation_flags() function — working
	•	backfill_target_prices() function — working
	•	Warning detection (e.g., active count mismatch) — working
HL-01 work = wrapping this into scheduled workflow + adding safety rails + Telegram audit. Net effort: M (not L originally scoped).

🔶 PIN tier — PWA Security (NEW 2026-04-24)



|# |ID        |Title                                                                                                                                                                                                                                             |File(s)                                                          |Effort|Status                             |
|--|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|------|-----------------------------------|
|43|**PIN-01**|PWA PIN inject broken — `PWA_PIN_PLACEHOLDER` missing from `output/index.html`, Master Check FAIL. Root cause + fix + add regression prevention in Master Check. If OPS-01 repo split happens: move PIN inject to public repo’s Pages deploy step.|`scanner/html_builder.py` + deploy workflow + `output/index.html`|M     |PENDING (Day 1 diagnose, Day 2 fix)|

PIN-01 Day 1 Investigation Tasks
	1.	Read current output/index.html in repo — does placeholder exist or not?
	2.	Read scanner/html_builder.py — does it include placeholder when writing shell?
	3.	Search .github/workflows/ for PWA_PIN_PLACEHOLDER reference — find the sed inject step
	4.	Check GitHub repo secrets — is PIN value stored?
	5.	Determine if inject was ever working (check git history of the placeholder presence)
PIN-01 Day 2 Fix Approach (depends on diagnosis)
Scenario A — Placeholder was removed accidentally:
	•	Restore placeholder in html_builder.py
	•	Verify sed step in deploy workflow still exists
	•	Test end-to-end
Scenario B — Deploy workflow’s sed step is missing:
	•	Restore inject step in deploy workflow
	•	Verify secret is still set
Scenario C — Secret not set:
	•	User regenerates PIN
	•	Adds to GitHub repo secrets
	•	Re-runs deploy
Regression prevention:
	•	Extend Master Check to catch placeholder regression (already exists — that’s how we found it)
	•	Add pre-commit hint in CONTRIBUTING if applicable

🟤 OPS tier — Repo Operations (NEW 2026-04-24)
Full Scope



|# |ID        |Title                                                                                                                                                                                          |File(s)                                                           |Effort|Status                          |
|--|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|------|--------------------------------|
|44|**OPS-01**|**Repo split (HYDRAX CP16 preview)** — convert `tietiy/tietiy-scanner` to PRIVATE (strategy IP) + create `tietiy/tietiy-scanner-public` (PWA shell + sanitized data). Public repo serves Pages.|Both repos + sync infrastructure                                  |L     |PENDING (Day 2 execute)         |
|45|**OPS-02**|**Sanitizer script** — whitelist-only copier from private output/ to public output/. Strategy IP (patterns, proposed_rules, stop_alerts, contra_shadow) stays private.                         |`scripts/sanitize_for_public.py`                                  |M     |PENDING (Day 2 ship with OPS-01)|
|46|**OPS-03**|**Sync workflow** — triggered in private repo after morning_scan/eod_master/open_validate success. Pushes sanitized output to public repo via PAT.                                             |`.github/workflows/sync_to_public.yml` (private repo)             |S     |PENDING (Day 2 ship with OPS-01)|
|47|**OPS-04**|**Budget alert** — Telegram when GitHub Actions monthly minutes cross 1,500 (private repo early warning against GitHub Free’s 2,000 min cap).                                                  |`.github/workflows/budget_alert.yml` + `scripts/budget_checker.py`|S     |PENDING (Day 3)                 |

OPS-01 Split — File Allocation
PUBLIC repo (tietiy-scanner-public):
	•	output/index.html, output/ui.js, output/app.js, output/journal.js, output/stats.js, output/sw.js, output/manifest.json
	•	output/signal_history.json (SANITIZED — tickers + dates + outcomes only, no PII)
	•	output/meta.json
	•	output/scan_log.json
	•	output/nse_holidays.json
	•	output/analysis.html + output/analysis.js (AN-01 tool)
PRIVATE repo (tietiy-scanner):
	•	All scanner/*.py — all scanner logic
	•	All .github/workflows/*.yml — all workflows
	•	All data/*.csv, data/*.json — universe, kill rules, etc.
	•	All doc/*.md — fix table, session context, engineering dock
	•	All scripts/*.py — migration scripts, sanitizer, healer
	•	output/contra_shadow.json — STRATEGY IP
	•	output/proposed_rules.json — STRATEGY IP
	•	output/patterns.json — STRATEGY IP
	•	output/rejected_log.json — reveals detection logic
	•	output/mini_log.json — reveals detection logic
	•	output/eod_prices.json, output/ltp_prices.json, output/open_prices.json — live data
	•	output/stop_alerts.json — active trading signals
	•	output/weekly_intelligence_* — engineering output
	•	quarantine/ backups
OPS-01 Execution Sequence (Day 2, MUST be atomic)
	1.	Create empty tietiy/tietiy-scanner-public on GitHub
	2.	Clone current tietiy/tietiy-scanner locally (or via GitHub web editor equivalent)
	3.	Copy current output/ to new public repo — one-time initial sync
	4.	Enable Pages on public repo → test URL works
	5.	Ship scripts/sanitize_for_public.py to private repo
	6.	Ship .github/workflows/sync_to_public.yml to private repo (workflow_dispatch only for now)
	7.	Test sync workflow manually → confirm public repo updates
	8.	Update AN-01 + Colab notebooks + external docs to new public URL (if URL changes)
	9.	Generate PAT with repo scope on private repo, store as PUBLIC_REPO_PAT secret
	10.	Turn tietiy/tietiy-scanner PRIVATE (GitHub setting)
	11.	Flip sync workflow trigger from workflow_dispatch-only to on-workflow-success
	12.	Verify Pages still serves, PWA still works, AN-01 still fetches
OPS-02 Sanitizer Whitelist

# scripts/sanitize_for_public.py
ALLOWED_FILES = [
    'signal_history.json',
    'meta.json',
    'scan_log.json',
    'nse_holidays.json',
    'index.html',
    'ui.js', 'app.js',
    'journal.js', 'stats.js',
    'sw.js',
    'manifest.json',
    'analysis.html',
    'analysis.js',
]

# Deliberately excluded (strategy IP or live data):
EXCLUDED_EXPLICIT = [
    'contra_shadow.json',
    'proposed_rules.json',
    'patterns.json',
    'rejected_log.json',
    'mini_log.json',
    'eod_prices.json',
    'ltp_prices.json',
    'open_prices.json',
    'stop_alerts.json',
    'weekly_intelligence_latest.json',
]


OPS-04 Budget Alert Logic

# Runs daily via GitHub schedule
# Fetches GitHub API for current month's Actions minutes used
# If used > 1500 → Telegram warning
# If used > 1800 → Telegram critical (near cap)
# If used > 2000 → workflows are now paid, Telegram emergency


🔷 TG tier — Telegram Interface Health (NEW 2026-04-24)



|# |ID       |Title                                                                                                                                                                          |File(s)                                                                             |Effort|Status                             |
|--|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|------|-----------------------------------|
|48|**TG-01**|`telegram_poll` workflow failed 2× at 09:40 PM + 10:20 PM IST on 2026-04-23. Telegram command interface (`/status`, `/signals`, `/today`, `/exits`, `/pnl`, `/stops`) degraded.|`scanner/telegram_bot.py` (poll_and_respond) + `.github/workflows/telegram_poll.yml`|M     |PENDING (Day 1 diagnose, Day 2 fix)|

TG-01 Day 1 Investigation Tasks
	1.	Pull last 5 runs of telegram_poll.yml from GitHub Actions logs
	2.	Read error messages from 09:40 + 10:20 failure runs
	3.	Check .github/workflows/telegram_poll.yml — cron schedule, env vars, secrets
	4.	Check scanner/telegram_bot.py:poll_and_respond() — Telegram API call pattern
	5.	Possible causes to rule out:
	•	Telegram API rate limit hit
	•	TELEGRAM_TOKEN or TELEGRAM_CHAT_ID secret missing/expired
	•	Python syntax error from recent commit
	•	Network timeout
	•	GitHub Actions minute budget exhausted
TG-01 Day 2 Fix
Depends on diagnosis. Categories:
	•	Secret/env issue: fix secret, re-enable
	•	Code bug: patch poll_and_respond, ship
	•	Rate limit: add retry logic with exponential backoff
	•	Schedule mismatch: correct cron

🔺 BP tier — BULL_PROXY Regression (NEW 2026-04-24)



|# |ID       |Title                                                                                                                                                                                                                          |File(s)                                                                                        |Effort|Status                                                             |
|--|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|------|-------------------------------------------------------------------|
|49|**BP-01**|BULL_PROXY SL-hit uptick — MFSL (Bank sector, grade B) stopped out -3.2% on 2026-04-23 with “gradual move to target then reversal”. Possibly Bank-sector-wide pattern similar to DOWN_TRI. Needs data analysis + rule decision.|`data/mini_scanner_rules.json` (possibly new kill_002 or expand kill_001) + Colab investigation|M     |PENDING (Day 1 investigate via AN-01, Day 2 rule ship if warranted)|

BP-01 Day 1 Investigation via AN-01
SQL queries to run once AN-01 Stage 1 is live:

-- All BULL_PROXY signals with outcomes
SELECT signal, result, COUNT(*), AVG(pnl_pct)
FROM signals
WHERE signal='BULL_PROXY' AND result IS NOT NULL
GROUP BY result;

-- BULL_PROXY by sector
SELECT sector, COUNT(*) as n, 
       SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
       AVG(pnl_pct) as avg_pnl
FROM signals
WHERE signal='BULL_PROXY' AND result IS NOT NULL
GROUP BY sector
ORDER BY n DESC;

-- BULL_PROXY Bank specifically
SELECT symbol, date, entry, stop, target, pnl_pct, outcome
FROM signals
WHERE signal='BULL_PROXY' AND sector='Bank'
ORDER BY date DESC;

-- BULL_PROXY by regime
SELECT regime, COUNT(*) as n,
       SUM(CASE WHEN result='STOPPED' THEN 1 ELSE 0 END) as stops,
       SUM(CASE WHEN result='WON' THEN 1 ELSE 0 END) as wins
FROM signals
WHERE signal='BULL_PROXY' AND result IS NOT NULL
GROUP BY regime;


BP-01 Day 2 Rule Decision Matrix
Based on Day 1 findings:



|Finding                                               |Action                                 |
|------------------------------------------------------|---------------------------------------|
|Bank BULL_PROXY WR <50% with n≥10                     |Ship `kill_002` (BULL_PROXY+Bank)      |
|Bank+NBFC+Insurance pattern holds                     |Expand `kill_001` to include BULL_PROXY|
|Only MFSL-specific (sample of 1-2)                    |Monitor, no rule yet                   |
|Not Bank-specific — any sector with BULL_PROXY failing|Broader BULL_PROXY rule tightening     |

🟫 DQ tier — Data Quality (NEW 2026-04-24)



|# |ID       |Title                                                                                                                                                                                               |File(s)                                                                               |Effort|Status         |
|--|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|------|---------------|
|50|**DQ-01**|Active count mismatch — `meta.json` says 131, `signal_history.json` has 129. 2-signal sync drift. Investigate root cause BEFORE healing. Do not let HL-02 auto-fix this until root cause understood.|`scanner/meta_writer.py` + `scanner/main.py` (step 17 meta write) + `output/meta.json`|S     |PENDING (Day 2)|

DQ-01 Investigation
Possible root causes:
	1.	Meta-write race condition (main.py updates meta before journal.py commits)
	2.	-REJ dupe double-counting (per memory, cleared naturally but may recur)
	3.	Actual lost signals (scan wrote to history but meta missed)
	4.	-REJ records counted in one place not the other
Day 2 fix approach:
	•	Run diagnostic query via AN-01 to find which 2 signals differ
	•	Identify which direction (meta over-counts or history over-counts)
	•	Patch the write path that drifts
	•	Add DQ check to chain_validator + Master Check inline checks

🔬 INV tier — Investigation Threads (NEW 2026-04-24)
Not code fixes. Data questions requiring analysis.



|# |ID        |Title                                                                                                                                                                                                                                                       |Tool                                                       |Effort      |Status                                        |
|--|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|------------|----------------------------------------------|
|51|**INV-01**|**DOWN_TRI live vs backtest mystery** — backtest says ~87% WR, live Apr 6+ shows 18% WR. kill_001 (DOWN_TRI+Bank) addressed Bank sector but unexplained drift remains. Needs data analysis: survivorship bias? regime shift? signal parameter drift?        |AN-01 Stage 1 (SQL queries) + Colab notebook               |L (research)|PENDING (Day 1 Colab + Day 4 deeper via AN-01)|
|52|**INV-02**|**G-series bug catalog** — formalize G1/G2/G6/G9 (killed in Wave 4) + G12 (DOWN_TRI mystery = INV-01) + any future G-series into tracking registry. Wave 4 fixes documented only in wave_execution_log; need proper fix_table rows for historical reference.|`doc/fix_table.md` + `doc/wave_execution_log_2026-04-23.md`|S           |PENDING (Week 2)                              |

INV-01 Investigation Plan
Hypothesis set to test:
	1.	Survivorship bias — backtest universe of 110 stocks may have excluded stocks that delisted/stopped. Live 188-stock universe includes current survivors AND current strugglers. Query: WR by “was-in-backtest vs new-to-live” buckets.
	2.	Regime shift — 20-year backtest window may include regime different from Apr 2026. Query: WR by regime, segmented to last 30 days vs backtest average.
	3.	Sector composition shift — current live scan hits different sectors at different rates than backtest. Query: sector distribution of signals, then sector-specific WR.
	4.	Parameter drift — DOWN_TRI detection rules changed slightly over time? Verify scanner_core.py detection logic unchanged from backtest baseline.
	5.	Quality tier drift — backtest may have been dominated by Grade A stocks, live more Grade B. Query: WR by grade, both windows.
	6.	Cluster effect — multiple DOWN_TRI signals in correlated stocks failing together. Not individual signal weakness, but cluster risk. Query: DOWN_TRI losing trades, are they clustered by sector/date?
Deliverable: doc/investigation_inv01_down_tri_mystery.md with findings, hypotheses ruled in/out, and recommended action (e.g., “restrict DOWN_TRI to non-Bank sectors for now” or “investigate deeper — no clear finding”).
INV-02 G-Series Catalog
For historical reference, add to fix_table as verified items:

|G-01|scan_watchdog false positive after successful morning_scan (Apr 22)|Wave 4|✅ VERIFIED (2026-04-22)|
|G-02|MARUTI ghost stop alert — yfinance returned ₹4,757 for ₹12K stock|Wave 4|✅ VERIFIED (2026-04-22, price sanity layer)|
|G-06|No price sanity validation layer on stop_alert_writer|Wave 4|✅ VERIFIED (2026-04-22)|
|G-09|No watchdog dedup guard|Wave 4|✅ VERIFIED (2026-04-22, API-first check)|
|G-12|DOWN_TRI live vs backtest mystery|promoted to INV-01|IN PROGRESS|


🟢 LOW — polish (Session C)



|# |ID      |Title                                                                                       |File(s)                             |Effort|Status                                          |
|--|--------|--------------------------------------------------------------------------------------------|------------------------------------|------|------------------------------------------------|
|53|**L-01**|`TELEGRAM_CHAT_ID` default hardcoded to `'8493010921'` in source                            |`telegram_bot.py`                   |S     |PENDING (Week 2)                                |
|54|**L-02**|Memory mentions `nightly_ops.yml` / `weekly_ops.yml` — only `weekly_intelligence.yml` exists|memory / `engineering_dock.md`      |S     |DOC ONLY                                        |
|55|**L-03**|Many `"NEW (Session 3)"` markers now stale                                                  |multiple files                      |S     |PENDING (Week 2)                                |
|56|**L-04**|`master_check.yml` title claims counts that differ from reality                             |`.github/workflows/master_check.yml`|S     |PENDING (Week 2, absorbed by MC-01)             |
|57|**L-05**|Workflow filename typo — `recover_struck_signals.yml` should be `recover_stuck_signals.yml` |`.github/workflows/`                |S     |✅ VERIFIED (2026-04-23, already correct in repo)|

⚪ DEFERRED — Design Decisions (not bugs)



|# |ID       |Question                                                                                     |Needs                                                                |
|--|---------|---------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
|58|**D6**   |Grade refresh cadence — grades frozen since initial backtest. When/how to refresh?           |Decision on cadence (quarterly? after n≥N resolved?) + refresh script|
|59|**D7**   |Dynamic grading via `pattern_miner` — replace CSV grades with data-driven grades from live WR|Phase 3/4 — needs n≥50 per stock before viable                       |
|60|**UX-06**|Order-execution deeplink to broker (Zerodha/5paisa) — reduce copy-paste friction             |Needs broker API research — liability/scope decision first           |

4-Day Sprint Execution Plan (2026-04-24 → 2026-04-27)
Method — Out-of-Box Bundled Scripts (Wave 2/5 pattern)
	•	Claude tests every script in sandbox first
	•	Backup + syntax check + rollback on failure baked in
	•	Single paste per day, single workflow trigger, atomic commits
	•	User active time: 2-3 hours per day instead of 8
Day 1 — 2026-04-24 (Thursday)
Morning (~2 hours user time):
	1.	Ship AN-01 Stage 1 — Claude pre-builds output/analysis.html + output/analysis.js in sandbox, tests against real signal_history.json schema. User pastes 2 files, commits. Live at <pages-url>/analysis.html.
	2.	Diagnose TG-01 — Claude reads workflow logs via project knowledge, identifies telegram_poll failure cause. Reports findings. User decides Day 2 fix approach.
	3.	Diagnose PIN-01 — Claude reads html_builder.py + deploy workflow, identifies missing placeholder root cause. Reports. User decides Day 2 fix approach.
	4.	Start BP-01 investigation — Claude provides Colab notebook pre-loaded with BULL_PROXY diagnostic queries. User runs in Colab mobile, reviews findings.
	5.	Audit diagnostic.py –heal — Claude reads the existing heal infrastructure, scopes HL-01 accordingly. Update fix_table if scope shifts further.
Evening (~1 hour user time):
	6.	Review BP-01 findings — Decide: kill_002 Day 2, or wait for more data.
	7.	Review TG-01/PIN-01 fix approaches — approve Day 2 plan.
End of Day 1: AN-01 live, 3 diagnoses complete, BP-01 data in hand, HL-01 scope finalized.
Day 2 — 2026-04-25 (Friday) — HEAVIEST DAY
~4-5 hours user time.
Single bundled script: scripts/day2_bundle.py + workflow day2.yml.
Fixes shipped:
	•	PIN-01 fix (based on Day 1 diagnosis)
	•	TG-01 fix (based on Day 1 diagnosis)
	•	BP-01 rule ship (if Day 1 investigation warranted)
	•	DQ-01 active count mismatch root-cause fix
	•	Logic bug bundle:
	•	D3/H-04: Narrow kill_001 scope from “Bank=38 stocks” to “Bank core + NBFCs separate”
	•	H-06: Sector taxonomy — expand SECTOR_INDICES to cover all 14 CSV tags
	•	M-05: Extend chain_validator to check proposed_rules.json + contra_shadow.json
	•	M-02: Standardize atomic-write helper across 4 writers
	•	Repo split (OPS-01 + OPS-02 + OPS-03) if user approved path
	•	Create public repo, sanitizer script, sync workflow
	•	Turn private repo private
	•	Update AN-01 + Colab URLs if needed
	•	Ensure PIN inject moves to public repo Pages deploy
Master Check after each sub-bundle, final Master Check green at end of Day 2.
Day 3 — 2026-04-26 (Saturday) — MacBook arrives
~3 hours user time.
Single bundled script: scripts/day3_bundle.py + workflow day3.yml.
UX bundle shipped:
	•	UX-02: Fold gap-skip summary into morning brief (stop 12-min delay)
	•	UX-03: Surface failure_reason in EOD Telegram
	•	UX-05: R:R recalc at actual_open in signal card
UI scaffold shipped:
	•	Empty 4-tab shell with routing (Brief/Market/Review/Intel modes)
	•	Fraunces serif + Geist sans + Geist Mono fonts
	•	iPad landscape 3-column layout
	•	Nav structure, time-aware mode switching
OPS-04 budget alert workflow shipped (post-split early warning).
Master Check green.
Day 4 — 2026-04-27 (Sunday)
~4 hours user time.
Single bundled script: scripts/day4_bundle.py + workflow day4.yml.
UI fill shipped:
	•	Signals tab populated (from existing data)
	•	Journal tab populated
	•	Stats tab populated (with AN-01 link)
	•	Intel tab populated
Infrastructure skeletons shipped:
	•	MC-01 framework (Ultimate Master Check with 8 scopes, dispatched manually only for now)
	•	HL-01 framework (auto-healer wrapper around diagnostic.py –heal, diagnose-only mode, Telegram audit)
Final verification:
	•	Full Master Check (57+/57 target)
	•	Observation run through pre-market + morning brief
	•	INV-01 DOWN_TRI mystery deeper analysis via AN-01 preset queries
	•	Confirm scanner operates clean Monday morning
Week 2 (2026-04-28 to 2026-05-02) — MacBook era
	•	Fill MC-02 (expanded check coverage)
	•	Fill MC-03 (daily health report)
	•	Fill HL-02 through HL-05 (heal scopes, one at a time with tests)
	•	Ship UX-04 (target-near intraday alert)
	•	Ship polish (L-01, L-03, L-04)
	•	AN-02 Stage 2 (preset queries + charts + CSV export)
	•	HYDRAX Phase 0 kickoff

Execution Sequence (Prior Sessions)
Session A — Unblock intelligence loop — ✅ COMPLETE
All 9 items shipped. P-01 skipped by user decision (2026-04-23).



|Order|ID   |Status                     |
|-----|-----|---------------------------|
|1    |C-02 |✅ VERIFIED                 |
|2    |C-01 |✅ VERIFIED                 |
|3    |C-03 |✅ VERIFIED                 |
|4    |C-04 |✅ VERIFIED                 |
|5    |D1   |✅ VERIFIED                 |
|6    |M-11 |✅ VERIFIED                 |
|7    |L-05 |✅ VERIFIED (never had typo)|
|8    |UX-01|✅ VERIFIED                 |
|9    |P-01 |⚪ SKIPPED (user decision)  |

Session B — Unify technical debt + close remaining UX gaps — 🟡 PARTIAL (8 of 10)



|Order|ID   |Title                                               |Status                     |
|-----|-----|----------------------------------------------------|---------------------------|
|10   |C-05 |eod_prices schema adapter                           |✅ VERIFIED (Apr 21)        |
|11   |M-01 |Fix outcome_evaluator docstrings (fold w/ C-05)     |✅ VERIFIED (Apr 21)        |
|12   |H-03 |Centralize trading-day logic in calendar_utils      |✅ VERIFIED (Apr 23, Wave 2)|
|13   |H-09 |Replace `date.today()` with `ist_today()` everywhere|✅ VERIFIED (Apr 23, Wave 2)|
|14   |M-06 |Consolidate IST helpers                             |✅ VERIFIED (Apr 23, Wave 2)|
|15   |M-07 |Fix html_builder docstring                          |✅ VERIFIED (Apr 21)        |
|16   |H-08 |Drop backup_manager weekday cron                    |✅ VERIFIED (Apr 22)        |
|17   |UX-02|Fold gap-skip summary into morning brief            |PENDING (Day 3)            |
|18   |UX-03|Surface failure_reason in EOD Telegram              |PENDING (Day 3)            |
|19   |UX-05|R:R recalc at actual_open in signal card            |PENDING (Day 3)            |

Session 4 — UI build (multi-sitting) — PENDING
12 UI items (UI2–UI12) per memory entry 29. New tab structure, time-aware modes (Brief/Market/Review), Fraunces + Geist fonts, iPad landscape 3-column. Day 3-4 scaffold + fill.
Session C — Quality + polish (after UI)
Absorbed into 4-day sprint + Week 2:
	•	D3/H-04 → Day 2
	•	H-06 → Day 2
	•	H-07 → Week 2
	•	M-02 → Day 2
	•	M-05 → Day 2
	•	M-08 → ✅ VERIFIED (Wave 5.1)
	•	UX-04 → Week 2
	•	L-01, L-03, L-04 → Week 2
	•	L-02 → DOC ONLY
Phase 3+ — Deferred
	•	F2, F3 — design-decision gated
	•	M-09, M-10 — scale-gated
	•	P-02 — correlation detection (session 8)
	•	P-03 — score calibration (session 7)
	•	D6, D7 — grade refresh strategy
	•	UX-06 — broker integration scope decision

What NOT to fix (intentional, do not touch)
	•	Dual scoring constants config.py vs scorer.py — represent backtest baseline vs current weights, intentionally different.
	•	mini_scanner.DEFAULT_RULES — graceful fallback when JSON corrupt, keep.
	•	parent_signal_id + sa_parent_id dual-write — legacy migration safety, drop at V6.
	•	eod_master.yml + eod_update.yml.bak coexistence — rollback escape hatch, keep.
	•	main.py STEP numbering comments — navigation aid for 500-line function.
	•	push_sender 3-value return (True/False/None) — None signals 410 Gone for sub cleanup.
	•	_already_validated_today still triggers D6B — entries vs exits are separate concerns, keep.
	•	signal_history.json.backup.json + backups/ dated — two recovery horizons, keep both.
	•	recover_stuck_signals.yml mapping line TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_TOKEN }} — removed in Wave 3 (M-11), no longer applies.

Verification Infrastructure
	•	verify_fixes.py + verify_fixes.yml do NOT exist — planned but not built. AICREDITS_API_KEY not set.
	•	Master Check covers Tier 1 (syntax), Tier 2 (imports), Tier 3 (safe execution + 7 inline validations) — no logic-validation layer exists yet.
	•	After each fix: run Master Check manually, confirm green. That’s the current verification gate.
	•	Post-MC-01 (Day 4): Ultimate Master Check with 8 time-scoped validations becomes the permanent verification layer.
	•	Post-HL-01 (Day 4): Auto-healer in dry-run mode gives ongoing data integrity visibility.
	•	Automated pattern migrations run via scripts/wave2_migration.py + scripts/wave5_m08_migration.py with workflow dispatch — backup + syntax-check + rollback-on-failure built in.

Key Design Principles (Affirmed 2026-04-24)
	1.	signal_history.json is persistent truth. All other JSONs are overlays.
	2.	price_feed.py abstraction: yfinance now, 5paisa as plug-in swap later (one-line config).
	3.	Mini scanner shadow mode collects data before activating rules. Don’t activate on insufficient n.
	4.	Confidence gates before any rule activation: n≥20, confidence≥85%, WR gap≥15% vs baseline.
	5.	Atomic writes critical for signal_history.json integrity (M-02 extends this to all writers).
	6.	Every ship has a defined rollback path (e.g., eod_update.yml.bak).
	7.	Automated migrations use AST-based function/import boundary detection (not regex). Backup + syntax check + rollback-on-failure is non-negotiable.
	8.	All scanner time helpers route through scanner/calendar_utils.py (ist_today, ist_now, ist_now_str, is_trading_day). No more date.today() UTC drift.
	9.	Auto-healer NEVER touches trading core. Entry/stop/target/outcome/result/pnl_pct of existing signals are immutable.
	10.	Strategy IP is private (post OPS-01). Public repo serves only sanitized data + PWA shell.

Files You Will Need To See Frequently
Orchestration
	•	scanner/main.py — 500+ line orchestrator, 21 steps
	•	scanner/config.py — constants, paths, price source toggle
	•	scanner/calendar_utils.py — canonical time helpers
	•	scanner/universe.py — CSV loader
Detection / Scoring
	•	scanner/scanner_core.py — signal detection
	•	scanner/scorer.py — 0–10 score
	•	scanner/mini_scanner.py — shadow-mode + kill_patterns
Persistence
	•	scanner/journal.py — signal_history.json
	•	scanner/meta_writer.py — meta.json + nse_holidays.json
	•	scanner/backup_manager.py — dated backups
Outcome / Price
	•	scanner/outcome_evaluator.py — resolves OPEN signals
	•	scanner/open_validator.py — 9:15 open prices
	•	scanner/ltp_writer.py — LTP fetch every 5min
	•	scanner/stop_alert_writer.py — stop alerts + price sanity
	•	scanner/eod_prices_writer.py — 3:35 EOD snapshot
	•	scanner/price_feed.py — yfinance/5paisa abstraction
Intelligence (all healthy post Session A)
	•	scanner/pattern_miner.py
	•	scanner/chain_validator.py
	•	scanner/contra_tracker.py
	•	scanner/rule_proposer.py
	•	scanner/weekly_intelligence.py
	•	scanner/auto_analyst.py
Delivery
	•	scanner/telegram_bot.py — canonical _esc + 11 message types + command handler
	•	scanner/html_builder.py — index.html shell
	•	scanner/push_sender.py — VAPID web push
	•	output/ui.js, app.js, journal.js, stats.js, sw.js — PWA
	•	output/analysis.html, analysis.js — AN-01 (Day 1)
Recovery / Diagnostic
	•	scanner/recover_stuck_signals.py + .github/workflows/recover_stuck_signals.yml
	•	scanner/diagnostic.py — multi-mode health check with –heal
	•	scanner/deep_debugger.py — signal forensics
	•	scanner/gap_report.py — weekly gap risk
Migration Infrastructure
	•	scripts/wave2_migration.py — AST-based migration framework (kept for future)
	•	scripts/wave5_m08_migration.py — _esc consolidation (done)
	•	scripts/day2_bundle.py, day3_bundle.py, day4_bundle.py — sprint bundled scripts (will be created)
	•	scripts/sanitize_for_public.py — OPS-02 (Day 2)
	•	scripts/budget_checker.py — OPS-04 (Day 3)
	•	scripts/master_check_ultimate.py — MC-01 (Day 4)
	•	scripts/auto_healer.py — HL-01 (Day 4)

Change Log



|Date      |Change                                                                                                                                                                                                                                                                                                                                                                           |
|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|2026-04-20|Initial creation after master audit. 39 items locked.                                                                                                                                                                                                                                                                                                                            |
|2026-04-23|Wave 2/3/5.1 session — 16 IDs VERIFIED (C-01..C-05, H-03, H-05/D1, H-08, H-09, M-01, M-06, M-07, M-08, M-11, L-05, UX-01). P-01 SKIPPED per user decision. Summary counts updated. See `doc/wave_execution_log_2026-04-23.md`.                                                                                                                                                   |
|2026-04-24|Added 18 new items across 8 new tiers (AN, MC, HL, PIN, OPS, TG, BP, DQ, INV) — totaling 60 items. Full 4-day sprint plan (Day 1 AN-01 + diagnoses, Day 2 heavy fix bundle + repo split, Day 3 UX + UI scaffold, Day 4 UI fill + MC-01 + HL-01 frameworks). Out-of-box bundled-script method locked. INV-01 (DOWN_TRI mystery) promoted from G12 to tracked investigation thread.|


---

## 📋 Instructions

1. **Open `doc/fix_table.md`** in GitHub web editor
2. **Select all, delete**
3. **Paste the content above**
4. **Commit:** `Docs: Full fix_table rewrite — 60 items, 4-day sprint plan, all investigation threads`

---

## 🛏️ Final Final — SLEEP

This doc captures **everything** we discussed tonight. When you wake up and start a fresh chat, point Claude at:
1. `doc/session_context.md`
2. `doc/fix_table.md` (this rewrite)
3. `doc/wave_execution_log_2026-04-23.md`

Say: *"Read these 3 docs. Start Day 1."*

That's it. Zero context loss. Fresh Claude picks up exactly where we are.

⏰ **Good night for real this time. GG. 🌙**
