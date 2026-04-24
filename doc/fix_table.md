# TIE TIY Fix Table

**Purpose:** Single source of truth for all open work, ship plans, and design decisions.
**Owner:** Abhishek (decisions) + Claude (execution)
**Last updated:** 2026-04-25 night (Wave 1 shipped + M-05 shipped + ENV-01 complete)
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
- **SHIPPED** — code committed, awaiting production verification
- **VERIFIED** — confirmed working in production
- **DEFERRED** — intentionally pushed to later phase
- **WATCH** — monitoring for enough data/evidence to act
- **SUPERSEDED** — absorbed into another item
- **BLOCKED** — waiting on another item or evidence

---

## Summary

- **Total items: 40**
- **🔴 Critical:** 0 pending (all C-series verified April 21)
- **🟠 High:** 12 items
- **🟡 Medium:** 9 items (M-05 verified 2026-04-25 night)
- **🟢 Low:** 4 items
- **🧠 BR-series (Bridge):** 7 items — primary build track (Wave 2 next)
- **🎨 IT-series (Intelligence tab):** 6 items — PWA plugin architecture
- **🔬 LE-series (Learner):** 6 items — self-queries + proposal approval
- **⚙️ ENV-series (environment):** 0 pending (ENV-01 verified 2026-04-25 night)
- **📋 PROP-series (live-data proposals):** 3 items — prop_001 deferred, prop_005 ready, prop_007 ready
- **🚀 Wave 1:** ✅ ALL SHIPPED (CACHE-01 + UX-08 + WIN-RULES + M-05 additive + ENV-01)

**Phase state:** Phase 2 unlocked. 120 live resolved, 81% WR. Bridge design complete 2026-04-25. Live-data deep dive complete 2026-04-25. Wave 1 verified 2026-04-25 night. MacBook dev environment ready.

---

## 🎯 IMMEDIATE NEXT ACTION

**Wave 2 — Bridge skeleton. Starts on MacBook, next session.**

Morning spin-up sequence:
cd ~/code/tietiy-scanner
source .venv/bin/activate
git pull
claude
First-time Claude Code run inside the repo: `/init` to generate repo-scoped `CLAUDE.md`.

Wave 2 scope: **BR-01 + BR-02 + BR-06 + BR-07 (premarket) + IT-01 + IT-02 (partial) + IT-03 + TG-01 sidecar.** End-state: Monday pre-market delivers unified brief with sorted TAKE_FULL / TAKE_SMALL / WATCH / SKIP signals.

---

## ⚙️ TIER 0 — ENVIRONMENT

### ENV-01 — MacBook stack install

**Status:** ✅ VERIFIED 2026-04-25 · **Priority:** Prerequisite · **Effort:** ~3 hours actual

