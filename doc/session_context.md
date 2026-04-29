# TIE TIY Session Context — Start Here

**Purpose:** Drop-in context for any new Claude session. Read this instead of recalling memory piecemeal.
**Read order:** This file → `wave_execution_log_2026-04-23.md` → `fix_table.md` → `engineering_dock.md` → `roadmap.md`
**Last updated:** 2026-04-29 early-morning (Wave 5 backend complete: 7/7 steps shipped + brain.yml workflow; head: d874180)

-----

## 30-Second Project Summary

TIE TIY is a personal NSE equity scanner + decision-support system for Abhishek, a discretionary positional trader in India. It scans 188 F&O stocks daily, detects 3 signal types (UP_TRI, DOWN_TRI, BULL_PROXY), scores them 0–10, tracks for 6-day windows, and delivers alerts via Telegram + PWA.

Built solo on iPad via Safari + GitHub web editor + Google Colab. Python + yfinance + GitHub Actions + GitHub Pages. **iPad-only workflow means full file rewrites, no diffs.**

**Repo:** tietiy/tietiy-scanner · **URL:** tietiy.github.io/tietiy-scanner/ · **Chat ID:** 8493010921

-----

## Current Production State (2026-04-23)

|Metric               |Value                                                                |
|---------------------|---------------------------------------------------------------------|
|Phase                |**Phase 2 UNLOCKED**                                                 |
|Live resolved signals|118 (true unique ~86 after -REJ dedup note)                          |
|Win rate             |81% (96W / 22L)                                                      |
|Avg P&L per trade    |+4.02%                                                               |
|Open positions       |58                                                                   |
|Scan days            |9                                                                    |
|Universe             |188 F&O stocks, 14 sectors in CSV                                    |
|Signal types live WR |UP_TRI 95% (n=83), DOWN_TRI 18% (killed via kill_001), BULL_PROXY 75%|
|Active kill rules    |kill_001 (DOWN_TRI+Bank)                                             |
|Shadow mode          |ON — all signals pass, kill_patterns hard-block                      |
|Master Check status  |52/53 green (1 pre-existing PWA_PIN_PLACEHOLDER fail, unrelated)     |

**Schema version:** 5 (record-level), 4 (meta).

-----

## Wave 5 Backend Build Status (as of 2026-04-29 early-morning)

**Head commit on `main`:** `d874180`

|Wave  |Layer / Item                                                |Status                                                       |
|------|------------------------------------------------------------|-------------------------------------------------------------|
|Wave 2|Backend foundation + TG-01 + schema bug fixes               |✅ SHIPPED 2026-04-26                                         |
|Wave 3|BR-02..BR-04 composers (Sessions A/B/C/D) + BR-07 renderers |✅ SHIPPED                                                    |
|Wave 4|Steps 1-4: LE-07 + prop_005 + LE-06 + prop_007              |✅ SHIPPED 2026-04-28                                         |
|Wave 4|Step 5 LE-05 (PWA → Telegram deep-link)                     |⏸ DEFERRED to Wave UI / IT-05                                |
|Wave 5|Step 1: brain_design_v1.md design lock                      |✅ SHIPPED `720c127`                                          |
|Wave 5|Step 2: scanner/brain/ folder skeleton                      |✅ SHIPPED `060d7c9`                                          |
|Wave 5|Step 3: derived views layer (4 derivers)                    |✅ SHIPPED `76a85f4` 2026-04-29                               |
|Wave 5|Step 4: verification framework + 4 deterministic generators |✅ SHIPPED `8e5be29` 2026-04-29                               |
|Wave 5|Step 5: LLM reasoning gates (3 gates Opus 4.7)              |✅ SHIPPED `c047fd2` 2026-04-29                               |
|Wave 5|Step 6: unified queue + decisions_journal + dual-write      |✅ SHIPPED `05570fb` 2026-04-29                               |
|Wave 5|Step 7: Telegram /approve + /reject + /explain + brain_digest.yml | ✅ SHIPPED `1e1c786` 2026-04-29                          |
|Wave 5|brain.yml production-fire workflow + main.py brain mode     |✅ SHIPPED `d874180` 2026-04-29                               |
|Wave 5|Step 8: PWA Monster tab                                     |⏸ DEFERRED to Wave UI per D-11 (≥1 week trader feedback first)|

