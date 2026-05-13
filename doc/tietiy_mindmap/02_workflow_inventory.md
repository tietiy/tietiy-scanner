# Dimension 2 — Workflow Inventory & Purpose

**Generated:** 2026-05-13
**Scope:** Every `.yml` file in `.github/workflows/` — what it triggers, what it runs, what it touches, whether it's alive.

Total workflows on disk: **28** active `.yml` + 1 `.bak` = 29 files.

---

## Active workflows — alphabetical

### backup_manager.yml (100 LOC)
- **Trigger:** GH schedule `0 3 * * 6` (Sat 08:30 IST) + workflow_dispatch
- **Purpose:** Saturday weekly snapshot of signal_history into `backups/`
- **Scripts:** `scanner/backup_manager.py`
- **Reads:** `output/signal_history.json`, `output/signal_archive.json`
- **Writes:** `backups/<timestamp>/`
- **Commits:** Yes (backup folder)
- **Telegram:** Yes (status)
- **Active:** ✅

### brain.yml (147 LOC)
- **Trigger:** cron-job.org @ 22:00 IST (Mon-Sun) + workflow_dispatch
- **Purpose:** Nightly brain — Step 3 derive → Step 4 verify → Step 5 LLM gates → Step 6 unified proposals
- **Scripts:** `python -m scanner.brain.brain_cli run` (orchestrator at `scanner/brain/brain_cli.py`)
- **Reads:** `output/signal_history.json`, `output/patterns.json`, `output/proposed_rules.json`, `output/contra_shadow.json`, `output/weekly_intelligence_latest.json`, `data/mini_scanner_rules.json`, `output/bridge_state_history/<date>_EOD.json`
- **Writes:** `output/brain/cohort_health.json`, `regime_watch.json`, `portfolio_exposure.json`, `ground_truth_gaps.json`, `unified_proposals.json`, `reasoning_log.json` (append), `decisions_journal.json` (init), `verification_failures.json`, plus history archives in `output/brain/history/`
- **Commits:** Yes (`output/brain/`)
- **Telegram:** No (digest fires separately in `brain_digest.yml`)
- **Secrets:** `ANTHROPIC_API_KEY` (required; LLM gates skip with error if missing)
- **Cost:** ~$0.05–$0.10/run (Opus 4.7 at $5/$25 per Mtok)
- **Active:** ✅ Last verified run 2026-05-12 22:00 IST

### brain_digest.yml (72 LOC)
- **Trigger:** cron-job.org @ 22:05 IST (Mon-Sun) + workflow_dispatch
- **Purpose:** Read `output/brain/unified_proposals.json` and send Telegram digest (top-3 cards + conflict badges per §5.1)
- **Scripts:** `scanner/brain/brain_telegram.py` (currently a 6-line **stub**; Step 7 not implemented)
- **Reads:** `output/brain/unified_proposals.json` (read-only)
- **Writes:** none
- **Commits:** No (`permissions: contents: read`)
- **Telegram:** Yes (digest)
- **Active:** ⚠️ Workflow runs, but `brain_telegram.py` is a stub — no actual digest is sent. **Step 7 deferred.**

### colab_sync.yml (79 LOC)
- **Trigger:** GH schedule `45 10 * * 1-5` (16:15 IST) + workflow_dispatch
- **Purpose:** Export resolved signal history into a Colab-readable JSON for backtest research
- **Scripts:** `scanner/colab_sync.py`
- **Reads:** `output/signal_history.json`
- **Writes:** `output/colab_export.json`
- **Commits:** Yes
- **Telegram:** Yes (success/fail)
- **Active:** ✅

### deep_debugger.yml (129 LOC)
- **Trigger:** workflow_dispatch only (manual; modes: audit / sa-check / regime-audit / signal / lifecycle)
- **Purpose:** Signal forensics console
- **Scripts:** `scanner/deep_debugger.py`
- **Reads:** signal_history, patterns, eod_prices, etc.
- **Writes:** stdout / Telegram only
- **Commits:** No
- **Telegram:** Optional (input flag)
- **Active:** ✅ on-demand

