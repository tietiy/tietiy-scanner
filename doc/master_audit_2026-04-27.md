# TIE TIY Master Audit — 2026-04-27

**Scope:** Full project map, brain-layer integration plan, UI flow, gaps catalog.
**Author:** Claude (autonomous late-night audit, pre-authorized).
**Repo head at audit time:** `3a7ceae` (after analysis-script header edit).
**Audit basis:** repo state, git log, fix_table, session_context, bridge_design_v1, code reads. No fabrication — `[needs-verification]` where I'd otherwise guess.

This audit is honest, not flattering. Where the architecture has tradeoffs or weaknesses (including in code shipped this week), they're named explicitly.

---

## Table of contents

1. PART 1 — Data flow map
2. PART 2 — Daily project rhythm
3. PART 3 — Module dependency graph
4. PART 4 — Workflow audit
5. PART 5 — Bridge architecture deep-dive
6. PART 6 — PWA UI flow
7. PART 7 — Trader cognitive flow
8. PART 8 — Wave 5 brain-layer integration map
9. PART 9 — Approval gate consolidation
10. PART 10 — Gaps and fixes catalog
11. PART 11 — Final integration picture
12. PART 12 — Out-of-scope flags

---

## PART 1 — Data flow map

The project has 28+ JSON state files. Each is owned by one writer and consumed by zero-to-many readers. The cardinal sin (pre-Apr 26) was reaching across writer boundaries with the wrong field names — fixed when the schema-discipline principle was locked.

### File inventory

| File | Owner (writer) | Readers | Update cadence | Schema | If missing |
|---|---|---|---|---|---|
| `output/signal_history.json` | `journal.py` (new signals); `outcome_evaluator.py` (resolutions); `open_validator.py` (entry_valid + actual_open) | scanner_core, mini_scanner, bridge composers, queries, PWA app.js/journal.js/stats.js, weekly_intelligence, pattern_miner, rule_proposer, gap_report, contra_tracker | Multi-touch daily | v5 record-level | catastrophic — system blind |
| `output/signal_archive.json` | `journal.py` | bridge composers, weekly_intelligence | Append on resolution | v5 | reduces multi-quarter view; non-fatal |
| `output/bridge_state.json` | `bridge/core/state_writer.py` (single chokepoint) | PWA (planned via Wave UI); `bridge_telegram_*.py` renderers | 3× daily (L1 8:55, L2 9:40, L4 ~16:00 — when Session D ships) | v1 | renderers fail; PWA falls back to non-bridge data |
| `output/bridge_state_history/{YYYY-MM-DD}_{PHASE}.json` | `state_writer.write_state` | `bridge/composers/_history_reader.py` (L2 needs L1) | 3 archives per trading day, 30-day retention | matches state | L2 loses bucket_change reasoning vs L1 |
| `output/meta.json` | `meta_writer.py` | PWA ui.js, app.js (last_scan), heartbeat, weekly_intelligence | Per scan + EOD | v4 | PWA shows stale-data banner |
| `data/mini_scanner_rules.json` | `rule_proposer.approve_proposal` (mutates `kill_patterns[]`); manual `boost_patterns[]` edits; future demotion (LE-06) | mini_scanner, bridge bucket_engine via boost_matcher/kill_matcher, PWA stats.js | Rare, change-controlled | v3 | mini_scanner falls back to DEFAULT_RULES; bridge degrades to no-boost-no-kill |
| `output/patterns.json` | `pattern_miner.py` (eod_master step 7) | rule_proposer, bridge q_pattern_match, weekly_intelligence | Daily 15:35+ | preliminary/validated tiers | bridge degrades; rule_proposer skips |
| `output/proposed_rules.json` | `rule_proposer.py` (eod_master step 8); `approve_proposal`/`reject_proposal` mutators | telegram_bot `/proposals`, `/approve_rule`, `/reject_rule`; bridge q_proposals_pending; evidence_collector | Daily + on approval | v1 | Wave 4 approval flow blocked |
| `output/contra_shadow.json` | `contra_tracker.record()` (when kill_pattern hits); `outcome_evaluator._resolve_contra_shadows` | bridge `_build_contra_block`; weekly_intelligence | Per kill match + EOD | v2 (`original_direction`, `inverted_direction`) | contra-promotion track unobservable |
| `output/eod_prices.json` | `eod_prices_writer.py` (eod_master) | outcome_evaluator (Day 6 OHLC), weekly_intelligence | Daily 15:35 | v2 (`ohlc_by_symbol`) | outcome resolution falls back to yfinance |
| `output/open_prices.json` | `open_validator.py` | bridge q_gap_evaluation (L2), outcome_evaluator | Daily 09:32 | v1 | L2 falls back to NOT_VALIDATED for all signals |
| `output/ltp_prices.json` | `ltp_writer.py` | PWA app.js (intraday P&L), stop_alert_writer, telegram /pnl /stops | Every 5 min during market hours | dict by symbol | intraday P&L unavailable; stops degrade to last-known |
| `output/system_health.json` | `chain_validator.py` (eod_master step 6) | bridge upstream_health, weekly_intelligence, PWA health.html | Daily 15:35 | 7-check format | bridge phase_status reflects "unknown" upstream |
| `output/weekly_intelligence_latest.json` | `weekly_intelligence.py` (Sunday 20:00 IST) | Telegram weekly summary, PWA stats.js (planned) | Weekly | v1 | weekly summary skipped |
| `output/scan_log.json` | `journal.write_scan_log` | PWA, weekly_intelligence | Per scan | per-scan record | timeline view broken |
| `output/rejected_log.json` | `journal.write_scan_log` (rejected pile) | PWA journal.js (rejection reasons summary), gap_report | Per scan | flat list | rejection insight lost |
| `output/banned_stocks.json` | `ban_fetcher.py` (manual run? — `[needs-verification]`) | scanner_core (filter universe) | Rare | symbol list | banned stocks pass through universe filter |
| `output/regime_debug.json` | `main._log_regime_debug` | manual debug only | Per scan | flat | no impact |
| `output/mini_log.json` | `mini_scanner.py` (shadow-mode passthrough log) | PWA, debug | Per scan | log records | shadow visibility lost |
| `output/stop_alerts.json` | `stop_alert_writer.py` | telegram /stops, push_sender | Every 5 min | flat | trader misses stop proximity warnings |
| `output/stop_alerts_sent.json` | `stop_alert_writer.py` (dedup ledger) | stop_alert_writer (self) | Every 5 min | dedup keys | stops re-fire repeatedly until file rebuilt |
| `output/target_alerts_sent.json` | `stop_alert_writer.py` or `ltp_writer.py` (`[needs-verification]`) | same writer (dedup) | Every 5 min | dedup keys | target alerts re-fire |
| `output/tg_offset.json` | `telegram_poll_runner.py` / `telegram_bot.poll_and_respond` | self | Every 10 min | `{offset: int}` | bot replays processed messages |
| `output/colab_export.json` | `colab_sync.py` (16:15 IST) | Colab notebook (external) | Daily | flattened | backtest analysis stale |
| `output/health_report.json` | `diagnostic.py` | PWA health.html | On diagnostic run | health-report record | PWA health tab empty |
| `output/manifest.json` | `html_builder.py` | PWA service worker | Per build | PWA-version manifest | SW cache may not refresh |
| `output/nse_holidays.json` | `meta_writer.write_holidays` | calendar_utils, outcome_evaluator | Once at start of year + reload | list | trading-day check falls through to weekday-only |
| `output/signal_history.backup.json` | `open_validator.py` (snapshot before D6 mutations) | manual rollback only | Daily | mirrors history | rollback lost; non-fatal |
| `output/analysis_report_*.md` | `scripts/analyze_full.py` (manual or planned overnight) | trader manual read | On demand | markdown | non-blocking |

### Cross-writer hazards

- **`signal_history.json`** has THREE writers (journal, outcome_evaluator, open_validator). They run at different times (08:45, 09:32, 15:35) and each grabs its own atomic write — but if cron runs collide (e.g. retry storm), last-writer-wins could silently drop fields. Mitigation: each writer reads-merge-writes a full record set; single writer file lock not in place. **GAP-01 (HIGH).**
- **`mini_scanner_rules.json`** is mutated by `rule_proposer.approve_proposal`. If a Telegram approval fires during morning_scan, mini_scanner could read mid-mutation. **GAP-02 (MEDIUM).** Probability low (mutator is rare); impact would be one bad scan.
- **`bridge_state.json`** is the single chokepoint for bridge — but the renderers (`bridge_telegram_*.py`) read it without any version check. If state schema bumps, renderers may surface garbage. **GAP-03 (LOW)** — schema is stable for now.

