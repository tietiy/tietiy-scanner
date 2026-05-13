# Dimension 5 — Module Inventory

**Generated:** 2026-05-13
**Scope:** Every code module in the repo — purpose, key entry points, line count, active vs legacy.

Total Python LOC across the live tree: **~19,769 in `scanner/`** + brain subpackage + bridge subpackage.

---

## scanner/ (top-level pipeline)

37 Python files. Listed alphabetically with key entry points and the JSON files each one touches.

| File | LOC | Purpose | Reads | Writes | Active |
|---|---|---|---|---|---|
| `alert_failure.py` | 28 | Tiny helper to fire Telegram alerts on workflow failure | env vars | — | ✅ |
| `backup_manager.py` | 410 | Weekly snapshots into `backups/`; weekday backups also invoked in eod_master step 1 | signal_history | `backups/<ts>/` | ✅ |
| `ban_fetcher.py` | 168 | Pull NSE F&O ban list (HTTP fetch + parse CSV) | NSE web | `banned_stocks.json` | ✅ |
| `bridge_telegram_eod.py` | ~492 | EOD Telegram digest renderer; reads `bridge_state.json` (phase=EOD), always fires | bridge_state | Telegram | ✅ |
| `bridge_telegram_postopen.py` | ~431 | POST_OPEN renderer; respects `should_send_telegram` | bridge_state | Telegram | ✅ |
| `bridge_telegram_premarket.py` | ~530 | PRE_MARKET renderer; always fires | bridge_state | Telegram | ✅ |
| `calendar_utils.py` | 277 | IST time helpers, trading-day calendar (uses `nse_holidays.json`) | nse_holidays | — | ✅ |
| `chain_validator.py` | 433 | EOD chain post-validation (CRIT-03): checks all expected mutations happened, emits DEGRADED | meta, open_prices, eod_prices, signal_history, patterns, proposed_rules, contra_shadow | `system_health.json` | ✅ |
| `colab_sync.py` | 309 | Export resolved signal history into Colab-friendly JSON | signal_history | `colab_export.json` | ✅ |
| `config.py` | 72 | Constants: TARGET_R_MULTIPLE, RISK_PCT_*, EMA_PERIOD, PIVOT_LOOKBACK, ATR_PERIOD, SMC_COOLDOWN, paths | — | — | ✅ |
| `contra_tracker.py` | 357 | Records inverted shadow when a kill_pattern fires; resolves at Day 6 (CS3) | mini_scanner_rules | `contra_shadow.json` | ✅ |
| `deep_debugger.py` | 859 | Forensics console: audit / signal / lifecycle / sa-check / regime-audit modes | all | stdout / Telegram | ✅ on-demand |
| `diagnostic.py` | 838 | Daily diagnostic + self-heal | meta, system_health | maybe system_health | ✅ |
| `eod_prices_writer.py` | 521 | Fetch daily OHLC (CRIT-01 includes open); schema v2 nested `ohlc_by_symbol` | signal_history | `eod_prices.json` | ✅ |
| `gap_report.py` | 428 | Weekly Monday gap-risk analysis | signal_history | Telegram | ✅ |
| `heartbeat.py` | 165 | Daily alive ping | meta | Telegram | ✅ |
| `html_builder.py` | 372 | Generate `index.html` shell with cache-bust query strings | — | `index.html` | ✅ |
| `journal.py` | 994 | Owner of `signal_history.json`. `log_signal()`, `log_rejected()`, `archive_old_records()`, `update_sa_parent_outcome()` | signal_history, signal_archive | signal_history, signal_archive, backup | ✅ |
| `ltp_writer.py` | 439 | Intraday LTP fetch (every 5 min, 09:30–15:30). LW1 excludes terminal outcomes; BX3 holiday guard | signal_history | `ltp_prices.json` | ✅ |
| `main.py` | 1,085 | Master orchestrator. `run_morning_scan()`, `run_morning_stop_check()`, `run_eod()`, `run_brain()` | all | all | ✅ |
| `meta_writer.py` | 148 | Write meta.json + nse_holidays.json | — | `meta.json`, `nse_holidays.json` | ✅ |
| `mini_scanner.py` | 579 | Rule overlay. Shadow mode default; kill/warn/boost pattern matching; calls contra_tracker on kill | mini_scanner_rules (data/) | `mini_log.json`, `rejected_log.json` | ✅ |
| `open_validator.py` | 488 | 09:32 IST. Fetch 9:15 open, compute gap_pct, set entry_valid. D6B: trigger same-day Day-6 outcome resolution | signal_history | `open_prices.json`, mutates signal_history | ✅ |
| `outcome_evaluator.py` | 1,215 | **Sole post-09:32 mutator of signal_history.** Resolves 6-day window: STOP/TARGET/DAY6 + MFE/MAE + failure_reason + data_quality | signal_history, eod_prices, open_prices, nse_holidays, contra_shadow | mutates signal_history, contra_shadow | ✅ |
| `pattern_miner.py` | 538 | Mine resolved signals → (regime, sector, grade) cohorts → `patterns.json` (Tier validated/preliminary) | signal_history | `patterns.json` | ✅ |
| `price_feed.py` | 133 | Price feed abstraction (yfinance now; 5paisa planned) | — | — | ✅ |
| `push_sender.py` | 336 | Web push (VAPID) | `subscriptions.json` | — | ✅ |
| `recover_stuck_signals.py` | 592 | Resolve PENDING signals stranded by yfinance failures, using eod_prices as source of truth | signal_history, eod_prices | mutates signal_history | ✅ on-demand |
| `rule_proposer.py` | 925 | Generate kill/warn/boost proposals from patterns. Approve/reject mutators called from telegram_bot | patterns, proposed_rules, mini_scanner_rules | `proposed_rules.json`, mutates mini_scanner_rules | ✅ |
| `scanner_core.py` | 794 | Signal detection: pivots, zones, EMA alignment, UP_TRI/DOWN_TRI/BULL_PROXY + Second-Attempt | yfinance | in-memory dicts | ✅ |
| `scorer.py` | 234 | `score_signal`, `get_action`, `calc_target`, `calc_position_size`, `enrich_signal` | — | in-memory | ✅ |
| `stop_alert_writer.py` | 849 | Stop/target hit detection every 5 min. SA1 terminal exclusion, BX6 entry_valid, BX7+BX8 dedup, G2/G6 sanity | signal_history, eod_prices, stop_alerts_sent | `stop_alerts.json`, `stop_alerts_sent.json` | ✅ |
| `telegram_bot.py` | 2,915 | THE bot. Send functions + command handlers + polling loop. Owns _esc MarkdownV2 escaper | meta, signal_history, ltp_prices, patterns, proposed_rules, mini_scanner_rules, stop_alerts | Telegram, mutates tg_offset + mini_scanner_rules | ✅ |
| `telegram_poll_runner.py` | 60 | Workflow entry point that loads JSON inputs and calls `telegram_bot.poll_and_respond()` | meta, signal_history, ltp_prices | tg_offset | ✅ |
| `universe.py` | 53 | Load `fno_universe.csv` and produce symbol/sector/grade maps | fno_universe.csv | — | ✅ |
| `weekend_summary.py` | 217 | Saturday weekly recap (W/L/F counts) | signal_history | Telegram | ✅ |
| `weekly_intelligence.py` | 485 | Sunday AI intelligence — **owns the `regime` field that brain reads** | signal_history, patterns, proposed_rules, contra_shadow, regime_debug, system_health, mini_scanner_rules | `weekly_intelligence_latest.json` | ✅ |