### deploy_pages.yml (151 LOC)
- **Trigger:** `push:` to `output/**` (auto-deploys PWA) + workflow_dispatch
- **Purpose:** Publish `output/` to GitHub Pages (tietiy.in CNAME), inject PWA PIN
- **Scripts:** inline shell + `actions/configure-pages` + `actions/deploy-pages`
- **Reads:** `output/*` (entire directory)
- **Writes:** GitHub Pages artifact
- **Commits:** No
- **Telegram:** No
- **Active:** ✅ fires on every commit that touches `output/`

### diagnostic.yml (134 LOC)
- **Trigger:** GH schedule `0 11 * * 1-5` (16:30 IST) + workflow_dispatch (modes + self-heal flag)
- **Purpose:** End-of-day system diagnostic & self-heal
- **Scripts:** `scanner/diagnostic.py`
- **Reads:** signal_history, meta, system_health
- **Writes:** `output/system_health.json` (potentially)
- **Commits:** Yes (if changes)
- **Telegram:** Yes
- **Active:** ✅ but GH schedule is the known-unreliable mechanism

### eod.yml (120 LOC)
- **Trigger:** cron-job.org @ 16:15 IST + workflow_dispatch
- **Purpose:** **Bridge L4 EOD composer** — reads resolved signal_history (mutated by `eod_master.yml` at 15:35), composes EOD SDRs (plain dicts, no `bucket` field), writes `bridge_state.json` + dated history
- **Scripts:** `python scanner/bridge/bridge.py --phase EOD`, `python scanner/bridge_telegram_eod.py`
- **Reads:** signal_history, patterns, proposals, contra, mini_scanner_rules
- **Writes:** `output/bridge_state.json`, `output/bridge_state_history/<date>_EOD.json`
- **Commits:** Yes (atomic single commit per state_writer)
- **Telegram:** Yes (always, even if no resolutions today)
- **Active:** ✅ (migrated from GH schedule → cron-job.org on 2026-04-28; see bridge_design_v1 §13.4)

### eod_master.yml (271 LOC)
- **Trigger:** cron-job.org @ 15:35 IST + workflow_dispatch (debug flags: skip_pattern_miner, skip_rule_proposer, skip_validation)
- **Purpose:** **The 8-step EOD chain.** Backup → EOD prices → outcome resolve → open-validate → recover-stuck → pattern miner → rule proposer → chain validator (CRIT-03)
- **Scripts:** Step-by-step inline Python via `.venv/bin/python -m scanner.<module>`:
  1. `scanner/backup_manager.py` (`weekday_backup`)
  2. `scanner/eod_prices_writer.py`
  3. `scanner/outcome_evaluator.py`
  4. (optional re-run of open_validator for late corrections)
  5. `scanner/recover_stuck_signals.py`
  6. `scanner/pattern_miner.py`
  7. `scanner/rule_proposer.py`
  8. `scanner/chain_validator.py`
- **Reads:** signal_history, eod_prices, open_prices, patterns
- **Writes:** mutates signal_history (sole mutator post-09:32); writes eod_prices.json, patterns.json, proposed_rules.json, system_health.json
- **Commits:** Yes (one commit per chain run)
- **Telegram:** Yes (chain status)
- **Active:** ✅ Most load-bearing single workflow in the system
- **M-12 ordering fix:** Pattern miner runs *before* chain validator so the validator reads fresh `generated_at`

### gap_report.yml (76 LOC)
- **Trigger:** GH schedule `0 3 * * 1` (Mon 08:30 IST) + workflow_dispatch (input: telegram=true/false)
- **Purpose:** Weekly gap-risk analysis — finds stocks that often gap through their stops (entry_valid=False)
- **Scripts:** `scanner/gap_report.py`
- **Reads:** `output/signal_history.json`
- **Writes:** Telegram only (no file writes)
- **Commits:** No
- **Telegram:** Yes
- **Active:** ✅

