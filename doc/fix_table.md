# TIE TIY Fix Table

**Purpose:** Single source of truth for all open work, ship plans, and design decisions.
**Owner:** Abhishek (decisions) + Claude (execution)
**Last updated:** 2026-04-25 (post 3 AM Bridge design session + live-data deep dive)
**Canonical status:** This file + `doc/session_context.md` = complete handoff.

---

## 🚨 FIRST THING — CHECK MACBOOK STATUS

**Before starting any Wave, fresh Claude must ask:**

> "Has MacBook been set up yet? (Homebrew + Python 3.12 + Cursor + repo cloned locally?)"

### If YES — MacBook ready

Use the **Modern Workflow:**
- File deliveries can be **diff-based** (surgical edits via Cursor)
- Local testing before commit (`python scanner/diagnostic.py` runs locally)
- Pre-commit hooks prevent broken syntax from landing
- Live-reload for PWA changes possible
- Wave 1 should take ~1 hour, not a painful night

Skip to "Ship Plan" section below.

### If NO — still on iPad

Use the **Legacy iPad Workflow:**
- All file deliveries are **complete rewrites** (no diffs possible)
- Paste via GitHub web editor, commit via Safari
- Test via Pages redeploy + hard-refresh
- Cache-bust URLs required for JS changes
- Wave 1 takes 2-3 focused hours

Work continues as before. MacBook setup is a fix_table item itself — see ENV-01 below.

### First Saturday morning MacBook action

See ENV-01 for the 60-minute stack install guide (Homebrew → Python → Cursor → repo clone → venv → verification). **That's the FIRST thing to do** when MacBook arrives, before any code work.

---

## Status legend

- **PENDING** — not started
- **IN PROGRESS** — currently being fixed
- **SHIPPED** — code committed, awaiting verification
- **VERIFIED** — confirmed working in production
- **DEFERRED** — intentionally pushed to later phase
- **WATCH** — monitoring for enough data/evidence to act
- **SUPERSEDED** — absorbed into another item

---

## Summary

- **Total items: 40** (down from 60 — several obsoleted by AN-02 + Bridge design)
- **🔴 Critical:** 0 pending (all C-series verified April 21)
- **🟠 High:** 12 items
- **🟡 Medium:** 10 items
- **🟢 Low:** 4 items
- **🧠 BR-series (Bridge):** 7 items — primary build track
- **🎨 IT-series (Intelligence tab):** 6 items — PWA plugin architecture
- **🔬 LE-series (Learner):** 6 items — self-queries + proposal approval
- **⚙️ ENV-series (environment):** 1 item — MacBook stack setup
- **📋 PROP-series (live-data proposals):** 3 items — prop_001 deferred, prop_005 ready, prop_007 ready

**Phase state:** Phase 2 unlocked. 120 live resolved, 81% WR. Bridge design complete 2026-04-25. Live-data deep dive complete 2026-04-25 (see DATA section).

---

## ⚙️ TIER 0 — ENVIRONMENT (NEW)

### ENV-01 — MacBook stack install

**Status:** PENDING (do first when MacBook arrives) · **Priority:** Prerequisite · **Effort:** 45-60 min

**60-minute install sequence:**

1. System Settings → Software Update (install pending)
2. Xcode Command Line Tools: `xcode-select --install`
3. Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
4. pyenv + Python 3.12: `brew install pyenv && pyenv install 3.12.3 && pyenv global 3.12.3`
5. Git config: name, email, pull.rebase=false
6. GitHub CLI: `brew install gh && gh auth login`
7. Clone repo: `cd ~/code && gh repo clone tietiy/tietiy-scanner`
8. Venv: `python -m venv .venv && source .venv/bin/activate && pip install yfinance pandas numpy requests`
9. Cursor IDE: download from cursor.sh, open `~/code/tietiy-scanner`
10. Verification: `python scanner/diagnostic.py` runs cleanly

**Optional Phase 9:** pre-commit hooks (`pip install pre-commit`, create `.pre-commit-config.yaml`, `pre-commit install`) — prevents broken syntax from landing on main.

**Do NOT install** (until specific need): PostgreSQL, Docker, Redis, Node.js, Anaconda, multiple Python versions.

**Success criterion:** `python scanner/diagnostic.py` passes on MacBook with fresh clone.