---

## PART 2 — Daily project rhythm

All times IST. Asterisk = workflow_dispatch via cron-job.org (not GitHub native schedule). All other times = GitHub native `schedule:` block.

```
Sun 20:00  weekly_intelligence.yml     [native schedule]
              └── writes weekly_intelligence_latest.json + Telegram

Mon-Fri (trading day):
08:30      heartbeat.yml               [native schedule]
              └── alive ping to Telegram

08:30      backup_manager.yml          [Sat only, native schedule]
              └── snapshots history + archive

08:30      gap_report.yml              [Mon only, native schedule]
              └── analyzes prior week's entry_valid=False signals

08:45*     morning_scan.yml            [cron-job.org]
              └── main.py morning (scanner_core → scorer → mini_scanner
                                   → journal → meta_writer → chain_validator)
              └── writes: signal_history, meta, scan_log, rejected_log,
                          mini_log, regime_debug, system_health
              └── Telegram morning brief

08:55*     premarket.yml               [cron-job.org] ← bridge L1
              └── bridge.py --phase=PRE_MARKET
                  → composers/premarket.compose
                  → reads truth files (load_truth_files)
                  → q_signal_today (today's PENDING)
                  → per-signal: evidence_collector + bucket_engine → SDR
                  → contra_block from contra_shadow + mini_rules
                  → state_writer.write_state (atomic + history archive)
              └── bridge_telegram_premarket.py reads bridge_state.json,
                  renders L1 brief with bucket grouping

09:02*     scan_watchdog.yml           [cron-job.org]
              └── verifies morning_scan ran; retriggers if missed

09:15      [MARKET OPENS]              ← TRADER ACTION
              └── trader places entries based on premarket brief

09:32*     open_validate.yml           [cron-job.org]
              └── open_validator.py
                  → fetches 9:15 open prices via yfinance
                  → computes gap%, sets entry_valid
                  → triggers outcome_evaluator (D6B same-day Day-6 resolve)
              └── writes open_prices, signal_history (entry_valid +
                  outcome fields for D6 resolutions)

09:40*     postopen.yml                [cron-job.org] ← bridge L2
              └── bridge.py --phase=POST_OPEN
                  → composers/postopen.compose
                  → reads truth files + open_prices.json
                  → reads bridge_state_history/{date}_PRE_MARKET.json
                  → per-signal: evidence + q_gap_evaluation + bucket re-eval
                       → if entry invalid: force-skip override
                  → state_writer (POST_OPEN phase)
              └── bridge_telegram_postopen.py
                  → CONDITIONAL fire (should_send_telegram only when
                    bucket_change OR severe gap)

09:30+ to 15:30 — INTRADAY (continuous):
  every 5 min*  ltp_updater.yml       → ltp_prices.json
  every 5 min*  stop_check.yml         → stop_alerts + Telegram alerts
  every 10 min* telegram_poll.yml     → /today /exits /pnl /stops /signals
                                       /status /health /proposals
                                       /approve_rule /reject_rule /patterns

15:30      [MARKET CLOSES]

15:35*     eod_master.yml              [cron-job.org] ← 8-step chain
              1. backup_manager.py     → snapshots
              2-4. main.py eod         → outcome_evaluator (resolves OPEN)
                                        + eod_prices_writer (OHLC capture)
                                        + Telegram EOD digest [legacy fragmented]
              5. EOD validation        → CRIT-03 sanity gate
              6. chain_validator       → system_health.json
              7. pattern_miner         → patterns.json
              8. rule_proposer         → proposed_rules.json
              ATOMIC commit of ALL outputs

16:00*     [PLANNED] eod.yml          [Wave 3 Session D — NOT YET SHIPPED]
              └── bridge.py --phase=EOD
                  → composers/eod.compose
                  → reads fresh signal_history (just mutated)
                  → q_outcome_today (today's resolutions)
                  → per-resolution: build EOD SDR (plain dict, outcome embedded)
                  → state_writer (EOD phase)
              └── bridge_telegram_eod.py renders digest per §12.3

16:15*     colab_sync.yml              [cron-job.org]
              └── flattens gen=1 signals to colab_export.json

16:30*     diagnostic.yml              [cron-job.org]
              └── 6-mode self-check + auto-heal frame

Sat 09:00  weekend_summary.yml         [native schedule]
              └── W/L/F counts by signal type + Telegram

Sun 20:00  weekly_intelligence.yml     [native schedule]
              └── 5-section weekly digest + Telegram
```

### Trigger source dependency

**14 of 24 workflows depend on cron-job.org.** A cron-job.org outage breaks every precision-critical workflow (morning_scan, all bridge phases, open_validate, ltp_updater, stop_check, telegram_poll, eod_master, etc.). GitHub native `schedule:` is only used for non-precision items (heartbeat, weekly, weekend, gap_report, backup) where ±1hr drift is acceptable. **GAP-04 (HIGH).**

### Race conditions observed in production

1. **`b8f6e94` (premarket bot push at 22:16 UTC Sun) vs failed postopen `24968471468` (22:18 UTC Sun)** — postopen's commit-and-push exhausted 3 retries, fired notify-on-failure. Confirmed by user as benign during cron-job.org test fire. **GAP-05 (LOW)** — production schedule (45-min separation) prevents this.
2. **All bot commits use UTC labeled "IST"** — cosmetic but causes timeline confusion. Fix: `TZ='Asia/Kolkata' date ...` in 3 bridge workflows + others. **GAP-06 (LOW).**

---

## PART 3 — Module dependency graph

37 scanner modules + 41 bridge files + 14 utility scripts = ~92 Python files. Total scanner LOC: 18,374.

### Top-level modules by size

| Module | LOC | Role |
|---|---|---|
| telegram_bot.py | 2232 | Canonical `_esc`, 11 message types, command router, /approve|reject_rule, send_workflow_failure |
| outcome_evaluator.py | 1119 | The sole mutator of resolved fields. D6 trading-day arithmetic, OHLC fallback chain, contra shadow resolution |
| main.py | 1005 | 21-step morning scan orchestrator + EOD orchestrator |
| journal.py | 967 | signal_history + signal_archive owner; ensure_archive_exists, dedup logic |
| deep_debugger.py | 859 | Forensic tool — manual diagnostic |
| stop_alert_writer.py | 849 | Stop proximity, target hit detection, dedup ledger |
| diagnostic.py | 838 | Multi-mode (--quick / --heal etc) self-check + heal scaffold |
| scanner_core.py | 794 | UP_TRI / DOWN_TRI / BULL_PROXY detection logic, SA variants |

### Scanner modules — read/write summary

| Module | Reads | Writes |
|---|---|---|
| `scanner_core.py` | yfinance via price_feed, mini_scanner_rules (kill check), banned_stocks, fno_universe | (returns signals) |
| `scorer.py` | (per-signal context) | (returns score 0-10) |
| `mini_scanner.py` | mini_scanner_rules.json | mini_log.json |
| `journal.py` | signal_history (read-merge-write) | signal_history, signal_archive, scan_log, rejected_log |
| `meta_writer.py` | (no read) | meta.json, nse_holidays.json |
| `outcome_evaluator.py` | signal_history, eod_prices, open_prices, contra_shadow | signal_history (resolved), contra_shadow (resolved), backups |
| `open_validator.py` | signal_history, yfinance | open_prices.json, signal_history (entry_valid), backup |
| `eod_prices_writer.py` | yfinance, signal_history (filter) | eod_prices.json (v2 ohlc_by_symbol) |
| `ltp_writer.py` | yfinance | ltp_prices.json |
| `stop_alert_writer.py` | ltp_prices, signal_history, stop_alerts_sent | stop_alerts.json, stop_alerts_sent.json, target_alerts_sent.json (?) |
| `chain_validator.py` | meta, signal_history, mini_rules, contra_shadow, patterns, proposed_rules | system_health.json |
| `pattern_miner.py` | signal_history (resolved) | patterns.json |
| `rule_proposer.py` | patterns, mini_rules, proposed_rules | proposed_rules, mini_scanner_rules.json (on approve) |
| `contra_tracker.py` | mini_rules, signal_history (context) | contra_shadow.json |
| `weekly_intelligence.py` | patterns, proposals, contra, system_health, signal_history | weekly_intelligence_latest.json |
| `colab_sync.py` | signal_history, meta | colab_export.json |
| `gap_report.py` | open_prices, signal_history | (telegram only) |
| `heartbeat.py` | meta, mini_rules | (telegram only) |
| `weekend_summary.py` | signal_history | (telegram only) |
| `recover_stuck_signals.py` | signal_history | signal_history (mutates stuck-PENDING records) |
| `telegram_bot.py` | (everything readers consume) + tg_offset | tg_offset, sends Telegram |
| `telegram_poll_runner.py` | (calls telegram_bot.poll_and_respond) | tg_offset (via bot) |
| `diagnostic.py` | (everything) | health_report.json |
| `deep_debugger.py` | signal_history | (read-only) |
| `backup_manager.py` | signal_history, archive | backups/ |
| `ban_fetcher.py` | (external NSE source — `[needs-verification]`) | banned_stocks.json |
| `html_builder.py` | (templates) | index.html, manifest.json (with PIN injection) |
| `push_sender.py` | (subscribers) | sends VAPID web push |
| `alert_failure.py` | (called from workflows) | sends Telegram failure alert |

