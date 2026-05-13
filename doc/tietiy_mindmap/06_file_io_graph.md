# Dimension 6 — File I/O Dependency Graph

**Generated:** 2026-05-13
**Scope:** Every JSON / CSV file in `output/` and `data/` — who writes, who reads, when, whether the PWA or Telegram consumes it.

---

## Notation

- **W**: writer script(s)
- **R**: reader script(s) and surfaces (PWA / Telegram bot / Bridge / Brain)
- **Cadence**: how often it changes
- **Git**: committed each change? (Yes/No)
- **Surface**: served via GitHub Pages → tietiy.in? (visible to browser fetch)

---

## Core signal files

### `output/signal_history.json` (~706 KB, schema v5)
- **W**: `scanner/journal.py` (create at 08:45), `scanner/open_validator.py` (09:32, gap fields), `scanner/outcome_evaluator.py` (15:35 + D6B, terminal outcomes), `scanner/recover_stuck_signals.py` (on-demand)
- **R**: `scanner/telegram_bot.py` (all command handlers), `scanner/colab_sync.py`, `scanner/pattern_miner.py`, `scanner/rule_proposer.py`, `scanner/weekly_intelligence.py`, `scanner/weekend_summary.py`, `scanner/gap_report.py`, `scanner/chain_validator.py`, `scanner/diagnostic.py`, `scanner/heartbeat.py`, `scanner/stop_alert_writer.py`, `scanner/ltp_writer.py`, bridge composers (all 3), `scanner/brain/brain_input.py`, PWA `ui.js`, PWA `analysis.js` (via SQL.js bundle)
- **Cadence**: 1× morning, 1× 09:32, 1× 15:35, plus ad-hoc resolves
- **Git**: Yes
- **Surface**: Yes (PWA fetches it)
- **Invariant**: written by 4 scripts only; everyone else read-only

### `output/signal_history.backup.json` (~704 KB)
- **W**: `scanner/journal.py` (`_backup_history()` before every signal_history mutation)
- **R**: emergency restore only
- **Cadence**: same as signal_history
- **Git**: Yes
- **Surface**: Yes (but never read by app)

### `output/signal_archive.json` (42 bytes)
- **W**: `scanner/journal.py` `archive_old_records()` — moves records older than 90 days
- **R**: historical lookup
- **Cadence**: daily, but essentially empty right now
- **Git**: Yes
- **Surface**: Yes
- **Anomaly**: 42 bytes — archival pipeline either hasn't pruned yet, or the 90-day window hasn't been crossed

### `data/fno_universe.csv` (3.6 KB)
- **W**: manual (user-edited)
- **R**: `scanner/universe.py` → `load_universe()` → consumed by `scanner/main.py` morning scan
- **Cadence**: rarely (when adding/removing F&O stocks)
- **Git**: Yes
- **Surface**: No (data/ is not in output/)

### `data/mini_scanner_rules.json` (8.9 KB, schema v3)
- **W**: manual + `scanner/telegram_bot.py:_respond_approve_rule()` (activates a kill_pattern) + `scanner/rule_proposer.py:approve_proposal()` (mutator) + brain's dual-write path
- **R**: `scanner/mini_scanner.py`, bridge `kill_matcher.py`, `boost_matcher.py`, `watch_matcher.py`, `scanner/contra_tracker.py`, `scanner/brain/brain_input.py`, `scanner/brain/brain_output.py` (conflict detection §5.1)
- **Cadence**: only when user/brain approves a rule
- **Git**: Yes
- **Surface**: No
- **Anomaly**: this is the only file in `data/` that mutates during normal operation — it's not pure static config

---

## Bridge files