---

## 🔴 TIER 1 — DATA INTEGRITY

### DQ-01 — meta.json active count drift

**Status:** PENDING · **Severity:** Medium · **Priority:** Week 1

**Symptom:** Meta.json `active_signals_count` drifts from signal_history.json actual count by ~2 signals.

**Hypothesis set:**
1. Race condition between main.py step 17 meta-write and journal.py commit
2. -REJ duplicate double-counting
3. Meta counts rejected+active where history counts only active

**Fix approach:** Run diagnostic query to identify which signals differ. Patch write path that drifts. Add DQ check to chain_validator inline.

**Files:** `scanner/meta_writer.py`, `scanner/main.py` step 17.

### DQ-02 — stock_regime missing on 24% of signals

**Status:** OPEN · **Severity:** High · **Priority:** Week 1 (from live data audit)

**Evidence:** 61/254 signals have stock_regime = "(missing)". These signals have lowest WR of any cohort (72.1%).

**Fix approach:** Audit end-to-end on a sample signal. Determine if regime computation fails silently, or if legacy records lack field. Add explicit log on regime computation.

**Files:** `scanner/main.py`, `scanner/scorer.py`.

### DQ-03 — 78 signals flagged "recovery_flagged"

**Status:** OPEN · **Severity:** Medium · **Priority:** Week 2

Unclear what condition sets this flag. Audit and either fix or document.

**Files:** `scanner/recover_stuck_signals.py`, `scanner/diagnostic.py`.

### DQ-04 — 43 REJ records (duplicate tracking)

**Status:** OPEN · **Severity:** Low · **Priority:** Week 2

Known issue. True unique resolved n is ~86. Impacts downstream stats.

**Files:** `scanner/journal.py`.

---

## 🟠 TIER 2 — TRADING LOGIC

### prop_001 — DOWN_TRI system-wide kill

**Status:** DEFERRED · **Priority:** Revisit Apr 29-30 after Choppy resolutions

**Claim:** DOWN_TRI shows 20% WR live vs 87% backtest.

**Why deferred:** Deep-dive analysis 2026-04-25 shows 7 of 9 losses clustered Apr 6-8 with MAE 14-21% — classic short-squeeze event signature, not permanent edge failure. 3 Choppy DOWN_TRIs (LUPIN Apr 16, OIL Apr 17, ONGC Apr 20) resolve Apr 27-29. Their outcomes decide:
- 0-1 win → signal truly broken → activate prop_001
- 2-3 win → Apr 6-8 was artifact → keep signal, narrow kill_001

**Action now:** Monitor, no ship.

### prop_005 — Stop/target rebalance (EX-01)

**Status:** APPROVE READY · **Priority:** Week 2

**Claim:** Realized R-multiple 0.44 vs target 1.5+. Stops too wide, targets too far.

**Evidence:** 86% of signals never drop >3% below entry. 84% see MFE ≤ 10%. Targets at 20-40% almost never hit. n=120 resolved.

**Proposed change:** `stop_mode='atr'` (1.5× ATR14) parameter, `target_mode='trailing'` with first TP at +5%.

**Files:** `scanner/scorer.py`, new `data/scorer_config.json`.

**Ship method:** Parameter toggle, old default preserved. A/B shadow test for 20 trades before switching default.

### prop_007 — Demotion framework (LE-06)

**Status:** APPROVE READY · **Priority:** Week 1 (ships with Wave 4)

**Claim:** Active kill rules currently have no exit path. If a killed pattern starts winning (contra-shadow), no auto-alert or demotion fires.

**Proposed logic:** Rolling 30-day window. If killed-pattern contra-shadow shows ≥4/5 wins, auto-demote to shadow mode + Telegram /reactivate_rule prompt.

**Files:** `scanner/mini_scanner.py`, `scanner/contra_tracker.py`.

### WIN-RULES — Add confirmed winning patterns to mini_scanner_rules.json

**Status:** PENDING · **Priority:** Wave 1 (ship with cache-bust)

**Purpose:** Protect growth — explicitly flag Tier-A validated cohorts so bridge can mark them as TAKE_FULL conviction.