### Bridge modules

| Module | Reads | Writes |
|---|---|---|
| `bridge.py` | (CLI dispatch) | (none directly) |
| `composers/premarket.py` | truth files, q_signal_today, q_open_positions | (returns SDRs to state_writer) |
| `composers/postopen.py` | truth files, open_prices, L1 history file | (POST_OPEN SDRs) |
| `composers/eod.py` | truth files (signal_history primary) | (EOD SDRs — plain dicts) |
| `composers/_history_reader.py` | bridge_state_history/{date}_PRE_MARKET.json | (returns SDR lookup) |
| `core/state_writer.py` | (state dict from composer) | bridge_state.json + history archive |
| `core/evidence_collector.py` | truth files, calls 10 queries | (returns evidence dict) |
| `core/bucket_engine.py` | evidence, kill_match, boost_match | (returns bucket assignment) |
| `rules/boost_matcher.py` | mini_rules.boost_patterns | (match result) |
| `rules/kill_matcher.py` | mini_rules.kill_patterns | (match result) |
| `queries/q_*.py` (15 plugins) | various truth files | (per-query result) |

### Inconsistencies / dead code

- **Bridge `learner/` folder is empty** — `__init__.py` only. Wave 5 placeholder. Not dead, but not yet alive.
- **Bridge `templates/` folder is empty** — same.
- **Bridge `alerts/` folder is empty** — alerts are built inline in composers via `_build_basic_alerts` (premarket).
- **`q_outcome_today.py` exists in bridge/queries/** but is NOT called by `composers/eod.py` (which inlines `_select_resolutions_today`). **GAP-07 (MEDIUM)** — duplicate logic; pick one.
- **`q_contra_status.py` exists** but contra block is built inline by `_build_contra_block` in premarket.py. **GAP-08 (MEDIUM)** — same pattern.
- **`scanner/eod_update.yml.bak`** preserved as rollback escape hatch. Intentional (per fix_table); not dead.
- **Two telegram_poll entry points:** `telegram_poll_runner.py` (script) + `telegram_bot.poll_and_respond` (function). Wrapper relationship `[needs-verification]` but appears intentional.
- **No circular imports detected** — bridge composers import from premarket via direct symbol re-export; postopen and eod follow that pattern. Acceptable.
- **`recover_stuck_signals.py`** mutates signal_history outside the journal/outcome_evaluator chain — only safe because it runs manually with explicit user intent. **GAP-09 (LOW)** — no enforcement.

---

## PART 4 — Workflow audit

24 workflows. Categorized:

| Category | Workflows | Trigger |
|---|---|---|
| Precision-critical | morning_scan, premarket, open_validate, postopen, eod_master, ltp_updater, stop_check, telegram_poll, scan_watchdog, colab_sync, diagnostic | cron-job.org dispatch |
| Drift-tolerant | heartbeat, gap_report, backup_manager, weekend_summary, weekly_intelligence | GitHub native `schedule:` |
| Manual | deep_debugger, master_check, recover_stuck_signals, register_push, wave2, wave5_m08 | workflow_dispatch only |
| Auto | deploy_pages (push), rebuild_html (push) | `on: push:` |
| Future | eod.yml [Wave 3 Session D — NOT YET SHIPPED] | cron-job.org planned |

### Concurrency groups

| Group | Workflows | `cancel-in-progress` |
|---|---|---|
| `tietiy-scan` | morning_scan, scan_watchdog | false |
| `tietiy-open-validate` | open_validate | false |
| `tietiy-eod-master` | eod_master | false |
| `bridge-premarket` | premarket | false |
| `bridge-postopen` | postopen | false |
| `telegram-poll` | telegram_poll | false (TG-01: in-flight commits to tg_offset must complete) |
| `[no group]` | ltp_updater, stop_check, others | n/a |

`cancel-in-progress: false` is the right default — every workflow involves a git commit cycle; cancelling mid-cycle leaves the repo inconsistent. **One concern:** `ltp_updater` has no concurrency group and runs every 5 min. If a single run takes >5 min (yfinance slow day), two runs could compete on `ltp_prices.json` push. **GAP-10 (MEDIUM).**

### Failure handling consistency

14 workflows use `send_workflow_failure(workflow_name, run_url)`. Standard pattern. Consistent across the board.

**Inconsistency**: `morning_scan.yml` uses `if: steps.scan.outcome == 'failure'`, while bridge workflows use `if: failure()`. Functionally equivalent but stylistically split. **GAP-11 (LOW).**

### Push-retry pattern

11 workflows have a `for i in 1 2 3` push retry loop with `git pull --rebase`. Pattern is correct. **One subtle issue:** when all 3 retries fail, several workflows (premarket, postopen, others) `exit 1` at the end of the step, so the step fails and notify-on-failure fires correctly. But `morning_scan.yml` does NOT have the explicit `exit 1` on push exhaustion (just falls through). **GAP-12 (LOW)** — could miss an alert on prolonged push failure.

### Secrets surface

Used: `GH_TOKEN`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIM_EMAIL`, `PUSH_PIN`.

No surprises. All consumed via `${{ secrets.X }}` env injection. No hard-coded fallbacks in code. ✓

### Schedule overlaps to watch

- Saturday 08:30: `backup_manager` + `weekend_summary` + `gap_report` (Mon only, but `gap_report` and `backup_manager` both fire if Mon falls on a holiday with rescheduled events).
- Sunday 20:00: only `weekly_intelligence`.
- Daily 08:30-09:02: `heartbeat`, `morning_scan` (08:45), `premarket` (08:55), `scan_watchdog` (09:02). No conflicts — `tietiy-scan` group covers morning_scan + scan_watchdog. `bridge-premarket` is separate.

---

## PART 5 — Bridge architecture deep-dive

### L1 PRE_MARKET (`composers/premarket.py`, 635 lines)

**Inputs:** truth files (signal_history, patterns, proposed_rules, contra_shadow, colab_insights, mini_scanner_rules) via `evidence_collector.load_truth_files`.

**Pipeline per signal:**
1. `q_signal_today` filters PENDING signals dated today.
2. `_to_bridge_signal` translates production schema (`signal`, `date`, `age`) → bridge schema (`signal_type`, `signal_date`, `age_days`).
3. `evidence_collector.collect_evidence` runs 10 queries (q_pattern_match, boost_matcher, kill_matcher, q_exact_cohort, q_sector_recent_30d, q_regime_baseline, q_score_bucket, q_stock_recency, q_anti_pattern, q_proposals_pending). Note: `q_gap_evaluation` is also called by evidence_collector but returns None on L1 (no open_prices yet — additive Wave 3 wiring `f9de31f`).
4. `bucket_engine.assign_bucket` runs 4-gate decision tree → bucket (TAKE_FULL/TAKE_SMALL/WATCH/SKIP) + reasoning.
5. `_build_sdr` assembles SDR dataclass with display, gap_caveat, evidence, audit, learner_hooks.

**Output:** `bridge_state.json` phase=PRE_MARKET. Signals are SDR dicts via `sdr.to_dict()`.

**Renderer:** `bridge_telegram_premarket.py` (488 lines). Bucket grouping (TAKE_FULL → SKIP). Per-signal multi-line block. Always fires on trading day.

### L2 POST_OPEN (`composers/postopen.py`, 607 lines)

**Inputs:** L1 inputs + `open_prices.json` + L1 SDR archive at `bridge_state_history/{date}_PRE_MARKET.json` (via `_history_reader`).

**Pipeline per signal:**
1. Same evidence collection (now `q_gap_evaluation` returns real data).
2. **L2-specific override**: if `gap_evaluation.entry_still_valid is False` → force-skip via `_force_skip_invalid_entry` (gate=`L2_GAP_INVALID`).
3. Otherwise inject updated `rr_at_actual_open` into bridge_signal so bucket_engine sees post-open math.
4. `_build_l2_sdr` adds `bucket_changed`/`previous_bucket`/`bucket_change_reason` vs L1 lookup.
5. State adds top-level fields: `should_send_telegram`, `bucket_changes`, `gap_breaches` for renderer's single-source-of-truth on whether to fire.

**Renderer:** `bridge_telegram_postopen.py` (431 lines). **Conditional firing** — only if `should_send_telegram=True`. 3-line template for bucket-changed signals; 1-line template for gap-breach-only.

### L4 EOD (`composers/eod.py`, 467 lines) — Sessions A+B only

**Inputs:** truth files (signal_history is the primary read; outcome_evaluator has already mutated it at 15:35).

**Pipeline:**
1. `_select_resolutions_today`: filter `outcome_date == market_date AND outcome != 'OPEN'`.
2. Per resolution: `_build_eod_sdr_dict` (plain dict, no SDR dataclass).
3. State written with phase=EOD, plain-dict signals.

**Renderer:** `bridge_telegram_eod.py` (492 lines). Section-driven: header → resolutions → pattern_updates → proposals → open_positions → contra. Always fires on trading day.

### Inconsistencies across L1/L2/L4

| Aspect | L1 | L2 | L4 |
|---|---|---|---|
| SDR shape | dataclass | dataclass | **plain dict** |
| Has `bucket` field | ✓ | ✓ | **✗** |
| Has `bucket_reason_*` | ✓ | ✓ | ✗ |
| Has `gap_caveat` | ✓ | ✓ | ✗ |
| Has `display` (PWA hints) | ✓ | ✓ | **✗** |
| Has `learner_hooks` | ✓ | ✓ | ✗ |
| Has `outcome` block | ✗ | ✗ | ✓ (resolution data) |
| Telegram firing | always | conditional | always |

**GAP-13 (HIGH).** PWA app.js currently only knows L1/L2 SDR shape. When eod.yml ships (Session D), the PWA will receive plain-dict EOD signals and either:
- Defensively `.get()` everything → render incomplete cards
- Crash on missing `display` field
- Skip `signals[]` entirely on EOD phase

The user already flagged this in tonight's audit but the Wave UI plan defers PWA work. **Recommend: write a one-line PWA guard before Session D ships** — `if (state.phase === 'EOD') skip signals tab render` until Wave UI integrates the resolution-card view.

### Renderer escape-pattern bug

Caught + fixed tonight in `_render_contra_section`. Pattern: any literal between two `_esc()` calls (`f"{_esc(a)} sep {_esc(b)}"`) is a reserved-char leak vector. The fix: build pieces as plain strings, `_esc` whole body once. **Already documented in CLAUDE.md.** Worth grepping the L1/L2 renderers for the same anti-pattern. `[needs-verification]` — not done in this audit.

### Single chokepoint

Bridge composers write only to `bridge_state.json` via `state_writer.write_state` (atomic + history archive + 30-day retention + schema-version validation). Renderers read state ONLY — never touch truth files. **This is correct architecture.** ✓

### Bridge state_writer enforcement

`state_writer._validate_state` rejects writes missing `schema_version` / `phase` / `phase_timestamp` / `market_date`. Catches the most basic shape errors. Does NOT validate signals[] shape per phase — meaning the L1/L2/L4 SDR divergence is invisible to the writer. Acceptable for now; revisit if PWA breakage materializes.

---

## PART 6 — PWA UI flow

### File map

| File | Role | Size band |
|---|---|---|
| `output/index.html` | Shell — loader, tab content host, status bar, alert banner, tap-overlay/tap-panel, help-overlay | small |
| `output/ui.js` | Master controller — boot, fetch all data JSONs, route to tab renderers, SW message bridge, pull-to-refresh | medium |
| `output/app.js` | Signals tab — compact/expanded cards, filter bar, tap panel, conflict detection, day-N urgency animations | large |
| `output/journal.js` | Trade Journal — tracking screen, took/skip personal decisions, stop proximity traffic light, expiry banner | large |
| `output/stats.js` | Stats — WR by regime, MAE/MFE, timeline, performance dashboard, CSV export | large |
| `output/sw.js` | Service worker — cache + DATA_REFRESH broadcast | small |
| `output/analysis.html` + `output/analysis/*.js` (5 files) | Standalone analysis page (overview, segmentation, signals, post-mortem, advanced) | medium each |
| `output/health.html` | Health diagnostic view | small |
| `output/manifest.json` | PWA manifest (PIN-injected at build) | tiny |

### Data sources read by PWA

`window.TIETIY` (set by ui.js) holds:
- meta.json (last_scan timestamp, regime, version)
- scan_log.json (timeline)
- mini_log.json (shadow-mode passthrough)
- signal_history.json (the canonical truth — every tab keys off this)
- open_prices.json (gap%, entry_valid)
- eod_prices.json (Day-6 OHLC for resolution display)
- stop_alerts.json (current proximity)
- ltp_prices.json (intraday P&L)
- banned_stocks.json (filtered out of signals view)
- nse_holidays.json (trading-day arithmetic)

**Notably missing from PWA fetch:** `bridge_state.json`. As of today, no PWA tab reads bridge state. All bridge work is server-only. The PWA still derives its decision view from raw signal_history + scoring rules. **GAP-14 (HIGH).** This is an intentional Wave UI deferral — the IT-series (IT-01 through IT-06) is the dedicated PWA-bridge integration track. But it means:
- Trader's PWA "Signals" tab does NOT show TAKE_FULL/TAKE_SMALL/WATCH/SKIP buckets from bridge.
- PWA Telegram-brief preview function `_buildMorningBrief` derives its own brief client-side, parallel to (and possibly disagreeing with) `bridge_telegram_premarket`.
- Two sources of truth on the same screen.

### Trader's PWA journey today (pre-Wave-UI)

```
Open PWA (tietiy.in)
   │
   ├─ ui.js boots, fetches all JSONs in parallel
   ├─ Renders status bar (regime, last scan, "2m ago")
   │
   └─ Default tab: SIGNALS (app.js)
          ├─ Today's signals (compact cards, score-coded border)
          ├─ Filter bar (sector dropdown, signal-type pills, score slider)
          ├─ Tap a card → tap-panel slides in
          │     ├─ Score breakdown (per-bonus components)
          │     ├─ R:R, entry/stop/target
          │     ├─ Stop proximity if open
          │     ├─ TradingView chart link
          │     ├─ "Why this trade" plain-language summary
          │     └─ Took / Skip buttons (logs to localStorage)
          │
          └─ Bottom nav: Signals · Journal · Stats · Help
                              │         │
                              │         └─ Stats tab (stats.js)
                              │              ├─ WR by regime
                              │              ├─ MAE/MFE distribution
                              │              ├─ Score-bucket cross-tab
                              │              ├─ Timeline by scan day
                              │              └─ CSV export
                              │
                              └─ Journal tab (journal.js)
                                   ├─ "Took" filter (took=1 in localStorage)
                                   ├─ "Skipped" filter
                                   ├─ "Resolved" filter — WR/wins/losses/avg P&L
                                   ├─ Per-card: stop traffic light, day N/6,
                                   │           unrealized P&L, expiry alert,
                                   │           failure/win reason tag
                                   └─ Modal with full detail
```

### PWA gaps observed

1. **No bridge-state-driven view.** Per Wave UI plan; not a regression. Trader makes decisions from raw signal data + their own mental ranking. **GAP-14 (HIGH).**
2. **No proposals/approval surface in PWA.** All approval flows today are Telegram-only (`/approve_rule prop_001`). PWA shows nothing about pending proposals. **GAP-15 (MEDIUM)** — IT-05 covers this in Wave UI.
3. **No contra-tracker visibility in PWA.** Trader can't see kill_001 progress (n=15, WR%) without /status command. **GAP-16 (LOW)** — IT-related.
4. **No phase-aware banner.** Trader can't tell at a glance whether it's pre-market provisional vs post-open live vs EOD review. Currently just "2m ago" timestamp. **GAP-17 (MEDIUM)** — IT-02.
5. **`_buildMorningBrief` in app.js duplicates `bridge_telegram_premarket.py` logic** client-side. Two parallel rendering paths. **GAP-18 (MEDIUM)** — should converge in Wave UI.
6. **CSV export in stats.js had wrong field names** (fixed in CSV1 patch — `stock` → `symbol`, `entry_price` → `entry`). Pattern of schema drift between PWA-side and writer-side names. Same root cause as the Apr 26 bridge schema discipline lesson. **GAP-19 (LOW — already fixed but pattern remains).**

### Dead code

- Some V1/V1.1/V2 patch comments in app.js/journal.js/stats.js list fix IDs that may have been superseded; full-scope dead-code grep `[needs-verification]`.
- `output/analysis.js` exists alongside `output/analysis/*.js` — relationship `[needs-verification]`. May be deprecated parent or shim.

---

## PART 7 — Trader cognitive flow

The trader is one person (Abhishek), trading positionally on NSE F&O, capital ≤5% per trade, 6-day hold max, manual entries via broker, no auto-execution. The system is decision-support, not auto-trading.

### Day-of-trade flow

| Time IST | What system does | What trader sees | What trader decides | Cognitive load |
|---|---|---|---|---|
| 08:30 | heartbeat ping | "alive" Telegram | none | trivial |
| 08:45 | morning_scan runs | (bot output not surfaced) | none | none |
| 08:55 | bridge premarket fires | Telegram L1 brief: bucket-grouped signals (TAKE_FULL → SKIP), Score, R:R, Entry/Stop/Target, gap caveat at 2% threshold | which signals to PLAN orders for | **HIGH** — key decision point |
| 09:00-09:15 | PWA shows compact cards (raw signal_history) | Signal list, score, sector | refines plan, opens TradingView, picks 2-5 trades to enter at open | **HIGH** |
| 09:15 | (market opens) | (none — system is silent at open) | places orders manually via broker | **HIGH** — execution moment |
| 09:32 | open_validator runs | (bot commit lands; PWA next refresh sees actual_open) | none | low |
| 09:40 | bridge postopen fires; conditional alert | Telegram L2 alert ONLY if bucket flipped or severe gap | "should I exit/abort if I entered?" — context-dependent | medium when triggered |
| 09:45-15:30 | ltp + stop_check every 5 min | Stop proximity Telegram alerts; PWA traffic light | exit if stop fires intraday | low normally; HIGH if alert |
| 15:35 | eod_master runs | Telegram EOD digest (legacy — fragmented messages: pattern updates, contra resolutions, proposals) | review today's outcomes | medium |
| 16:00 | [planned] bridge eod fires | Telegram L4 unified digest (replaces 5 fragmented messages) | reflect, journal in head | medium |
| Day N (1-6) | outcome_evaluator runs each EOD | resolved cards in PWA Journal tab | reflect on outcome reason | low |
| Day 6 | outcome_evaluator force-exits at OPEN of Day 6 | DAY6_WIN/LOSS/FLAT card | review what happened | low |

### Cognitive gaps

1. **No portfolio-level synthesis.** Trader sees per-signal decisions but no "you have 11 open positions across 7 sectors, capital deployed 67%, sector concentration in Auto/IT" view. PWA Journal H5 patch claims "Capital at risk in portfolio summary" exists; verify when next session opens. **GAP-20 (MEDIUM).**
2. **No cross-signal correlation awareness.** If trader has 4 UP_TRI Bear-regime trades open, they're all subject to the same regime risk. Nothing flags this. **GAP-21 (HIGH)** — single regime shift could blow up multiple positions simultaneously.
3. **No "learning loop" surface.** When DAY6_LOSS fires on a signal, trader has to manually reconstruct "what kind of signal was that, what's its WR profile, am I overweight that cohort?" — the data exists in patterns.json + signal_history but isn't synthesized at trader level. **GAP-22 (HIGH)** — this is exactly what Wave 5 brain layer is meant to solve.
4. **No "today's regime in plain English"** statement. Trader sees `regime=Bear` but the implication ("bear-regime UP_TRI is highest-conviction trade") lives in their head, not the brief. Heartbeat workflow shows regime tag; brief shows it; neither contextualizes. **GAP-23 (MEDIUM).**
5. **No "what would I do differently" reflection prompt.** EOD digest shows outcomes but doesn't ask the synthesis question. **GAP-24 (LOW)** — daily_checkin_template.md exists but isn't a system feature, just a doc.
6. **Telegram-first interaction means iPad/phone is primary.** No reply-to-Telegram-message workflow for noting "skipped because XXX" — those notes live only in user's head or localStorage in PWA. **GAP-25 (MEDIUM)** — feeds back into brain-layer ground-truth gap.

### Multi-trade scenarios

When trader has 5+ open positions, the per-signal Telegram messages fragment. There's no "morning portfolio view" Telegram message — the brief shows new candidates, not existing exposure. The PWA Journal tab shows portfolio but trader has to switch contexts. **GAP-26 (MEDIUM).**

---

## PART 8 — Wave 5 brain-layer integration map

The user described the locked architecture as: input → derived views → reasoning → pre-verification → output, single approval layer, LLM at gates only, three-tier rules, top-3 nightly proposals, three interfaces. This audit cannot fully verify the locked design (it lives in chat history, not in the repo), so the section below is **the integration map IF the locked design ships as described**. Where I'd otherwise guess specifics, marked `[needs-verification]`.

### Integration premise

Brain layer is a NEW module that:
- Reads from existing truth files + bridge_state + signal_history (input)
- Materializes derived views for consumption (e.g., "patterns at risk," "regime shift watch," "exposure concentration")
- Runs reasoning via LLM at specific gates (NOT continuously) to keep cost/latency bounded
- Pre-verifies its proposals (counter-evidence, what-if, reversibility) before surfacing
- Outputs into the unified approval queue
- Single approval flow consolidates `/approve_rule`, future `/approve_query`, manual PWA buttons, and brain proposals

### Where brain plugs into existing data flow

```
              EXISTING                          NEW (Wave 5)
              ────────                          ────────────
signal_history.json ────┐
patterns.json ──────────┤
proposed_rules.json ────┤
contra_shadow.json ─────┼──→ brain_input_layer.py    (1) reads cohort
mini_scanner_rules.json─┤        - cohort views
bridge_state_history/ ──┤        - regime view
weekly_intelligence ────┘        - exposure view
                                 - proposals queue (read all proposers)
                                          │
                                          ▼
                          brain_derive.py             (2) materializes
                                 - cohort_health.json (NEW)
                                 - regime_watch.json  (NEW)
                                 - portfolio_exposure.json (NEW)
                                 - ground_truth_gaps.json (NEW)
                                          │
                                          ▼
                          brain_reason.py             (3) LLM at gates
                                 ↓
                          brain_verify.py             (4) pre-verification
                                 - claim/counter/effect/reversibility
                                          │
                                          ▼
                          unified_proposals.json      (5) NEW unified queue
                                 - brain proposals
                                 - rule_proposer rule proposals
                                 - future query proposals
                                 - all share schema
                                          │
                                          ▼
                          brain_telegram.py           (6) nightly batch
                                 - top-3 nightly digest
                          PWA Monster tab             (7) approval UI
                          /approve <unified_id>       (8) single command
```

### Files brain reads (existing — unchanged)

- `output/signal_history.json` (the canonical record)
- `output/patterns.json` (already-mined patterns with WR/n/edge)
- `output/proposed_rules.json` (rule_proposer proposals)
- `output/contra_shadow.json` (kill-pattern shadow tracking)
- `data/mini_scanner_rules.json` (active rules + boost patterns)
- `output/weekly_intelligence_latest.json` (weekly aggregates)
- `output/bridge_state_history/` (per-phase SDR archives)

### New files brain writes

- `output/brain/cohort_health.json` — derived: per-pattern WR rolling window, drift detection [`needs-verification` on schema]
- `output/brain/regime_watch.json` — regime transition early-warning
- `output/brain/portfolio_exposure.json` — open-position concentration analysis (sector, regime, signal-type)
- `output/brain/ground_truth_gaps.json` — cohorts where n<5, sectors not yet observed, signals lacking baseline
- `output/brain/unified_proposals.json` — the consolidated approval queue
- `output/brain/reasoning_log.json` — append-only LLM call log (cost tracking + audit)
- `output/brain/decisions_journal.json` — what brain proposed vs what was approved/rejected/expired

### Integration with bridge_state.json vs separate state file

**Recommendation:** brain output stays in `output/brain/*.json` (separate). Reasons:
1. Bridge state has 30-day rolling history; brain output has different retention semantics (proposals expire 7 days, reasoning_log is append-only).
2. Bridge writes 3× daily on a tight schedule; brain writes nightly + on triggers.
3. Schema versions evolve independently.
4. Bridge SDR shape is per-signal; brain output is per-cohort/per-portfolio/per-proposal — different aggregation grain.

Brain-derived **summaries** can be surfaced into bridge_state via the existing `state.summary.pattern_updates[]` and `state.alerts[]` channels — same hook EOD renderer already uses.

### Unified approval queue replacing fragmented surfaces

**Today's surfaces:**
- `/approve_rule prop_001` — Telegram, kill_pattern proposals from rule_proposer
- `/reject_rule prop_001` — Telegram, same proposal type (shipped tonight)
- `/approve_query Q-007` — planned Wave 5, query proposals from learner [not yet built]
- `/reject_query Q-007` — planned Wave 5 [not yet built]
- PWA Took/Skip buttons in app.js — localStorage only, no system feedback
- Manual edits to mini_scanner_rules.json by trader [implicit, not gated]

**Target unified queue:**
- One file: `output/brain/unified_proposals.json`
- One schema across proposal types (id, type, claim, counter, effect, reversibility, source, created_at, expires_at, status)
- One Telegram message format nightly (top 3 most-pressing, batch review)
- One PWA Monster tab UI (proposal cards with same anatomy regardless of source)
- One handler: `/approve <unified_id>` and `/reject <unified_id> [reason]`
- All proposers (rule_proposer, future query_proposer, brain itself) feed into this queue rather than each writing their own JSON.

### What PWA Monster tab needs that doesn't exist

Per Wave UI plan, the IT-series is the integration track. The Monster tab (brain interface) would need:
- New tab in bottom nav (or separate full-screen app)
- Fetch `output/brain/unified_proposals.json`
- Render proposal cards with claim/counter/effect/reversibility expansion
- Approve/reject buttons that fire via Telegram deep-link (LE-05 — currently PENDING in fix_table)
- Status indicator: pending count, expiring-soon count
- History view: approved/rejected log [`needs-verification` on shape]

**None of this exists today.** It's a fresh build. Wave UI is the home.

### Tier 1 CLI commands to build

If brain has a Tier 1 CLI surface (`[needs-verification]` from chat history):
- `brain audit` — print today's derived views summary
- `brain propose` — manually trigger a reasoning + proposal cycle
- `brain history` — show recent decisions journal
- `brain verify <proposal_id>` — re-run pre-verification on a specific proposal

### Modules that become subordinate to brain

- **`rule_proposer.py`** — keeps writing `proposed_rules.json` BUT now also forwards to `unified_proposals.json` via brain's intake layer. `/approve_rule` becomes `/approve <id>` against unified queue.
- **Future `query_proposer`** (Wave 5 LE-03) — directly writes to unified queue, never has its own dedicated JSON.
- **`telegram_bot.py`** — gains `/approve` and `/reject` handlers; existing `/approve_rule` and `/reject_rule` become deprecated aliases (preserve for back-compat one wave, then remove).
- **PWA approval surfaces** — collapse into Monster tab, deep-link to `/approve <id>` Telegram command (per LE-05 design).

### 8-step build sequence mapped to files

`[needs-verification]` — exact 8 steps live in chat history; this is my best inference:

1. **Schema lock** — write `doc/brain_design_v1.md` (new) defining unified_proposals.json schema + 7 brain output files. **Files:** doc only.
2. **Brain folder skeleton** — `scanner/brain/{__init__.py, brain_input.py, brain_derive.py, brain_reason.py, brain_verify.py, brain_output.py, brain_telegram.py}`. **Files:** 7 new.
3. **Derived views layer** — implement `brain_derive.py`: cohort_health, regime_watch, portfolio_exposure, ground_truth_gaps. **Files:** 1 + 4 JSON outputs.
4. **Pre-verification scaffolding** — `brain_verify.py`: claim/counter/effect/reversibility format, no LLM yet. **Files:** 1.
5. **Reasoning gates** — `brain_reason.py`: identify the 3-5 specific gates where LLM is invoked, with bounded prompt + cost tracking. **Files:** 1 + reasoning_log.json schema.
6. **Unified proposal queue** — `unified_proposals.json` + intake adapters in rule_proposer + `brain_output.py`. **Files:** 1 new schema, modifications to rule_proposer.
7. **Approval handlers** — `/approve` and `/reject` in telegram_bot.py + deprecation alias for `/approve_rule`/`/reject_rule`. **Files:** modify telegram_bot.py.
8. **PWA Monster tab** — Wave UI track; defer to Wave UI session. **Files:** new PWA tab.

**Estimated effort:** 30-50 hours across multiple sessions. Brain is the single biggest component remaining.

---

## PART 9 — Approval gate consolidation

### Current state (fragmented)

| Surface | Mechanism | Storage | Audit trail |
|---|---|---|---|
| `/approve_rule prop_001` | Telegram command | mutates mini_scanner_rules + proposed_rules.json | proposed_rules.json status field, approved_by, approved_date |
| `/reject_rule prop_001 reason` | Telegram command | proposed_rules.json | rejected_reason, rejected_by, rejected_date |
| `/approve_query Q-007` | planned Wave 5 — NOT BUILT | would write query_proposals.json | TBD |
| `/reject_query Q-007` | planned Wave 5 — NOT BUILT | TBD | TBD |
| PWA Took/Skip per signal | localStorage in browser | localStorage `tietiy.took.<id>` | none — client-side only |
| Manual rule edits | direct JSON edit by trader | mini_scanner_rules.json | git history (informal) |
| Telegram replies for context | not captured | n/a | none |

**Audit trail consistency:** zero. Each surface uses a different field convention.

### Target unified state

```json
// output/brain/unified_proposals.json (proposed)
{
  "schema_version": 1,
  "proposals": [
    {
      "id": "prop_unified_2026-04-27_001",
      "type": "kill_rule" | "boost_demote" | "query_promote" | "regime_alert" | "exposure_warn",
      "source": "rule_proposer" | "brain_derive" | "query_proposer" | "user",
      "title": "Energy sector × DOWN_TRI: 0/11 WR (kill candidate)",
      "claim": {
        "what":   "Add kill_pattern: signal=DOWN_TRI, sector=Energy",
        "expected_effect": "Block ~6 signals/month with -19pp edge",
        "confidence": "high"
      },
      "counter": {
        "evidence": ["sample size n=11 below n≥20 floor"],
        "risks":    ["misses any post-event regime mean reversion"]
      },
      "reversibility": "1-line revert in mini_scanner_rules.json kill_patterns",
      "evidence_refs": ["proposed_rules.json#prop_007", "patterns.json#..."],
      "status":   "pending",
      "created_at": "2026-04-27T...",
      "expires_at": "2026-05-04T...",   // 7-day default
      "approver": null,
      "decision_reason": null
    }
  ]
}
```

### Migration path (current → unified)

| Phase | Action | Backward compat |
|---|---|---|
| W4-A | rule_proposer dual-writes: existing proposed_rules.json **+** new unified_proposals.json | `/approve_rule` continues to work |
| W4-B | New `/approve` handler treats `prop_*` ids as routed to old path; `prop_unified_*` ids to new path | both work |
| W5-A | brain_output.py consolidates derived-view-driven proposals into unified queue | all via /approve |
| W5-B | rule_proposer becomes thin adapter — only writes unified queue | proposed_rules.json deprecated as separate writer; readable for read-only history |
| W5-C | `/approve_rule` becomes deprecated alias logging "use /approve" | one-wave grace period |
| W6 | Remove `/approve_rule` alias | clean state |

### Risks of consolidation

- **Rejection-reason granularity loss** if unified format doesn't preserve rule-specific vs query-specific reason fields. Mitigate via `decision_metadata` open-ended dict.
- **PWA Approve button latency** — if PWA goes through Telegram deep-link (LE-05) round-trip, response is slower than client-side localStorage commit. Mitigate via optimistic UI.
- **Audit trail forking during migration** — if a proposal exists in both old + new files, source-of-truth is ambiguous. Mitigate by treating new file as canonical and old as read-only mirror during W4-A.

---

## PART 10 — Gaps and fixes catalog

| ID | Severity | Where | What's wrong | Fix | Effort | Wave |
|---|---|---|---|---|---|---|
| GAP-01 | HIGH | signal_history.json multi-writer | Three writers (journal, outcome_evaluator, open_validator) without explicit file lock; cron retry storm could last-write-wins drop fields | Add file-lock or fcntl-based atomic writes; or single writer pattern via state queue | M | 6+ |
| GAP-02 | MEDIUM | mini_scanner_rules.json mutation | rule_proposer.approve_proposal mutates while morning_scan may read; race window | Mutex via lock file or queue approval to off-hours | S | 5 |
| GAP-03 | LOW | bridge_state.json renderer schema check | Renderers don't version-gate on schema_version; future bumps could surface garbage | Add version assertion at top of each renderer | XS | 4 |
| GAP-04 | HIGH | cron-job.org single point of failure | 14 of 24 workflows depend on cron-job.org; outage breaks the day | Document failover playbook; consider GitHub schedule mirrors with looser timing | M | 7+ |
| GAP-05 | LOW | premarket vs postopen push race | Test-fire window proved races possible; production schedule prevents | (no fix needed; documented) | n/a | n/a |
| GAP-06 | LOW | UTC labeled as IST in commit msgs | All bot commits show wrong tz label | `TZ='Asia/Kolkata' date ...` in 3 bridge workflows + others | XS | 3 cleanup |
| GAP-07 | MEDIUM | q_outcome_today vs eod._select_resolutions_today | Duplicate logic — query plugin exists but composer inlines | Pick one; recommend using q_outcome_today and removing inline | S | 3 Session C |
| GAP-08 | MEDIUM | q_contra_status vs _build_contra_block | Same pattern — query plugin exists but composers inline | Same fix; pick query plugin path | S | 3 Session C |
| GAP-09 | LOW | recover_stuck_signals mutates outside chain | No enforcement; relies on operator discipline | Add audit log on every mutation; require dry-run flag default | S | 6 |
| GAP-10 | MEDIUM | ltp_updater no concurrency group | If yfinance slow, two runs could compete on push | Add `concurrency: ltp-updater` group | XS | 6 |
| GAP-11 | LOW | failure handling style split | morning_scan uses `outcome=='failure'`; bridge uses `failure()` | Standardize on `if: failure()` everywhere | XS | 6 |
| GAP-12 | LOW | morning_scan no exit-1 on push exhaustion | 3 retries fail silently; notify-on-failure won't fire | Add `exit 1` after for-loop | XS | 6 |
| GAP-13 | HIGH | EOD plain-dict SDRs vs L1/L2 dataclass | PWA app.js will choke when eod.yml ships and EOD signals[] lands | Add PWA `if (state.phase === 'EOD') skip signals tab render` guard | XS (guard) / L (full integration) | 3 Session D pre-req / Wave UI |
| GAP-14 | HIGH | PWA doesn't read bridge_state.json | Trader UI lives parallel to bridge decisions | IT-01 in Wave UI | L | UI |
| GAP-15 | MEDIUM | No proposals/approval surface in PWA | Approval is Telegram-only | IT-05 in Wave UI | M | UI |
| GAP-16 | LOW | No contra-tracker visibility in PWA | Kill-rule progress invisible | IT (contra tab) in Wave UI | M | UI |
| GAP-17 | MEDIUM | No phase-aware PWA banner | Trader can't tell pre-market vs post-open vs EOD | IT-02 in Wave UI | S | UI |
| GAP-18 | MEDIUM | _buildMorningBrief duplicates premarket renderer | Two parallel paths client/server | Converge in Wave UI | M | UI |
| GAP-19 | LOW | CSV export had wrong field names (now fixed) | Schema-drift pattern persists | Schema-discipline lesson — codified in CLAUDE.md | n/a | n/a |
| GAP-20 | MEDIUM | No portfolio-level synthesis surface | Trader cognitive load unaided | Brain layer Wave 5 | L | 5 |
| GAP-21 | HIGH | No cross-signal correlation awareness | 4 same-regime trades = single point of risk | Brain layer exposure view | M | 5 |
| GAP-22 | HIGH | No learning-loop surface | Outcome → cohort revision is mental | Brain layer derived views | L | 5 |
| GAP-23 | MEDIUM | No "regime in plain English" | Implication of regime is in trader's head | Brain layer or smart brief enhancement | S | 5 |
| GAP-24 | LOW | No reflection prompt | daily_checkin_template exists in doc only | EOD digest enhancement | S | 5+ |
| GAP-25 | MEDIUM | No reply-to-Telegram note capture | Trader rationale lost | Telegram bot inbox + structured notes | M | 5 |
| GAP-26 | MEDIUM | No portfolio-view Telegram message | Multi-trade context fragments | Add to bridge L1 brief or new digest | S | 5 |
| GAP-27 | MEDIUM | Empty bridge folders (learner, templates, alerts) | Wave 5 placeholders not yet alive | Build out as Wave 5 progresses | n/a | 5 |
| GAP-28 | LOW | "Some V1/V1.1/V2 patch comments may be obsolete" | Legacy patch annotations in PWA JS | Spring-clean during Wave UI | S | UI |
| GAP-29 | MEDIUM | No live broker P&L correlation (P-01) | Scanner claims 81% WR; user-skipped on Apr 23 | Establish ritual or skip explicitly forever | M (process) | n/a |
| GAP-30 | LOW | analysis.js parent vs analysis/*.js relationship unclear | Possible deprecated shim | Verify and remove if dead | XS | UI |
| GAP-31 | LOW | renderer escape pattern caught in EOD only | Same anti-pattern may exist in L1/L2 renderers | Grep both for `f"...{_esc(x)} <literal> {_esc(y)}..."` patterns | S | 3 cleanup |
| GAP-32 | MEDIUM | bridge state_writer doesn't validate signals[] shape | L1/L2/L4 SDR divergence invisible to writer | Add per-phase signals[] validator (or accept as design choice) | S | 4 |
| GAP-33 | HIGH | Brain layer has zero design doc in repo | Locked-in-chat-history-only architecture is fragile | Write `doc/brain_design_v1.md` BEFORE coding starts in Wave 5 | S | 5 pre-req |

### Severity tally

- CRITICAL: 0
- HIGH: 7 (GAP-01, 04, 13, 14, 21, 22, 33)
- MEDIUM: 14
- LOW: 12

### Ranked Top 5 (CRITICAL/HIGH only)

1. **GAP-33** (HIGH) — Brain layer has no design doc in the repo. Architecture decisions live only in chat history; if that context is lost, Wave 5 has to rediscover from scratch. **Highest immediate impact** despite zero code-level severity.
2. **GAP-13** (HIGH) — EOD plain-dict SDRs will break PWA when eod.yml ships in Session D. Fix is one-line guard, takes 5 minutes; failure to fix means a broken signals tab on Day 1 of L4 production.
3. **GAP-14** (HIGH) — PWA doesn't read bridge_state.json yet. Trader's UI is parallel to (and may disagree with) bridge decisions. Wave UI dependency; large effort to fix.
4. **GAP-21 & GAP-22** (HIGH, related) — No portfolio correlation awareness, no learning-loop surface. Both are cognitive-gap issues that brain layer is meant to solve. Without brain, system gives signals but doesn't help trader synthesize across them.
5. **GAP-01** (HIGH) — Multi-writer race on signal_history.json. Probability low under current cron schedule, but the cost when it fires is corruption of the canonical truth file.

---

## PART 11 — Final integration picture (post-Wave-5 brain)

### Updated daily rhythm

```
SAME morning chain (08:30 → 09:40) — bridge L1 + L2 unchanged
                                                 │
                                                 ▼
                          L1 brief + L2 alert read brain.unified_proposals
                          → "1 pending approval expires today" footer line
                                                 │
                                                 ▼
            Intraday (09:50 → 15:30) — unchanged
                                                 │
                                                 ▼
            EOD chain (15:35 → 16:00) — unchanged
                                                 │
                                                 ▼
            16:00  bridge L4 EOD digest (now with brain pattern_updates)
                                                 │
                                                 ▼
            16:30  brain_derive.py runs nightly
                          → cohort_health, regime_watch,
                          → portfolio_exposure, ground_truth_gaps
                                                 │
                                                 ▼
            17:00  brain_reason.py LLM gates fire
                          → top-3 nightly proposals
                                                 │
                                                 ▼
            17:15  brain_verify.py pre-verifies
                          → unified_proposals.json updated
                                                 │
                                                 ▼
            18:00  brain_telegram.py fires
                          → "Tonight's review: 3 proposals.
                             Reply /approve <id> or /reject <id>"
                                                 │
                                                 ▼
            Trader reviews PWA Monster tab OR Telegram batch
                                                 │
                                                 ▼
            /approve or /reject via Telegram
                                                 │
                                                 ▼
            Brain logs decision, updates rules + journals
```

### Updated PWA layout (post-Wave UI)

Bottom nav: **Signals · Journal · Stats · Monster · Help**

The Monster tab is the brain interface:
- Pending proposals (count badge)
- Approve / reject inline
- Decision history
- Cohort health summary
- Portfolio exposure heatmap

### Updated trader cognitive flow

| Old flow | Post-brain flow |
|---|---|
| "I have 5 signals; which to take?" — trader synthesizes | "I have 5 signals; bridge ranked them; brain warns 'Auto sector exposure already 35%, top signal is in Auto'" |
| "Outcome was a loss; was it bad luck?" — trader guesses | "Brain flagged this cohort had drift to 65% WR last 10 — system caught the regime shift" |
| "Should I activate kill_002?" — trader weighs alone | "Brain proposes kill_002 with claim/counter/effect/reversibility — one-line review on PWA" |
| "Three proposals lying around" — fragmented Telegram | "Tonight's batch: 3 proposals, 2 expire tomorrow" |

### Good day end-to-end

```
08:30  heartbeat ✓
08:45  morning_scan finds 12 signals
08:55  bridge L1: 1 TAKE_FULL, 2 TAKE_SMALL, 3 WATCH, 6 SKIP
       Trader plans 3 entries.
09:15  Trader places orders.
09:32  open_validator: all 3 entries valid, gaps within 2%.
09:40  bridge L2: 0 bucket changes, 0 severe gaps. Silent.
Intraday: 1 stop-proximity alert at 12:30, doesn't fire.
15:35  eod_master: outcomes resolve. 1 TARGET_HIT (+5.2%),
       2 still OPEN.
16:00  bridge L4 digest: 1 won, 0 stopped, 0 flat, 11 open positions.
       (Brain pattern_updates, if Wave 5 shipped: "UP_TRI×Auto×Bear
        holds 22/22 — Tier A holding")
16:30  brain_derive nightly run.
18:00  brain_telegram: "1 proposal: prop_unified_001 — kill_002
       BULL_PROXY × Bank cohort (n=14, 21% WR). Claim, counter,
       effect, reversibility on PWA Monster."
18:30  Trader reviews, /approve prop_unified_001.
       Brain mutates mini_scanner_rules.json kill_patterns.
       Approval logged to decisions_journal.
```

### Bad day end-to-end

```
08:30  heartbeat ✓
08:45  morning_scan FAILS (yfinance throttle)
       Workflow alerts via Telegram: "morning_scan FAILED at <url>"
08:55  premarket fires: read truth files → DEGRADED status
       (signal_history not refreshed) → Telegram brief shows
       "(partial data) — yesterday's signals only"
09:15  Trader is informed; relies on yesterday's signals if any
       still valid, otherwise sits out today.
09:32  open_validator runs cleanly (independent of morning_scan).
09:40  postopen runs against yesterday's L1 → DEGRADED.
       No alerts fire (should_send_telegram=False).
Intraday: ltp + stops continue normally.
15:35  eod_master: outcome resolution catches yesterday's
       outcomes, not today's. EOD digest: "0 resolutions today
       (morning_scan upstream unavailable — investigate)"
16:00  bridge L4 marks state phase_status=DEGRADED, alerts
       surface "morning_scan stale 1 day".
16:30  brain_derive picks up the DEGRADED signal, includes a
       "system health" line in tonight's batch.
       Trader investigates morning_scan failure.
```

### Where humans intervene vs where system is autonomous

**Human-in-loop (always, by design):**
- Trade entry/exit at broker
- Rule activations (kill_pattern, boost_pattern)
- Brain proposal approval/rejection
- Manual rule edits
- P-01 outcome correlation (skipped, technically still on the table)

**System autonomous (no approval needed):**
- Signal detection, scoring, bucket assignment
- Outcome resolution (TARGET_HIT/STOP_HIT/DAY6_*)
- Pattern mining (read-only)
- Rule proposal generation (read-only — proposals only)
- Auto-revert on contra collapse (Wave 4 future — only "de-escalate, never escalate" exception)
- Brain derived views, reasoning, pre-verification (read-only outputs)

The contract is: **system proposes, human disposes.** Brain extends what the system can propose, not what it can do.

---

## PART 12 — Out-of-scope flags

This audit deliberately did NOT cover:

1. **Backtest reconciliation.** The 20-year backtest claims (UP_TRI 87% WR etc.) vs live 81% WR live divergence is a separate workstream. INV-01 in fix_table.
2. **Broker P&L correlation (P-01).** User-skipped on 2026-04-23. Acknowledged ongoing risk.
3. **HYDRAX (next platform).** Out of scope per principle #9 in fix_table — defer until Waves 1-5 stable + 2 weeks observed.
4. **Phase 6 (commercial product).** Out of scope per roadmap.
5. **5paisa integration.** Future price_feed.py swap; H-07 in fix_table is partial adoption — full migration deferred.
6. **PWA security/auth.** Single-user system; PIN-injected manifest is current state. No multi-user audit done.
7. **Sector taxonomy expansion (H-06).** 14 CSV tags vs 8 tracked; design-first item, evidence-gathering still ongoing.
8. **PWA Session 4 design pass.** UI2-UI12 12-file design pass deferred to Wave UI; not audited line by line.
9. **wave_execution_log_2026-04-23 contents.** Referenced in session_context as canonical record; this audit relied on the reference rather than re-reading the full log.
10. **Recovery scripts (`recover_stuck_signals.py`).** Operational tool, not part of the daily flow; audited only at module-summary level.
11. **Service worker cache strategy.** PWA `sw.js` audited only at message-bridge level; full cache-pruning logic not deep-dived.
12. **Cost-optimization for LLM calls in brain layer.** Brain reasoning gate count + token budget = a separate design exercise.

Each of these is a legitimate audit topic; this audit leaves them for future passes.

---

## Closing assessment

**What's strong:**
- Bridge backend is a clean architectural win: read-only by design, single chokepoint write, plugin queries, immutable phase records, schema versioning.
- Telegram delivery is mature and reliable; 14 workflows route failures consistently.
- Schema discipline principle (Apr 26) catches a real bug class before it ships.
- L1 + L2 are production-verified end-to-end as of Mon Apr 27.

**What's weak:**
- Brain layer architecture lives only in chat history; no doc in repo. Single largest risk to Wave 5.
- PWA still derives decisions parallel to bridge — two sources of truth on the same screen until Wave UI integrates.
- L4 SDR shape diverges from L1/L2 — guard before Session D ships or PWA breaks.
- Approval surface fragmented across Telegram/PWA/manual; consolidation is on roadmap but not yet done.
- Multi-writer race on signal_history is real, low-probability, high-cost.
- Cognitive synthesis (portfolio correlation, learning loop) is the trader's mental load; brain layer is meant to solve this and hasn't shipped.

**What's right-sized:**
- Wave 4 partial scope (LE-07 reject_rule shipped tonight; LE-06 demotion + prop_005 + prop_007 pending) — correct priority order.
- Wave UI as a single dedicated track — avoids piecemeal PWA churn.
- 7-day proposal expiry, 30-day bridge state retention, single-approval principle — all consistent with proof-gated approval ethos.

**Overall maturity:** Wave 2 backend foundation + Wave 3 L1/L2 + L4 sessions A/B + Wave 4 Step 1 = system is in a strong position to enter the brain-layer build. The remaining gaps are well-understood and ranked.

---

_Audit end. 33 gaps catalogued. 7 HIGH. 0 CRITICAL. The system is healthy enough to keep building, with three priorities for the next session: (1) write brain_design_v1.md before Wave 5 code, (2) add the EOD-phase PWA guard before Session D ships, (3) ship Sessions C+D to close out Wave 3._