**Subdirectories under `scanner/`:** `brain/`, `bridge/`, `journal/` (just `trades.csv`), `output/` (just `index.html` template).

---

## scanner/brain/ (Wave 5 nightly intelligence)

9 files. Steps 3-6 complete; Step 7 (Telegram digest + `/approve` handlers) deferred.

| File | LOC | Purpose | Active |
|---|---|---|---|
| `__init__.py` | — | Package marker | ✅ |
| `brain_cli.py` | 27 | CLI orchestrator entry point; sub-step routing — **Tier 1 commands (`status`/`rules`/`explain`/`trace`) are stubs** | partial |
| `brain_input.py` | 63 | Load truth files; missing-file → empty dict + stderr warning (P-12 discipline) | ✅ |
| `brain_state.py` | 133 | Atomic write + dated history archive; no prune (K-4 lock) | ✅ |
| `brain_derive.py` | 597 | 4 derivers: `_derive_cohort_health`, `_derive_regime_watch`, `_derive_portfolio_exposure`, `_derive_ground_truth_gaps` | ✅ |
| `brain_verify.py` | 620+ | 16-violation taxonomy. `verify_proposal`, `build_proposal_candidate`, `score_priority`, 4 candidate generators (boost_promote/demote, kill_rule, cohort_review) | ✅ |
| `brain_reason.py` | 1085 | 3 LLM gates (cohort_promotion_judge, regime_shift_detector, exposure_correlation_analyzer). Cost tracker $1 warn / $5 abort. Append-only `reasoning_log.json` | ✅ |
| `brain_output.py` | 853 | Step 6: combine, score-prio rank, top-3 cap, §5.1 conflict detection, dual-write to `proposed_rules.json` | ✅ |
| `brain_telegram.py` | **6** | Step 7 stub. **Empty.** `brain_digest.yml` fires this but it's a no-op | ⚠️ stub |