Shipped stack:
- Xcode Command Line Tools (clang 21.0.0)
- Homebrew 5.1.7 (Apple Silicon `/opt/homebrew` path)
- Python 3.12.13 + pip 26.0.1
- Git 2.54.0 (brew, replaces Apple's 2.50.1)
- Node.js 22.22.2 + npm 10.9.7
- Claude Code 2.1.119 (Claude Max subscription)
- Cursor IDE (GitHub auth)
- Claude desktop app
- Repo cloned to `~/code/tietiy-scanner`
- Python venv + 40 pip dependencies (yfinance, pandas, numpy, requests, pywebpush, cryptography, python-dotenv + transitive)
- `requirements.txt` + `.gitignore` committed + pushed
- GitHub PAT saved in macOS Keychain (no future prompts)
- `diagnostic.py --quick` → 6/6 PASS on Mac

Verified commit: `e35b49c`

---

## 🔴 TIER 1 — CRITICAL

**Zero pending.** All C-series (C-01 through C-05) VERIFIED April 21, 2026. Intelligence loop functional end-to-end (contra_tracker, rule_proposer, outcome_evaluator schema-aligned). See `wave_execution_log_2026-04-23.md` for canonical record.

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

Design locked 2026-04-25. Integration layer between backend JSONs (`signal_history.json` + `mini_log.json` + `patterns.json` + `proposed_rules.json` + `contra_shadow.json` + `colab_insights.json` + `meta.json`) and PWA. Reads, queries, composes — never modifies.

### BR-01 — bridge.py orchestrator + plugin folder

**Status:** PENDING · **Priority:** Wave 2 · **Effort:** M

New `scanner/bridge/` folder. `bridge.py` as orchestrator. Plugin subfolders for query modules (mirrors AN-02 pattern). Read-only by design.

### BR-02 — Pre-market composer (Layer 1)

**Status:** PENDING · **Priority:** Wave 2 · **Effort:** M

Triggered at 08:45 IST after morning_scan. Composes provisional recommendations with `phase: "PRE_MARKET"`. Signals sorted TAKE_FULL / TAKE_SMALL / WATCH / SKIP.

### BR-03 — Post-open composer (Layer 2)

**Status:** PENDING · **Priority:** Wave 3 · **Effort:** M

Triggered at 09:30 IST after open_validator. Validates overnight calls against actual opens. R:R recalc. D6 holiday-aware.

### BR-04 — EOD composer (Layer 4)

**Status:** PENDING · **Priority:** Wave 3 · **Effort:** M

Triggered at 16:00 IST after eod_master chain. Outcome digest. Unifies UX-02/03/05 fragmented Telegram messages.

### BR-05 — GitHub Actions workflow wiring

**Status:** PENDING · **Priority:** Wave 2 (partial) + Wave 3 (full) · **Effort:** S per workflow

Three bridge trigger workflows (premarket / postopen / eod). Each `workflow_dispatch` + upstream chain of workflow_run triggers.

### BR-06 — bridge_state.json schema v1

**Status:** PENDING · **Priority:** Wave 2 · **Effort:** S

New output file. Composed state for PWA Intel tab. Schema includes: phase, generated_at, sorted_signals[], banner_state, alerts[], self_queries[] (Wave 5).

### BR-07 — Unified Telegram templates

**Status:** PENDING · **Priority:** Wave 2 (premarket) + Wave 3 (all three) · **Effort:** M

Three Markdown-V2 templates replacing the current 5 fragmented messages. Template-bounded rendering.

---

## 🎨 TIER 4 — PWA INTELLIGENCE TAB

PWA Intel tab — built inside Session 4 UI design from Wave 2 onwards. Same fonts (Fraunces + Geist + Geist Mono), same 3-column iPad landscape layout, same time-aware mode structure. **Don't build twice.**

### IT-01 — PWA plugin folder + bridge_state fetch

**Status:** PENDING · **Priority:** Wave 2

Mirrors `output/analysis/` pattern from AN-02.

### IT-02 — Phase-aware UI banner

**Status:** PENDING · **Priority:** Wave 2

- Pre-market: yellow banner "PROVISIONAL — validated at 09:30"
- Post-open: green banner "LIVE — trading today"
- EOD: gray banner "DAY COMPLETE — review outcomes"

### IT-03 — Sorted signal card renderer

**Status:** PENDING · **Priority:** Wave 2

Groups: ✅ TAKE_FULL, 🟡 TAKE_SMALL, 👁 WATCH, ❌ SKIP. Each card shows symbol, signal type, score, sector, one-line reasoning. Sorted by bridge recommendation.

### IT-04 — Expandable [why?] reasoning

**Status:** PENDING · **Priority:** Wave 4

Tap any signal → shows queries that informed the recommendation, evidence numbers, counter-evidence, any self-queries used.

### IT-05 — Proposal approval card

**Status:** PENDING · **Priority:** Wave 4

Renders Proof-Gated Approval structure: claim + evidence + counter-evidence + expected effect + reversibility + [Approve] [Reject] [Review SQL].

### IT-06 — Self-query disclosure card

**Status:** PENDING · **Priority:** Wave 5

Shows experimental queries bridge wrote, their SQL, results, signals they influenced. [Promote to curated] [Reject] buttons.

---

## 🔬 TIER 5 — THE LEARNER

Self-query pipeline + approval flow. Proof-Gated Approval framework.

### LE-01 — Query template registry

**Status:** PENDING · **Priority:** Wave 5

5-7 bounded SQL templates. Bridge fills parameters, can't write arbitrary SQL. Read-only enforcement at connection level.

### LE-02 — Gap detection (triggers B + C)

**Status:** PENDING · **Priority:** Wave 5

**Trigger B (automatic):** cohort n<5, new signal type, low confidence recommendation.
**Trigger C (user-requested):** "Dig deeper" button on PWA signal card.

Max 3 self-queries per bridge run.

### LE-03 — query_proposals.json

**Status:** PENDING · **Priority:** Wave 5

New file. Atomic writes. Stores: question, SQL, result, signals affected, status (pending/approved/rejected/promoted).

### LE-04 — Telegram approval commands

**Status:** PENDING · **Priority:** Wave 5

`/approve_query N` — promotes to curated set. `/reject_query N` — never generate again.

### LE-05 — PWA → Telegram deep-link approval

**Status:** PENDING · **Priority:** Wave 4

PWA tap Approve → opens Telegram with pre-filled `/approve_rule prop_XXX` or `/approve_query N`. User confirms send in Telegram. telegram_poll picks up command. Minimal friction, uses existing working flow.

### LE-06 — Demotion framework (paired with prop_007)

**Status:** APPROVE READY · **Priority:** Wave 4

See prop_007 in PROP series. Rolling N-signal window. If killed-pattern contra-shadow shows reverse edge, auto-demote to shadow mode + Telegram `/reactivate_rule` prompt. If boost_patterns drop below 70% WR in 10-signal window, tier demotion (A→B→watchlist).

---

## 🚚 TIER 6 — DELIVERY RELIABILITY

### CACHE-01 — Plan B cache-bust on analysis.html

**Status:** ✅ VERIFIED 2026-04-25 · **Priority:** Wave 1 · **Effort:** S

Shipped: 6 local scripts converted to `data-src` stubs + inline loader injects `?v=Date.now()` cache-busted `<script>` tags with `async=false`. CDN scripts untouched (URL-versioned). Live console confirms `[CACHE-01] injected 6 cache-busted scripts`.

### CACHE-02 — analysis.html via html_builder pipeline

**Status:** PENDING · **Priority:** Wave 6 · **Effort:** M

Long-term proper solution. Convert analysis.html to Python-generated (like index.html). Add to rebuild_html.yml watched paths. Build-time cache-bust via `?v={build_time}`.

**Files:** new `scanner/analysis_html_builder.py`, `.github/workflows/rebuild_html.yml`.

### TG-01 — Telegram poll concurrency + try/except

**Status:** DIAGNOSED (2026-04-24) · PENDING FIX · **Priority:** Wave 2 sidecar (small, MacBook)

**Root cause:** No concurrency lock in `telegram_poll.yml`. Overlapping runs race on `tg_offset.json`. No per-command try/except in poll loop.

**Fix bundle A+B:**
- A: Add `concurrency: group: telegram-poll, cancel-in-progress: true` to workflow
- B: Wrap dispatch loop in try/except in `poll_and_respond`

**Files:** `.github/workflows/telegram_poll.yml`, `scanner/telegram_bot.py`.

### TG-02 — Unified messages replace fragmented

**Status:** DEPENDENT on BR-02/03/04 · **Priority:** Wave 3

Once Bridge ships, delete old fragmented messages. BR-07 replaces UX-02, UX-03, UX-05.

### PIN-01 — PWA PIN placeholder injection

**Status:** DIAGNOSED · PENDING FIX · **Priority:** Wave 6 / Week 2

Independent of bridge work.

---

## 🎨 TIER 7 — UI / POLISH

### UX-07 — whats_open trading-day math

**Status:** ✅ VERIFIED 2026-04-24 (commit e37f869)

Day column uses trading-day count with color-coded urgency (ACTIVE/EXIT TMRW/EXIT TODAY/OVERDUE).

### UX-08 — "📊 Analysis" button in PWA header

**Status:** ✅ VERIFIED 2026-04-25 · **Priority:** Wave 1 · **Effort:** S

Shipped: Fixed-position pill button top-right, z-index 50 (above content, below overlays), safe-area aware via `env(safe-area-inset-top)`. Added in `scanner/html_builder.py`. Migrate into ui.js rendered header when Session 4 UI ships.

### UX-02 — Gap-skip summary in morning brief

**Status:** SUPERSEDED by BR-02

### UX-03 — Failure_reason in EOD Telegram

**Status:** SUPERSEDED by BR-04

### UX-05 — R:R recalc at actual_open

**Status:** SUPERSEDED by BR-03

### Session 4 UI (UI2-UI12)

**Status:** DESIGN COMPLETE · **Priority:** Waves 2-3 alignment

Hybrid design approved. 12 files scoped. Intelligence tab (IT-series) built using same fonts (Fraunces + Geist + Geist Mono), same 3-column iPad landscape layout, same time-aware mode structure. **Bridge Intelligence tab adopts Session 4 design from Wave 2 onwards — don't build it twice.**

---

## 🏥 TIER 8 — OBSERVABILITY & OPERATIONS

### M-05 — chain_validator extended coverage

**Status:** ✅ SHIPPED 2026-04-25 · **Priority:** Wave 1 additive · **Effort:** S

Shipped: `scanner/chain_validator.py` rewritten. Added `_check_rule_proposer()` (error on unreadable, warn on missing/stale) and `_check_contra_tracker()` (warn on missing, error on unreadable, warn on counter drift between `total_tracked` and `len(shadows)`; staleness is benign since the file only moves on kill matches). Checks dict expanded from 5 to 7. Schema_version unchanged — consumers iterate dynamically. Verification runs in Monday's `eod_master.yml`.

### HL-01 — Auto-healer framework

**Status:** PENDING · **Priority:** Week 2 (parallel to Bridge) · **Effort:** M

Wraps existing `diagnostic.py --heal`. Schedules periodic health checks. Telegram audit trail. **Never touches trading core** (entry/stop/target/outcome immutable).

### HL-02 through HL-05 — Heal scopes

**Status:** PENDING · **Priority:** Week 2+ (sequential, one at a time with tests)

### MC-01 — Ultimate master check

**Status:** PENDING · **Priority:** Week 2 (parallel to Bridge) · **Effort:** M

Framework with 8 scopes. Manual dispatch initially. Monitors bridge health too.

### MC-02, MC-03 — Expanded check + daily report

**Status:** PENDING · **Priority:** Week 2-3

### OPS-01 through OPS-04 — Repo split

**Status:** PENDING · **Priority:** Separate decision track

Public vs private repo split. Not sprint-critical. Discuss when ready.

---

## 📊 TIER 9 — ANALYSIS & INVESTIGATION

### AN-02 — 36-question catalog

**Status:** ✅ VERIFIED 2026-04-24 (commits e37f869 + preceding)

Full catalog shipped. Bridge reuses these queries.

### AN-04 — WR by score × signal-type cross-tab

**Status:** PENDING · **Priority:** Week 2 · **Effort:** S

Addresses SCR-01 hypothesis (score 5-6 non-monotonicity). Add as 37th AN-02 question.

### SCR-01 — Score calibration investigation

**Status:** DEFERRED · **Priority:** After AN-04 ships

Hypothesis: score 5-6 buckets polluted by DOWN_TRIs. If prop_001 activates, re-evaluate.

### DATA-01 — Apr 6-8 cluster flag in history

**Status:** DEFERRED · **Priority:** Low

Document the Apr 6-8 event window in signal_history.json via metadata field so future analysis can filter/annotate.

### DATA-02 — Choppy regime watch protocol

**Status:** PENDING · **Priority:** Wave 2 (part of bridge)

Every Choppy resolution (next 2 weeks) triggers Telegram alert with full context. Integrates with bridge edge_health tracking.

---

## 📋 TIER 10 — LIVE-DATA PROPOSALS

### prop_001 — DOWN_TRI restriction

**Status:** DEFERRED · **Priority:** Gate on Apr 27-29 Choppy resolutions

3 Choppy DOWN_TRIs open (LUPIN/OIL/ONGC). Their resolution determines whether DOWN_TRI edge extends beyond Bear regime or collapses as Apr 6-8 event artifact. If collapses → ship prop_001 (DOWN_TRI restricted to Bear regime only). If holds → keep DOWN_TRI open across regimes, narrow kill_001 instead.

### prop_005 — Stop/target rebalance as parameter toggle

**Status:** APPROVE READY · **Priority:** Wave 4

R-multiple currently 0.44 vs 1.5 target (from 2026-04-25 deep-dive). Parameter toggle to rebalance stop distance vs target distance, ship as config-only change with shadow mode for N signals before activation.

### prop_007 — Demotion framework (paired with LE-06)

**Status:** APPROVE READY · **Priority:** Wave 4

See LE-06. Shipping them together — LE-06 is the framework, prop_007 is the policy.

### WIN-RULES — boost_patterns in mini_scanner_rules.json

**Status:** ✅ SHIPPED 2026-04-25 · **Priority:** Wave 1 · **Consumer:** Bridge Wave 2

Shipped: 7 boost_patterns (5 Tier A UP_TRI × {Auto/FMCG/IT/Metal/Pharma} × Bear, 2 Tier B — UP_TRI × Infra × Bear + BULL_PROXY × ANY × Bear). Schema v3. Pharma flagged `validated_under_floor` (n=13 below the n≥15 Tier A floor). No Python reads boost_patterns yet — metadata only until Bridge composer ships.

---

## 🚀 SHIP PLAN — WAVES

### Wave 1 — ✅ COMPLETE (2026-04-25)

Shipped:
- ✅ CACHE-01 (Plan B cache-bust)
- ✅ UX-08 (Analysis button in PWA header)
- ✅ WIN-RULES (boost_patterns in mini_scanner_rules.json)
- ✅ M-05 (chain_validator extended coverage — additive to wave)
- ✅ ENV-01 (MacBook stack install)

Verified: PWA Analysis button live top-right, console shows `[CACHE-01] injected 6 cache-busted scripts`, `diagnostic.py --quick` 6/6 green on Mac.

### Wave 2 — Next session (6-8 hours on MacBook)

**Bridge skeleton (Layer 1 pre-market only) + TG-01 sidecar:**
- BR-01 (orchestrator + plugin folder)
- BR-02 (pre-market composer)
- BR-05 partial (premarket workflow)
- BR-06 (schema v1)
- BR-07 partial (premarket template)
- IT-01 (PWA plugin folder)
- IT-02 partial (pre-market banner)
- IT-03 (signal card renderer)
- TG-01 (poll concurrency + try/except — small, ships with wave for delivery reliability)

**End of Wave 2:** Monday morning you receive a unified pre-market brief. Signals sorted. Pipeline proven end-to-end.

### Wave 3 — Following week (6-8 hours)

**Full 3-layer rhythm:**
- BR-03 (post-open composer)
- BR-04 (EOD composer)
- BR-05 complete (both remaining workflows)
- BR-07 complete (all three templates)
- IT-02 complete (all banner states)
- IT-03 extended (gap-invalidated + live states)
- DATA-02 (Choppy watch protocol folded into bridge)

**End of Wave 3:** Full bridge live. Three unified messages daily. UX-02/03/05 marked SUPERSEDED.

### Wave 4 — Proposals + approvals (4-6 hours)

- IT-04 ([why?] expandable reasoning)
- IT-05 (proposal approval card)
- LE-05 (PWA → Telegram deep-link flow)
- prop_005 SHIP
- prop_007 / LE-06 SHIP (demotion framework)

### Wave 5 — Self-queries (5-7 hours)

- LE-01 (query template registry)
- LE-02 (gap detection B + C)
- LE-03 (query_proposals.json)
- LE-04 (Telegram approval commands)
- IT-06 (self-query disclosure card)

### Wave 6 — Polish + parallel (5-7 hours)

- CACHE-02 (analysis.html via html_builder)
- PIN-01 (PWA PIN injection)
- AN-04 (score × signal cross-tab)

### Wave 7+ — Parallel tracks

- HL-01, MC-01 (auto-healer + master check)
- OPS-01..04 (repo split decision)
- prop_001 revival (after Choppy resolutions Apr 27-29)
- H-04/D3 (kill_001 scope)
- H-06 (sector taxonomy)
- H-07 (price_feed.py full adoption)

---

## 🧭 KEY DESIGN PRINCIPLES (locked)

1. **signal_history.json is persistent truth.** All other JSONs are overlays.
2. **Proof-Gated Approval.** Every structural change ships with claim + evidence + counter-evidence + expected effect + reversibility path. No exceptions.
3. **Read-only bridge.** Bridge never modifies db or module outputs. Only reads, queries, composes.
4. **Human approval mandatory.** No auto-execute. No auto-activate kill rules. Every change gates on /approve command.
5. **Plugin architecture everywhere.** AN-02 pattern extends to bridge + intelligence tab. Each new query/view = new plugin file, no engine changes.
6. **Template-bounded self-queries.** Bridge can't write arbitrary SQL. 5-7 bounded templates, fill parameters only.
7. **Disclosure before promotion.** Self-queries visible to user with full SQL before becoming curated.
8. **MacBook is additive, not replacement.** Code and data stay on existing repo. MacBook = faster workflow, not new architecture.
9. **Build TIE TIY to stable first.** HYDRAX deferred until TIE TIY Bridge Waves 1-5 complete and observed for 2+ weeks.
10. **Confidence gates for rule activation:** n ≥ 20 · confidence ≥ 85% · WR gap ≥ 15% below baseline. May refine post-prop_005.
11. **No diffs-on-iPad.** Diff-based edits require Cursor (MacBook). iPad falls back to complete-rewrite if ever needed.

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

---

## 📜 CHANGE LOG

| Date | Change |
|------|--------|
| 2026-04-20 | Initial master audit. 42 items catalogued. |
| 2026-04-21 | Session A shipped: 9 items (C-01..C-04, D1, M-11, L-05, UX-01, P-01 skipped). |
| 2026-04-23 | Wave 2/3/5.1: 16 IDs VERIFIED. See wave_execution_log_2026-04-23.md. |
| 2026-04-24 | AN-02 36-question catalog shipped (plugin architecture). UX-07 verified. |
| 2026-04-25 | **Full rewrite.** Bridge design locked (3-layer rhythm, plugin architecture, self-queries, Proof-Gated Approval). Live-data deep dive complete. Added BR/IT/LE series (19 new items), ENV series (MacBook setup), WIN-RULES (boost_patterns). Superseded UX-02/03/05. Total items: 40. |
| 2026-04-25 (night) | **Wave 1 shipped + ENV-01 complete.** CACHE-01 + UX-08 + WIN-RULES + M-05 all VERIFIED. MacBook Air M5 set up with full dev stack (Homebrew 5.1.7 / Python 3.12.13 / Git 2.54 / Node 22.22.2 / Claude Code 2.1.119 / Cursor). Repo cloned, venv + 40 deps, requirements.txt + .gitignore committed. GitHub PAT in Keychain. diagnostic.py --quick 6/6 green on Mac. Production PWA verified live: 📊 Analysis button works + console shows cache-bust injection. Ready for Wave 2 Bridge skeleton. |