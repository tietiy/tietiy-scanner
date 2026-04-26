# TIE TIY Fix Table

**Purpose:** Single source of truth for all open work, ship plans, and design decisions.
**Owner:** Abhishek (decisions) + Claude (execution)
**Last updated:** 2026-04-26 night (Wave 2 bridge backend shipped — 16 files; TG-01 sidecar shipped; 3 schema bugs fixed)
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
- **🎨 IT-series (Intelligence tab):** 6 items — PWA plugin architecture
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

**2. Wave 2 continuation — Bridge composer, GitHub Actions wiring, PWA, end-to-end test.**
Backend foundation is in place. Next sub-tasks:
- Composer entry point (`composers/premarket.py`) — read truth, run queries, build SDRs, write bridge_state.json
- 7 background query plugins (`q_exact_cohort`, `q_sector_recent_30d`, `q_regime_baseline`, `q_score_bucket`, `q_stock_recency`, `q_anti_pattern`, `q_cluster_check`)
- BR-05 partial (premarket workflow YAML)
- BR-06 (bridge_state.json schema enforcement at composer level)
- BR-07 partial (premarket Telegram template)
- IT-01/02/03 (PWA Intel tab)
- End-to-end test against Monday morning data

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

1. **bucket_engine `_MODERATE_SECTOR_WR=0.65` hardcoded** — should move to `scanner/bridge/rules/thresholds.py` as `COHORT_MODERATE_SECTOR_WR`. Single-line change. Effort: trivial.
2. **evidence_collector + bucket_engine both call boost_matcher and kill_matcher for the same signal** — duplicate work per signal. Move calls into `evidence_collector` (which already populates `evidence['boost_match']` / `evidence['kill_match']`), have `bucket_engine` read from the evidence dict instead of re-calling matchers. Saves work and guarantees a single source of truth for which boost/kill matched. Effort: small refactor.

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

**Status:** PENDING · **Priority:** Wave 3 · **Effort:** M

Triggered at 16:00 IST after eod_master chain. Outcome digest. Unifies UX-02/03/05 fragmented Telegram messages.

### BR-05 — GitHub Actions workflow wiring

**Status:** PENDING · **Priority:** Wave 2 partial (premarket) + Wave 3 (full) · **Effort:** S per workflow

Three bridge trigger workflows (premarket / postopen / eod). Each `workflow_dispatch` + upstream chain of workflow_run triggers.

### BR-06 — bridge_state.json schema v1

**Status:** PARTIAL — schema_version constant + `state_writer._validate_state` shipped; full composer-level enforcement pending · **Priority:** Wave 2 · **Effort:** S

`BRIDGE_STATE_SCHEMA_VERSION = 1` lives in `rules/thresholds.py`. `state_writer._validate_state` rejects writes missing `schema_version`/`phase`/`phase_timestamp`/`market_date`. Composer-level shape (banner, summary, signals[], open_positions[], contra{}, alerts[], etc.) defined in `error_handler.build_emergency_state` for fatal-failure case but not yet emitted on the success path.

### BR-07 — Unified Telegram templates

**Status:** PENDING · **Priority:** Wave 2 (premarket) + Wave 3 (all three) · **Effort:** M

Three Markdown-V2 templates replacing current 5 fragmented messages. Template-bounded rendering. `templates/` folder skeleton in place.

---

## 🎨 TIER 4 — PWA INTELLIGENCE TAB

PWA Intel tab — built inside Session 4 UI design from Wave 2 onwards. **Don't build twice.**

### IT-01 — PWA plugin folder + bridge_state fetch

**Status:** PENDING · **Priority:** Wave 2

### IT-02 — Phase-aware UI banner

**Status:** PENDING · **Priority:** Wave 2

- Pre-market: yellow banner "PROVISIONAL — validated at 09:30"
- Post-open: green banner "LIVE — trading today"
- EOD: gray banner "DAY COMPLETE — review outcomes"

### IT-03 — Sorted signal card renderer

**Status:** PENDING · **Priority:** Wave 2

Groups: ✅ TAKE_FULL, 🟡 TAKE_SMALL, 👁 WATCH, ❌ SKIP. Reads from `SDR.display.*` fields populated by `display_hints.assemble_display_block` (already shipped).

### IT-04 — Expandable [why?] reasoning

**Status:** PENDING · **Priority:** Wave 4

Reads `SDR.evidence.*` (already produced by `evidence_collector`).

### IT-05 — Proposal approval card

**Status:** PENDING · **Priority:** Wave 4

### IT-06 — Self-query disclosure card

**Status:** PENDING · **Priority:** Wave 5

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

**Status:** PENDING · **Priority:** Wave 4

PWA tap Approve → opens Telegram with pre-filled command. User confirms send. Minimal friction, uses existing flow.

### LE-06 — Demotion framework (paired with prop_007)

**Status:** APPROVE READY · **Priority:** Wave 4

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

**Status:** DESIGN COMPLETE · **Priority:** Waves 2-3 alignment

Hybrid design approved. 12 files scoped. **Bridge Intelligence tab adopts Session 4 design from Wave 2 onwards — don't build twice.**

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

**Status:** APPROVE READY · **Priority:** Wave 4

R-multiple currently 0.44 vs 1.5 target (from 2026-04-25 deep-dive). Parameter toggle to rebalance stop distance vs target distance, ship as config-only change with shadow mode for N signals.

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
- IT-01/02/03 (PWA Intel tab)
- End-to-end test against Monday morning data
- Cron-job.org dashboard update before Monday open

### Wave 3 — Following week

Full 3-layer rhythm. BR-03 + BR-04 + BR-05 complete + BR-07 complete + IT-02 complete + IT-03 extended + DATA-02.

### Wave 4 — Proposals + approvals

IT-04 + IT-05 + LE-05 + prop_005 SHIP + prop_007/LE-06 SHIP.

### Wave 5 — Self-queries

LE-01 + LE-02 + LE-03 + LE-04 + IT-06.

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
- Do not build Intelligence tab and Session 4 UI separately. Build Intelligence tab inside Session 4 design from Wave 2.
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