### heartbeat.yml (64 LOC)
- **Trigger:** GH schedule `0 3 * * 1-5` (08:30 IST Mon-Fri) + workflow_dispatch
- **Purpose:** Daily alive ping — regime, active count, last scan time
- **Scripts:** `scanner/heartbeat.py`
- **Reads:** `output/meta.json`
- **Writes:** Telegram only
- **Commits:** No
- **Telegram:** Yes
- **Active:** ✅ (single most important canary — if it stops, the entire GH-schedule layer is dead)

### lab_ms1_fetch.yml (137 LOC)
- **Trigger:** workflow_dispatch only (manual; branch: backtest-lab; smoke / 5y / 15y modes)
- **Purpose:** Build 15-year OHLCV cache for 188 stocks + indices — feeds the `lab/` backtest factory
- **Scripts:** `lab/infrastructure/fetcher.py`
- **Reads:** universe CSV
- **Writes:** Parquet cache (uploaded as `lab-cache` artifact, 90-day retention)
- **Commits:** No (artifact only)
- **Telegram:** No
- **Active:** ✅ on-demand; not in daily critical path

### ltp_updater.yml (93 LOC)
- **Trigger:** cron-job.org `*/5 04-10 * * 1-5` UTC = every 5 min from 09:30 to 15:30 IST
- **Purpose:** Fetch intraday LTP for every PENDING signal via yfinance 1m bars
- **Scripts:** `scanner/ltp_writer.py`
- **Reads:** signal_history (PENDING signals + today entry_date)
- **Writes:** `output/ltp_prices.json`
- **Commits:** Yes (every 5 min — high commit churn)
- **Telegram:** No (the writer itself doesn't send; alerts go via stop_check)
- **Concurrency:** `cancel-in-progress: true` (latest run replaces older one)
- **Active:** ✅ ~76 fires/day

### master_check.yml (555 LOC)
- **Trigger:** workflow_dispatch only (telegram input flag)
- **Purpose:** Runtime validation of every scanner Python file — T1 syntax (py_compile), T2 imports, T3 safe execution + 13 inline checks
- **Scripts:** inline Python only (no separate module)
- **Reads:** all `scanner/**/*.py`
- **Writes:** stdout / Telegram
- **Commits:** No
- **Telegram:** Optional
- **Active:** ✅ on-demand (run after batch edits before deploy)

### morning_scan.yml (102 LOC)
- **Trigger:** cron-job.org @ 08:45 IST + workflow_dispatch
- **Purpose:** **The day starts here.** 188-stock F&O scan (UP_TRI, DOWN_TRI, BULL_PROXY, SA detection)
- **Scripts:** `python -m scanner.main` (entry: `run_morning_scan()` in `scanner/main.py:491`)
- **Reads:** `data/fno_universe.csv`, yfinance daily bars, banned_stocks.json
- **Writes:** signal_history.json (new PENDING signals), scan_log.json, mini_log.json, rejected_log.json, regime_debug.json, meta.json, index.html, banned_stocks.json
- **Commits:** Yes (one consolidated commit)
- **Telegram:** Yes (morning brief + scan results)
- **Concurrency:** group `tietiy-scan`
- **Active:** ✅ Precision-critical

### open_validate.yml (91 LOC)
- **Trigger:** cron-job.org @ 09:32 IST + workflow_dispatch (and retry slots at 10:02, 10:32)
- **Purpose:** Fetch actual 09:15 open prices, compute gap%, set `entry_valid` flag. **Also internally fires Day-6 outcome resolution** (D6B) if any signal's `effective_exit_date == today`
- **Scripts:** `scanner/open_validator.py`
- **Reads:** signal_history (PENDING signals with entry_date == today)
- **Writes:** `output/open_prices.json`, mutates `signal_history.json` (gap_pct, entry_valid, actual_open); may also write outcome fields via internal D6B trigger
- **Commits:** Yes
- **Telegram:** Yes
- **Concurrency:** `tietiy-open-validate`
- **Active:** ✅

### postopen.yml (113 LOC)
- **Trigger:** cron-job.org @ 09:40 IST + workflow_dispatch
- **Purpose:** **Bridge L2 POST_OPEN** — gap evaluation + bucket re-assignment + conditional Telegram (`should_send_telegram` only fires on bucket_change or severe gap)
- **Scripts:** `python scanner/bridge/bridge.py --phase POST_OPEN`, `python scanner/bridge_telegram_postopen.py`
- **Reads:** signal_history, open_prices, L1 dated history file (`bridge_state_history/<date>_PRE_MARKET.json`)
- **Writes:** `output/bridge_state.json`, `output/bridge_state_history/<date>_POST_OPEN.json`
- **Commits:** Yes
- **Telegram:** **Conditional** — only when `bucket_changes > 0 OR gap_breaches > 0`
- **Concurrency:** `bridge-postopen`
- **Active:** ✅

### premarket.yml (110 LOC)
- **Trigger:** cron-job.org @ 08:55 IST + workflow_dispatch
- **Purpose:** **Bridge L1 PRE_MARKET** — reads truth files, runs 10 background queries, builds SDRs, writes bridge_state, sends Telegram brief
- **Scripts:** `python scanner/bridge/bridge.py --phase PRE_MARKET`, `python scanner/bridge_telegram_premarket.py`
- **Reads:** signal_history, patterns, proposed_rules, contra_shadow, mini_scanner_rules, colab_insights
- **Writes:** `output/bridge_state.json`, `output/bridge_state_history/<date>_PRE_MARKET.json`
- **Commits:** Yes
- **Telegram:** Always (the daily brief is the trader's first signal)
- **Concurrency:** `bridge-premarket`
- **Active:** ✅

### rebuild_html.yml (105 LOC)
- **Trigger:** `push:` to `output/{ui,app,journal,stats,sw}.js`, `output/manifest.json`, `scanner/html_builder.py`
- **Purpose:** Regenerate `output/index.html` with fresh cache-bust timestamp so PWA refetches changed JS
- **Scripts:** `scanner/html_builder.py` (`build_html()`)
- **Reads:** none (template-generates)
- **Writes:** `output/index.html`
- **Commits:** Yes (uses `[skip ci]` to avoid infinite loop)
- **Telegram:** No
- **Active:** ✅

### recover_stuck_signals.yml (90 LOC)
- **Trigger:** workflow_dispatch only
- **Purpose:** One-shot recovery for PENDING signals stranded by yfinance fetch failures
- **Scripts:** `scanner/recover_stuck_signals.py`
- **Reads:** signal_history, eod_prices (M-11 fix: source of truth)
- **Writes:** mutates signal_history
- **Commits:** Yes
- **Telegram:** Yes
- **Active:** ✅ on-demand

### register_push.yml (152 LOC)
- **Trigger:** workflow_dispatch only (called by PWA via repository_dispatch in older designs; currently manual)
- **Purpose:** Register a web-push subscription from the PWA (VAPID)
- **Scripts:** inline Python + `scanner/push_sender.py`
- **Reads:** PIN hash, subscription payload
- **Writes:** `output/subscriptions.json` (appends; file is not currently in the repo listing — may be `.gitignore`d)
- **Commits:** Yes
- **Telegram:** Yes (registration ack)
- **Active:** ✅ on-demand

### scan_watchdog.yml (340 LOC)
- **Trigger:** cron-job.org @ ~09:02 IST + workflow_dispatch
- **Purpose:** **Verify morning_scan landed.** If not, retrigger. Wave 4 G1/G9 fixes: check GitHub Actions API first (immediate), fall back to Pages `meta.json` (CDN lag); dedup guard prevents redundant retriggers
- **Scripts:** inline shell + `gh api`
- **Reads:** GitHub Actions API, `meta.json` from Pages
- **Writes:** triggers `morning_scan.yml` if stale
- **Commits:** No
- **Telegram:** Yes (alert if morning_scan missed)
- **Active:** ✅ This is the single most important reliability workflow

### stop_check.yml (88 LOC)
- **Trigger:** cron-job.org `2-57/5 04-10 * * 1-5` UTC = every 5 min staggered +2 from LTP updater
- **Purpose:** Detect stop-hit and target-hit breaches, send Telegram alerts (deduped via stop_alerts_sent.json)
- **Scripts:** `scanner/stop_alert_writer.py` → `run_stop_check()`
- **Reads:** signal_history, eod_prices, stop_alerts_sent
- **Writes:** stop_alerts.json, stop_alerts_sent.json
- **Commits:** Yes (every 5 min)
- **Telegram:** Yes (on breach + dedup)
- **Active:** ✅ ~76 fires/day

### telegram_poll.yml (94 LOC)
- **Trigger:** cron-job.org every 10 min, 24×7
- **Purpose:** Poll Telegram `getUpdates`, dispatch any user commands (`/today`, `/exits`, `/pnl`, `/stops`, `/signals`, `/stats`, `/health`, `/status`, `/proposals`, `/patterns`, `/approve`, `/reject`, `/approve_rule`, `/reject_rule`, `/explain`, `/help`)
- **Scripts:** `scanner/telegram_poll_runner.py` → `scanner/telegram_bot.py::poll_and_respond()`
- **Reads:** meta.json, signal_history.json, ltp_prices.json, plus per-command JSONs (patterns, proposals, stop_alerts)
- **Writes:** tg_offset.json (offset advance)
- **Commits:** Yes (tg_offset only)
- **Telegram:** Yes (responses)
- **Concurrency:** `telegram-poll`
- **Active:** ✅

### wave2.yml (137 LOC)
- **Trigger:** workflow_dispatch only (modes: dry_run / execute)
- **Purpose:** Legacy migration runner (kills fix-table items H-03, H-09, M-06: IST helper consolidation)
- **Status:** ✅ Migration completed; workflow retained as escape hatch

### wave5_m08.yml (121 LOC)
- **Trigger:** workflow_dispatch only (modes: dry_run / execute)
- **Purpose:** Wave 5.1 migration — consolidate `_esc()` MarkdownV2 escaper across gap_report/heartbeat/deep_debugger/diagnostic → canonical import from telegram_bot
- **Status:** ✅ Completed; retained

### weekend_summary.yml (63 LOC)
- **Trigger:** GH schedule `30 3 * * 6` (Sat 09:00 IST) + workflow_dispatch
- **Purpose:** Saturday weekly recap — W/L/F counts, win rate, top winners/losers
- **Scripts:** `scanner/weekend_summary.py`
- **Reads:** signal_history
- **Writes:** Telegram only
- **Commits:** No
- **Telegram:** Yes
- **Active:** ✅

### weekly_intelligence.yml (153 LOC)
- **Trigger:** GH schedule `30 14 * * 0` (Sun 20:00 IST) + workflow_dispatch
- **Purpose:** Sunday AI intelligence — patterns, proposals, regime outlook. **This is where the `regime` field that brain reads gets refreshed.**
- **Scripts:** `scanner/weekly_intelligence.py`
- **Reads:** signal_history, patterns, proposed_rules, contra_shadow, regime_debug, system_health, mini_scanner_rules
- **Writes:** `output/weekly_intelligence_latest.json`
- **Commits:** Yes
- **Telegram:** Yes (intelligence brief)
- **Active:** ✅ — **load-bearing for brain's regime label** (see Dimension 10 for the staleness implication)

### eod_update.yml.bak (preserved)
- **Trigger:** none (file extension `.bak`)
- **Purpose:** Old monolithic EOD workflow — preserved as escape hatch per eod_master.yml line 30 comment
- **Status:** ❌ Disabled; do not invoke

---

## Workflow → script dependency map

```
.github/workflows/                  Calls (Python entry)              Mutates
─────────────────────────────────   ──────────────────────────────    ─────────────────────────────
morning_scan.yml                →   scanner.main:run_morning_scan  →  signal_history, scan_log, …
scan_watchdog.yml               →   (gh api + inline shell)        →  retriggers morning_scan
premarket.yml                   →   scanner.bridge.bridge --PRE_M  →  bridge_state (PRE_MARKET)
open_validate.yml               →   scanner.open_validator         →  open_prices, signal_history
postopen.yml                    →   scanner.bridge.bridge --POST_O →  bridge_state (POST_OPEN)
ltp_updater.yml  (every 5m)     →   scanner.ltp_writer             →  ltp_prices
stop_check.yml   (every 5m)     →   scanner.stop_alert_writer      →  stop_alerts, stop_alerts_sent
eod_master.yml                  →   backup → eod_prices_writer →   →  signal_history (resolutions),
                                    outcome_evaluator → open_v →      eod_prices, patterns,
                                    recover_stuck → pattern_miner →   proposed_rules,
                                    rule_proposer → chain_validator   system_health
eod.yml                         →   scanner.bridge.bridge --EOD    →  bridge_state (EOD)
brain.yml                       →   scanner.brain.brain_cli run    →  output/brain/*
brain_digest.yml                →   scanner.brain.brain_telegram   →  (stub — no-op currently)
diagnostic.yml                  →   scanner.diagnostic             →  system_health
heartbeat.yml                   →   scanner.heartbeat              →  (Telegram only)
gap_report.yml                  →   scanner.gap_report             →  (Telegram only)
backup_manager.yml              →   scanner.backup_manager         →  backups/
weekend_summary.yml             →   scanner.weekend_summary        →  (Telegram only)
weekly_intelligence.yml         →   scanner.weekly_intelligence    →  weekly_intelligence_latest
colab_sync.yml                  →   scanner.colab_sync             →  colab_export
telegram_poll.yml               →   scanner.telegram_poll_runner   →  tg_offset
deploy_pages.yml                →   actions/deploy-pages           →  GH Pages artifact
rebuild_html.yml                →   scanner.html_builder           →  index.html
recover_stuck_signals.yml       →   scanner.recover_stuck_signals  →  signal_history
register_push.yml               →   scanner.push_sender            →  subscriptions
master_check.yml                →   inline                          →  (Telegram only)
deep_debugger.yml               →   scanner.deep_debugger           →  (Telegram only)
lab_ms1_fetch.yml               →   lab.infrastructure.fetcher      →  artifact only
wave2.yml / wave5_m08.yml       →   scripts/wave*_migration.py      →  (one-shot completed)
```

---

## Workflows by activity classification

| Class | Workflows | Count |
|---|---|---|
| **Daily critical path** | morning_scan, premarket, open_validate, postopen, ltp_updater, stop_check, eod_master, eod, brain | 9 |
| **Daily supplementary** | scan_watchdog, telegram_poll, brain_digest (stub), heartbeat, diagnostic | 5 |
| **Weekly** | gap_report, backup_manager, weekend_summary, weekly_intelligence, colab_sync | 5 |
| **Deploy automation** | deploy_pages, rebuild_html | 2 |
| **Manual / on-demand** | deep_debugger, master_check, recover_stuck_signals, register_push, lab_ms1_fetch | 5 |
| **Migration (one-shot, retained)** | wave2, wave5_m08 | 2 |
| **Disabled** | eod_update.yml.bak | 1 |
| **Total** | | 29 |

---

## Anomalies worth flagging

1. **brain_digest.yml fires but does nothing.** `brain_telegram.py` is a 6-line stub. The cron-job.org schedule wakes the workflow, the workflow imports the stub, the stub returns. No digest is sent. Step 7 deferred.
2. **`eod.yml` time is 16:15 IST** per its own header comment — but `CLAUDE.md` and `bridge_design_v1.md` say 16:00 IST. The repo file is the source of truth; docs are out of date.
3. **`scan_watchdog.yml` is huge (340 LOC).** It's grown into a major reliability layer with its own G1/G9 fix logic.
4. **`master_check.yml` is the largest workflow** at 555 LOC — 73 inline checks across syntax/imports/runtime. Has its own bug-fix history (`nonlocal → global`).
5. **`weekly_intelligence.yml` runs on GH schedule** even though it produces the `regime` label that brain (cron-job.org) reads. If GH schedule misses on a Sunday, brain reads stale regime for the entire next week.
6. **No workflow currently mutates `signal_history.json` between 09:32 and 15:35.** open_validator.yml at 09:32 is the only morning mutator; outcome_evaluator at 15:35 is the only EOD mutator. All midday work is read-only.