**Tier A — fully validated** (n ≥ 15, WR ≥ 95%, Bear regime):
- UP_TRI × Auto (n=21, 100% WR)
- UP_TRI × FMCG (n=19, 100% WR)
- UP_TRI × Metal (n=15, 100% WR)
- UP_TRI × IT (n=18, 100% WR)
- UP_TRI × Pharma (n=13, 100% WR)

**Tier B — validated, moderate sample**:
- UP_TRI × Infra × Bear (n=12, 87.5% WR)
- BULL_PROXY × Bear regime aggregate (n=16, 87.5% WR)

**Implementation:** Add `boost_patterns[]` section to `mini_scanner_rules.json` (already scaffolded, empty). Bridge reads it for conviction tagging.

**Files:** `data/mini_scanner_rules.json`.

### INV-01 — DOWN_TRI live vs backtest divergence

**Status:** PARTIALLY RESOLVED (2026-04-25 deep-dive) · **Priority:** Monitor

**Findings from live-data analysis:**
- Apr 6-8 short squeeze event drove 7/9 DOWN_TRI losses (78% of all DOWN_TRI bleed)
- Average MAE on those stops: 14-21% (not noise-volatility, event-driven)
- All resolved DOWN_TRIs were in Bear regime — 3 Choppy DOWN_TRIs open = decisive test
- UP_TRI in same window thrived (95% WR) — consistent with rally-crushing-shorts explanation

**Remaining investigation:** Choppy DOWN_TRI resolutions Apr 27-29. Feeds prop_001 decision.

### HL-04/D3 — kill_001 scope narrowing

**Status:** PENDING · **Priority:** After prop_001 decision (Week 2-3)

Currently kill_001 blocks Bank+DOWN_TRI (38 stocks). Live evidence suggests narrowing to Bank core + NBFC separate, or expanding to Bank+Energy+DOWN_TRI.

**Decision gate:** prop_001 outcome drives this. If prop_001 ships, kill_001 becomes redundant. If prop_001 stays deferred, narrow kill_001 to Bank+Energy cohort.

---

## 🧠 TIER 3 — THE BRIDGE (Primary build track)

Design locked 2026-04-25. Integration layer between backend JSONs (signal_history.json + mini_log.json + patterns.json + proposed_rules.json + contra_shadow.json + colab_insights.json + meta.json) and PWA. Reads, queries, composes — never modifies.

### BR-01 — bridge.py orchestrator + plugin folder

**Status:** PENDING · **Priority:** Wave 2 · **Effort:** M

New `scanner/bridge/` folder. `bridge.py` as orchestrator. Plugin subfolders for query modules (mirrors AN-02 pattern). Read-only by design.

### BR-02 — Pre-market composer (Layer 1)

**Status:** PENDING · **Priority:** Wave 2 · **Effort:** M

Triggered at 08:45 IST after morning_scan. Composes provisional recommendations with `phase: "PRE_MARKET"`. Signals sorted TAKE_FULL / TAKE_SMALL / WATCH / SKIP. Explicit "gap validation pending" banner.

### BR-03 — Post-open composer (Layer 2)

**Status:** PENDING · **Priority:** Wave 3 · **Effort:** M

Triggered at 09:30 IST after open_validate. Incorporates actual open prices, gap invalidations, D6 resolutions (e.g., LUPIN exit). `phase: "POST_OPEN"`. Validated picks — the real decision moment.

### BR-04 — EOD composer (Layer 4)

**Status:** PENDING · **Priority:** Wave 3 · **Effort:** M

Triggered at 16:00 IST after eod_master. Daily digest. Pattern miner updates. New proposal cards. Regime validation progress. `phase: "EOD"`.

### BR-05 — Three bridge workflow YAMLs

**Status:** PENDING · **Priority:** Waves 2-3

- `.github/workflows/bridge_premarket.yml` (after morning_scan)
- `.github/workflows/bridge_postopen.yml` (after open_validate)
- `.github/workflows/bridge_eod.yml` (after eod_master)

Each workflow: pulls latest, runs bridge with phase flag, commits `bridge_state.json`.

### BR-06 — bridge_state.json schema v1

**Status:** PENDING · **Priority:** Wave 2

Versioned schema. Fields: phase, as_of, regime, edge_health, signals_sorted, pending_proposals, active_rules, bridge_self_queries, exits_today, just_resolved, today_resolutions.