Brain reads: signal_history, patterns, proposed_rules, contra_shadow, weekly_intelligence_latest, mini_scanner_rules, bridge_state_history/<date>_EOD.json, plus its own reasoning_log + decisions_journal.

Brain writes: `output/brain/cohort_health.json`, `regime_watch.json`, `portfolio_exposure.json`, `ground_truth_gaps.json`, `verification_failures.json`, `reasoning_log.json`, `decisions_journal.json`, `unified_proposals.json` + dated history copies in `output/brain/history/`. Dual-writes kill_rule/boost_demote candidates into `proposed_rules.json`.

---

## scanner/bridge/ (decision composition layer)

Organized into subdirectories. ~3,500 LOC total.

```
scanner/bridge/
├── __init__.py
├── bridge.py                   (330 LOC) — CLI router (--phase PRE_MARKET / POST_OPEN / EOD)
├── composers/
│   ├── premarket.py            (646 LOC) — L1 composer
│   ├── postopen.py             (607 LOC) — L2 composer, history-aware
│   ├── eod.py                  (618 LOC) — L4 composer, plain-dict SDRs
│   └── _history_reader.py      (114 LOC) — Read L1 dated history file for L2
├── core/
│   ├── sdr.py                  (116 LOC) — SDR dataclass (immutable)
│   ├── state_writer.py         (189 LOC) — Atomic tmp→rename, 30-day history retention
│   ├── error_handler.py        (223 LOC) — Phase status computation
│   ├── bucket_engine.py        (477 LOC) — 4-gate decision tree
│   ├── evidence_collector.py   (258 LOC) — Orchestrates 10 background queries
│   ├── display_hints.py        (175 LOC) — Card title/emoji/priority/color
│   └── upstream_health.py      (162 LOC) — Check system_health.json
├── rules/
│   ├── kill_matcher.py         (109 LOC) — Gate 1
│   ├── validity_checker.py     (68 LOC)  — Gate 2 (min RR, max age, entry_valid)
│   ├── boost_matcher.py        (110 LOC) — Gate 3 (Tier A/B → TAKE_FULL/TAKE_SMALL)
│   ├── watch_matcher.py        (107 LOC) — Informational only
│   └── thresholds.py           (84 LOC)  — Central constants source
├── queries/
│   ├── q_exact_cohort.py       (130) — signal × sector × regime exact match
│   ├── q_sector_recent_30d.py  (143) — sector last-30-day stats
│   ├── q_regime_baseline.py    (76)  — regime WR baseline
│   ├── q_score_bucket.py       (81)  — same-score WR
│   ├── q_stock_recency.py      (120) — per-stock last outcome
│   ├── q_anti_pattern.py       (112) — opposing low-WR patterns
│   ├── q_cluster_check.py      (158) — clustering warnings (Wave 5)
│   ├── q_pattern_match.py      (142) — supporting + opposing pattern lists
│   ├── q_gap_evaluation.py     (153) — L2-only: gap severity, entry_still_valid
│   ├── q_signal_today.py       (58)  — filter PENDING signals for today
│   ├── q_open_positions.py     (122) — still-OPEN from prior days
│   └── _registry.py            (94)  — plugin auto-discovery (Wave 2 unused)
├── learner/                    — reserved (Wave 4-5)
├── alerts/                     — reserved
└── templates/                  — reserved
```

