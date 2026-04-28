# TIE TIY Fix Table

**Purpose:** Single source of truth for all open work, ship plans, and design decisions.
**Owner:** Abhishek (decisions) + Claude (execution)
**Last updated:** 2026-04-28 (Wave 3 Session D + Wave 4 Steps 2-4 shipped — see change-log row for commit hashes)
**Canonical status:** This file + `doc/session_context.md` = complete handoff.

---

## 🖥️ WORKFLOW STATE — MacBook Active

**MacBook Air M5 set up 2026-04-25 night. Modern workflow active.**

- File edits: **diff-based** via Cursor (no more complete-rewrite pastes)
- Local testing: `python scanner/diagnostic.py --quick` runs locally
- Python venv: `~/code/tietiy-scanner/.venv` (Python 3.12.13, 40 pinned deps in `requirements.txt`)
- Git push: PAT saved in macOS Keychain, no prompts
- Claude Code: v2.1.119, launch with `claude` from repo root (run `/init` first session to generate `CLAUDE.md`)
- Pre-commit hooks: TBD (Wave 2 polish)

iPad remains as fallback device. Complete-rewrite workflow no longer required.

---

## Status legend

- **PENDING** — not started
- **IN PROGRESS** — currently being fixed
- **PARTIAL** — partially shipped, more sub-tasks remain
- **SHIPPED** — code committed, awaiting production verification
- **VERIFIED** — confirmed working in production
- **DEFERRED** — intentionally pushed to later phase
- **WATCH** — monitoring for enough data/evidence to act
- **SUPERSEDED** — absorbed into another item
- **BLOCKED** — waiting on another item or evidence

---

## Summary

- **Total items: 40+**
- **🔴 Critical:** 0 pending (all C-series verified April 21)
- **🟠 High:** 12 items
- **🟡 Medium:** 9 items (M-05 verified 2026-04-25)
- **🟢 Low:** 4 items
- **🧠 BR-series (Bridge):** 7 items — backend foundation **PARTIAL** (16 files shipped 2026-04-26)
- **🎨 IT-series (Intelligence tab):** 6 items — all on Wave UI track (single dedicated pass after Wave 5)
- **🔬 LE-series (Learner):** 6 items — self-queries + proposal approval
- **⚙️ ENV-series (environment):** 0 pending (ENV-01 verified 2026-04-25 night)
- **📋 PROP-series:** 3 items — prop_001 deferred, prop_005 ready, prop_007 ready
- **🚀 Wave 1:** ✅ ALL SHIPPED
- **🚀 Wave 2 backend:** ✅ 16 files shipped 2026-04-26 (composers / GH Actions / PWA still pending)
- **📦 TG-01:** ✅ Code shipped 2026-04-26 (cron-job.org dashboard update PENDING for Apr 26 evening)

**Phase state:** Wave 2 bridge backend foundation in place. 16 bridge files shipped, 3 schema bugs fixed end-to-end against real data, TG-01 sidecar code shipped.

---

## 🎯 IMMEDIATE NEXT ACTION

**1. Cron-job.org dashboard update — Apr 26 evening (BEFORE Monday open).**
The TG-01 docstring shift is committed (`0a77ea8`) but the actual schedule change has NOT taken effect. Three jobs need adjusting on cron-job.org:
- Primary: 9:27 IST → **9:32 IST** (UTC: 3:57 → 4:02)
- Retry 1: 9:57 IST → **10:02 IST** (UTC: 4:27 → 4:32)
- Retry 2: 10:27 IST → **10:32 IST** (UTC: 4:57 → 5:02)

Until done, the workflow continues firing on the OLD schedule despite docstrings reflecting the new one.

**2. Wave 2 continuation — Bridge composer, GitHub Actions wiring, end-to-end test.**
Backend foundation is in place. Next sub-tasks:
- Composer entry point (`composers/premarket.py`) — read truth, run queries, build SDRs, write bridge_state.json
- 7 background query plugins (`q_exact_cohort`, `q_sector_recent_30d`, `q_regime_baseline`, `q_score_bucket`, `q_stock_recency`, `q_anti_pattern`, `q_cluster_check`)
- BR-05 partial (premarket workflow YAML)
- BR-06 (bridge_state.json schema enforcement at composer level)
- BR-07 partial (premarket Telegram template)
- End-to-end test against Monday morning data

(IT-series and Session 4 UI both moved to **Wave UI** — single dedicated track after Wave 5. See ship plan below.)

---

## 🧱 WAVE 2 BRIDGE BUILD (2026-04-25 → 2026-04-26)

### Files shipped tonight (Apr 26)

**Folder skeleton + thresholds (2 commits):**
- `fed4ab3` — bridge folder skeleton (8 subfolders + `__init__.py` files)
- `fe82af2` — `rules/thresholds.py` (39 central numeric constants)

**Core building blocks (8 commits):**
- `8d4f6c3` — `core/sdr.py` (Signal Decision Record dataclass; `to_dict`, `from_dict`, `validate`)
- `7aff57a` — `core/display_hints.py` (7 pure functions for SDR.display fields)
- `c0964e0` — `core/state_writer.py` (atomic writes, 30-day history retention, schema validation)
- `3336aa5` — `core/upstream_health.py` (system_health.json reader + status mapper)
- `c5d1c8e` — `core/error_handler.py` (3 severity levels, safe_run, build_emergency_state)
- `63ef2de` — `core/bucket_engine.py` (decision tree: 4 gates, 8 outcomes, full reasoning strings)
- `012d487` — `core/evidence_collector.py` (orchestrates 10 queries, loads truth files once)

**Rule matchers (3 commits):**
- `1db08d7` — `rules/validity_checker.py` (Gate 2)
- `4c02c5b` — `rules/boost_matcher.py` (Gate 3)
- `e09c7e3` — `rules/kill_matcher.py` (Gate 1)