### `output/bridge_state.json` (~247 KB, schema v1)
- **W**: `scanner/bridge/core/state_writer.py:write_state()` — invoked by all three composers
- **R**: `scanner/bridge_telegram_premarket.py`, `scanner/bridge_telegram_postopen.py`, `scanner/bridge_telegram_eod.py`
- **Cadence**: 3× per trading day (08:55 → 09:40 → 16:15)
- **Git**: Yes
- **Surface**: Yes (PWA could read, but **currently does NOT** — that's a gap)

### `output/bridge_state_history/<date>_<phase>.json`
- **W**: `state_writer.write_state()` — dated archive copy every compose
- **R**: `scanner/bridge/composers/_history_reader.py` (L2 reads L1), `scanner/brain/brain_derive.py:_derive_portfolio_exposure()` (reads `<date>_EOD.json`)
- **Cadence**: 3 files per trading day
- **Git**: Yes
- **Retention**: 30 days (auto-cleanup by `state_writer._cleanup_history`)
- **Surface**: Yes

---

## Price data files

### `output/ltp_prices.json` (~10 KB)
- **W**: `scanner/ltp_writer.py` (every 5 min, 09:30–15:30)
- **R**: `scanner/telegram_bot.py` (`/today`, `/exits`, `/pnl`, `/stops`), `scanner/telegram_poll_runner.py`, `scanner/stop_alert_writer.py` (last-tick reference), PWA `ui.js`
- **Cadence**: ~76 writes per trading day
- **Git**: Yes (high churn!)
- **Surface**: Yes

### `output/eod_prices.json` (~49 KB, schema v2 with `ohlc_by_symbol`)
- **W**: `scanner/eod_prices_writer.py` (15:35)
- **R**: `scanner/outcome_evaluator.py` (EOD1 — primary OHLC source), `scanner/stop_alert_writer.py` (sanity-check baseline), `scanner/chain_validator.py`, `scanner/recover_stuck_signals.py` (M-11 source of truth)
- **Cadence**: 1× daily
- **Git**: Yes
- **Surface**: Yes
- **Schema note**: CRIT-01 added `open` per symbol/date; CRIT-02 adapter handles both v1 and v2

### `output/open_prices.json` (~3.9 KB)
- **W**: `scanner/open_validator.py` (09:32)
- **R**: `scanner/outcome_evaluator.py` (D6A — Day 6 open resolution), `scanner/stop_alert_writer.py`, `scanner/chain_validator.py`
- **Cadence**: 1× daily
- **Git**: Yes
- **Surface**: Yes

---

## Logging & filter files

### `output/scan_log.json` (~6.6 KB)
- **W**: `scanner/main.py` (morning scan)
- **R**: PWA `ui.js`, diagnostics
- **Cadence**: 1× morning
- **Git**: Yes
- **Surface**: Yes
- **Note**: weekend fix ensures valid JSON on non-trading days

### `output/mini_log.json` (~9 KB)
- **W**: `scanner/mini_scanner.py`
- **R**: diagnostics, PWA (potentially)
- **Cadence**: 1× morning
- **Git**: Yes
- **Surface**: Yes

### `output/rejected_log.json` (~4.5 KB)
- **W**: `scanner/mini_scanner.py`, `scanner/main.py` (line 690)
- **R**: diagnostics
- **Cadence**: 1× morning
- **Git**: Yes
- **Surface**: Yes

---

## Alert files

### `output/stop_alerts.json` (~26 KB)
- **W**: `scanner/stop_alert_writer.py` (every 5 min, 09:32–15:32)
- **R**: `scanner/telegram_bot.py` (`/stops`), PWA `ui.js`
- **Cadence**: ~76 writes per trading day
- **Git**: Yes (high churn)
- **Surface**: Yes

### `output/stop_alerts_sent.json` (57 bytes)
- **W**: `scanner/stop_alert_writer.py` (dedup state)
- **R**: same script next cycle (BX8 fix)
- **Cadence**: every 5 min, resets daily
- **Git**: Yes
- **Surface**: Yes (but never read by app)

### `output/target_alerts_sent.json` (72 bytes)
- Same pattern as `stop_alerts_sent.json` for target hits

---

## Intelligence files

### `output/patterns.json` (~141 KB, schema v1)
- **W**: `scanner/pattern_miner.py` (15:35 via eod_master step 6)
- **R**: `scanner/rule_proposer.py`, `scanner/telegram_bot.py` (`/patterns`), `scanner/brain/brain_input.py`, bridge `q_pattern_match.py` + `q_anti_pattern.py`, `scanner/weekly_intelligence.py`
- **Cadence**: 1× daily
- **Git**: Yes
- **Surface**: Yes

### `output/proposed_rules.json` (~59 KB, schema v1)
- **W**: `scanner/rule_proposer.py` (15:35), brain `brain_output.py` (dual-write kill_rule / boost_demote at 22:00)
- **R**: `scanner/telegram_bot.py` (`/proposals`, `/approve_rule`, `/reject_rule`), `scanner/weekly_intelligence.py`, bridge `q_pattern_match.py`, brain conflict detection
- **Cadence**: 1× daily (eod_master) + 1× nightly (brain dual-write)
- **Git**: Yes
- **Surface**: Yes
- **Note**: this is the *legacy* proposal queue. The brain's *unified* queue lives in `output/brain/unified_proposals.json`, but kill_rule + boost_demote candidates are also dual-written here for backward compat.

### `output/contra_shadow.json` (~31 KB, schema v2)
- **W**: `scanner/contra_tracker.py` (on kill_pattern fire), `scanner/outcome_evaluator.py` (Day 6 resolution, CS3)
- **R**: bridge composers (contra block in `bridge_state`), `scanner/weekly_intelligence.py`
- **Cadence**: event-driven on kill fires + Day-6 resolves
- **Git**: Yes
- **Surface**: Yes

---

## Brain files (`output/brain/`)

### `output/brain/cohort_health.json` (~15 KB)
- **W**: `scanner/brain/brain_derive.py:_derive_cohort_health()` (22:00)
- **R**: brain Step 4 generators, brain Step 5 LLM context, bridge `q_exact_cohort.py` (potentially)
- **Cadence**: 1× nightly
- **Git**: Yes; daily archive at `output/brain/history/<date>_cohort_health.json` (no prune)

### `output/brain/regime_watch.json` (~851 B)
- **W**: `brain_derive._derive_regime_watch()` — reads `weekly_intelligence_latest.json#regime` (does NOT compute regime itself)
- **R**: brain Step 5 (regime_shift_detector gate), brain Step 5 cohort_promotion context
- **Cadence**: 1× nightly
- **Git**: Yes; daily archive

### `output/brain/portfolio_exposure.json` (~1.7 KB)
- **W**: `brain_derive._derive_portfolio_exposure()` — reads `bridge_state_history/<date>_EOD.json`, falls back to signal_history if archive missing
- **R**: brain Step 5 (exposure_correlation_analyzer gate)
- **Cadence**: 1× nightly
- **Git**: Yes; daily archive

### `output/brain/ground_truth_gaps.json`
- **W**: `brain_derive._derive_ground_truth_gaps()` — thin rules (n<5), thin patterns (n<10)
- **R**: brain Step 4 cohort_review generator
- **Cadence**: 1× nightly
- **Git**: Yes; daily archive

### `output/brain/reasoning_log.json` (~58 KB; **append-only forever, K-4 lock**)
- **W**: `brain_reason.py` per LLM gate invocation
- **R**: `brain_reason.py` next-run history context (last 20 entries per gate, 90-day window)
- **Cadence**: appended each brain run
- **Git**: Yes
- **Note**: never pruned

### `output/brain/decisions_journal.json` (~231 B; **append-only forever**)
- **W**: `brain_output.py` initializes if missing; future Step 7 `/approve`/`/reject` handlers will append
- **R**: `brain_reason.py` history context (last 10 cohort-matched entries)
- **Cadence**: should be event-driven on user decisions; currently empty (Step 7 stub)

### `output/brain/unified_proposals.json` (~12 KB)
- **W**: `brain_output.py` (overwritten daily)
- **R**: `brain_digest.yml` (currently no-op stub); future Step 7 Telegram digest + PWA Monster tab
- **Cadence**: 1× nightly
- **Git**: Yes
- **History**: daily archive at `output/brain/history/<date>_unified_proposals.json`

### `output/brain/verification_failures.json`
- **W**: `brain_verify`, `brain_reason`, `brain_output` — failed proposals appended (1000-entry cap)
- **R**: forensics only

---

## System metadata files

### `output/meta.json` (~701 B)
- **W**: `scanner/meta_writer.py` (08:45)
- **R**: `scanner/telegram_poll_runner.py` (every poll), `scanner/telegram_bot.py` (`/status`, `/health`, `/today`), PWA `ui.js`, `scanner/heartbeat.py`
- **Cadence**: 1× daily
- **Git**: Yes
- **Surface**: Yes

### `output/system_health.json` (~897 B, schema v1)
- **W**: `scanner/chain_validator.py` (eod_master step 8), `scanner/diagnostic.py`
- **R**: bridge `core/upstream_health.py`, `scanner/weekly_intelligence.py`, PWA `health.html`
- **Cadence**: 1× daily + ad-hoc diagnostic runs
- **Git**: Yes
- **Surface**: Yes

### `output/health_report.json` (~711 B)
- **Status**: LEGACY (superseded by `system_health.json`)
- **W**: nobody currently
- **R**: nobody
- **Cadence**: never
- **Git**: Yes (stale)
- **Surface**: Yes

### `output/nse_holidays.json` (323 B)
- **W**: `scanner/meta_writer.py`
- **R**: `scanner/calendar_utils.py`, `scanner/outcome_evaluator.py`, bridge `bridge.py`
- **Cadence**: 1× daily
- **Git**: Yes

### `output/banned_stocks.json` (133 B)
- **W**: `scanner/ban_fetcher.py` (08:45)
- **R**: `scanner/main.py` (sets `is_banned` flag), PWA `ui.js`
- **Cadence**: 1× daily
- **Git**: Yes
- **Surface**: Yes

### `output/regime_debug.json` (~4.5 KB, schema v1)
- **W**: `scanner/main.py:_log_regime_debug` (08:45)
- **R**: `scanner/weekly_intelligence.py`, research only
- **Cadence**: 1× daily
- **Git**: Yes
- **Note**: explicit "read-only debug — never consumed by scanner logic"

### `output/weekly_intelligence_latest.json` (~4.1 KB, schema v1)
- **W**: `scanner/weekly_intelligence.py` (Sun 20:00 IST)
- **R**: `scanner/brain/brain_derive.py:_derive_regime_watch()` — **brain reads its `regime` field as the authoritative current regime**, PWA (potentially)
- **Cadence**: 1× weekly
- **Git**: Yes
- **Surface**: Yes
- **Anomaly**: this weekly file feeds the daily brain regime label. Brain can read a Sunday-stale regime for an entire week.

### `output/colab_export.json` (~800 KB)
- **W**: `scanner/colab_sync.py` (16:15)
- **R**: external Google Colab notebooks for backtest research
- **Cadence**: 1× daily
- **Git**: Yes (largest committed file in normal rotation)
- **Surface**: Yes

### `output/tg_offset.json` (21 B)
- **W**: `scanner/telegram_bot.py:_get_updates()` — advances after each polled update
- **R**: same script next run
- **Cadence**: every 10 min
- **Git**: Yes (very high churn — could grow noisy in git log)
- **Surface**: Yes

---

## PWA assets (served, not read as data)

| File | Role |
|---|---|
| `output/index.html` | PWA root; loads ui.js, app.js, journal.js, stats.js |
| `output/analysis.html` | Analysis dashboard; loads sql.js + chart.js + analysis bundle |
| `output/health.html` | Health dashboard (auto-refreshes every 60s) |
| `output/manifest.json` | PWA manifest |
| `output/sw.js` | Service worker (cache v8; never caches data JSON) |
| `output/ui.js`, `app.js`, `journal.js`, `stats.js` | Main PWA bundles |
| `output/analysis.js` | Analysis engine |
| `output/analysis/{overview,signals,segmentation,post_mortem,advanced}.js` | Analysis plugin bundles |
| `output/icon-*.png`, `badge-*.png`, `health-icon-*.png` | PWA icons |
| `output/CNAME` (root, not in output/) | tietiy.in CNAME |

---

## Dependency graph (file → file)

```
                            08:45 morning_scan.yml
                                    │
                                    ▼
        ┌─────────────────┬─────────┬────────┬──────────────┬──────────┐
        ▼                 ▼         ▼        ▼              ▼          ▼
banned_stocks      signal_history  scan_log  meta   regime_debug   index.html
        │                 │
        ▼                 ▼
   (morning scan filter)  └──────────► every reader script
                                       │
                            08:55 premarket.yml
                                    │
                                    ▼
                          bridge_state.json (PRE_MARKET)
                          + bridge_state_history/<date>_PRE_MARKET.json

                            09:15 MARKET OPEN
                            09:32 open_validate.yml
                                    │
                                    ▼
                          open_prices.json ──► outcome_evaluator (D6A, D6B)
                          + mutate signal_history (gap_pct, entry_valid)

                            09:40 postopen.yml
                                    │
                                    ▼
                          bridge_state.json (POST_OPEN)
                          (reads bridge_state_history/<date>_PRE_MARKET.json)

                            every 5m ltp_updater.yml
                                    │
                                    ▼
                          ltp_prices.json ──► telegram_bot (/today, /pnl, /stops, /exits)
                                                          PWA ui.js

                            every 5m stop_check.yml
                                    │
                                    ▼
                          stop_alerts.json
                          stop_alerts_sent.json (dedup)
                                    │
                                    ▼
                          📨 Telegram alerts

                            15:35 eod_master.yml (8 steps)
                                    │
        ┌────────┬───────────┬──────┴─────────┬─────────────┬──────────────┐
        ▼        ▼           ▼                ▼             ▼              ▼
   backups/  eod_prices  signal_history   patterns     proposed_rules  system_health
                          (resolutions
                           + MFE/MAE
                           + failure_reason)
                                                  │
                                                  ▼
                                       eligible for /patterns, /proposals

                            16:15 eod.yml
                                    │
                                    ▼
                          bridge_state.json (EOD, plain-dict)

                            22:00 brain.yml
                              │
                              ├── reads: signal_history, patterns, proposed_rules,
                              │           contra_shadow, weekly_intelligence_latest,
                              │           mini_scanner_rules, bridge_state_history/<date>_EOD.json
                              │
                              ├── writes: brain/cohort_health, regime_watch,
                              │           portfolio_exposure, ground_truth_gaps,
                              │           reasoning_log (append), unified_proposals,
                              │           decisions_journal (init)
                              │
                              └── dual-writes kill_rule / boost_demote candidates
                                    into proposed_rules.json (legacy queue)

                            22:05 brain_digest.yml — STUB, no-op
```

---

## "Hot" files (high commit churn)

These commit on every cadence — useful to know if you want to git-grep your way around:

| File | Commit cadence |
|---|---|
| `output/ltp_prices.json` | every 5 min during market hours (~76/day) |
| `output/stop_alerts.json` | every 5 min during market hours |
| `output/stop_alerts_sent.json` | every 5 min |
| `output/tg_offset.json` | every 10 min (24×7) |
| `output/bridge_state.json` | 3× per trading day (08:55, 09:40, 16:15) |
| `output/signal_history.json` | 1× morning + 1× 09:32 + 1× 15:35 |
| `output/eod_prices.json` | 1× daily (15:35) |
| `output/patterns.json`, `proposed_rules.json` | 1× daily (15:35) + brain dual-write |
| `output/brain/*` | 1× nightly (22:00) |
| `output/weekly_intelligence_latest.json` | 1× weekly (Sun 20:00) |
| `data/mini_scanner_rules.json` | only on rule approve/reject (rare) |

---

## Surfaces summary (where each file is consumed)

| Surface | Files it reads |
|---|---|
| **Telegram bot** (`telegram_bot.py`) | meta, signal_history, ltp_prices, stop_alerts, patterns, proposed_rules, mini_scanner_rules, brain/unified_proposals (future Step 7) |
| **PWA `ui.js`** | banned_stocks, eod_prices, ltp_prices, meta, mini_log, nse_holidays, open_prices, scan_log, signal_history, stop_alerts |
| **PWA `analysis.js`** | signal_history (via SQL.js) + patterns potentially |
| **PWA `health.html`** | system_health.json |
| **Bridge composers** | signal_history, patterns, proposed_rules, contra_shadow, mini_scanner_rules, open_prices (L2), bridge_state_history/<date>_PRE_MARKET (L2) |
| **Brain derive** | signal_history, patterns, proposed_rules, contra_shadow, weekly_intelligence_latest, mini_scanner_rules, bridge_state_history/<date>_EOD |
| **Brain reason (LLM)** | reasoning_log, decisions_journal, all derived views |
| **Bridge Telegram renderers** | bridge_state.json (only) |
| **Outcome evaluator** | signal_history, eod_prices, open_prices, nse_holidays, contra_shadow |
| **Pattern miner** | signal_history |
| **Rule proposer** | patterns, proposed_rules, mini_scanner_rules |

---

## What the PWA dashboard would need to display ALL system state

If you were building "TIE TIY 2.0 Dashboard" the consumed files are:

1. `meta.json` — system snapshot
2. `signal_history.json` — table + history
3. `ltp_prices.json` — live ticker
4. `stop_alerts.json` — active alerts
5. `bridge_state.json` — phase + bucket assignment + DEGRADED banner (**currently NOT read by ui.js** — gap)
6. `output/brain/unified_proposals.json` — pending proposals (currently NOT read by PWA)
7. `output/brain/cohort_health.json`, `regime_watch.json`, `portfolio_exposure.json` — for nightly intelligence views
8. `patterns.json` + `proposed_rules.json` — proposals queue
9. `system_health.json` — chain health badge
10. `weekly_intelligence_latest.json` — weekly recap card

The PWA currently consumes ~6 of these. The other 4 are a TIE TIY 2.0 dashboard opportunity.