### BR-07 — Phase-aware Telegram unified messages

**Status:** PENDING · **Priority:** Wave 2-3

Three templates: pre-market brief (provisional), post-open (validated picks), EOD (digest). Reads `bridge_state.json`. Replaces fragmented UX-02/03/05 messages.

---

## 🎨 TIER 4 — INTELLIGENCE TAB (PWA)

Plugin architecture mirroring AN-02. New `output/intelligence/` folder. Session 4 UI design language.

### IT-01 — Intelligence plugin folder scaffold

**Status:** PENDING · **Priority:** Wave 2 · **Effort:** S

`output/intelligence/` with engine + plugin bundle structure. Mirrors `output/analysis/` pattern from AN-02.

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

### LE-06 — Demotion framework (same as prop_007)

**Status:** APPROVE READY · **Priority:** Wave 4

See prop_007 above.

---

## 🚚 TIER 6 — DELIVERY RELIABILITY

### CACHE-01 — Plan B cache-bust on analysis.html

**Status:** PENDING · **Priority:** Wave 1 · **Effort:** S

Runtime `Date.now()` appended to analysis JS bundle URLs. Prevents Safari cache nightmares. Done in minutes.

**Files:** `output/analysis.html`.

### CACHE-02 — analysis.html via html_builder pipeline

**Status:** PENDING · **Priority:** Wave 6 · **Effort:** M

Long-term proper solution. Convert analysis.html to Python-generated (like index.html). Add to rebuild_html.yml watched paths. Build-time cache-bust via `?v={build_time}`.

**Files:** new `scanner/analysis_html_builder.py`, `.github/workflows/rebuild_html.yml`.

### TG-01 — Telegram poll concurrency + try/except

**Status:** DIAGNOSED (2026-04-24) · PENDING FIX · **Priority:** Wave 6

**Root cause:** No concurrency lock in `telegram_poll.yml`. Overlapping runs race on `tg_offset.json`. No per-command try/except in poll loop.

**Fix bundle A+B:**
- A: Add `concurrency: group: telegram-poll, cancel-in-progress: true` to workflow
- B: Wrap dispatch loop in try/except in `poll_and_respond`

**Files:** `.github/workflows/telegram_poll.yml`, `scanner/telegram_bot.py`.

### TG-02 — Unified messages replace fragmented

**Status:** DEPENDENT on BR-02/03/04 · **Priority:** Wave 3

Once Bridge ships, delete old fragmented messages. BR-07 replaces UX-02, UX-03, UX-05.

### PIN-01 — PWA PIN placeholder injection

**Status:** DIAGNOSED · PENDING FIX · **Priority:** Week 2

Independent of bridge work.

---

## 🎨 TIER 7 — UI / POLISH

### UX-07 — whats_open trading-day math

**Status:** ✅ VERIFIED 2026-04-24 (commit e37f869)

Day column uses trading-day count with color-coded urgency (ACTIVE/EXIT TMRW/EXIT TODAY/OVERDUE).

### UX-08 — "📊 Analysis" button in PWA header

**Status:** PENDING · **Priority:** Wave 1 · **Effort:** S

Add button in PWA header (via `html_builder.py`). Opens `analysis.html` same tab.

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

## 🚀 SHIP PLAN — WAVES

### Wave 1 — Saturday morning on MacBook (1 hour)

**Preconditions:** ENV-01 complete. MacBook ready to code.

- CACHE-01 (Plan B cache-bust)
- UX-08 (Analysis button in PWA header)
- WIN-RULES (confirmed Tier-A cohorts → mini_scanner_rules.json boost_patterns)
- This fix_table rewrite (commit)

**If MacBook not ready:** Same four items via iPad web editor. Allow 2-3 hours.

### Wave 2 — Saturday afternoon / Sunday (6-8 hours)

**Bridge skeleton (Layer 1 pre-market only):**
- BR-01 (orchestrator + plugin folder)
- BR-02 (pre-market composer)
- BR-05 partial (premarket workflow)
- BR-06 (schema v1)
- BR-07 partial (premarket template)
- IT-01 (PWA plugin folder)
- IT-02 partial (pre-market banner)
- IT-03 (signal card renderer)

**End of Wave 2:** Monday morning you receive a unified pre-market brief. Signals sorted. Pipeline proven end-to-end.