**Query plugin framework + first 3 queries (4 commits):**
- `5052161` — `queries/_registry.py` (plugin auto-discovery)
- `d606fb0` — `queries/q_signal_today.py` (today's PENDING)
- `992c648` — `queries/q_open_positions.py` (active positions, 6-day trading window)
- `755f9c0` — `queries/q_pattern_match.py` (supporting + opposing patterns)

**Total: 16 commits, ~2200 lines of new bridge code, syntax-clean and smoke-tested.**

### Critical bug fixes shipped tonight (after end-of-session schema audit)

Three silent failures discovered when comparing synthetic test fixtures against real production JSON files. All three were returning empty results against real data while smoke tests passed:

- `975efcf` — `q_signal_today.py`: record field `signal_date` → `date` (canonical schema). Was always returning `[]` against real `signal_history.json`.
- `0905c4c` — `q_open_positions.py`: same bug, same fix.
- `a7fd156` — `evidence_collector._filter_relevant_proposals`: `cohort.signal_type/sector` → top-level `target_signal/target_sector`. Real `proposed_rules.json` has no nested `cohort` key (rule_proposer puts cohort identity at top level). Was always returning `[]`.

**Real-data sanity verified for all 3:**
- q_signal_today: Apr 23 returns 9 PENDING, Apr 22 returns 6 PENDING (was 0 before)
- q_open_positions: Apr 30 returns 11 active positions sorted by day_count (was 0 before)
- evidence_collector: DOWN_TRI signal returns 4 matches from real `proposed_rules.json` (was 0 before)

### TG-01 sidecar shipped tonight

- `14423fb` — `.github/workflows/telegram_poll.yml`: concurrency lock added (`group: telegram-poll`, `cancel-in-progress: false`)
- `c5451e5` — `scanner/telegram_bot.py`: per-command try/except in `poll_and_respond` so one failing command can't lose `tg_offset.json` advance
- `0a77ea8` — `.github/workflows/open_validate.yml`: docstring shifted +5 min (9:27/9:57/10:27 → 9:32/10:02/10:32 IST) for yfinance settlement window

⚠️ **Manual action still required:** cron-job.org dashboard schedule change. See "IMMEDIATE NEXT ACTION" above.

### Schema audit (project-wide)

Full grep audit ran end-of-session covering all 19,306 lines of `scanner/`. Findings: **0 new bugs, 0 ambiguous, ~30 hits classified clean.** The 3 bugs already fixed tonight were the only manifestations of this bug class in the entire codebase.

Audit doc: `/tmp/project_wide_schema_audit.md` (will be moved or summarised here when reviewed).

### Known follow-ups (formerly `/tmp/tonight_followups.md`)

1. ✅ **DONE 2026-04-27** — ~~bucket_engine `_MODERATE_SECTOR_WR=0.65` hardcoded — should move to `scanner/bridge/rules/thresholds.py` as `COHORT_MODERATE_SECTOR_WR`. Single-line change. Effort: trivial.~~ Migrated to `COHORT_MODERATE_SECTOR_WR` in `scanner/bridge/rules/thresholds.py`. Original text preserved (strikethrough) for audit trail.
2. **evidence_collector + bucket_engine both call boost_matcher and kill_matcher for the same signal** — duplicate work per signal. Move calls into `evidence_collector` (which already populates `evidence['boost_match']` / `evidence['kill_match']`), have `bucket_engine` read from the evidence dict instead of re-calling matchers. Saves work and guarantees a single source of truth for which boost/kill matched. Effort: small refactor.
3. **Plain-dict EOD SDRs diverge from L1/L2 SDR schema.** EOD SDRs (composers/eod.py) omit `bucket`, `bucket_reason_*`, `gap_caveat`, `display`, `learner_hooks`. Verify PWA defensively `.get()`s these or skips signals[] on EOD phase BEFORE eod.yml workflow deploys to production. Track as Wave 3 Session D pre-req.
4. **`_render_contra_section` escape pattern (now fixed).** Any literal between two `_esc()` calls is a reserved-char leak vector. Caught during code review of EOD digest renderer (`19d4146`); smoke test 8 verified the fix. Pattern to watch in future renderers — when in doubt, build pieces as plain strings and `_esc` whole body once.
5. **`composers/eod.py` lacks explicit `is_trading_day` SKIPPED branch.** Currently handled at `bridge.py` pre-flight (line 119). Operationally fine since cron-job.org runs Mon-Fri only, but a SKIPPED branch in `eod.py` would make the composer self-contained. Cosmetic.
6. **`pattern_updates[]` and proposal alerts assume flat `{message}` shape** in `bridge_telegram_eod.py`. If Session C ships richer structure (e.g. nested fields per pattern), update renderer to read those fields and re-render rather than just `_esc(message)`.
7. **(2026-04-27) Companion migration:** `_THIN_FALLBACK_SECTOR_WR` + `_THIN_FALLBACK_REGIME_WR` also moved to `scanner/bridge/rules/thresholds.py` per same pattern (commit `b1359f1`). Closes the locally-hardcoded threshold cluster in `bucket_engine.py`.

---

## 🧠 SCHEMA DISCIPLINE (new principle, Apr 26 lessons)

Three bugs tonight all matched the same pattern: **bridge code reaching into production JSON records using bridge-side field names instead of canonical writer names.** Discovered only when audited against real data — synthetic fixtures had matched the buggy code.

**Going-forward rules:**

1. **Every query/composer that reads from a JSON file gets a real-data sanity check in its smoke test.** Informational only (no hard count assertions, since production data varies day-to-day) — just confirm the function returns non-empty when it should. Synthetic fixtures alone are insufficient.
2. **Bridge owns its own schema.** SDR fields, evidence-dict keys, input signal arg keys all use bridge naming (`signal_type`, `age_days`, `pnl_pct`). When reaching INTO a production record (signal_history, proposed_rules, patterns, mini_scanner_rules, system_health, contra_shadow), use the canonical writer's field names.
3. **Every cross-module data flow gets a schema audit before design.** Read the writer first, confirm field names, then write the reader.
4. **Field-name normalisation happens at the matcher boundary.** When a rule matcher returns a record from a JSON file, it should normalise to flat aliases the bridge expects (e.g., `boost_id` ← `id`, `n` ← `n_resolved`, `wr` to fraction). One translation point, not scattered.

---

## 🔴 TIER 1 — CRITICAL

**Zero pending.** All C-series (C-01 through C-05) VERIFIED April 21, 2026.

---

## 🟠 TIER 2 — HIGH-PRIORITY OPEN ITEMS

### H-04 / D3 — kill_001 bank scope narrowing

**Status:** BLOCKED on prop_001 decision · **Priority:** After prop_001 resolves (Week 2-3)

Currently kill_001 blocks Bank+DOWN_TRI (38 stocks on 11-signal evidence). Live evidence suggests narrowing to Bank core + NBFC separate, or expanding to Bank+Energy+DOWN_TRI.

**Decision gate:** prop_001 outcome drives this. If prop_001 ships, kill_001 becomes redundant. If prop_001 stays deferred, narrow kill_001 to Bank+Energy cohort.

### H-06 — Sector taxonomy (14 CSV tags vs 8 tracked)

**Status:** PENDING · **Priority:** Design-first (needs evidence review)

~45 stocks in `data/fno_universe.csv` tagged with sectors the scorer doesn't track → these never earn `sec_leading` bonus. Touches scorer + config + universe. Needs evidence review on which missed stocks actually emit signals before reshaping taxonomy.

### H-07 — price_feed.py full adoption

**Status:** PENDING · **Priority:** Week 2-3

Currently only `ltp_writer.py` uses the `price_feed` abstraction. Remaining fetches (scanner_core, eod_prices_writer) still hit yfinance directly. Migrate the remaining fetches so one-line config swap to 5paisa works across the whole pipeline.

### INV-01 — DOWN_TRI live vs backtest divergence

**Status:** PARTIALLY RESOLVED (2026-04-25 deep-dive) · **Priority:** Monitor

**Findings from live-data analysis:**
- Apr 6-8 short squeeze event drove 7/9 DOWN_TRI losses (78% of all DOWN_TRI bleed)
- Average MAE on those stops: 14-21% (not noise-volatility, event-driven)
- All resolved DOWN_TRIs were in Bear regime — 3 Choppy DOWN_TRIs open = decisive test
- UP_TRI in same window thrived (95% WR) — consistent with rally-crushing-shorts explanation

**Remaining investigation:** Choppy DOWN_TRI resolutions Apr 27-29. Feeds prop_001 decision.

---

## 🧠 TIER 3 — THE BRIDGE (Primary build track)

Design locked 2026-04-25. Backend foundation shipped 2026-04-26. Composers / GH Actions / PWA still pending.

### BR-01 — bridge.py orchestrator + plugin folder

**Status:** ✅ PARTIAL — folder skeleton + core + rules + queries framework shipped (2026-04-26) · **Priority:** Wave 2 · **Effort:** M

**Shipped tonight:** Folder structure (8 subfolders), 16 implementation files, query plugin auto-discovery via `_registry.py`. All syntax-clean, smoke-tested, real-data sanity-checked. Composer entry points still pending.

### BR-02 — Pre-market composer (Layer 1)

**Status:** PENDING · **Priority:** Wave 2 (next session) · **Effort:** M

Composer entry point in `composers/premarket.py`. Read truth files via `evidence_collector.load_truth_files`, iterate today's PENDING signals via `q_signal_today`, run `evidence_collector.collect_evidence` per signal, run `bucket_engine.assign_bucket`, build SDRs, write `bridge_state.json` via `state_writer`. End-to-end pipeline test required.

### BR-03 — Post-open composer (Layer 2)

**Status:** PENDING · **Priority:** Wave 3 · **Effort:** M

Triggered at 09:30 IST after open_validator. Validates overnight calls against actual opens. R:R recalc. D6 holiday-aware.

### BR-04 — EOD composer (Layer 4)

**Status:** PARTIAL — Sessions A+B shipped; Sessions C (LE-06 demotion warnings) + D (eod.yml workflow) pending · **Priority:** Wave 3 · **Effort:** M

Triggered at 16:00 IST after eod_master chain. Outcome digest. Unifies UX-02/03/05 fragmented Telegram messages.

**Session A (skeleton) shipped 2026-04-26 (`c94e523`):** `composers/eod.py` (467 lines). Selects `outcome_date == market_date AND outcome != 'OPEN'` from signal_history, builds plain-dict EOD SDRs (no `bucket` field, embeds `outcome` block), writes bridge_state phase=EOD. `bridge.py` wired for `--phase=EOD`. Smoke test 47/47 PASS, real history SHA256 unchanged.

**Session B (digest renderer) shipped 2026-04-26 (`19d4146`):** `bridge_telegram_eod.py` (492 lines). Section-driven template per design §12.3 (header / resolutions / pattern_updates / proposals / open_positions / contra). All sections defensive — auto-skip when empty. ALWAYS fires on trading day; SKIPPED → short notice; ERROR → short-circuit. Smoke test 10/10 PASS.

**Sessions C+D pending:** LE-06 boost demotion warnings (rolling-window WR per `boost_pattern` → `state.summary.pattern_updates`); `.github/workflows/eod.yml` + cron-job.org dashboard schedule.

**Status update 2026-04-28 (manual dispatch verified):** Sessions C + D both shipped (LE-06 in `7b96a97`, eod.yml in `f9d4746`). eod.yml ran end-to-end clean via manual `workflow_dispatch` at 19:01 IST today (commit `a5edc32` "Bridge eod 2026-04-28 13:31 IST" — UTC labeled as IST per GAP-06; real IST 19:01). `output/bridge_state_history/2026-04-28_EOD.json` (150KB) shape verified: 3 resolutions (W:1 L:2 F:0, total_pnl_pct +3.01%), 80 open positions, `pattern_updates: []` empty as expected (81% baseline well above 70% LE-06 floor — code path verified by absence-of-fire), contra block carries kill_001 + 2 RBLBANK shadows. Telegram digest delivered (user-confirmed). DEGRADED phase_status traces to known M-12 step-ordering artifact, not a fresh defect. Scheduled-tick verification deferred to upcoming cron-job.org migration (today the GitHub-native-schedule trigger missed entirely — see M-15). **UX-03 retirement priority elevated:** bridge L4 digest verified content-complete vs legacy `main.py eod` digest; once cron-job.org migration lands, legacy path should retire same week to avoid trader confusion (two parallel EOD digests per day fired today — see M-16 for an open-positions count discrepancy that surfaced during the comparison).

### BR-05 — GitHub Actions workflow wiring

**Status:** PENDING · **Priority:** Wave 2 partial (premarket) + Wave 3 (full) · **Effort:** S per workflow

Three bridge trigger workflows (premarket / postopen / eod). Each `workflow_dispatch` + upstream chain of workflow_run triggers.

**Status update 2026-04-28 (manual dispatch verified):** All three bridge workflows shipped — premarket.yml + postopen.yml on cron-job.org, eod.yml on GitHub native schedule (`f9d4746` per §13.4). eod.yml verified end-to-end via manual `workflow_dispatch` at 19:01 IST today (commit `a5edc32`). Workflow ran in ~3 min from dispatch to commit-on-main. Bridge L4 archive + Telegram digest both produced clean. **Scheduled-tick verification still pending** — today's GitHub-native-schedule trigger missed (see M-15); cron-job.org migration upcoming.

### BR-06 — bridge_state.json schema v1

**Status:** PARTIAL — schema_version constant + `state_writer._validate_state` shipped; full composer-level enforcement pending · **Priority:** Wave 2 · **Effort:** S

`BRIDGE_STATE_SCHEMA_VERSION = 1` lives in `rules/thresholds.py`. `state_writer._validate_state` rejects writes missing `schema_version`/`phase`/`phase_timestamp`/`market_date`. Composer-level shape (banner, summary, signals[], open_positions[], contra{}, alerts[], etc.) defined in `error_handler.build_emergency_state` for fatal-failure case but not yet emitted on the success path.

### BR-07 — Unified Telegram templates

**Status:** ✅ SHIPPED — all 3 renderers complete · **Priority:** Wave 2/3 · **Effort:** M (actual)

Three MarkdownV2 renderers replacing fragmented messages, all reading bridge_state.json:
- `bridge_telegram_premarket.py` — L1 brief, bucket grouping (commit `3f4ca97`)
- `bridge_telegram_postopen.py` — L2 alert, conditional via `should_send_telegram` (commit `2e170c5`)
- `bridge_telegram_eod.py` — L4 digest, section-driven (commit `19d4146`)

---

## 🎨 TIER 4 — PWA INTELLIGENCE TAB

All IT-series items belong to **Wave UI** — a dedicated track that runs after Wave 5. Design system + information architecture + components + bridge integration ship together as one coherent design pass, not piecemeal across waves.

### IT-01 — PWA plugin folder + bridge_state fetch

**Status:** PENDING · **Priority:** Wave UI

### IT-02 — Phase-aware UI banner

**Status:** PENDING · **Priority:** Wave UI

- Pre-market: yellow banner "PROVISIONAL — validated at 09:30"
- Post-open: green banner "LIVE — trading today"
- EOD: gray banner "DAY COMPLETE — review outcomes"

### IT-03 — Sorted signal card renderer

**Status:** PENDING · **Priority:** Wave UI

Groups: ✅ TAKE_FULL, 🟡 TAKE_SMALL, 👁 WATCH, ❌ SKIP. Reads from `SDR.display.*` fields populated by `display_hints.assemble_display_block` (already shipped).

### IT-04 — Expandable [why?] reasoning

**Status:** PENDING · **Priority:** Wave UI

Reads `SDR.evidence.*` (already produced by `evidence_collector`).

### IT-05 — Proposal approval card

**Status:** PENDING · **Priority:** Wave UI

### IT-06 — Self-query disclosure card

**Status:** PENDING · **Priority:** Wave UI

---

## 🔬 TIER 5 — THE LEARNER

Self-query pipeline + approval flow. Proof-Gated Approval framework.

### LE-01 — Query template registry

**Status:** PENDING · **Priority:** Wave 5

### LE-02 — Gap detection (triggers B + C)

**Status:** PENDING · **Priority:** Wave 5

**Trigger B (automatic):** cohort n<5, new signal type, low confidence recommendation.
**Trigger C (user-requested):** "Dig deeper" button on PWA signal card.
Max 3 self-queries per bridge run. `bridge/learner/` folder skeleton in place (empty in Wave 2 per design).

### LE-03 — query_proposals.json

**Status:** PENDING · **Priority:** Wave 5

### LE-04 — Telegram approval commands

**Status:** PENDING · **Priority:** Wave 5

`/approve_query N` — promotes to curated set. `/reject_query N` — never generate again.

### LE-05 — PWA → Telegram deep-link approval

**Status:** DEFERRED to Wave UI track · **Priority:** Wave UI (paired with IT-05)

Originally framed as Wave 4 with "PWA tap Approve → opens Telegram with pre-filled command." Audit-first verification 2026-04-28 confirmed this is misaligned: the PWA has no proposal-approval surface today (zero references to `proposed_rules` in `output/*.js`; no Monster/Proposals/Brain tab). The deep-link mechanism itself is one line of HTML, but it requires the IT-05 host surface to attach to. Building that surface piecemeal in Wave 4 would either ship a throwaway stub or smuggle IT-05 work in under an LE-05 label.

Cross-doc alignment: `master_audit_2026-04-27.md` PART 6 + PART 9 + closing assessment, `wave5_prerequisites_2026-04-27.md` Recommended sequence, and `brain_design_v1.md` Step 8 all place LE-05 inside Wave UI / IT-05 / Brain Step 8 (Monster tab). fix_table now agrees.

Approval flow today: Telegram-only via `/approve_rule` + `/reject_rule`. No change to that flow until Wave UI ships.

### LE-06 — Demotion framework (paired with prop_007)

**Status:** APPROVE READY · **Priority:** Wave 4

### LE-07 — Telegram /reject_rule command

**Status:** ✅ SHIPPED 2026-04-26 (commit `c43189a`) · **Priority:** Wave 4 Step 1 · **Effort:** S (actual)

Counterpart to existing `/approve_rule`. Free-form reason: `/reject_rule <prop_id> [reason words...]` → `reason = " ".join(parts[2:]) or "No reason given"`. Wires `rule_proposer.reject_proposal()` (already implemented). Smoke test 12/12 PASS in sandbox; real `output/proposed_rules.json` untouched.

**Deferred (intentional):** 2-strikes auto-flip to INSUFFICIENT per design §7.4 — track for future cleanup.

---

## 🚚 TIER 6 — DELIVERY RELIABILITY

### TG-01 — Telegram poll concurrency + try/except

**Status:** ✅ CODE SHIPPED 2026-04-26 (cron-job.org dashboard update PENDING) · **Priority:** Wave 2 sidecar · **Effort:** S (actual)

**Shipped:**
- A: `concurrency: group: telegram-poll, cancel-in-progress: false` in `telegram_poll.yml` (commit `14423fb`). `cancel-in-progress: false` chosen because in-flight runs may be committing `tg_offset.json` — killing mid-commit would leave inconsistent state.
- B: per-command try/except in `poll_and_respond` (commit `c5451e5`). Failed commands log + send Telegram error reply but don't crash the loop, so the offset still advances.
- C: open_validate.yml docstring shifted +5min for yfinance settlement (commit `0a77ea8`).

⚠️ **Cron-job.org dashboard update NOT YET DONE.** Before Monday market open, three jobs need their schedules changed (see IMMEDIATE NEXT ACTION).

### TG-02 — Unified messages replace fragmented

**Status:** DEPENDENT on BR-02/03/04 · **Priority:** Wave 3

Once Bridge ships, delete old fragmented messages. BR-07 replaces UX-02, UX-03, UX-05.

### PIN-01 — PWA PIN placeholder injection

**Status:** DIAGNOSED · PENDING FIX · **Priority:** Wave 6 / Week 2

### CACHE-02 — analysis.html via html_builder pipeline

**Status:** PENDING · **Priority:** Wave 6 · **Effort:** M

---

## 🎨 TIER 7 — UI / POLISH

### UX-02 — Gap-skip summary in morning brief

**Status:** SUPERSEDED by BR-02

### UX-03 — Failure_reason in EOD Telegram

**Status:** SUPERSEDED by BR-04

### UX-05 — R:R recalc at actual_open

**Status:** SUPERSEDED by BR-03

### Session 4 UI (UI2-UI12)

**Status:** DESIGN COMPLETE · **Priority:** Wave UI

Hybrid design approved. 12 files scoped. Ships together with the IT-series in Wave UI — design system + IA + components + bridge integration as one coherent pass.

---

## 🏥 TIER 8 — OBSERVABILITY & OPERATIONS

### HL-01 — Auto-healer framework

**Status:** PENDING · **Priority:** Week 2 (parallel to Bridge) · **Effort:** M

Wraps existing `diagnostic.py --heal`. Schedules periodic health checks. **Never touches trading core.**

### HL-02 through HL-05 — Heal scopes

**Status:** PENDING · **Priority:** Week 2+ (sequential)

### MC-01 — Ultimate master check

**Status:** PENDING · **Priority:** Week 2 (parallel to Bridge) · **Effort:** M

### MC-02, MC-03 — Expanded check + daily report

**Status:** PENDING · **Priority:** Week 2-3

### OPS-01 through OPS-04 — Repo split

**Status:** PENDING · **Priority:** Separate decision track

### M-12 — chain_validator runs before pattern_miner/rule_proposer in eod_master.yml

**Status:** PENDING · **Priority:** L (cosmetic — produces daily false-positive DEGRADED warns; no data impact)

In `eod_master.yml`: chain_validator runs at step 6, pattern_miner at step 7, rule_proposer at step 8. chain_validator's `_check_pattern_miner` / `_check_rule_proposer` functions (`scanner/chain_validator.py:228–285`) read each output file's `generated_at` field at execution time — but pattern_miner and rule_proposer haven't written today's outputs yet at step 6. Result: chain_validator reads yesterday's `generated_at` and writes a "Last run: <yesterday>" warn into `system_health.json`. Today's actual chain runs ~125ms later (steps 7-8 complete) but `system_health.json` is never re-written, so the stale warn persists into tomorrow morning's bridge read.

**Symptoms:**
- L1 premarket brief shows DEGRADED status every morning despite clean overnight chain
- L4 EOD digest will exhibit the same misleading DEGRADED label going forward
- Trader sees "PROVISIONAL — partial data" subtitle when underlying data is actually fresh

Diagnosed 2026-04-28 during F-2 audit (premarket fire-result review). Proven by sub-second timestamps on Apr 27 showing the chain wrote three files within ~125ms of each other (`system_health.json` 10:05:51.637Z → `patterns.json` 10:05:51.713Z → `proposed_rules.json` 10:05:51.760Z).

**Two viable fixes (defer implementation):**
1. Move chain_validator from step 6 to step 9 (post-mining). Cleanest — chain_validator validates what just happened.
2. Run chain_validator twice — early sanity at step 6 + post-mining truth at step 9. More robust if any consumer depends on early system_health.

No code changes during F-2 audit. Files referenced (read-only): `scanner/chain_validator.py`, `.github/workflows/eod_master.yml`, `output/system_health.json`.

### M-13 — 8 signal_history records carry outcome='OPEN' AND outcome_date set simultaneously

**Status:** PENDING · **Priority:** L (potential data-quality artifact; no current consumer crashes)

Found during F-2 audit 2026-04-28: 8 records with `outcome='OPEN'` but `outcome_date='2026-04-27'` set on the same record. Either `outcome_evaluator` stamps `outcome_date` prematurely on still-OPEN signals, or there's a transitional state in the resolution pipeline that sets `outcome_date` before flipping `outcome` to its terminal value.

**Symptoms:**
- `patterns.json total_resolved_signals = 161`, but `signal_history` non-OPEN count = 181 (20-record gap)
- Approximately 8 of the gap is explained by these OPEN-with-outcome_date records
- Remaining ~12 likely from late-arriving resolutions post-Apr-27 chain (today's 3 + ~9 stragglers)

**Current consumer is defensive:** the EOD composer selector (`composers/eod.py`, see BR-04 Session A above) AND's `outcome != 'OPEN'` with `outcome_date == market_date`, so EOD digests already exclude these records. No production impact today; the question is whether the writer should be cleaned up.

Worth investigating during M-12 fix audit (related — both touch the resolution pipeline). Files to read: `scanner/outcome_evaluator.py` write block, `scanner/recover_stuck_signals.py` write block, `scanner/journal.py` outcome-update path.

### M-14 — eod.yml + colab_sync.yml schedule collision (16:15 IST simultaneous fire)

**Status:** PENDING · **Priority:** L (cosmetic/process — both fire successfully via GitHub Actions parallel runners; no functional risk, but creates concurrent-push race on main that the rebase-fallback handles)

Both workflows configured with identical cron `45 10 * * 1-5` (16:15 IST Mon–Fri). They run in parallel on separate runners. Different output files (eod.yml → `output/bridge_state.json` + `output/bridge_state_history/<date>_EOD.json`; colab_sync.yml → `output/colab_export.json`) — no file-level collision. Push race on main is handled by the existing rebase-fallback infrastructure (visible all day in LTP/stop_check 5-min loops).

Identified during B-2 verification audit 2026-04-28. No code changes during audit.

**Fix proposal (defer):** Move colab_sync.yml from `45 10 * * 1-5` to e.g. `15 11 * * 1-5` (16:45 IST). Gives eod.yml an exclusive 16:15 IST window, leaves colab_sync 30 min later, still post-eod_master. Could pair with M-12 fix audit since both touch workflow scheduling.

### M-15 — GitHub native schedule miss-rate observed 2026-04-28

**Status:** PENDING (full scope captured in upcoming cron-job.org migration commit) · **Priority:** Will be addressed by eod.yml migration

All three weekday GitHub-native-schedule workflows (eod.yml at 16:15 IST, colab_sync.yml at 16:15 IST, diagnostic.yml at 16:30 IST) failed to fire today (2026-04-28) despite cron-job.org-dispatched workflows running cleanly. This reverses the §13.4 SPOF-reduction rationale that placed eod.yml on GitHub schedule. Scope of fix: migrate eod.yml to cron-job.org dispatch; colab_sync + diagnostic separately. Full migration plan in upcoming dedicated prompt.

**Status update 2026-04-28:** M-15 RESOLVED via this commit. eod.yml migrated to cron-job.org `workflow_dispatch` (`on: schedule:` block removed; only `on: workflow_dispatch:` remains). `bridge_design_v1.md §13.4` annotated with the reversal rationale. colab_sync.yml + diagnostic.yml remain on GitHub native schedule (not Wave 5 load-bearing; deferred to separate audit). **User-side action required to complete migration:** add eod.yml as new dispatch on cron-job.org dashboard with cron `45 10 * * 1-5` UTC (target URL `https://api.github.com/repos/tietiy/tietiy-scanner/actions/workflows/eod.yml/dispatches`, body `{"ref": "main"}`, headers copied from existing eod_master / premarket / postopen entries). Until dashboard entry exists, eod.yml only fires via manual GitHub UI dispatch.

### M-16 — open-positions count discrepancy: 94 (legacy main.py eod) vs 80 (bridge L4)

**Status:** PENDING · **Priority:** L (definitional difference, not a defect; trader-confusing once both digests are live)

Surfaced during 2026-04-28 manual eod.yml dispatch verification. Today's two EOD Telegram digests reported different open-position counts:
- 15:36 IST legacy `main.py eod` digest: "Open: 94"
- 19:01 IST bridge L4 digest: 80 (per `bridge_state_history/2026-04-28_EOD.json` `summary.open_positions_count`)

Likely explanation: legacy counts any record with `outcome=OPEN`; bridge L4 filter is "active positions in current 6-day trading window." Not a defect in either workflow — just two different counting schemes that diverge on stale records.

**Fix scope (investigate during UX-03 retirement audit):**
1. Determine which count is correct for trader's mental model (likely the 6-day-window count is what the trader cares about)
2. Either align the legacy count to the bridge filter (preferred — single source of truth), OR document the difference inline so trader understands what each digest is showing
3. Once cron-job.org migration lands and eod.yml fires reliably, UX-03 retirement (legacy `main.py eod` digest path) becomes the natural moment to resolve M-16 — the legacy count goes away.

---

## 📊 TIER 9 — ANALYSIS & INVESTIGATION

### AN-04 — WR by score × signal-type cross-tab

**Status:** PENDING · **Priority:** Week 2 · **Effort:** S

Addresses SCR-01 hypothesis (score 5-6 non-monotonicity). Add as 37th AN-02 question.

### SCR-01 — Score calibration investigation

**Status:** DEFERRED · **Priority:** After AN-04 ships

### DATA-01 — Apr 6-8 cluster flag in history

**Status:** DEFERRED · **Priority:** Low

### DATA-02 — Choppy regime watch protocol

**Status:** PENDING · **Priority:** Wave 2 (part of bridge)

Every Choppy resolution (next 2 weeks) triggers Telegram alert with full context. Integrates with bridge edge_health tracking.

---

## 📋 TIER 10 — LIVE-DATA PROPOSALS

### prop_001 — DOWN_TRI restriction

**Status:** DEFERRED · **Priority:** Gate on Apr 27-29 Choppy resolutions

3 Choppy DOWN_TRIs open (LUPIN/OIL/ONGC). Their resolution determines whether DOWN_TRI edge extends beyond Bear regime or collapses as Apr 6-8 event artifact.

### prop_005 — Stop/target rebalance as parameter toggle

**Status:** ✅ SHIPPED 2026-04-28 (commits `9d4dcb2` + `550b5f0`) · **Priority:** Wave 4 Step 2 · **Effort:** S (actual)

**What shipped:** `TARGET_R_MULTIPLE_SHADOW = 3.0` constant in `config.py` + parallel-track shadow fields (`shadow_target`, `shadow_outcome`, `shadow_r_multiple`) on every new V6 signal. `journal._calculate_target` parameterised on `multiplier`. `outcome_evaluator._evaluate_signal` augmented in-place with shadow bar-walk + Day-6 force-exit shadow. `recover_stuck_signals` carries shadow logic for the recovery path. Forward-only: pre-prop_005 records do not carry shadow fields and are not backfilled. Smoke 48/48 PASS, real-history SHA256 invariant.

**What did NOT ship and why:** prop_005 was originally framed as the R-multiple solver ("0.44 → 1.5"). Audit-first review revealed the framing was misaligned with the actual lever: R-multiple is dominated by Day-6 forced-exit outcomes (35/36 of 2026-04-27 resolutions, per the eod_anomaly investigation), not by target-multiplier choice. A real R-multiple fix requires exit-logic redesign (Day-6 forced-exit reform, dynamic stops, partial profit-taking) — too heavy for a config-toggle ship. Scope was reframed mid-session to "parallel-shadow infrastructure that lets the heavier exit-logic redesign track measure 3.0× outcomes against today's 2.0× live decisions." The full redesign now tracks separately as `doc/exit_logic_redesign_v1.md` (design-only, not yet drafted).

**Coupling note:** `TARGET_R_MULTIPLE` is the single source of truth for both `_calculate_target` body AND `_calc_r_multiple` TARGET_HIT cap — they must move together if ever changed. `TARGET_R_MULTIPLE_SHADOW` is forward-only metadata; never feeds live trade decisions.

**Audit-first discovery:** mid-session, found `recover_stuck_signals.py` had been silently broken since Wave 2 migration `c312316` (2026-04-23) — a stale `_is_trading_day` import made the module unimportable for 5 days but went undetected because no other code imports it. Fixed as a separate prerequisite commit (`9d4dcb2`) before prop_005 landed.

### prop_007 — Demotion framework (paired with LE-06)

**Status:** APPROVE READY · **Priority:** Wave 4

---

## 🚀 SHIP PLAN — WAVES

### Wave 1 — ✅ COMPLETE (2026-04-25)

CACHE-01 + UX-08 + WIN-RULES + M-05 + ENV-01 all shipped & verified.

### Wave 2 — IN PROGRESS

**Backend foundation shipped 2026-04-26:**
- ✅ Bridge folder skeleton + 8 core/rules/queries files
- ✅ 3 query plugins (q_signal_today / q_open_positions / q_pattern_match)
- ✅ Plugin registry framework
- ✅ TG-01 sidecar code (cron-job.org dashboard PENDING)
- ✅ 3 schema bug fixes against real data

**Remaining:**
- BR-02 composer entry point
- 7 more query plugins (q_exact_cohort, q_sector_recent_30d, q_regime_baseline, q_score_bucket, q_stock_recency, q_anti_pattern, q_cluster_check)
- BR-05 partial (premarket workflow YAML)
- BR-07 partial (premarket Telegram template)
- End-to-end test against Monday morning data
- Cron-job.org dashboard update before Monday open

(IT-series moved to Wave UI — see below.)

### Wave 3 — Following week

Full 3-layer rhythm. BR-03 + BR-04 + BR-05 complete + BR-07 complete + DATA-02. (UI-side phase banners + card extensions deferred to Wave UI.)

### Wave 4 — Proposals + approvals

✅ Closed 2026-04-28 at 4 shipped items: LE-07 (`/reject_rule`, `c43189a`), prop_005 (parallel-shadow infra, `550b5f0`), LE-06 (boost demotion warnings, `7b96a97`), prop_007 (boost demotion proposals, `c647e94`). LE-05 deferred to Wave UI track (paired with IT-05). Approval-card UI deferred to Wave UI.

### Wave 5 — Self-queries

LE-01 + LE-02 + LE-03 + LE-04. (Self-query disclosure card deferred to Wave UI.)

### Wave UI — PWA Intelligence tab + Session 4 design pass (after Wave 5)

**Single dedicated track.** Design system + information architecture + components + bridge integration done together, not piecemeal.

Scope:
- IT-01 (PWA plugin folder + bridge_state fetch)
- IT-02 (phase-aware banner — pre-market / post-open / EOD)
- IT-03 (sorted signal card renderer with bucket grouping)
- IT-04 (expandable [why?] reasoning panel reading SDR.evidence.*)
- IT-05 (proposal approval card with Proof-Gated Approval structure)
- IT-06 (self-query disclosure card with full SQL preview)
- Session 4 UI (UI2–UI12) — 12-file design pass: fonts (Fraunces + Geist + Geist Mono), 3-column iPad landscape layout, time-aware mode structure
- All IT-series adopt Session 4 design vocabulary natively (not retrofitted)

Why one track: SDR.display fields, evidence schema, alerts, contra block, and self-queries are all already shipped server-side. Building the UI piecemeal across waves means re-touching the same screens 4 times. One coherent pass — design once, build once.

### Wave 6 — Polish + parallel

CACHE-02 + PIN-01 + AN-04.

### Wave 7+ — Parallel tracks

HL-01 + MC-01 + OPS-01..04 + prop_001 revival + H-04/D3 + H-06 + H-07.

---

## 🧭 KEY DESIGN PRINCIPLES (locked)

1. **signal_history.json is persistent truth.** All other JSONs are overlays.
2. **Proof-Gated Approval.** Every structural change ships with claim + evidence + counter-evidence + expected effect + reversibility path. No exceptions.
3. **Read-only bridge.** Bridge never modifies db or module outputs. Only reads, queries, composes.
4. **Human approval mandatory.** No auto-execute. No auto-activate kill rules.
5. **Plugin architecture everywhere.** AN-02 pattern extends to bridge + intelligence tab. New query/view = new plugin file, no engine changes.
6. **Template-bounded self-queries.** Bridge can't write arbitrary SQL.
7. **Disclosure before promotion.** Self-queries visible to user with full SQL before becoming curated.
8. **MacBook is additive, not replacement.** Code and data stay on existing repo.
9. **Build TIE TIY to stable first.** HYDRAX deferred until Waves 1-5 complete and observed for 2+ weeks.
10. **Confidence gates for rule activation:** n ≥ 20 · confidence ≥ 85% · WR gap ≥ 15% below baseline.
11. **No diffs-on-iPad.** Diff-based edits require Cursor (MacBook).
12. **Schema discipline.** When reading FROM production records, use canonical writer names; when reading the bridge's own input/SDR, use bridge names. Every JSON-reading function must have a real-data sanity check in its smoke test. Schema audits run before designing any cross-module data flow. (See Apr 26 lessons section above.)

---

## 🚫 WHAT NOT TO DO

- Do not rebuild TIE TIY. Current system works. Bridge is additive.
- Do not auto-execute trades. Ever.
- Do not activate kill rules without contra-shadow + demotion framework (LE-06) in place.
- Do not start the PWA Intelligence tab piecemeal across Waves 2-5. Wave UI is its own dedicated track after Wave 5 — IT-series + Session 4 design ship together as one coherent pass. Backend is ready early; UI ships once.
- Do not let Wave sessions balloon past scope. Cut if it bloats.
- Do not start HYDRAX Phase 0 until TIE TIY bridge is stable (Waves 1-5 shipped + observed 2 weeks).
- Do not touch: `config.py` vs `scorer.py` dual constants (intentional), `mini_scanner.DEFAULT_RULES` fallback (safety), `parent_signal_id` + `sa_parent_id` dual-write (legacy migration), `eod_master.yml` + `eod_update.yml.bak` coexistence (rollback escape hatch), `main.py` STEP numbering (navigation aid).
- Do not use `sudo npm` on MacBook. If you hit EACCES, reconfigure npm prefix instead.
- Do not commit `.venv/` or `.env`. Both gitignored — verify before every push.
- **Do not trust synthetic test fixtures alone.** Every JSON-reading function gets a real-data sanity check (post-Apr 26 lesson).
- **Do not match production-record fields with bridge-side names.** Always grep the writer first.

---

## 📜 CHANGE LOG

| Date | Change |
|------|--------|
| 2026-04-20 | Initial master audit. 42 items catalogued. |
| 2026-04-21 | Session A shipped: 9 items (C-01..C-04, D1, M-11, L-05, UX-01, P-01 skipped). |
| 2026-04-23 | Wave 2/3/5.1: 16 IDs VERIFIED. See wave_execution_log_2026-04-23.md. |
| 2026-04-24 | AN-02 36-question catalog shipped (plugin architecture). UX-07 verified. |
| 2026-04-25 | **Full rewrite.** Bridge design locked. Live-data deep dive complete. Added BR/IT/LE series (19 new items), ENV series, WIN-RULES. Superseded UX-02/03/05. Total items: 40. |
| 2026-04-25 (night) | **Wave 1 shipped + ENV-01 complete.** CACHE-01 + UX-08 + WIN-RULES + M-05 all VERIFIED. MacBook Air M5 fully set up. Production PWA verified live. |
| 2026-04-26 | **Wave 2 backend foundation shipped.** 16 bridge files (folder skeleton + thresholds + sdr + display_hints + state_writer + upstream_health + error_handler + bucket_engine + evidence_collector + 3 rules matchers + queries registry + 3 query plugins). TG-01 sidecar code shipped (cron-job.org dashboard PENDING for Apr 26 evening). 3 silent-failure schema bugs fixed in q_signal_today, q_open_positions, evidence_collector — discovered when comparing synthetic fixtures vs real production JSON. **New principle locked: Schema discipline (#12)** — every JSON-reading function gets a real-data sanity check; bridge owns its own schema but uses canonical names when reaching INTO production records. Full project-wide audit ran (19,306 lines, 0 new bugs found). 2 follow-ups tracked: bucket_engine `_MODERATE_SECTOR_WR` to thresholds; dedupe boost/kill matcher calls between evidence_collector and bucket_engine. |
| 2026-04-26 (night-2) | **Wave 3 Session A/B + Wave 4 Step 1 shipped.** `/reject_rule` Telegram command (`c43189a`). BR-04 EOD composer skeleton (`c94e523`) — 467 lines, reads signal_history resolutions, plain-dict EOD SDRs, `bridge.py` wired for `--phase=EOD`. EOD digest renderer `bridge_telegram_eod.py` (`19d4146`) — 492 lines, section-driven template per §12.3. Renderer escape-pattern bug caught + fixed in code review: `_render_contra_section` had unescaped `=` between `_esc` calls; refactored to plain-string pieces + `_esc` whole body. BR-07 now fully shipped (all 3 renderers). Sessions C (LE-06 boost demotion warnings) + D (eod.yml workflow + cron-job.org schedule) pending. |
| 2026-04-28 | **Wave 4 Steps 2-4 shipped tonight + Wave 3 Session D shipped earlier this evening.** eod.yml workflow live (`f9d4746`). bridge_design_v1.md §13 EOD-exception note (`d4433e7`). LE-06 boost demotion warnings in EOD digest (`7b96a97`). prop_007 boost demotion proposal generation + approval (`c647e94`). prop_005 reframed and shipped as parallel-shadow infrastructure (`550b5f0`) — NOT the R-multiple solver originally implied; heavy exit-logic rework deferred to `exit_logic_redesign_v1.md` design track. recover_stuck_signals.py Wave 2 migration leftover fixed (`9d4dcb2`). |
| 2026-04-28 (late-night) | **Wave 4 closed at 4 shipped items: LE-07, prop_005, LE-06, prop_007.** LE-05 placement reclassified DEFERRED to Wave UI track aligning with master_audit, wave5_prerequisites, and brain_design_v1. The PWA host surface required for LE-05 to be user-visible is IT-05 / Brain Step 8 (Monster tab). |
| 2026-04-28 (mid-day) | **Premarket Phase 1 watch_pattern verified clean + F-2 diagnosis benign + B-3 shipped.** 08:55 IST premarket fire produced clean L1 brief; watch_001 (UP_TRI×Choppy) fired against COALINDIA with full evidence + warning text rendered into Telegram. F-2 (pattern_miner/rule_proposer 4-day stale claim from `system_health.json`) diagnosed as cosmetic step-ordering artifact in `eod_master.yml` — chain ran cleanly Apr 27 per sub-second timestamps. Filed as M-12 (chain_validator step ordering) + M-13 (OPEN-with-outcome_date schema oddity). eod.yml first fire at 16:15 IST cleared by F-2 audit to proceed (verification still pending). B-3 shipped: Anthropic SDK + ANTHROPIC_API_KEY validated against live Messages API with `claude-opus-4-7` (`d6ddc01`). |
| 2026-04-28 (mid-day) | **B-2 verified — Wave 5 prereq cleared on infrastructure side.** All 6 cron-job.org dispatches (morning_scan, open_validate, premarket, postopen, ltp_updater, stop_check) fired on schedule today with timestamp evidence in git log. eod.yml uses GitHub native schedule per `bridge_design_v1.md §13.4` (deliberate cron-job.org bypass for SPOF reduction). eod_master at 15:35 IST will populate today's chain outputs; eod.yml at 16:15 IST will read fresh data via the 25–55 min buffer. Schedule collision between eod.yml and colab_sync.yml at 16:15 IST surfaced and filed as M-14 (cosmetic, no fire-blocker). All Wave 5 prereqs B-1, B-2, B-3 status: B-2 ✅ verified, B-3 ✅ shipped (`d6ddc01`), B-1 ⏸ pending eod.yml first fire at 16:15 IST today. |
| 2026-04-28 (mid-day) | **master_audit_2026-04-27.md gap status refresh.** GAP-33 (Brain design doc) marked RESOLVED via `720c127`; GAP-04 (cron-job.org SPOF) annotated PARTIAL via `f9d4746` (eod.yml moved off, 13 of 14 workflows still on cron-job.org). Severity tally HIGH 6 → 5; closing line corrected from "7 HIGH" → "5 HIGH". Pre-existing closing-line inconsistency (carried forward from GAP-13 reclass) also resolved. |
| 2026-04-28 (mid-day) | **brain_design_v1.md drift audit — design substance intact, 4 status annotations applied.** §1 amendment header notes today's audit pass. §3 status note flags R-multiple-as-tier-threshold concern under Day-6 forced-exit dominance (deferred to `exit_logic_redesign_v1.md` track when that doc gets drafted). §11 Q5 status update notes Session D shipped (`f9d4746`); fallback logic now narrowed to per-day eod.yml-fail tolerance. §12 LE-06 cross-ref row updated with ship commit `7b96a97`. No design substance changes; status refresh only. |
| 2026-04-28 (evening) | **B-1 verified via manual workflow_dispatch — eod.yml runs end-to-end clean.** GitHub native schedule missed today's 16:15 IST tick (along with colab_sync + diagnostic — see M-15). User manually dispatched eod.yml via GitHub UI; workflow committed `a5edc32` "Bridge eod 2026-04-28 13:31 IST" at 19:01 IST. Bridge L4 archive `bridge_state_history/2026-04-28_EOD.json` (150KB) shape verified: 3 resolutions (W:1 L:2 F:0, +3.01%), 80 open positions, `pattern_updates: []` empty as expected (LE-06 path verified by absence-of-fire), contra block clean. Telegram digest delivered (user-confirmed). DEGRADED phase_status traces to known M-12 step-ordering. Filed M-15 (GitHub schedule miss-rate) + M-16 (open-positions count discrepancy 94 legacy vs 80 bridge). UX-03 retirement priority elevated. **Scheduled-tick verification still pending** — cron-job.org migration commit upcoming (separate prompt) will reverse §13.4 GitHub-native decision based on today's miss-rate evidence and add eod.yml as a cron-job.org dispatch entry. |
| 2026-04-28 (evening) | **eod.yml migrated GitHub native schedule → cron-job.org dispatch.** Reverses `bridge_design_v1.md §13.4` SPOF-reduction rationale based on today's miss-rate evidence (3-of-3 weekday GitHub-schedule workflows skipped; 6-of-6 cron-job.org workflows fired). M-15 RESOLVED in same commit. Manual workflow_dispatch retained as user-only safety valve. cron-job.org now dispatches 15 workflows (was 14); failover playbook (Wave 5 prereq S-4) priority elevated accordingly. **User-side action required:** add eod.yml as new dispatch on cron-job.org dashboard with cron `45 10 * * 1-5` UTC (target URL: `https://api.github.com/repos/tietiy/tietiy-scanner/actions/workflows/eod.yml/dispatches`, body `{"ref":"main"}`). Until dashboard entry exists, scheduled-tick verification of eod.yml will not occur — only manual dispatch will fire it. colab_sync.yml + diagnostic.yml miss filed for separate audit, not in scope tonight. |
| 2026-04-28 (late evening) | **Tonight's full-session batch closeout** — 3 docs synced atomically. `project_anchor_v1.md` shipped commit `50325c7` (762 LOC, 128 commit citations / 49 unique) — single canonical reference. `session_context.md` resume-point refreshed with tonight's 15 commits + Wave 5 Steps 1-2 SHIPPED + Step 3 design pass mid-flight + 11 D-items from `project_anchor_v1.md §7`. `master_audit_2026-04-27.md` GAP-04 PARTIAL annotation REVERSED (eod.yml moved BACK to cron-job.org via `2fc1f35`; original PARTIAL via `f9d4746` was reversed same evening; severity stays HIGH). This change-log row references all 15 of tonight's meaningful commits via cross-pointer to `project_anchor_v1.md §8.3`. Wave 5 Step 3 audit complete (Parts A–E surfaced); schema lock-in next session resume point. |

---

## 📦 CLOSED (HISTORICAL — VERIFIED)

Items kept here for historical traceability. Source-of-truth status set above tier sections.

### ENV-01 — MacBook stack install — ✅ VERIFIED 2026-04-25 (commit `e35b49c`)
Xcode CLI · Homebrew 5.1.7 · Python 3.12.13 · Git 2.54.0 · Node 22.22.2 · Claude Code 2.1.119 · Cursor IDE · Repo + venv + 40 deps · GitHub PAT in Keychain · `diagnostic.py --quick` 6/6 PASS.

### CACHE-01 — Plan B cache-bust on analysis.html — ✅ VERIFIED 2026-04-25
Wave 1. 6 local scripts converted to `data-src` stubs + inline loader injects `?v=Date.now()` cache-busted scripts. CDN scripts untouched. Live console confirms `[CACHE-01] injected 6 cache-busted scripts`.

### UX-08 — "📊 Analysis" button in PWA header — ✅ VERIFIED 2026-04-25
Wave 1. Fixed-position pill button, top-right, z-index 50, safe-area aware. Migrate into ui.js rendered header when Session 4 UI ships.

### M-05 — chain_validator extended coverage — ✅ SHIPPED 2026-04-25
`chain_validator.py` rewritten. Added `_check_rule_proposer()` and `_check_contra_tracker()`. Checks dict expanded from 5 to 7. Schema_version unchanged.

### WIN-RULES — boost_patterns in mini_scanner_rules.json — ✅ SHIPPED 2026-04-25
7 boost_patterns (5 Tier A + 2 Tier B). Schema v3. Pharma flagged `validated_under_floor`. Consumer: Bridge Wave 2 (now reading via boost_matcher).

### UX-07 — whats_open trading-day math — ✅ VERIFIED 2026-04-24 (commit `e37f869`)
Day column uses trading-day count with color-coded urgency.

### AN-02 — 36-question catalog — ✅ VERIFIED 2026-04-24 (commit `e37f869` + preceding)
Full catalog shipped. Bridge reuses these queries (plugin pattern carried into `bridge/queries/`).

### C-series (C-01 through C-05) — ✅ VERIFIED 2026-04-21
Intelligence loop functional end-to-end (contra_tracker, rule_proposer, outcome_evaluator schema-aligned). See `wave_execution_log_2026-04-23.md`.

---