**Wave 5 backend: 7/7 backend steps shipped 2026-04-29.** Brain end-to-end operational from local manual chain (verified via tonight's smoke + live-data sample runs).

**Tonight's session arc — 11 substantive commits + 4 design commits (chronological):**
- `76a85f4` Step 3 derived views (4 derivers + standing R-mult Day-6 warn)
- `31b608f` wave5_prerequisites S-6 advisory (Step 4 audit byproduct)
- `8e5be29` Step 4 verification + 4 deterministic generators
- `fe0a669` M-12 fix (chain_validator step reorder; Step 5 prerequisite)
- `c047fd2` Step 5 LLM reasoning gates (Opus 4.7; reasoning_log accumulation)
- `27b60cb` brain_design §5.1 + §2 amendments (D-2 + D-4 lock)
- `997d4af` brain_design §5.1 watch_pattern overlap row (V-8 closure)
- `ee4007d` brain_design §5.1 verify_conflict_surfacing location correction
- `05570fb` Step 6 unified queue + decisions_journal + dual-write rule_proposer adapter
- `1e1c786` Step 7 Telegram approval handlers + brain_digest.yml
- `d874180` brain.yml production-fire workflow + main.py brain mode

**End-to-end operational chain:**
truth files → Step 3 derived views → Step 4 verify+generate → Step 5 LLM gates ($0.10/run, smarter-every-day reasoning_log) → Step 6 unified queue + decisions_journal init + dual-write → Step 7 Telegram digest + /approve + /reject + /explain → trader action → mutation: rule_proposer (kill_rule, boost_demote) OR apply_boost_promote → mini_scanner_rules.boost_patterns[] → decisions_journal append (Step 5 90-day lookback for cross-day disagreement awareness)

**Resume point for next session (`apex` / `kabu` trigger):**

Wave 5 backend complete (7/7 steps shipped 2026-04-29). Production fire blocked on user-side actions (cron-job.org dashboard entries + ANTHROPIC_API_KEY GitHub secret). Brain end-to-end chain verified via tonight's smoke + live-data sample runs.

**Canonical reference doc:** `doc/project_anchor_v1.md` (commit `50325c7`, 762 LOC). Read first when resuming.

**Pending production-fire user actions (NOT blocking next-session work):**
- `ANTHROPIC_API_KEY` GitHub secret (Settings → Secrets → Actions). Without this, Step 5 LLM gates fail at runtime.
- cron-job.org dashboard entry — `brain.yml`. URL: `https://api.github.com/repos/tietiy/tietiy-scanner/actions/workflows/brain.yml/dispatches`; Schedule: `30 16 * * *` (16:30 UTC = 22:00 IST Mon-Sun); Body: `{"ref": "main"}`.
- cron-job.org dashboard entry — `brain_digest.yml`. URL same pattern; Schedule: `35 16 * * *` (22:05 IST Mon-Sun).
- cron-job.org dashboard entry — `eod.yml` (carryover from 2026-04-28 reversal). Schedule: `45 10 * * 1-5` (16:15 IST weekday).

**Earned next items, in order:**
1. **Observation period** — ≥1 week of brain production runs; collect Telegram-only trader feedback on /approve + /reject + /explain UX. Per D-11 lock, Step 8 PWA Monster tab design pass waits on this data.
2. **First-fire watches** post user-side actions:
   - 22:00 IST first scheduled brain.yml fire — verify Step 3+4+5+6 chain runs clean; cohort_health/regime_watch/portfolio_exposure/ground_truth_gaps regenerate; reasoning_log appends; unified_proposals.json + decisions_journal.json get written.
   - 22:05 IST first scheduled brain_digest.yml fire — verify Telegram digest delivered with 3 cards or empty-queue tone.
3. **Step 8 PWA Monster tab** (Wave UI session) — design pass with full trader-feedback context.

**Decision items open (per `project_anchor_v1.md §7`):**
- D-1 Bot username for deep-link tightening (Wave UI scope)
- D-5 S-4 cron-job.org failover playbook (highest cost-of-wrong-call; recommendation: ship pre-Step-8)
- D-6 master_check discipline (recommendation: relax CLAUDE.md to match observed practice)
- D-8 exit_logic_redesign DRAFT vs REJECT (recommendation: DRAFT; parallel track)
- D-10 Wave UI kickoff trigger (post-observation period)

**Decision items locked tonight:** D-2 (surface conflicts in counter via §5.1 amendment); D-3 (M-12 fix shipped `fe0a669`); D-4 (Mon-Sun cadence); D-7 (full unified_id text command per Step 7); D-9 (conflict badge format); D-11 (PWA defer to Step 8).

**Parallel track (not blocking Wave 5 production fire):**
- `doc/exit_logic_redesign_v1.md` — design doc capturing Day-6 forced-exit dominance findings (D-8). Deferred to fresh-headed session.

**Tonight's audit-first lessons hardened:**
- Multi-phase design lock-in discipline (D-2/D-4 → V-questions → implementation) prevented two tripwires from becoming bugs (V-1 alpha tie-break prediction error caught by smoke; brain_verify location ambiguity caught by user before code touched brain_verify).
- Citation-density grep (`'\`[0-9a-f]{7}\`'`) more robust than literal-string grep for verifying audit-trail integrity.
- Tripwire surfacing > silent-bulldozing: `brain_derive.run_all()` API mismatch + ANTHROPIC_API_KEY GitHub secret both surfaced before code landed.
- Phase-discipline (Phase 0/1/2/3 stop-and-confirm) made 5-hour bundled sessions executable without losing track of locked decisions.

-----

## Non-Negotiable Trading Rules

- Entry at 9:15 AM IST next trading day after signal detection
- Stop-loss placed immediately at entry
- Exit at open of Day 6
- Max 5% capital per trade
- No moving stop, no adding to position
- Stop hit intraday = exit same day
- R:R 2.0+ strong, 1.5 acceptable, below 1.5 reduce size

-----

## Backtest-Validated Signal Rules (20yr, 110 stocks)

- **UP_TRI:** No EMA50 filter. Ages 0–3 valid. All regimes. ~87–88% WR. Bear regime = highest conviction (avg +4.85%). Stop never hit in backtest.
- **DOWN_TRI:** No regime filter. **Age 0 ONLY.** ~87–89% WR. Edge gone at age 1+. (Live data shows 18% WR — investigation ongoing, kill_001 firing correctly on Bank sector)
- **BULL_PROXY:** Trend filter kept. Ages 0–1 only. ~67% WR. ~20% stop rate. (Live 75% WR, small sample)

-----

## Scoring System

- UP_TRI: Age0=+3, Age1=+2. Bear regime=+3, Bull=+2, Choppy=+1
- DOWN_TRI: +2 flat all regimes
- BULL_PROXY: Bull/Choppy=+1 only
- Quality: vol_confirm+1, sec_leading+1, rs_strong+1, grade_A+1
- Max = 10. stock_regime stored on every signal (not in scoring yet — Phase 3)

-----

## Architecture — Daily Flow

08:30 IST  heartbeat.yml           → alive ping to Telegram
08:45 IST  morning_scan.yml        → main.py morning (21 steps)
09:02 IST  scan_watchdog.yml       → verify scan fired (API-first since Apr 22)
09:15 IST  [MARKET OPENS]          → trader places entries/exits manually
09:27 IST  open_validate.yml       → 9:15 open prices + gap% + D6 resolution
09:30 IST  ltp_updater.yml         → every 5min (staggered)
09:32 IST  stop_check.yml          → every 5min (+2min offset, price sanity layer Apr 22)
15:35 IST  eod_master.yml          → 8-step chain: backup→outcomes→EOD→telegram→chain→patterns→proposals→commit
22:00 IST  brain.yml               → Step 3 derive → Step 4 verify → Step 5 LLM gates → Step 6 unified queue (Mon-Sun)
22:05 IST  brain_digest.yml        → Telegram digest of unified_proposals.json (Mon-Sun)
Saturdays 08:30         → backup_manager.yml + weekend_summary.yml
Mondays 08:30           → gap_report.yml
Sundays 20:00 IST       → weekly_intelligence.yml


**Cron triggers:** All via cron-job.org using `workflow_dispatch` (no `schedule:` blocks in YAML, so GitHub cron drift doesn't apply), except `backup_manager.yml`, `gap_report.yml`, `weekly_intelligence.yml` which use GitHub's native `schedule:` (drift-tolerant, weekly only).

-----

## Trigger Words (Skip Intro, Jump Into Work)

- `apex` / `kabu` → full TIE TIY context
- `morningstar` / `vedu` → GitHub scanner context
- `lucifer` → Colab backtest context
- `fixlog` → bug fix mode
- `uibuild` → UI redesign mode
- `phase2` → Phase 2 build mode

-----

## Working Method (Locked with User)

1. **No code without explicit "start" command.** Audit and discussion are fine; touching files requires green light.
1. **At the start of each fix, Claude lists files needed.** User points or pastes. Then Claude writes the fix once.
1. **If Claude is uncertain mid-fix (weird field, unclear intent), Claude stops and asks.** No guessing.
1. **One cycle per fix, not three.** Ship-then-debug is banned.
1. **All file deliveries are complete rewrites.** No diffs (iPad workflow).
1. **Verify after each fix:** run Master Check manually, confirm green.

-----

## Execution Sequence (Updated 2026-04-23)

|Order|Session      |Contents                                                                     |Status             |
|-----|-------------|-----------------------------------------------------------------------------|-------------------|
|1    |**Session A**|9 items: C-01 through C-04, D1, M-11, L-05, UX-01, P-01                      |✅ COMPLETE (P-01 skipped by user decision) |
|2    |**Session B (partial)**|C-05, H-03, H-09, M-01, M-06, M-07, H-08, M-08 shipped. UX-02/03/05 remaining|🟡 8 of 10 shipped|
|3    |**Session 4**|UI build — 12 items (UI2–UI12) per memory entry 29                           |PENDING            |
|4    |**Session C**|Quality + polish — D3, H-06, H-07, M-02, M-05, UX-04, L-01 through L-04      |PENDING            |
|—    |Phase 3+     |F2, F3, M-09, M-10, P-02, P-03, D6, D7, UX-06                                |DEFERRED           |

**See `fix_table.md` for full 39-item execution plan.**
**See `wave_execution_log_2026-04-23.md` for canonical record of shipped items.**

-----

## Critical Open Incidents (as of 2026-04-23)

**Zero open critical incidents.** All 5 C-series items shipped in Apr 21 batch + Wave 2/3/5.1 session (Apr 22-23).

Intelligence loop now functional end-to-end:
- C-01/C-02: contra_tracker + rule_proposer write to correct directories (`_HERE`/`_ROOT` abs paths)
- C-03: schema v2 alignment (original_direction / inverted_direction / entry_est) with reader-side `_shadow_field()` helper
- C-04: `/approve_rule` returns dict, handler calls `.get('success')`
- C-05: eod_prices.json schema v2 with `ohlc_by_symbol` + reader adapter handles both old/new schemas

Next priority layer (Session B/C remainder):
- **H-04/D3** — kill_001 bank scope (38 stocks on 11-stock evidence) — evidence-based tuning
- **H-06** — Sector taxonomy (14 CSV tags vs 8 tracked, ~45 stocks never earn sec_leading bonus)
- **M-05** — chain_validator doesn't check proposed_rules.json / contra_shadow.json (false "healthy" status)
- **UX-02/03/05** — morning brief + EOD Telegram enhancements

-----

## Key Design Principles

1. `signal_history.json` is persistent truth. All other JSONs are overlays.
1. `price_feed.py` abstraction: yfinance now, 5paisa as plug-in swap later (one-line config).
1. Mini scanner shadow mode collects data before activating rules. Don't activate on insufficient n.
1. Confidence gates before any rule activation: n≥20, confidence≥85%, WR gap≥15% vs baseline.
1. Atomic writes critical for `signal_history.json` integrity.
1. Every ship has a defined rollback path (e.g., `eod_update.yml.bak`).
1. **New (2026-04-23):** Automated migrations use AST-based function/import boundary detection (not regex). Backup + syntax check + rollback-on-failure is non-negotiable. See `scripts/wave2_migration.py` and `scripts/wave5_m08_migration.py`.
1. **New (2026-04-23):** All scanner time helpers route through `scanner/calendar_utils.py` (`ist_today`, `ist_now`, `ist_now_str`, `is_trading_day`). No more `date.today()` UTC drift.

-----

## Files You Will Need To See Frequently

### Orchestration

- `scanner/main.py` — 500+ line orchestrator, 21 steps
- `scanner/config.py` — constants, paths, price source toggle
- `scanner/calendar_utils.py` — trading day / holiday / next-trading-day helpers + IST date/time (canonical)
- `scanner/universe.py` — CSV loader

### Detection / Scoring

- `scanner/scanner_core.py` — signal detection (UP_TRI, DOWN_TRI, BULL_PROXY, SA variants)
- `scanner/scorer.py` — 0–10 score with quality bonuses
- `scanner/mini_scanner.py` — shadow-mode filter + kill_patterns enforcement

### Persistence

- `scanner/journal.py` — owns `signal_history.json` + `signal_archive.json`
- `scanner/meta_writer.py` — `meta.json` + `nse_holidays.json`
- `scanner/backup_manager.py` — dated backups

### Outcome / Price

- `scanner/outcome_evaluator.py` — resolves OPEN signals, writes outcome fields (schema-v2 adapter inside)
- `scanner/open_validator.py` — 9:15 open price, gap%, entry_valid, D6B trigger
- `scanner/ltp_writer.py` — LTP fetch every 5min
- `scanner/stop_alert_writer.py` — stop proximity, breach alerts (+ price sanity layer since Apr 22)
- `scanner/eod_prices_writer.py` — 3:35 EOD OHLC snapshot (schema v2 `ohlc_by_symbol`)
- `scanner/price_feed.py` — yfinance/5paisa abstraction (currently only ltp_writer uses it; H-07 remaining)

### Intelligence (Apr 20 ship — all 5 now healthy)

- `scanner/pattern_miner.py` — discovers edges/failures in resolved signals ✓
- `scanner/chain_validator.py` — system health report ✓ (C-05 shipped, M-05 pending for coverage extension)
- `scanner/contra_tracker.py` — ✓ (C-01 + C-03 shipped)
- `scanner/rule_proposer.py` — ✓ (C-02 + C-04 shipped)
- `scanner/weekly_intelligence.py` — ✓
- `scanner/auto_analyst.py` — nightly if ≥5 new resolutions

### Delivery

- `scanner/telegram_bot.py` — canonical `_esc` lives here; 11 message types + command handler
- `scanner/html_builder.py` — writes index.html shell with cache-bust
- `scanner/push_sender.py` — VAPID web push
- `output/ui.js`, `app.js`, `journal.js`, `stats.js`, `sw.js` — PWA frontend

### Recovery / Diagnostic

- `scanner/recover_stuck_signals.py` + `.github/workflows/recover_stuck_signals.yml` (filename confirmed correct)
- `scanner/diagnostic.py` — multi-mode health check (imports `_esc` from telegram_bot since Apr 23)
- `scanner/deep_debugger.py` — signal forensics (imports `_esc` from telegram_bot since Apr 23)
- `scanner/gap_report.py` — weekly gap risk analysis (imports `_esc` from telegram_bot since Apr 23)

### Migration Infrastructure (new 2026-04-23)

- `scripts/wave2_migration.py` — AST-based Python migration framework with safety rails
- `scripts/wave5_m08_migration.py` — config-specialized variant for `_esc` consolidation
- `.github/workflows/wave2.yml` + `.github/workflows/wave5_m08.yml` — manual-dispatch orchestration

-----

## Verification Infrastructure Reality Check

- `verify_fixes.py` / `verify_fixes.yml` — **DO NOT EXIST.** Planned Phase 2 item, never built.
- AICREDITS_API_KEY — **NOT SET.** Planned AI audit integration, not live.
- Master Check (`master_check.yml`) covers: Tier 1 syntax, Tier 2 imports, Tier 3 safe execution + 7 inline checks. **No logic validation layer.**
- After each code change: run Master Check → confirm green → that's the current verification gate.

-----

## Behavioral Gap (P-01) — Biggest Vision Risk (Skipped by User)

Roadmap success metric: "Positive P&L tracked in personal Google Sheet, correlated with scanner's claimed outcomes."

User explicitly skipped P-01 on 2026-04-23. Scanner claims 81% WR but no broker-statement correlation exists. 90-day validation phase cannot formally complete until this ritual is established.

Revisit at user's discretion.

-----

## What To Say At Session Start

If you (the user) land in a new chat with a fresh Claude and want to skip the full recall:

> "Read `doc/session_context.md`, then `doc/wave_execution_log_2026-04-23.md`, then `doc/fix_table.md` in the project knowledge. Then [your task]."

Or use a trigger word — `apex`, `phase2`, `fixlog` — which memory entry 1 decodes into the same context.

-----

## Change Log

|Date      |Change                                                                                                                                                                                                                                                      |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|2026-04-20|Initial creation post-master-audit. Locked with user.                                                                                                                                                                                                       |
|2026-04-23|Wave 2/3/5.1 session — 16 IDs VERIFIED (C-01..C-05, H-03, H-05/D1, H-08, H-09, M-01, M-06, M-07, M-08, M-11, L-05, UX-01). Zero critical incidents remaining. See `wave_execution_log_2026-04-23.md` for canonical session record. Updated daily flow, file list, design principles with migration infrastructure notes.|
|2026-04-26|**Wave 2 backend + TG-01 + Wave 3 Sessions A/B + Wave 4 Step 1.** Wave 2: 16 bridge backend files + TG-01 poll concurrency + 3 schema bugs caught/fixed via real-data sanity audit (new principle locked: schema discipline #12). Wave 3: BR-02/BR-03 composers shipped, BR-04 Session A (`composers/eod.py`, `c94e523`) + Session B (`bridge_telegram_eod.py`, `19d4146`) shipped, BR-07 fully complete (3 renderers), Sessions C+D pending. Wave 4 Step 1: `/reject_rule` Telegram command (`c43189a`, LE-07). Renderer escape-pattern bug caught in code review (`_render_contra_section`); fixed. Head: `03bdeb0`.|
|2026-04-28|**Wave 4 closed at 4 shipped items + Wave 3 Sessions C+D shipped + tonight's misc fixes.** Wave 4 closure: LE-07 (`c43189a`, prior), prop_005 (`550b5f0` reframed as parallel-shadow infra; not R-multiple solver), LE-06 (`7b96a97`), prop_007 (`c647e94`). LE-05 reclassified DEFERRED to Wave UI / IT-05 (`0512cd2`) after audit-first verification PWA has no proposal surface. Wave 3: Session C (LE-06 inside `7b96a97`) + Session D (eod.yml `f9d4746`, GitHub native schedule per bridge_design_v1.md §13.4 `d4433e7`). Misc: `_THIN_FALLBACK` migration to thresholds.py (`b1359f1` + `68063d3` + `e4d5d6a`), GAP-13 reclassified after PWA grep verification (`3650f57`), recover_stuck_signals.py Wave 2 migration leftover fixed (`9d4dcb2`). Head: `0512cd2`.|
|2026-04-28 (full session closeout)|**15 commits today** (chronological per `project_anchor_v1.md §8.3`): F-2 audit findings filed M-12+M-13 (`ddd66b7`); B-2 verified + M-14 filed (`10a3fb5`); master_audit GAP-33 RESOLVED + GAP-04 PARTIAL (`9336b32`); brain_design drift audit (`c278a32`); B-1 manual workflow_dispatch verified (`a5edc32` + `51448e8`); eod.yml migrated GitHub schedule → cron-job.org M-15 RESOLVED (`2fc1f35`); Wave 5 Step 2 folder skeleton shipped (`060d7c9`); B-3 Anthropic SDK shipped (`d6ddc01`); prop_005 parallel-shadow infra (`550b5f0`); recover_stuck_signals import fix (`9d4dcb2`); LE-05 deferred Wave UI (`0512cd2`); session_context Wave 4 closure (`cbdef3d` superseded by this row); fix_table prop_005 reframe (`4944c17`); **project_anchor_v1.md comprehensive reference doc** (`50325c7`, 762 LOC, 128 commit citations / 49 unique). master_audit GAP-04 re-amendment lands in this batch closeout commit. Head: `50325c7`.|
|2026-04-29 (early morning Wave 5 backend complete)|**11 substantive commits + production-fire workflow:** Step 3 derived views (`76a85f4`); Step 4 verify+generate (`8e5be29`); M-12 fix (`fe0a669`); Step 5 LLM gates (`c047fd2`); design lock commits §5.1+§2 (`27b60cb`) + watch_pattern row (`997d4af`) + verify location correction (`ee4007d`); Step 6 unified queue (`05570fb`); Step 7 Telegram approval handlers (`1e1c786`); brain.yml + main.py brain mode (`d874180`); plus wave5_prerequisites S-6 advisory (`31b608f`). Wave 5 backend complete: brain end-to-end operational. Pending production fire on user-side actions (ANTHROPIC_API_KEY secret + 3 cron-job.org dashboard entries). Step 8 PWA Monster tab deferred to Wave UI session per D-11 lock; needs ≥1 week trader feedback first. Head: `d874180`.|


