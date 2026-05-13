# Dimension 3 — Daily Timeline (minute-by-minute)

**Generated:** 2026-05-13
**Scope:** What runs, in what order, on a typical Mon–Fri trading day. Read this top-to-bottom and you will know what the system did between midnight and midnight.

All times are IST. Workflow fire is `>>`. Mutation of a tracked file is `→ FILE`. Telegram sends are `📨`.

---

## Overnight (00:00 – 08:29 IST)

**System is idle.** No scheduled workflow except `telegram_poll.yml` every 10 minutes (responds to user `/commands` if any). No JSON file mutates.

---

## Pre-market (08:30 – 09:14 IST)

### 08:30 IST — heartbeat.yml (GH schedule)
- Reads `meta.json` (which still reflects yesterday's scan).
- 📨 Sends "alive" ping to Telegram: regime, active count, last scan time.
- Mondays only: `gap_report.yml` also fires at 08:30 → weekly gap-risk Telegram digest.

### 08:45 IST >> morning_scan.yml (cron-job.org) — **THE DAY BEGINS**

Critical-path orchestrator. Inside `scanner/main.py:run_morning_scan()`:

| Step | What happens | File touched |
|---|---|---|
| 1 | Trading-day check + market regime fetch | → `regime_debug.json` (RA1 fix) |
| 2 | `scanner.ban_fetcher.write_ban_list()` — fetch NSE F&O ban list | → `banned_stocks.json` |
| 3 | Load universe (`data/fno_universe.csv`, 188 stocks) | |
| 4 | For each stock: `scanner_core.prepare()` + `detect_signals()` + `detect_second_attempt()` | yfinance fetch |
| 5 | `scorer.enrich_signal()` per signal — score/bucket/target/RR/position size | |
| 6 | Duplicate-pending filter | |
| 7 | `mini_scanner.filter_signals()` — overlay rules; SHADOW MODE by default | → `mini_log.json`, `rejected_log.json` |
| 8 | `journal.log_signal()` for every passed signal (and `log_rejected()` if shadow_mode off) | → `signal_history.json` |
| 9 | Archive records older than 90 days | → `signal_archive.json` |
| 10 | Write meta + holidays + index.html | → `meta.json`, `nse_holidays.json`, `index.html` |
| 11 | Send web push notifications | (via `push_sender.py`) |
| 12 | 📨 Send morning scan summary + brief to Telegram | |
| 13 | Poll Telegram for any queued commands (HC4) | → `tg_offset.json` |

One consolidated git commit at the end (the largest commit of the day).

### 08:55 IST >> premarket.yml (cron-job.org) — **BRIDGE L1**

`scanner/bridge/bridge.py --phase PRE_MARKET`:

1. Load truth files: `signal_history`, `patterns`, `proposed_rules`, `contra_shadow`, `colab_insights`, `mini_scanner_rules`.
2. `evidence_collector` runs **9 background queries per signal** (exact_cohort, sector_recent_30d, regime_baseline, score_bucket, stock_recency, anti_pattern_check, cluster_warnings, pattern_match, boost/kill match).
3. `bucket_engine` walks the 4-gate tree per signal → bucket ∈ {TAKE_FULL, TAKE_SMALL, WATCH, SKIP}.
4. Build PRE_MARKET SDRs (immutable dataclasses).
5. `state_writer.write_state()` — **atomic single write** to:
   - → `output/bridge_state.json`
   - → `output/bridge_state_history/<date>_PRE_MARKET.json`
6. 📨 `bridge_telegram_premarket.send_premarket_brief()` — always fires (the trader's primary briefing).

### 09:02 IST >> scan_watchdog.yml (cron-job.org)

Verifies `morning_scan.yml` completed.
- G1: queries GitHub Actions API directly (immediate state, no CDN lag).
- G9: dedup guard — if morning_scan is in_progress/queued, skip retrigger.
- If morning_scan missed → re-dispatch + 📨 alert.

---

## Open & post-open (09:15 – 09:45 IST)

### 09:15 IST — Market opens (no workflow; informational)

### 09:32 IST >> open_validate.yml (cron-job.org)

`scanner/open_validator.py`:
- For each signal whose `entry_date == today`:
  - Fetch yfinance 1m bar (first bar = 09:15 actual_open).
  - Compute `gap_pct = (actual_open - prev_close) / prev_close * 100`.
  - If `|gap_pct| > 3%` → `entry_valid = False` (outcome_evaluator will skip this signal).
- → `output/open_prices.json`
- → mutates `signal_history.json` with `gap_pct`, `actual_open`, `entry_valid`.
- **D6B trigger:** if any signal has `effective_exit_date == today`, internally calls outcome_evaluator NOW (rather than waiting for tomorrow's 01:00 IST run) — same-day Day-6 resolution.

### 09:40 IST >> postopen.yml (cron-job.org) — **BRIDGE L2**

`scanner/bridge/bridge.py --phase POST_OPEN`:

1. Load truth files **+ open_prices.json**.
2. Read L1 dated history (`bridge_state_history/<date>_PRE_MARKET.json`) via `_history_reader` to know the L1 bucket per signal.
3. For each signal:
   - Run `q_gap_evaluation` → `gap_severity` ∈ {minor, moderate, severe} + `entry_still_valid` + `rr_at_actual_open`.
   - If `entry_still_valid == False` → `_force_skip_invalid_entry()` (bucket = SKIP, gate_fired = "L2_GAP_INVALID").
   - Else: re-run `bucket_engine` with updated RR. Compare to L1 bucket.
   - Track `bucket_changed`, `previous_bucket`, `bucket_change_reason`.
4. Count `bucket_changes` + `gap_breaches`. Compute `should_send_telegram = (bucket_changes > 0 OR gap_breaches > 0)`.
5. → `bridge_state.json` + `bridge_state_history/<date>_POST_OPEN.json`.
6. 📨 `bridge_telegram_postopen.send_postopen_brief()` — **conditional**: respects `should_send_telegram`. If quiet, no Telegram fires.

---

## Intraday loops (09:30 – 15:30 IST)

These two run continuously, every 5 min, staggered.

### 09:30 + 5m increments >> ltp_updater.yml

`scanner/ltp_writer.py`:
- Filter PENDING signals that aren't terminal-state (LW1 fix excludes STOP_HIT/TARGET_HIT/DAY6_*).
- Skip if market closed (holiday guard).
- yfinance 1m intraday — fetch LTP for each ticker.
- → `output/ltp_prices.json` (schema: `{date, fetch_time, count, prices: {symbol → {ltp, prev_close, change_pct, fetch_time}}}`).
- Concurrency `cancel-in-progress: true` — only the latest run survives.
- No Telegram (the writer is silent).

### 09:32 + 5m increments >> stop_check.yml (offset +2 min)

`scanner/stop_alert_writer.run_stop_check()`:
- For each PENDING signal:
  - Exclude terminal outcomes (SA1).
  - Skip if entry_valid == False (BX6).
  - Sanity-check price: ±30% from entry, ±20% from last EOD close (G2/G6 — prevents MARUTI ghost-stop).
  - Detect breaches: `low <= stop` (LONG) or `high >= stop` (SHORT) → `BREACHED`.
  - Detect target hits separately (B3): `high >= target` → `TARGET` alert, but **signal continues to Day 6** (F1: dual-track).
  - Dedup: same stock × direction once per cycle (BX7), persisted across cycles (BX8 via `stop_alerts_sent.json`).
- → `output/stop_alerts.json` + `stop_alerts_sent.json`.
- 📨 Telegram alert per fresh breach.

### Every 10 min, 24×7 >> telegram_poll.yml

Independent of trading hours.
- `scanner/telegram_poll_runner.py` calls `telegram_bot.poll_and_respond(meta, history, ltp_prices, window_minutes=35)`.
- `_get_updates()` reads `tg_offset.json`, advances by `update_id+1` after processing each message.
- Per-command try/except (TG-01) ensures one crashing handler doesn't kill the poll.
- Handlers: `/today`, `/exits`, `/pnl`, `/stops`, `/signals`, `/stats`, `/health`, `/status`, `/proposals`, `/patterns`, `/approve`, `/reject`, `/approve_rule`, `/reject_rule`, `/explain`, `/help`.
- `/approve_rule <id>` mutates `data/mini_scanner_rules.json` (activates kill_pattern). `/approve` and `/reject` are designed for brain proposals but the brain Step-7 wiring is not yet in place.

---

## Market close → EOD chain (15:30 – 16:15 IST)

### 15:30 IST — Market closes (no workflow; informational)

### 15:35 IST >> eod_master.yml (cron-job.org) — **THE 8-STEP CHAIN**

The single most load-bearing workflow. Each step is a separate `.venv/bin/python -m scanner.<module>` invocation; the chain runs sequentially.

| Step | Module | What it does | File touched |
|---|---|---|---|
| 1 | `scanner.backup_manager weekday_backup` | Snapshot signal_history before mutations | → `backups/<timestamp>/` |
| 2 | `scanner.eod_prices_writer` | Fetch daily OHLC (CRIT-01: include open) for every ticker | → `output/eod_prices.json` (schema v2 with `ohlc_by_symbol`) |
| 3 | `scanner.outcome_evaluator` | **The only post-09:32 mutator of signal_history.** Resolves 6-day tracking windows: STOP_HIT, TARGET_HIT, DAY6_WIN/LOSS/FLAT. Writes `outcome`, `result`, `pnl_pct`, `r_multiple`, `mfe_pct`, `mae_pct`, `failure_reason`, `data_quality`. Also resolves `contra_shadow` entries at Day 6 (CS3). | → mutates `signal_history.json`, `contra_shadow.json` |
| 4 | (optional `open_validator` re-run for late corrections) | Catch any signals where actual_open arrived after 09:32 fetch | |
| 5 | `scanner.recover_stuck_signals` | Resolve PENDING signals stranded by yfinance failures, using eod_prices as source of truth | → mutates `signal_history.json` |
| 6 | `scanner.pattern_miner` | Mine patterns from resolved signals (M-12 ordering fix: this runs **before** chain_validator) | → `output/patterns.json` |
| 7 | `scanner.rule_proposer` | Generate kill/warn/boost proposals from patterns; only thinks about cohorts that don't already have an active rule | → `output/proposed_rules.json` |
| 8 | `scanner.chain_validator` | Validate the whole chain (CRIT-03): check that all expected mutations happened, no stale generated_at, no missing data; emit DEGRADED warnings if anything is off | → `output/system_health.json` |

One consolidated commit at the end. 📨 Telegram chain status.

### 16:15 IST >> eod.yml (cron-job.org) — **BRIDGE L4 EOD**

`scanner/bridge/bridge.py --phase EOD`:
- By now signal_history is fully mutated for today (eod_master finished at ~15:50–16:10).
- Build **plain-dict** EOD SDRs (no `bucket` field — the signal is closed; the SDR carries an `outcome` block instead).
- Demotion warnings: surface any cohort that has trended below boost threshold.
- → `bridge_state.json` (phase=EOD) + `bridge_state_history/<date>_EOD.json`.
- 📨 `bridge_telegram_eod.send_eod_brief()` — always fires.

### 16:15 IST >> colab_sync.yml (GH schedule)

`scanner.colab_sync`: export resolved signal history as Colab-friendly JSON → `output/colab_export.json`. (~800 KB; lives alongside other outputs.)

### 16:30 IST >> diagnostic.yml (GH schedule)

`scanner.diagnostic`: deep system inspection. Optional self-heal flag. → updates `system_health.json` if anomalies detected.

---

## Quiet hours (16:30 – 21:59 IST)

System idle except for `telegram_poll.yml` every 10 min.

---

## Brain night cycle (22:00 – 22:05 IST)

### 22:00 IST >> brain.yml (cron-job.org, **Mon–Sun all 7 days**)

`scanner.brain.brain_cli run`:

| Sub-step | What happens | File touched |
|---|---|---|
| **Step 3 Derive** | 4 deterministic derivers: cohort_health, regime_watch, portfolio_exposure, ground_truth_gaps | → `output/brain/<view>.json` + `output/brain/history/<date>_<view>.json` |
| **Step 4 Verify** | 4 generators emit candidate proposals (boost_promote from Tier M+S cohorts, boost_demote vs prior archive, kill_rule from negative-edge cohorts, cohort_review from thin rules); each verified against 16-violation taxonomy | → `output/brain/verification_failures.json` (1000-entry cap) |
| **Step 5 LLM gates** | 3 Claude Opus 4.7 calls: `cohort_promotion_judge` (per candidate), `regime_shift_detector` (once), `exposure_correlation_analyzer` (once). Cost tracker: $1 soft warn, $5 hard abort | → `output/brain/reasoning_log.json` (append-only forever, K-4 lock) |
| **Step 6 Output** | Combine, score-priority rank, top-3 cap, conflict detection (§5.1) against active mini_scanner_rules, dual-write kill_rule/boost_demote candidates into `proposed_rules.json` | → `output/brain/unified_proposals.json`, `output/proposed_rules.json` |

Typical cost per run: ~$0.05. Concurrency lock prevents overlap with self.

### 22:05 IST >> brain_digest.yml (cron-job.org, Mon–Sun)

**Currently a no-op.** `scanner/brain/brain_telegram.py` is a 6-line stub. The workflow fires, imports the stub, exits. Step 7 (digest send + `/approve` `/reject` handlers) is **deferred to Wave UI**.

---

## Weekend cycle

| When | Workflow | What |
|---|---|---|
| Sat 08:30 IST | `backup_manager.yml` | Weekly snapshot to `backups/` |
| Sat 09:00 IST | `weekend_summary.yml` | Telegram weekly recap |
| Mon-Sun 22:00 IST | `brain.yml` | Same brain run; weekend reads Friday-EOD-stable files |
| Mon-Sun 22:05 IST | `brain_digest.yml` | (stub) |
| Sun 20:00 IST | `weekly_intelligence.yml` | **Refreshes `weekly_intelligence_latest.json#regime` — the value brain reads as the current regime** |

The weekly_intelligence regime refresh is load-bearing: brain reads its `regime` field once a week, and that label drives most rule activation gates. See Dimension 10.

---

## Full-day reference table

| IST | Workflow | Mutation | Telegram |
|---|---|---|---|
| 08:30 | heartbeat | none | 📨 alive |
| 08:30 (Mon) | gap_report | none | 📨 weekly gap risk |
| 08:45 | **morning_scan** | signal_history (NEW), scan_log, meta, regime_debug | 📨 morning brief + scan |
| 08:55 | **premarket** | bridge_state (PRE_MARKET) | 📨 daily brief |
| 09:02 | scan_watchdog | retrigger if needed | 📨 only on miss |
| 09:15 | (market open) | — | — |
| 09:32 | **open_validate** | open_prices, signal_history (gap fields), maybe outcomes (D6B) | 📨 |
| 09:40 | **postopen** | bridge_state (POST_OPEN) | 📨 conditional |
| 09:30–15:30 ×76 | ltp_updater | ltp_prices | — |
| 09:32–15:32 ×76 | stop_check | stop_alerts, stop_alerts_sent | 📨 on breach |
| 24×7 ×144 | telegram_poll | tg_offset | 📨 on /command |
| 15:30 | (market close) | — | — |
| 15:35 | **eod_master** (8 steps) | eod_prices, signal_history (outcomes), patterns, proposed_rules, system_health | 📨 chain status |
| 16:15 | **eod** | bridge_state (EOD) | 📨 digest |
| 16:15 | colab_sync | colab_export | 📨 status |
| 16:30 | diagnostic | maybe system_health | 📨 |
| 22:00 | **brain** | output/brain/* + proposed_rules (dual-write) | — |
| 22:05 | brain_digest | (no-op — stub) | — (designed yes, actual no) |

---

## How to read this on a single screen

```
       ╔═══════════════════════════╗   ╔═══════════════════════════╗
       ║       MORNING (1)         ║   ║       MIDDAY (2)          ║
       ║                           ║   ║                           ║
08:30  ║ heartbeat 📨              ║   ║                           ║
08:45  ║ morning_scan → SH+scan_log║   ║                           ║
08:55  ║ premarket → bridge_state  ║   ║                           ║
09:02  ║ scan_watchdog (verify)    ║   ║                           ║
09:15  ║ ── MARKET OPEN ──         ║   ║                           ║
09:32  ║ open_validate → open+SH   ║   ║ ltp_updater every 5m      ║
09:40  ║ postopen → bridge_state   ║   ║ stop_check every 5m       ║
       ║                           ║   ║ telegram_poll every 10m   ║
       ╠═══════════════════════════╣   ╚═══════════════════════════╝
       ║       CLOSE (3)           ║   ╔═══════════════════════════╗
15:30  ║ ── MARKET CLOSE ──        ║   ║       NIGHT (4)           ║
15:35  ║ eod_master (8 steps)      ║   ║                           ║
       ║   → SH (outcomes), eod,   ║   ║                           ║
       ║     patterns, proposals   ║   ║                           ║
16:15  ║ eod (bridge L4) →         ║   ║                           ║
       ║   bridge_state            ║   ║                           ║
16:15  ║ colab_sync                ║   ║                           ║
16:30  ║ diagnostic                ║   ║                           ║
       ║                           ║22:00║ brain → cohort_health,    ║
       ║                           ║     ║  regime_watch, portfolio,║
       ║                           ║     ║  unified_proposals       ║
       ║                           ║22:05║ brain_digest (STUB)       ║
       ╚═══════════════════════════╝   ╚═══════════════════════════╝
```