### Wave 3 — Following week (6-8 hours)

**Full 3-layer rhythm:**
- BR-03 (post-open composer)
- BR-04 (EOD composer)
- BR-05 complete (both remaining workflows)
- BR-07 complete (all three templates)
- IT-02 complete (all banner states)
- IT-03 extended (gap-invalidated + live states)

**End of Wave 3:** Full bridge live. Three unified messages daily. UX-02/03/05 can be marked SUPERSEDED.

### Wave 4 — Proposals + approvals (4-6 hours)

- IT-04 ([why?] expandable reasoning)
- IT-05 (proposal approval card)
- LE-05 (PWA → Telegram deep-link flow)
- prop_005 SHIP (stop/target rebalance as parameter toggle)
- prop_007/LE-06 SHIP (demotion framework)

### Wave 5 — Self-queries (5-7 hours)

- LE-01 (query template registry)
- LE-02 (gap detection B + C)
- LE-03 (query_proposals.json)
- LE-04 (Telegram approval commands)
- IT-06 (self-query disclosure card)

### Wave 6 — Polish + parallel (5-7 hours)

- TG-01 (Telegram poll concurrency + try/except)
- DQ-01 (active count drift)
- DQ-02 (stock_regime missing audit)
- CACHE-02 (analysis.html via html_builder)

### Wave 7+ — Parallel tracks

- HL-01, MC-01 (auto-healer + master check)
- AN-04 (score × signal cross-tab)
- OPS-01..04 (repo split decision)
- prop_001 revival (after Choppy resolutions Apr 27-29)

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

---

## 🚫 WHAT NOT TO DO

- Do not rebuild TIE TIY. Current system works. Bridge is additive.
- Do not auto-execute trades. Ever.
- Do not activate kill rules without contra-shadow + demotion framework (LE-06) in place.
- Do not build Intelligence tab and Session 4 UI separately. Build Intelligence tab inside Session 4 design from Wave 2.
- Do not let Wave 1 grow past 1 hour (MacBook) or 3 hours (iPad). Cut scope if it bloats.
- Do not start HYDRAX Phase 0 until TIE TIY bridge is stable. Listed in memory as "when MacBook arrives" — revised to "when Bridge Waves 1-5 are shipped + observed for 2 weeks."
- Do not touch: `config.py` vs `scorer.py` dual constants (intentional), `mini_scanner.DEFAULT_RULES` fallback (safety), `parent_signal_id` + `sa_parent_id` dual-write (legacy migration), `eod_master.yml` + `eod_update.yml.bak` coexistence (rollback escape hatch), `main.py` STEP numbering (navigation aid).

---

## 📜 CHANGE LOG

| Date | Change |
|------|--------|
| 2026-04-20 | Initial master audit. 42 items catalogued. |
| 2026-04-21 | Session A shipped: 9 items (C-01..C-04, D1, M-11, L-05, UX-01, P-01 skipped). |
| 2026-04-23 | Wave 2/3/5.1: 16 IDs VERIFIED. See wave_execution_log_2026-04-23.md. |
| 2026-04-24 | AN-02 36-question catalog shipped (plugin architecture). UX-07 verified. |
| 2026-04-25 | **Full rewrite.** Bridge design locked (3-layer rhythm, plugin architecture, self-queries, Proof-Gated Approval). Live-data deep dive complete (UP_TRI 95% Bear, DOWN_TRI cluster Apr 6-8, score non-monotonic, R=0.44). Added BR/IT/LE series (19 new items), ENV series (MacBook setup), WIN-RULES (boost_patterns). Superseded UX-02/03/05. Total items: 40. |

---

## 🎯 IMMEDIATE NEXT ACTION

**If MacBook set up:**
1. Open Cursor, open repo
2. Ship Wave 1 (CACHE-01 + UX-08 + WIN-RULES + this file)
3. Stop. Do not proceed to Wave 2 until Saturday afternoon / Sunday.

**If still iPad:**
1. First: Do ENV-01 when MacBook arrives (60 min install)
2. Then: Wave 1 on MacBook
3. If MacBook not arrived yet: Wave 1 on iPad, full rewrites, 2-3 hours

**After Wave 1:** Sleep. Observe Monday's scan. Wave 2 after that.