Bridge invariants (per CLAUDE.md §5):
- **Read-only** w.r.t. `signal_history.json`. Outcome_evaluator at 15:35 is the sole mutator.
- **Single write chokepoint**: `state_writer.write_state()` is the only path to disk.
- **Atomic writes**: tmp → fsync → rename, plus 30-day history retention.

---

## data/ (committed config)

| File | Size | Purpose |
|---|---|---|
| `fno_universe.csv` | 3.6 KB | 188 F&O stocks: symbol, sector, grade |
| `mini_scanner_rules.json` | 8.9 KB | schema_version 3. shadow_mode flag + boost/kill/warn patterns. User-editable + mutated by `/approve_rule` |

---

## output/ (generated artifacts; served by GitHub Pages)

Catalogued thoroughly in Dimension 6. Top-level files (excluding subdirs):

```
output/
├── signal_history.json         (706 KB, schema v5)   ← THE central truth file
├── signal_history.backup.json  (704 KB)              ← pre-rejection migration backup
├── signal_archive.json         (42 B)                ← essentially empty
├── bridge_state.json           (247 KB, schema v1)   ← current bridge phase
├── ltp_prices.json             (10 KB)               ← every 5 min
├── eod_prices.json             (49 KB, schema v2)    ← daily OHLC with ohlc_by_symbol
├── open_prices.json            (3.9 KB)              ← 9:15 actual_open per signal
├── scan_log.json               (6.6 KB)              ← morning scan summary
├── mini_log.json               (9 KB)                ← mini_scanner activity
├── rejected_log.json           (4.5 KB)              ← shadow-mode rejections
├── stop_alerts.json            (26 KB)               ← stop/target breaches
├── stop_alerts_sent.json       (57 B)                ← dedup cache (resets daily)
├── target_alerts_sent.json     (72 B)
├── patterns.json               (141 KB, schema v1)   ← mined cohorts
├── proposed_rules.json         (59 KB, schema v1)    ← pending/approved rule proposals
├── contra_shadow.json          (31 KB, schema v2)    ← inverted-direction shadows
├── meta.json                   (701 B)               ← system snapshot
├── system_health.json          (897 B)               ← chain validator output
├── health_report.json          (711 B)               ← LEGACY (superseded by system_health)
├── banned_stocks.json          (133 B)               ← NSE F&O ban list
├── regime_debug.json           (4.5 KB)              ← regime classifier debug log
├── colab_export.json           (800 KB)              ← Colab research export
├── weekly_intelligence_latest.json (4.1 KB)          ← Sunday AI intelligence
├── tg_offset.json              (21 B)                ← Telegram update offset
├── nse_holidays.json           (323 B)
├── manifest.json                                     ← PWA manifest
├── index.html                                        ← PWA root
├── analysis.html                                     ← analysis dashboard
├── health.html                                       ← health dashboard
├── analysis.js                                       ← analysis engine
├── app.js, ui.js, journal.js, stats.js, sw.js        ← PWA scripts
├── analysis/  (6 bundle files)                       ← analysis plugins
├── brain/                                            ← brain output dir
│   ├── cohort_health.json, regime_watch.json, portfolio_exposure.json, ground_truth_gaps.json
│   ├── reasoning_log.json (append-only), decisions_journal.json (append-only)
│   ├── unified_proposals.json, verification_failures.json
│   └── history/<date>_<view>.json (daily archives, no prune)
├── bridge_state_history/<date>_<phase>.json          ← 30-day retention
└── backups/                                          ← outcome of weekday backups
```

**Note:** `output/` is committed to git and served by GitHub Pages. Every workflow that mutates an output file commits its change, which means the repo has very high commit volume (every 5 min during market hours from ltp_updater + stop_check).

---

## scripts/ (operator utilities, not invoked from workflows)

| File | Purpose |
|---|---|
| `analyze_full.py` | Ad-hoc full analysis |
| `test_anthropic_api.py` | Sanity-test the ANTHROPIC_API_KEY before brain.yml |
| `wave2_migration.py` | One-shot migration (Wave 2: IST helpers consolidation) |
| `wave5_m08_migration.py` | One-shot migration (Wave 5.1: _esc consolidation) |
| `_run_smoke_brain_*.py` | Five smoke-test runners (derive, output, reason, telegram, verify) |

---

## shadow_ops/, src/tietiy/, lab/, quarantine/, backups/

| Tree | Purpose | Status |
|---|---|---|
| `shadow_ops/` | Test harness for shadow/contra logic | ✅ has tests/ |
| `src/tietiy/` | Empty namespace package (`__pycache__` only) — placeholder for future packaging | ✅ structural |
| `lab/` | The 15-year backtest factory (`lab_ms1_fetch.yml` populates `lab/cache/`) | ✅ separate from production |
| `quarantine/` | Old code preserved as escape-hatches (backup_20260411, wave2_20260423, wave5_20260423) | ⚠️ legacy snapshots |
| `backups/` | Weekly snapshots of signal_history | ✅ rotating |
| `tests/` | Pytest suite | ✅ |

---

## Phantom modules — documented but absent

| Module | Doc reference | Reality |
|---|---|---|
| `auto_analyst.py` | `doc/bridge_design_v1.md` line 23, `doc/session_context.md` | Not implemented. Superseded by `pattern_miner.py` + `rule_proposer.py`. |
| `score_critique.py` | mentioned in `master_audit_2026-04-27.md` | Not implemented. Possibly future observability tool. |
| `query_proposer` | brain_design_v1 §5 line 338 (query_promote type) | Not implemented. Wave 6+ scope. |

---

## The 5 modules that move the most data

By LOC and by importance:

1. **`telegram_bot.py`** (2,915 LOC) — the system's user-facing surface; 16 commands + 11 broadcast functions.
2. **`outcome_evaluator.py`** (1,215 LOC) — sole post-09:32 mutator of signal_history; the most consequential single script.
3. **`main.py`** (1,085 LOC) — orchestrates morning_scan; the day's largest writer.
4. **`brain_reason.py`** (1,085 LOC) — Anthropic API integration; the only LLM dependency.
5. **`journal.py`** (994 LOC) — owns signal_history schema and migrations.

---

## Module age and "actively used" status

Verified via `git log --follow <file>`-style review of recent commits and workflow grep cross-references:

- **Actively invoked every trading day:** main, scanner_core, scorer, mini_scanner, journal, open_validator, ltp_writer, stop_alert_writer, outcome_evaluator, eod_prices_writer, pattern_miner, rule_proposer, chain_validator, meta_writer, ban_fetcher, calendar_utils, contra_tracker, telegram_bot, telegram_poll_runner, push_sender, html_builder, bridge (all subpackages), bridge_telegram_*.
- **Active weekly:** weekend_summary, weekly_intelligence, gap_report, backup_manager, colab_sync, diagnostic, heartbeat.
- **Active nightly (Mon-Sun):** brain_cli, brain_input, brain_derive, brain_verify, brain_reason, brain_output, brain_state.
- **Stub / inactive:** `brain_telegram.py` (Step 7 deferred).
- **On-demand only:** deep_debugger, recover_stuck_signals.
- **Legacy (one-shot migration scripts):** `scripts/wave*_migration.py`.

No dead code spotted at the module level. The repository is reasonably tight — almost every file is invoked somewhere.
