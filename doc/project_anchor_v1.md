# TIE TIY Project Anchor — Lifecycle + State + Future

**Authored:** 2026-04-28 evening IST · Audit-first read-only · Real-stage knowledge with citations
**Provenance:** Single-pass 4-phase audit during Wave 5 Step 3 design lock session
**Repo head at audit time:** `060d7c9` (Wave 5 Step 2 folder skeleton ship)
**Scope:** Present + future + gaps + drift + decisions; HYDRAX Phase 0 out of scope, exit_logic_redesign placeholder; Wave 5 Step 3 schema lock-in is parallel work and does NOT gate this doc.

**Citation discipline:** Every behavioral claim cites evidence — commit hash, file:line, design doc §, or workflow name. Future-state claims cite design doc §. Where design docs do not specify, marked `[PROJECTION-GAP-N]` (no source) or `[INTEGRATION-GAP-N]` (cross-system path unspecified).

**4 phases of audit:**
- Phase 1 (data collection): 25 workflows, 13 docs, 30 scanner root files, 32 bridge files, 9 brain files, 211 commits today.
- Phase 2 (Parts 1+3): present-state lifecycle + current component state.
- Phase 3 (Parts 2+4): future-state lifecycle + target component state.
- Phase 4 (Parts 5+6+7+8): gap inventory + drift report + decision log + cross-references.

---

## Part 1 — Present-state lifecycle

### 1.1 Trading day (2026-04-28 worked example)

All times IST; commit hashes from `git log` today; archive sizes from local working tree post-pull.

| IST | UTC | Trigger | Workflow / module | Reads | Writes | Telegram | Commit signature |
|---|---|---|---|---|---|---|---|
| 08:30 | 03:00 | GitHub schedule `0 3 * * 1-5` | `heartbeat.yml` | meta.json, signal_history.json | none | "💓 TIE TIY · regime · last scan" | (Telegram-only, no commit) |
| 08:45 | 03:15 | cron-job.org dispatch | `morning_scan.yml` → `main.py` (1005 LOC) | data/fno_universe.csv (188 stocks) | scan_log.json, mini_log.json, signal_history.json | morning brief | `87f9a34` "Morning scan 2026-04-28 03:17 IST" |
| 08:55 | 03:25 | cron-job.org dispatch | `premarket.yml` → `bridge.py --phase=PRE_MARKET` (330) → `composers/premarket.py` (646) | truth files | bridge_state.json, bridge_state_history/2026-04-28_PRE_MARKET.json (201KB) | L1 brief via `bridge_telegram_premarket.py` (530) — "🎯 Pre-market — 6 SKIP + COALINDIA WATCH caveat" | "Bridge premarket 2026-04-28 03:25 IST" |
| 09:02 | 03:32 | cron-job.org dispatch | `scan_watchdog.yml` | meta.json + GitHub Actions API | none unless retrigger | none unless retrigger | (no commit; clean today) |
| 09:15 | — | (market opens) | (manual trader entries) | — | — | — | — |
| 09:27 | 03:57 | cron-job.org dispatch | `open_validate.yml` → `open_validator.py` (488) | yfinance 9:15 opens | open_prices.json, signal_history.json (gap%, D6 resolutions) | per-resolution alerts | `da71243` "Open validate + D6 resolve 2026-04-28 03:57 IST" |
| 09:30+ | 04:00+ | cron-job.org every 5min | `ltp_updater.yml` → `ltp_writer.py` (439) → `price_feed.py` | yfinance LTP per stock | ltp_prices.json | none | ~70 commits today: "LTP update HH:MM IST" |
| 09:32+ | 04:02+ | cron-job.org every 5min (+2min offset) | `stop_check.yml` → `stop_alert_writer.py` (849) | ltp + signal_history | stop_alerts.json | proximity/breach alerts | ~70 commits today: "Stop check HH:MM IST" (UTC labeled IST per GAP-06) |
| 09:40 | 04:10 | cron-job.org dispatch | `postopen.yml` → `bridge.py --phase=POST_OPEN` → `composers/postopen.py` (607) | open_prices, prior bridge_state | bridge_state.json (phase=POST_OPEN), bridge_state_history/2026-04-28_POST_OPEN.json (201KB) | L2 conditional alert (only on bucket-change OR severe gap) | "Bridge postopen 2026-04-28 04:10 IST" |
| 15:30 | — | (market closes) | — | — | — | — | — |
| 15:35 | 10:05 | cron-job.org dispatch | `eod_master.yml` 8-step chain | signal_history, eod_prices.json | resolutions, eod_prices.json, system_health.json, patterns.json, proposed_rules.json | **legacy EOD digest** via `main.py eod` (steps 2-4/8) — "📊 EOD · Resolved: 3 · W:1 L:2 F:0" + 61-signal "EXIT TOMORROW" preview | `8edab07` "EOD master 2026-04-28 IST — backup+outcomes+eod+validate+chain+patterns+proposals" at 15:36 IST |
| 16:15 | 10:45 | (was GitHub schedule pre-`2fc1f35`; tonight migrated to cron-job.org dispatch) | `eod.yml` → `bridge.py --phase=EOD` → `composers/eod.py` (618) | signal_history, eod_prices, prior bridge_state | bridge_state.json (phase=EOD), bridge_state_history/2026-04-28_EOD.json (150KB) | bridge L4 digest via `bridge_telegram_eod.py` (492) | **today: scheduled tick MISSED** (M-15). Manual workflow_dispatch fired at 19:01 IST → commit `a5edc32` "Bridge eod 2026-04-28 13:31 IST" (UTC labeled IST per GAP-06) |
| 16:15 | 10:45 | GitHub schedule (still on it) | `colab_sync.yml` → `scanner/colab_sync.py` (309) | signal_history.json (gen1 flatten) | colab_export.json | none | **today: MISSED (M-15)** — `output/colab_export.json` mtime 27 Apr 21:48 (yesterday) |
| 16:30 | 11:00 | GitHub schedule `0 11 * * 1-5` | `diagnostic.yml` → `scanner/diagnostic.py` (838) | output/* + scanner/* | none (Telegram-only) | health summary | **today: MISSED (M-15)** |

**Anomalies materialized today (Phase 1 anomaly cross-references):**

- **M-12** — `system_health.json` written at 15:36 IST during eod_master step 6 (chain_validator) reports `pattern_miner: warn — Last run: 2026-04-27` despite step 7 (pattern_miner) writing fresh `generated_at: 2026-04-28T...` ~125ms later. Bridge L4 archive `phase_status: DEGRADED` propagates these stale warns; L1 brief at 08:55 IST also DEGRADED for same reason.
- **M-13** — signal_history non-OPEN count = 181 vs `patterns.json total_resolved_signals = 161` = 20-record gap; ~8 records have `outcome='OPEN'` AND `outcome_date='2026-04-27'` set simultaneously.
- **M-14** — eod.yml + colab_sync.yml schedule collision at 16:15 IST mooted today (neither fired); collision concern persists architecturally.
- **M-15** — eod.yml + colab_sync + diagnostic all missed today's tick. Drove tonight's eod.yml migration commit `2fc1f35`. RESOLVED.
- **M-16** — 15:36 IST legacy digest "Open: 94"; 19:01 IST bridge L4 digest `summary.open_positions_count: 80`. Definitional difference: legacy counts `outcome=='OPEN'` (105 raw); bridge L4 filters to 6-day-trading-window active (80).
- **UX-03** — both EOD digests fired today (15:36 IST legacy + 19:01 IST bridge L4). Two parallel digests visible to trader.

### 1.2 Non-trading day (2026-04-25 Saturday worked example)

| IST | Trigger | Workflow | Action | Commit |
|---|---|---|---|---|
| 08:30 | GitHub schedule `0 3 * * 6` | `backup_manager.yml` | Daily snapshot of signal_history + signal_archive | `cd5ddb2` "chore: Saturday backup 2026-04-25" |
| 09:00 | GitHub schedule `30 3 * * 6` | `weekend_summary.yml` → `scanner/weekend_summary.py` (217) | Telegram weekly W/L/F summary | (Telegram-only, no commit) |
| n/a | weekday-only schedules | morning_scan, premarket, postopen, open_validate, ltp_updater, stop_check, eod_master, eod, colab_sync, diagnostic, scan_watchdog, heartbeat, gap_report (Mon-only) | All correctly skip via cron `1-5` weekday-only filter | none |

**Saturday is a code-shipping day:** Apr-25 user shipped 8 commits including CACHE-01 + UX-08 + WIN-RULES + M-05 + ENV-01 verification + MacBook stack live (`e35b49c` "chore: add .gitignore and requirements.txt for local dev" 02:59 IST + 7 other Saturday-night ship commits). User-attributed commits are the dominant non-bot signal on weekends.

**Sunday (2026-04-26 worked example):**

| IST | Trigger | Workflow | Action | Commit / artifact |
|---|---|---|---|---|
| 20:00 | GitHub schedule `30 14 * * 0` | `weekly_intelligence.yml` → `scanner/weekly_intelligence.py` (485 LOC) | Mines 7-day patterns + regime trend + contra summary; Telegram digest | writes `output/weekly_intelligence_latest.json` (current file dated 2026-04-26 16:26 UTC = 21:56 IST per `generated_at`); single commit "Sunday weekly intel" pattern |
| n/a | weekday-only | morning_scan + scan_watchdog + premarket + open_validate + postopen + ltp_updater + stop_check + eod_master + eod + colab_sync + diagnostic + heartbeat | skip via `1-5` weekday filter | none |

**Week-shape pattern summary:**
- **Mon-Fri:** 11 cron-job.org workflows (precision-critical) + 7 GitHub-schedule workflows (drift-tolerant) all weekday-active. Today's M-15 evidence: 3-of-3 GitHub-schedule weekday workflows missed; 6-of-6 cron-job.org workflows fired. Reliability asymmetry drove tonight's `2fc1f35` migration.
- **Sat:** 2 active workflows (backup_manager + weekend_summary) + arbitrary user-driven commits (no cron schedule).
- **Sun:** 1 active workflow (weekly_intelligence at 20:00 IST). System otherwise idle.
- **Holidays:** `data/nse_holidays.json` consulted by `scanner/calendar_utils.py:is_trading_day()` (canonical since Wave 2 migration `c312316` 2026-04-23). cron-job.org workflows fire on schedule but check `is_trading_day()` and short-circuit; GitHub-schedule workflows have no such guard (heartbeat fires on holidays, sends "alive ping" with `regime: ?`).

**Anomaly observed in `output/bridge_state_history/`:** `2026-04-26_PRE_MARKET.json` exists at 1007 bytes (vs 201KB for trading-day archives). 2026-04-26 was Sunday — premarket should not have fired. File mtime 26 Apr 16:54 IST. Likely a manual workflow_dispatch test fire or degraded-state archive from early bridge wiring; not load-bearing today but worth flagging in Part 6 drift report.

---

## Part 2 — Future-state lifecycle (post brain Wave 5 + UI wave)

**Assumptions for projection (cited):**
- Brain Wave 5 Steps 1–7 all shipped (Step 1 ✓ `720c127`, Step 2 ✓ `060d7c9`, Steps 3–7 hypothetically complete per `brain_design_v1.md §4`)
- UI wave shipped: IT-01..IT-06 all done (per `fix_table.md TIER 4`)
- `exit_logic_redesign_v1.md` either DRAFTED + shipped OR REJECTED (Phase 1 anomaly #3 resolved either way)
- All current M-series resolved or annotated obsolete
- HYDRAX Phase 0 NOT in scope (separate audit per spec)

### 2.1 Trading day projected

| IST | Trigger | Workflow / module | Reads | Writes | Telegram | Source citation |
|---|---|---|---|---|---|---|
| 08:30 | GitHub schedule | heartbeat.yml | meta.json + signal_history | (Telegram only) | "💓 TIE TIY" | unchanged from Part 1.1 |
| 08:45 | cron-job.org | morning_scan.yml | fno_universe.csv | scan_log/mini_log/signal_history | morning brief | unchanged |
| 08:55 | cron-job.org | premarket.yml → bridge L1 | truth files | bridge_state, history archive | L1 brief | unchanged |
| 08:55+ | (PWA refresh) | `output/app.js` reads **NEW: bridge_state.json (IT-01)** | bridge_state.json + signal_history fallback | localStorage | (PWA UI render only) | `bridge_design §11.1` + `fix_table IT-01` |
| 08:55+ | (PWA banner) | UI wave: phase-aware banner | bridge_state.phase | DOM render | none | `fix_table IT-02`: "PROVISIONAL — validated at 09:30" yellow |
| 09:02 | cron-job.org | scan_watchdog.yml | meta + GitHub Actions API | (no-op healthy) | (Telegram on remediation only) | unchanged |
| 09:15 | market opens | (manual entries) | — | — | — | unchanged |
| 09:27 | cron-job.org | open_validate.yml | yfinance opens | open_prices, signal_history (D6 resolves) | per-resolution alert | unchanged |
| 09:30+ | cron-job.org every 5min | ltp_updater.yml | yfinance LTP | ltp_prices | none | unchanged |
| 09:32+ | cron-job.org every 5min | stop_check.yml | ltp + signal_history | stop_alerts | proximity/breach | unchanged |
| 09:40 | cron-job.org | postopen.yml → bridge L2 | open_prices, prior state | bridge_state (POST_OPEN), history archive | L2 conditional alert | unchanged |
| 09:40+ | (PWA refresh) | UI wave: banner flips green "LIVE — trading today" | bridge_state.phase | DOM | none | `fix_table IT-02` |
| 15:30 | market closes | — | — | — | — | unchanged |
| 15:35 | cron-job.org | eod_master.yml | signal_history, eod_prices | resolutions, eod_prices, system_health, patterns, proposed_rules | **brain-aligned only** — UX-03 retirement: legacy `main.py eod` Telegram path REMOVED | `fix_table BR-04` Status update from `51448e8` (UX-03 retirement priority elevated) |
| 16:15 | cron-job.org dispatch (post `2fc1f35`) | eod.yml → bridge L4 | signal_history, eod_prices, system_health | bridge_state (EOD), history archive | bridge L4 digest (single source post-UX-03) | unchanged once scheduled-tick verified |
| 16:15+ | (PWA refresh) | UI wave: banner flips gray "DAY COMPLETE — review outcomes" | bridge_state.phase=EOD | DOM | none | `fix_table IT-02` |
| 16:30 | (still GitHub schedule per current scope) | diagnostic.yml | scanner/* + output/* | system health Telegram | health summary | `[PROJECTION-GAP-1]` — design docs do not specify whether diagnostic.yml migrates to cron-job.org or stays |
| **22:00** | `[PROJECTION-GAP-2]` brain.yml (NEW) | `brain_input.py` | bridge_state_history/<date>_EOD.json primary; POST_OPEN fallback per §11 Q5 | (read-only) | none | `brain_design §2 line 71` |
| **22:01** | (chained) | `brain_derive.py` → 4 derivers | truth files | output/brain/cohort_health.json + regime_watch.json + portfolio_exposure.json + ground_truth_gaps.json (+ history archives, 30-day prune) | none | `brain_design §2 line 72 + §4 Step 3` |
| **22:02** | (chained) | `brain_verify.py` | derived views | proposal candidates (in-memory, format per §6) | none | `brain_design §2 line 73 + §4 Step 4 + §6` |
| **22:03–04** | (chained) | `brain_reason.py` → 3-5 LLM gates against `claude-opus-4-7` | derived views + verify candidates | output/brain/reasoning_log.json (append-only) | none | `brain_design §1 constraint 4 + §4 Step 5 + §11 Q1`. Cost <$1/day; circuit breaker $5 hard abort per `§11 Q2` |
| **22:05** | (chained) | `brain_output.py` → finalize | reasoning + verify | output/brain/unified_proposals.json (top-3 cap per §1 constraint 8) + dual-write proposed_rules.json (W5-S6) | none | `brain_design §2 line 75 + §4 Step 6 + §5 + §10 W5-S6` |
| **22:06** | (chained) | `brain_telegram.py` → nightly batch | unified_proposals.json | (Telegram only) | **brain digest: top-3 proposals** with `/approve <unified_id>` + PWA Monster tab deep link | `brain_design §2 line 76 + §8` |
| 22:06+ | trader review (out-of-band) | (on-demand) | — | — | — | — |
| 22:06+ | trader → PWA Monster tab | UI wave: `output/monster.js` (NEW) reads unified_proposals.json | unified_proposals.json | localStorage UI state | none | `fix_table IT-05 + LE-05 + brain_design §4 Step 8` |
| 22:06+ | trader taps PWA approve | UI wave: deep-link → Telegram | (PWA → Telegram bridge) | (no PWA write) | "/approve prop_unified_..." pre-fills | `brain_design §8 + LE-05` (`tg://msg?text=/approve%20<id>`); `[INTEGRATION-GAP-5]` 3-tap UX |
| 22:06+ | trader sends `/approve` | telegram_bot → `_respond_approve` (post W5-S7) | unified_proposals.json | mini_scanner_rules.json (if `kill_rule`/`boost_promote`) via legacy adapter; decisions_journal.json append | "✅ Approved" | `brain_design §4 Step 7 + §5 Type values + §10 W5-S7` |
| (next 22:00) | next-cycle brain | brain reads decisions_journal.json | decisions_journal.json | (informs disagreement detection per §11 Q4) | none | `brain_design §11 Q4` `[PROJECTION-GAP-3]` — disagreement logic flagged `[needs-verification]` |

**Anomaly resolution:**
- Phase 1 anomaly #2 (`output/brain/` missing) → **resolved**: 4 derived view JSONs + history archives + unified_proposals + decisions_journal + reasoning_log all populated.
- Phase 1 anomaly #5 (UX-03 dual digests) → **resolved**: legacy Telegram path retired.
- M-15 → already resolved (`2fc1f35`).

### 2.2 Non-trading day projected

**Brain weekend behavior `[PROJECTION-GAP-4]`:** `brain_design §2` says "Brain does NOT run during market hours" but does NOT specify weekend behavior. Two consistent interpretations: (a) brain runs Mon-Sun, weekend runs read stale-by-design inputs; (b) brain gated to weekday days only. Design doc does not lock either.

**Saturday (under projection (a) — daily run):**
- 08:30 backup_manager.yml unchanged
- 09:00 weekend_summary.yml unchanged
- 22:00–22:06 brain.yml reads Friday's `bridge_state_history/<friday>_EOD.json` as most-recent EOD; `_metadata.warnings: ["no fresh trading day"]`; nightly digest may be empty

**Sunday:**
- 20:00 weekly_intelligence.yml regenerates `weekly_intelligence_latest.json`
- 22:00–22:06 brain.yml reads weekly_intelligence_latest.json (just regenerated 2 hours ago) for `regime_watch.json` derivation per `§4 Step 3`

### 2.3 Trader approval loop — full proposal lifecycle

```
22:00 IST  brain_input loads truth files [§2 line 71]
              ↓
22:01      brain_derive → 4 derived views [§4 Step 3]
              ↓
22:02      brain_verify scaffolds candidates [§4 Step 4 + §6]
              ↓
22:03–04   brain_reason → 3-5 LLM gates Opus 4.7 [§4 Step 5 + §11 Q1]
              cost <$1/day; abort $5 [§11 Q2]
              ↓
22:05      brain_output → unified_proposals.json (top-3) [§5 + §10 W5-S6]
              ↓
22:06      brain_telegram → "🧠 Brain · 3 pending" [§2 line 76 + §8]
              ↓
       trader review (out-of-band)
              ↓
   ┌──────────────────────┐         ┌──────────────────────────────┐
   │ PATH A: Telegram     │         │ PATH B: PWA Monster tab      │
   │ /approve <id>        │         │ (IT-05) reads unified queue  │
   └────────┬─────────────┘         │ → tap Approve → tg://msg     │
            │                        │   ?text=/approve%20<id>      │
            │                        │ → 3-tap confirm send         │
            │                        │ [LE-05; INTEGRATION-GAP-1]   │
            │                        └──────────┬───────────────────┘
            └──────────┬────────────────────────┘
                       ↓
   telegram_bot _respond_approve (post W5-S7)
   → unified_proposals.json type dispatch [§5]:
     • kill_rule    → rule_proposer.approve_proposal
                       → mutates mini_scanner_rules.json
     • boost_promote→ append to mini_scanner_rules.json boost_patterns
     • boost_demote → auto-applied (read-only audit)
     • regime_alert / exposure_warn → informational
     • cohort_review→ triggers investigation
   → decisions_journal.json append
   [§4 Step 7 + §10 W5-S7]
                       ↓
   Next trading day 08:55 IST: bridge_premarket reads mutated
   mini_scanner_rules.json → bucket_engine evaluates with new rule
                       ↓
   Days later: outcomes accumulate in signal_history
   → next 22:00 brain run reads signal_history
   → cohort_health recomputes WR
   → if cohort drifts below tier (§3) → boost_demote auto-applied
   → LE-06 path fires demotion warning during EOD digest [7b96a97]
   → rule retires when cohort_health.tier drops to "Candidate"
   [§3 demotion path + §5 boost_demote routing]
```

**Integration gaps surfaced in this lifecycle:**

- `[INTEGRATION-GAP-1]` Bot username for deep-link target. `scanner/config.py` has `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` but no bot username. Tighter form `https://t.me/<bot_username>?text=...` blocked.
- `[INTEGRATION-GAP-2]` Rule conflict resolution. Brain proposing "demote DOWN_TRI×Bank kill" while trader already approved kill_001 — `decision_metadata: {}` open dict but no conflict path specified.
- `[INTEGRATION-GAP-3]` decisions_journal.json append cadence. Real-time per `/approve` vs nightly batch on next 22:00? Not specified.
- `[INTEGRATION-GAP-4]` M-12 false-DEGRADED propagating. Brain reads upstream_health → may receive false DEGRADED context; `decision_metadata.degraded_input` flag would mitigate but unspecified.
- `[INTEGRATION-GAP-5]` PWA → Telegram 10-min lag. `telegram_poll.yml` runs every 10 min; PWA-initiated `/approve` waits up to 10 min for pickup.

**Projection gaps surfaced:**

- `[PROJECTION-GAP-1]` diagnostic.yml future trigger (stays GitHub schedule? cron-job.org?).
- `[PROJECTION-GAP-2]` brain.yml workflow file. No `.yml` exists; trigger mechanism unspecified.
- `[PROJECTION-GAP-3]` brain disagreement detection logic. `§11 Q4` `[needs-verification]`.
- `[PROJECTION-GAP-4]` Brain weekend cadence (Mon-Sun vs Mon-Fri).
- `[PROJECTION-GAP-5]` exit_logic_redesign content. Doc doesn't exist; placeholder.

---

## Part 3 — Current component state

### 3.1 Scanner (`scanner/*.py`)

**Status:** SHIPPED stable; `recover_stuck_signals.py` import bug fixed today (`9d4dcb2`).
**Total:** 30 files, ~19,000 LOC.

**Detection + scoring:** `main.py` (1005), `scanner_core.py` (794), `scorer.py` (234), `mini_scanner.py` (579), `calendar_utils.py` (277).
**Persistence:** `journal.py` (994; prop_005 shadow_target wiring `550b5f0`), `outcome_evaluator.py` (1215; in-place shadow augmentation tonight), `backup_manager.py` (410), `eod_prices_writer.py` (521).
**Open positions / prices:** `open_validator.py` (488), `ltp_writer.py` (439), `stop_alert_writer.py` (849), `price_feed.py` (~250; H-07 PARTIAL).
**Intelligence loop (5 healthy per C-01..C-05 verified Apr-21):** `pattern_miner.py` (538), `chain_validator.py` (433), `contra_tracker.py` (357), `rule_proposer.py` (925), `weekly_intelligence.py` (485).
**Delivery:** `telegram_bot.py` (2232), bridge_telegram_premarket (530) / postopen (431) / eod (492), `push_sender.py` (336), `html_builder.py` (372).
**Recovery + diagnostic:** `recover_stuck_signals.py` (592), `diagnostic.py` (838), `deep_debugger.py` (859), `gap_report.py` (428).

**Known gaps (per fix_table):** H-06 sector taxonomy (PENDING), H-07 price_feed full adoption (PARTIAL), INV-01 DOWN_TRI live divergence (PARTIAL).

**Last meaningful change:** tonight commits `9d4dcb2` + `550b5f0`.

### 3.2 Bridge (`scanner/bridge/*`) — 32 files, ~4,800 LOC

**Status:** PARTIAL → effectively COMPLETE for backend. Three composers shipped; EOD verified end-to-end via tonight's manual dispatch.

#### 3.2.1 Bridge query plugin drift

**Reality vs design:** `bridge_design_v1.md §9.1` documents **7 background queries**. Live folder has **15 query plugins**. All shipped 2026-04-26. Doc never updated.

| Plugin | Add commit | Active dispatcher | One-line purpose |
|---|---|---|---|
| q_signal_today | `d606fb0` | composer (eod.py) | today's PENDING signals |
| q_open_positions | `992c648` | composer | currently-active 6-day-window positions |
| q_pattern_match | `755f9c0` | evidence_collector | supporting + opposing patterns |
| q_exact_cohort | `3274dc9` | evidence_collector | exact-cohort aggregate stats |
| q_sector_recent_30d | `b3bc01e` | evidence_collector | 30-day sector performance + trend |
| q_regime_baseline | `5c0e71a` | evidence_collector | per-regime baseline stats |
| q_score_bucket | `8a2667e` | evidence_collector | score-bucket historical WR |
| q_stock_recency | `f0177d9` | evidence_collector | per-symbol recent history |
| q_anti_pattern | `6fe35d3` | evidence_collector | strongest opposing pattern |
| q_cluster_check | `27392f6` | evidence_collector | Apr 6-8 style cluster warnings |
| q_boost_match | `a0a69f9` | evidence_collector | wraps boost_matcher |
| q_kill_match | `50933b0` | evidence_collector | wraps kill_matcher |
| q_gap_evaluation | `f4f590d` | evidence_collector | post-open gap evaluation |
| **q_outcome_today** | `52cdc5d` | **ORPHAN** (S-1 prereq) | EOD outcome lookup |
| **q_contra_status** | `ebab610` | **ORPHAN** (S-1 prereq) | contra-shadow status |
| **q_proposals_pending** | `c6b0160` | **ORPHAN** (no caller) | pending/approved proposals |

**Active count:** 13 of 15 dispatched. **Orphan count:** 3.

#### 3.2.2–3.2.5 Other bridge layers

**Core (8 files, ~1600 LOC):** sdr (115), bucket_engine (477), evidence_collector (258), state_writer (188), display_hints (175), upstream_health (162), error_handler (223).
**Composers (4 files, ~1985 LOC):** premarket (646; BR-02 SHIPPED), postopen (607; BR-03), eod (618; BR-04 Sessions A `c94e523` + B `19d4146` + C inside `7b96a97` + D `f9d4746`), `_history_reader.py` (114).
**Rules (5 files, ~478 LOC):** thresholds (84), boost_matcher (110), kill_matcher (109), validity_checker (68), watch_matcher (107; Phase 1 `034d4f5`).
**Entry point:** `bridge.py` (330).

**Last meaningful change:** tonight commits `7b96a97`, `c647e94`, `f9d4746`, `a5edc32`.

### 3.3 Brain (`scanner/brain/*`) — Wave 5 Steps 1-2 SHIPPED

**Status:** PARTIAL — Step 1 (`720c127`) + Step 2 (`060d7c9`) shipped tonight.

| File | LOC | Status | Step |
|---|---|---|---|
| `__init__.py` | 1 | shipped | 2 |
| `brain_cli.py` | 26 | shipped (argparse stub) | 2 |
| `brain_input.py` | 10 | shipped (`load_truth_files()` returns `{}`) | 2; **Step 3 fills** |
| `brain_state.py` | 5 | shipped (docstring only) | 2; **Step 3 fills** |
| `brain_derive.py` | 5 | shipped (docstring only) | 2; **Step 3 fills** |
| `brain_verify.py` | 5 | shipped (docstring only) | 2; Step 4 |
| `brain_reason.py` | 5 | shipped (docstring only) | 2; Step 5 |
| `brain_output.py` | 5 | shipped (docstring only) | 2; Step 6 |
| `brain_telegram.py` | 5 | shipped (docstring only) | 2; Step 7 |
| **Total** | **67** | | |

**Output directory:** `output/brain/` does NOT yet exist. Step 3 first write creates it.

**Prereqs status:** B-1 ✓ (manual; scheduled-tick pending), B-2 ✓ (`10a3fb5`), B-3 ✓ (`d6ddc01`), B-4 ✓ (`720c127`). S-1/S-2/S-3/S-4 PENDING; S-5 ✓ (`7b96a97`).

### 3.4 PWA (`output/*.html`, `*.js`, `analysis/`)

**Status:** SHIPPED stable; reads raw signal data (NOT bridge_state, NOT brain — both deferred to Wave UI).

**Files:** `index.html` (CACHE-01 SHIPPED), `app.js`, `journal.js`, `analysis.html` + `analysis.js` (parent) + `analysis/{advanced,overview,post_mortem,segmentation,signals}.js` (5 plugin views), `manifest.json`, `sw.js`.

**Bottom nav:** Signals · Journal · Stats · Help (per `output/ui.js:1395-1397`).
**Fetches** (`app.js:202-211`): meta, scan_log, mini_log, signal_history, open_prices, eod_prices, stop_alerts, nse_holidays, banned_stocks, ltp_prices. **Does NOT fetch bridge_state.json** (verified via grep tonight `3650f57`).

**Known gaps (Wave UI):** GAP-14, 15, 16, 17, 18, 30; IT-01..IT-06 all PENDING; LE-05 deferred (paired with IT-05 per `0512cd2`).

**Last meaningful PWA change:** `3650f57` (GAP-13 reclass — read-only verification).

### 3.5 Telegram bot (`scanner/telegram_bot.py` 2232 LOC)

**Status:** SHIPPED stable; canonical `_esc` consolidated via Wave 5.1 M-08 migration; poll concurrency hardened TG-01 Apr-26.

**Commands:** `/today`, `/exits`, `/pnl`, `/stops`, `/signals`, `/health`, `/help`, `/proposals`, `/approve_rule prop_NNN`, `/reject_rule prop_NNN [reason]` (LE-07 SHIPPED `c43189a`).

**Concurrency:** `concurrency: group: telegram-poll, cancel-in-progress: false` (TG-01 `14423fb`).

**Renderers:** bridge_telegram_premarket (L1), bridge_telegram_postopen (L2 conditional), bridge_telegram_eod (L4; fired today via manual eod.yml at 19:01 IST). Plus legacy `main.py eod` (UX-03 territory).

**Known gaps:** LE-05 DEFERRED (Wave UI), UX-03 retirement priority elevated, LE-04 PENDING Wave 5.

### 3.6 Workflow infrastructure (`.github/workflows/*.yml`)

**Status:** 25 YAMLs; tonight's eod.yml migration (`2fc1f35`) returned eod.yml to cron-job.org (so 14→13→14 cycles, plus orphan brain.yml not yet built).

**Current trigger families:**
1. **GitHub native schedule:** heartbeat (8:30 weekday), backup_manager (Sat 8:30), gap_report (Mon 8:30), weekend_summary (Sat 9:00), weekly_intelligence (Sun 20:00), colab_sync (16:15 weekday), diagnostic (16:30 weekday).
2. **cron-job.org workflow_dispatch:** morning_scan, scan_watchdog, premarket, open_validate, postopen, ltp_updater, stop_check, eod_master, eod (post-migration), telegram_poll.
3. **Manual workflow_dispatch only:** deep_debugger, master_check, register_push, recover_stuck_signals, wave2, wave5_m08.
4. **Push-triggered:** deploy_pages, rebuild_html.

**Concurrency groups:** `bridge-eod`, `bridge-postopen`, `bridge-premarket`, `telegram-poll`.

**Known gaps:** GAP-04 PARTIAL → reverted to UNCHANGED HIGH post `2fc1f35` (see Part 6 drift); M-12 chain step ordering; M-14 collision (mooted post-migration on eod side); ltp_updater no concurrency (GAP-10).

### 3.7 Documentation layer (`doc/*.md`)

**13 docs, 4,813 LOC.** Health: mostly current; 3 stale, 1 missing.

**Load-bearing (current):** bridge_design_v1 (1494; §13.4 amended tonight `2fc1f35`), brain_design_v1 (490; amended tonight `c278a32`), master_audit_2026-04-27 (991; HIGH 5 post `9336b32`), fix_table (696; 6 commits today), wave5_prerequisites_2026-04-27 (188), reconciliation_ritual (124; load-bearing P-01 process).

**Stale (Part 6 drift report):** session_context (313; resume-point stale post-eod migration), roadmap (77; 10 days behind reality), engineering_dock (260; claims "5 critical incidents" all resolved Apr-21).

**Missing:** `doc/exit_logic_redesign_v1.md` referenced 3× but doesn't exist.

### 3.8 Smoke + test infrastructure (`scripts/*`)

**Status:** mature for shipped components; CLAUDE.md §4 sandbox pattern established.

**Existing runners:** `scripts/analyze_full.py`, `scripts/wave2_migration.py`, `scripts/wave5_m08_migration.py`, `scripts/test_anthropic_api.py` (B-3, `d6ddc01`).

**Master Check:** Tier 1 (syntax, 25 files), Tier 2 (imports, 15 modules), Tier 3 (runtime, 13 inline checks). Manual-only; not visible in today's git log (Part 6 drift entry).

**Known gaps:** `verify_fixes.py` planned never built; `AICREDITS_API_KEY` not set; `jsonschema` library NOT installed (Step 3 inline assertions per spec fallback).

---

## Part 4 — Target component state (post Wave 5 + UI wave)

### 4.1 Scanner — UX-03 retirement + brain integration touchpoints

**Status:** SHIPPED stable; brain integration touchpoints added.

**Deltas from current Part 3.1:**

| Component | Current state (Part 3.1) | Target state | Source citation |
|---|---|---|---|
| `main.py` step `eod` (lines unknown — 1005 LOC orchestrator) | Telegram step inside step 2-4/8 fires "📊 EOD" + 61-signal "EXIT TOMORROW" preview at 15:36 IST | **Telegram step REMOVED.** Computational steps (outcome_evaluator + eod_prices + chain_validator + pattern_miner + rule_proposer) retained. Step name renamed to `eod-compute` to reflect non-Telegram scope. | `fix_table BR-04` Status update from commit `51448e8` ("UX-03 retirement priority elevated"); `master_audit GAP-22` partial closure path |
| `outcome_evaluator.py` (1215) | Resolution writer; prop_005 in-place shadow augmentation | unchanged | `brain_design §1 constraint 2` (read-only over truth files) — outcome_evaluator stays canonical writer |
| `journal.py` (994) | signal_history.json writer + prop_005 shadow_target wiring | unchanged | per design |
| `recover_stuck_signals.py` (592) | Manual-only via workflow_dispatch; fixed today commit `9d4dcb2` | unchanged unless M-13 audit (D-7) surfaces underlying outcome-pipeline issue requiring touch | `fix_table M-13` |
| `price_feed.py` (~250) | H-07 PARTIAL — only ltp_writer migrated | Either H-07 fully resolved OR explicitly accepted as Wave 6+ scope. Other readers (scanner_core, eod_prices_writer) still hit yfinance directly. | `fix_table H-07` (PENDING) |
| `calendar_utils.py` (277) | Canonical IST helpers since Wave 2 migration `c312316` (2026-04-23) | unchanged | per design |
| `scanner_core.py` / `scorer.py` / `mini_scanner.py` | 3 signals + scoring + shadow filter | unchanged | brain proposes rule changes via `rule_proposer.approve_proposal` adapter; brain never modifies signal generation |

**M-16 resolution by removal:** legacy `main.py eod` Telegram step computed open-positions count via `outcome=='OPEN'` filter (105 raw); removal of Telegram step removes the 94-vs-80 discrepancy at the user-visible layer (per `fix_table M-16`). Internal data unchanged; bridge L4 `summary.open_positions_count: 80` becomes the only count visible.

**No new files in `scanner/` root.** Brain lives in `scanner/brain/` sub-package per Part 4.3.

### 4.2 Bridge — orphan cleanup + minor schema enforcement

**Status:** SHIPPED COMPLETE; query plugin orphan disposition + S-3 validation.

**Deltas from current Part 3.2:**

| Component | Current state (Part 3.2) | Target state | Source citation |
|---|---|---|---|
| `bridge/queries/q_outcome_today.py` (32 LOC; ORPHAN — `_select_resolutions_today` inline in eod.py:230) | Wave 3 stub; not called | Either composer migrates (S-1 closes — eod.py:230 calls plugin) OR plugin removed `[PROJECTION-GAP-6]` | `wave5_prerequisites_2026-04-27.md S-1` (PENDING) |
| `bridge/queries/q_contra_status.py` (139 LOC; ORPHAN — `_build_contra_block` inline in premarket.py:430) | Stub; not called | Either composer migrates (S-1) OR removed | `wave5_prerequisites_2026-04-27.md S-1` |
| `bridge/queries/q_proposals_pending.py` (82 LOC; ORPHAN — no caller) | Stub; no consumer in scanner/ | **Removed** as confirmed dead code OR explicit consumer added during brain Step 5+ design (LLM gate may want pending-proposals context) | `[PROJECTION-GAP-6]` — design docs don't lock |
| `bridge/core/state_writer.py` (188) — `_validate_state` | Validates schema_version + phase + phase_timestamp + market_date | **S-3 expansion:** per-phase `signals[]` shape validation. EOD plain-dict SDR vs L1/L2 dataclass divergence enforced at write time so brain doesn't have to defensively handle every variation. | `wave5_prerequisites_2026-04-27.md S-3` (PENDING; advisory not blocking Step 3 since brain reads defensively) |
| `bridge/core/sdr.py` (115) | Single SDR dataclass | **Either:** (a) separate `EODSDR` dataclass for EOD plain-dict shape OR (b) accept divergence + document. S-3 decision pending. | `S-3` cross-ref |
| `bridge_design_v1.md §9.1` (the 7-query inventory) | Lists 7 background queries (drift) | Updated to reflect 12 active plugins (post-orphan-removal) OR 15 plugins (post-S-1-migration) | Part 6.2 drift report recommendation |
| `composers/premarket.py` (646), `composers/postopen.py` (607), `composers/eod.py` (618) | All shipped | unchanged unless S-1 migration adds plugin imports | per design |
| `bridge.py` (330) — orchestrator | shipped | unchanged | per design |
| `bridge_state.json` schema_version = 1 | shipped | unchanged | `bridge_design §10` schema definition |

**Bridge is feature-complete post Wave 3 closure tonight. No new bridge code expected; only cleanup + documentation alignment.**

### 4.5 Telegram bot — UX-03 retired + W5-S7 commands + W6 alias removal

**Status:** SHIPPED stable; multiple deprecation paths complete.

**Deltas from current Part 3.5 — explicit phase-by-phase per `brain_design §10` migration table:**

| Phase | Change | Status post-Wave-5 + UI wave | Source citation |
|---|---|---|---|
| **W5-S6** (Brain Step 6) | `rule_proposer.py` dual-writes: legacy `proposed_rules.json` + new `unified_proposals.json` | SHIPPED — unified queue is canonical for *display* and *new approvals*; legacy `proposed_rules.json` is canonical *execution path* for kill_rule type | `brain_design §10 W5-S6` |
| **W5-S7** (Brain Step 7) | New `/approve <unified_id>` and `/reject <unified_id> [reason]` route via `_respond_approve` (post W5-S7); legacy `/approve_rule` + `/reject_rule` print "deprecated; use /approve <unified_id>" + still execute | SHIPPED — both work; help text marks legacy deprecated | `brain_design §4 Step 7 + §10 W5-S7` |
| **W5+30** (30 days post-S7) | Telegram bot logs deprecation warning every time legacy command fires | SHIPPED — observable deprecation pressure | `brain_design §10 W5+30` |
| **W6** (post Wave 6 stabilization) | Remove legacy `/approve_rule` + `/reject_rule` aliases entirely | `[PROJECTION-GAP-7]` — only ships if Wave 6 stabilization criteria met; design doc doesn't lock criteria | `brain_design §10 W6` |
| **UX-03** (independent of Brain) | `main.py eod` Telegram step removed | SHIPPED — single EOD digest path = `bridge_telegram_eod.py` | `fix_table BR-04` Status update from commit `51448e8` |
| **LE-04** (Wave 5 LE-series) | `/approve_query Q-NNN` + `/reject_query Q-NNN` Telegram commands | SHIPPED concurrent with Brain Step 5 (LE-02 → query proposals enter the unified queue) | `fix_table LE-04` (PENDING currently) |
| **LE-05 deep-link form** | PWA Monster tab uses either `tg://msg?text=/approve%20<id>` (3-tap UX) OR `https://t.me/<bot_username>?text=...` (2-tap; requires bot username added to config per D-1) | `[INTEGRATION-GAP-1]` — depends on D-1 decision in Part 7 | `fix_table LE-05` + Part 7 D-1 |
| **Brain digest at 22:06 IST** | `brain_telegram.py` sends nightly batch (top-3 proposals) | SHIPPED via brain.yml chain step at 22:06 IST | `brain_design §2 line 76 + §8` |

**Single source of EOD digest:** `bridge_telegram_eod.py` (492 LOC). Section-driven template per `bridge_design §12.3`. Legacy path retired. **Phase 1 anomaly #5 resolved.**

**M-16 resolution at user-visible layer:** legacy "Open: 94" digest no longer fires; trader sees only bridge L4 `summary.open_positions_count: 80` (6-day-window filter). **Phase 1 M-16 resolved by absence.**

### 4.3 Brain — Wave 5 Steps 1-7 SHIPPED

| Step | LOC | Output | Cite |
|---|---|---|---|
| 1 ✓ | 600 | doc | `720c127` |
| 2 ✓ | 80 | scaffold | `060d7c9` |
| 3 | 800 (spec) / ~430-500 (audit) | output/brain/cohort_health + regime_watch + portfolio_exposure + ground_truth_gaps | `§4 Step 3` |
| 4 | 250 | candidates | `§4 Step 4 + §6` |
| 5 | 600 | reasoning_log.json | `§4 Step 5 + §1.4 + §11 Q1/Q2` |
| 6 | 350 | unified_proposals + decisions_journal | `§4 Step 6 + §5 + §10 W5-S6` |
| 7 | 200 | telegram_bot mods | `§4 Step 7 + §10 W5-S7` |
| 8 | (Wave UI) | output/monster.js | deferred per `§4 Step 8` |

**brain_cli.py Tier 1 functional:** status / rules / explain / trace per `§7`.

### 4.4 PWA — UI wave shipped

All IT-01..IT-06 done per `fix_table TIER 4` + `bridge_design §11`. GAP-14, 15, 16, 17, 18, 30 closed. `[INTEGRATION-GAP-1]` 3-tap UX persists unless bot username added.

### 4.5 Telegram bot — UX-03 retired

Single EOD digest path. W5-S7 commands (`/approve`, `/reject`) routed via brain_output.dispatch. M-16 resolution: only bridge L4 count visible.

### 4.6 Workflow infrastructure

**`brain.yml` (NEW)** `[PROJECTION-GAP-2]`. eod.yml unchanged from tonight. **colab_sync + diagnostic** `[PROJECTION-GAP-1]` may migrate to cron-job.org. **eod_master step ordering (M-12 fix)** chain_validator moved post-mining.

**`[PROJECTION-GAP-10]`** S-4 cron-job.org failover playbook ship target — promoted to Part 7 decision item per spec Addition 2.

### 4.7 Documentation layer

| Doc | Future state |
|---|---|
| engineering_dock.md | RETIRED or absorbed |
| roadmap.md | REFRESHED |
| session_context.md | CURRENT (refreshed end-of-session) |
| exit_logic_redesign_v1.md | DRAFTED OR REJECTED `[PROJECTION-GAP-5]` |
| brain_design_v1.md | Step 3 schemas annotated |
| bridge_design_v1.md | §11.1 marked SHIPPED post Wave UI |
| master_audit_2026-04-27.md | Severity tally updated as HIGH gaps close |
| wave5_prerequisites_2026-04-27.md | All B/S items RESOLVED |
| fix_table.md | All PENDING resolved or migrated to CLOSED |

### 4.8 Smoke + test infrastructure

Per-step smoke runners shipped (`_run_smoke_brain_step3.py` through `step7.py`). `jsonschema` installed. `master_check.yml` discipline `[PROJECTION-GAP-8]` either restored OR explicitly relaxed in CLAUDE.md. `verify_fixes.py` `[PROJECTION-GAP-9]` either built OR cancelled.

---

## Part 5 — Gap inventory (status as of 2026-04-28 19:30 IST)

### 5.1 HIGH gaps (master_audit, post tonight's GAP-33 RESOLVED)

| ID | Severity | Description | Status post-tonight | Wave | Closure path |
|---|---|---|---|---|---|
| GAP-01 | HIGH | signal_history multi-writer race | PENDING | Wave 6+ | fcntl-based locks OR single-writer queue |
| GAP-04 | HIGH | cron-job.org SPOF (now ~14 workflows) | **PARTIAL annotation in master_audit is STALE post tonight's `2fc1f35`** — see Part 6 drift | Wave 7+ | S-4 failover playbook (Part 7 decision item) |
| GAP-14 | HIGH | PWA doesn't read bridge_state.json | PENDING | Wave UI / IT-01 | IT-01 ship |
| GAP-21 | HIGH | No cross-signal correlation awareness | PENDING (PARTIAL via brain Step 3 portfolio_exposure when Step 3 ships) | Wave 5 | Brain Step 3+5+6 chain |
| GAP-22 | HIGH | No learning-loop surface | PENDING (PARTIAL via brain Step 3 cohort_health when Step 3 ships) | Wave 5 | Brain Step 3+5+6 chain |

### 5.2 M-series (10 numbered items per git history)

| ID | Status | Source / commit |
|---|---|---|
| M-05 | ✓ SHIPPED 2026-04-25 | `chain_validator extended coverage` (per fix_table CLOSED HISTORICAL) |
| M-06 | (historical, per Wave 2 commit log) | not currently tracked open |
| M-07 | (historical) | not currently tracked open |
| M-08 | ✓ SHIPPED via Wave 5.1 `_esc` consolidation (`scripts/wave5_m08_migration.py`) | per `wave5_m08_log_20260423_024400.md` |
| M-11 | ✓ SHIPPED Apr-21 Session A | per fix_table change-log |
| M-12 | PENDING (LOW) — chain_validator step ordering | filed today `ddd66b7` |
| M-13 | PENDING (LOW) — OPEN-with-outcome_date schema oddity | filed today `ddd66b7` |
| M-14 | PENDING (LOW) — eod.yml + colab_sync collision; mooted on eod side post-migration | filed today `10a3fb5` |
| M-15 | ✅ RESOLVED via `2fc1f35` — eod.yml migrated to cron-job.org | filed `51448e8`, resolved `2fc1f35` |
| M-16 | PENDING (LOW) — open-positions count discrepancy 94 vs 80 | filed today `51448e8` |

### 5.3 Wave 5 prerequisites

| ID | Status | Commit / source |
|---|---|---|
| B-1 (eod.yml) | ✅ workflow-logic verified manual dispatch (`a5edc32`); scheduled-tick verification pending tomorrow's first cron-job.org-dispatched fire post `2fc1f35` |
| B-2 (cron-job.org TG-01) | ✅ verified `10a3fb5` |
| B-3 (Anthropic SDK + key) | ✅ shipped `d6ddc01` |
| B-4 (Brain Step 1 doc lock) | ✅ shipped `720c127` |
| S-1 (q_outcome_today + q_contra_status dedup) | PENDING — advisory not blocking Step 3 |
| S-2 (renderer escape grep L1/L2) | PENDING |
| S-3 (state_writer per-phase signals[] validation) | PENDING — advisory |
| S-4 (cron-job.org failover playbook) | PENDING — **promoted to Part 7 decision item** |
| S-5 (LE-06 demotion framework) | ✅ shipped `7b96a97` |
| N-9 (ex B-2: GAP-13 PWA EOD-phase guard) | DEFERRED to Wave UI / IT-01 (closed by reclassification `3650f57`) |

### 5.4 UI wave items (per `fix_table TIER 4`)

| ID | Status | Wave |
|---|---|---|
| IT-01 PWA plugin folder + bridge_state fetch | PENDING | Wave UI |
| IT-02 Phase-aware UI banner | PENDING | Wave UI |
| IT-03 Sorted signal card renderer | PENDING | Wave UI |
| IT-04 Expandable [why?] reasoning | PENDING | Wave UI |
| IT-05 Proposal approval card (LE-05 paired) | PENDING | Wave UI |
| IT-06 Self-query disclosure card | PENDING | Wave UI |

### 5.5 Cross-cutting items

- **GAP-04 PARTIAL** annotation drift: master_audit `9336b32` annotated PARTIAL based on eod.yml→GitHub-schedule. Tonight's `2fc1f35` reversed the move. master_audit GAP-04 PARTIAL annotation is now stale (see Part 6.1).
- **GAP-13 LOW** closed by `3650f57` reclass + N-9 deferral.
- **GAP-21 / GAP-22 partial** via brain Step 3 + 5 + 6 chain (see Part 5.1 above).
- **prop_001 DOWN_TRI restriction** DEFERRED — gates on Apr 27-29 Choppy DOWN_TRI resolutions. Today (Apr 28) had 1 DOWN_TRI×Choppy MARUTI signal that fired this morning per `2026-04-28_PRE_MARKET.json` (will resolve Day 6 = 2026-05-06 unless TARGET/STOP hits earlier). Other 2 Choppy DOWN_TRIs (LUPIN/OIL/ONGC per session_context) still pending.
- **prop_005** SHIPPED tonight (`550b5f0`); reframed parallel-shadow infrastructure (NOT R-multiple solver). `TARGET_R_MULTIPLE_SHADOW = 3.0` constant added; shadow_target / shadow_outcome / shadow_r_multiple fields on every new V6 signal. Forward-only — pre-prop_005 records do not carry shadow fields.
- **prop_007** SHIPPED tonight (`c647e94`); boost demotion proposals via `rule_proposer._detect_boost_demotion_candidates` set INTERSECTION (not union) semantics. First fire earliest 2026-04-30 due to 3-day streak requirement.
- **LE-05** DEFERRED to Wave UI (paired with IT-05 per `0512cd2`). `[INTEGRATION-GAP-1]` Bot username decision pending (Part 7 D-1).
- **LE-06** SHIPPED tonight (`7b96a97`); rolling-window WR per boost_pattern → `state.summary.pattern_updates`. First production fire today: empty (81% baseline well above 70% LE-06 demotion floor — code path verified by absence-of-fire).
- **LE-07** SHIPPED 2026-04-26 (`c43189a`); `/reject_rule prop_NNN [reason]` Telegram command.
- **`output/health.html` + `health_report.json` + `health-icon-*.png`** — mtimes 25 Apr (Saturday Apr-25 ship). Part 1 anomaly #11 — likely static assets (icons, last-good HTML snapshot) + diagnostic.yml output (Telegram-only on success; HTML written only on weekly cycle). Not load-bearing today.
- **`output/weekly_intelligence_latest.json` mtime 26 Apr** — Sunday's `weekly_intelligence.yml` 20:00 IST run. 2 days behind today. Brain Step 3 `regime_watch.json` will read this and report `weekly_intelligence_age_days` so consumers see freshness (per Step 3 design D-2 spec).
- **`output/bridge_state_history/2026-04-26_PRE_MARKET.json`** at 1007 bytes (vs 201KB trading-day archives). Sunday Apr-26 shouldn't have fired premarket. File worth reading to determine: manual workflow_dispatch test? degraded-state archive? Phase 6 drift item (low priority).

---

## Part 6 — Drift report

**14 PROJECTION/INTEGRATION gaps from Phase 3 surfaced explicitly. Plus 7 specific drift items below.**

### 6.1 master_audit GAP-04 PARTIAL annotation stale

`doc/master_audit_2026-04-27.md:1196` (`Status update 2026-04-28 (GAP-04)`) annotated PARTIAL based on eod.yml→GitHub-schedule per `f9d4746`. Tonight's `2fc1f35` reversed the move (eod.yml back on cron-job.org). master_audit was not re-amended after `2fc1f35`. **Drift: real. Fix: re-amend master_audit GAP-04 with reversal note + revert PARTIAL to UNCHANGED HIGH.** Recommend during end-of-session batch closeout.

### 6.2 Bridge query plugin drift (Phase 1 anomaly #1)

`bridge_design_v1.md §9.1` documents 7 queries; reality is 15 plugins (13 active, 3 orphan). master_audit + fix_table claim "Wave 2 shipped 3 plugins"; reality all 15 shipped same day Apr-26. **Recommendations:**
- Update `bridge_design_v1.md §9.1` to reflect 15 plugins
- File S-1 prereq cleanup (q_outcome_today + q_contra_status dedup) OR remove orphan plugins
- q_proposals_pending: no caller anywhere; remove or document intended consumer

### 6.3 engineering_dock.md staleness recommendation

`doc/engineering_dock.md:13` claims "Last ship: 2026-04-20" + "5 critical incidents (C-01..C-05)". All C-series VERIFIED Apr-21 per master_audit. Doc effectively superseded by fix_table + master_audit + session_context. **Recommendation: retire (delete) OR convert to historical-only with retirement note at top + redirect pointer to current docs.** Decision in Part 7.

### 6.4 session_context.md staleness

Resume-point block last refreshed `cbdef3d` (early today); does not yet reflect tonight's eod migration `2fc1f35` + Step 2 ship `060d7c9`. **Recommendation: refresh during end-of-session batch closeout.** Standard practice already established.

### 6.5 roadmap.md staleness

`doc/roadmap.md` last_updated 2026-04-19 (10 days behind). Phase descriptions don't reflect Wave 1-4 closure. **Recommendation: refresh during end-of-session batch closeout.**

### 6.6 master_check discipline drift (per spec Addition 3)

CLAUDE.md says "After each code change: run Master Check → confirm green." Today (2026-04-28) shipped 14 meaningful commits without master_check evidence in git log. **Drift: real. Decision options:** (a) restore rule with stricter enforcement (pre-push git hook); (b) relax CLAUDE.md spec to "ship-cycle smokes substitute for master_check" matching observed practice; (c) keep documented but acknowledge violation with tracking. **Decision in Part 7.**

### 6.7 fix_table headline-vs-annotation pattern (Phase 1 anomaly #6)

fix_table convention: when an item RESOLVES via a Status update annotation, the headline `**Status:**` line stays at original PENDING/PARTIAL value; resolution captured only in subsequent annotation block. Means casual `grep "Status:.*PENDING"` overcounts PENDING items (M-15 RESOLVED today via `2fc1f35` but headline still says PENDING). **Question: convention change or stay?** If stay, document the convention in a fix_table preamble so readers know to scan for Status update blocks. **Decision in Part 7.**

### 6.8 patterns.json vs signal_history count gap (Phase 1 anomaly #10)

`patterns.json total_resolved_signals: 161` vs `signal_history.history` non-OPEN count = 181. 20-record gap from M-13 (8 OPEN-with-outcome_date oddity) + ~12 late-arriving resolutions post-Apr-27 chain. **Recommendation: document authoritative count rule** — patterns.json count is "resolved signals processed by pattern_miner at last chain run"; signal_history count is "all non-OPEN records as of read time including post-chain resolutions." Brain Step 3 uses signal_history directly per Step 3 design audit. Ship as inline comment in `derive_cohort_health` docstring.

### 6.9 14 PROJECTION/INTEGRATION-GAPs surfaced in Phase 3

Listed for traceability:

| ID | Type | Description | File reference |
|---|---|---|---|
| PROJECTION-GAP-1 | Future-state | diagnostic.yml future trigger (GitHub schedule vs cron-job.org) | Part 2.1 row |
| PROJECTION-GAP-2 | Future-state | brain.yml workflow file unspecified | Part 2.1 row + Part 4.6 |
| PROJECTION-GAP-3 | Future-state | brain disagreement detection logic | `§11 Q4 [needs-verification]` |
| PROJECTION-GAP-4 | Future-state | brain weekend cadence | Part 2.2 |
| PROJECTION-GAP-5 | Future-state | exit_logic_redesign content | Part 4.7 |
| PROJECTION-GAP-6 | Future-state | bridge orphan plugin disposition | Part 4.2 |
| PROJECTION-GAP-7 | Future-state | W6 deprecation timing | Part 4.5 |
| PROJECTION-GAP-8 | Future-state | master_check discipline restoration vs relaxation | Part 4.8 |
| PROJECTION-GAP-9 | Future-state | verify_fixes.py / .yml ship vs cancel | Part 4.8 |
| PROJECTION-GAP-10 | Future-state | S-4 cron-job.org failover playbook ship target | Part 4.6 |
| INTEGRATION-GAP-1 | Cross-system | Bot username for deep-link tightening | Part 2.3 + scanner/config.py |
| INTEGRATION-GAP-2 | Cross-system | Rule conflict resolution (brain proposal vs already-approved kill) | Part 2.3 + brain_design §5 |
| INTEGRATION-GAP-3 | Cross-system | decisions_journal.json append cadence | Part 2.3 + brain_design §2 |
| INTEGRATION-GAP-4 | Cross-system | M-12 false-DEGRADED propagating to brain reasoning | Part 2.3 + brain_design §11 Q5 |
| INTEGRATION-GAP-5 | Cross-system | PWA → Telegram 10-min lag | Part 2.3 + telegram_poll.yml |

---

## Part 7 — Decision log forward-looking

### 7.1 Promoted from Phase 3 (per spec Addition 1)

**D-1. INTEGRATION-GAP-1 — Bot username for deep-link tightening.**
- **Action:** Add `TELEGRAM_BOT_USERNAME` constant to `scanner/config.py`; LE-05 implementation uses `https://t.me/<bot_username>?text=/approve%20<id>` form.
- **Blocking:** Wave UI / IT-05 ship cleanly — without resolution, IT-05 ships with 3-tap share-picker UX.
- **Schedule:** Not blocking Step 3-7 brain backend; resolve concurrent with IT-05 design pass.
- **Decision options:** (a) accept 3-tap UX (`tg://msg?text=...` opens share picker; user picks bot chat then taps Send — 2 extra taps); (b) add bot username + use `https://t.me/...` form (2-tap UX: tap PWA approve → Telegram opens bot chat with text pre-filled → tap Send).
- **Recommendation:** (b) — 2-tap UX is materially better for trader cadence (nightly review, may approve 0-3 proposals per session); ~10 LOC config change + ~5 LOC LE-05 implementation. Bot username is non-secret; safe for `config.py` (no `.env` needed).
- **Cost of wrong call:** minor — UX friction only; not safety-critical. Wrong call = 3-tap UX persists; trader experiences mild annoyance for life of LE-05 path until W6 deprecation.

**D-2. INTEGRATION-GAP-2 — Rule conflict resolution (brain proposal vs approved kill rule).**
- **Action:** `brain_design_v1.md §5` needs amendment with conflict-handling path. Schema's open dict `decision_metadata: {}` allows extension but no semantics specified.
- **Blocking:** Step 6 ship. Brain proposing actions that conflict with active rules must be detected before `unified_proposals.json` finalize, or trader sees nonsensical proposals.
- **Schedule:** Resolve before Step 6 design pass (concurrent with Step 5 LLM gates audit, since gates may want conflict context).
- **Decision options:** (a) brain auto-suppresses conflicting proposals + logs to `cohort_review` type for visibility but no action; (b) brain surfaces conflict explicitly in `claim.counter` field for trader awareness, proposal still enters queue; (c) brain proposes both with `decision_metadata.conflicts_with: <kill_id>` flag, trader sees both + chooses.
- **Recommendation:** (b) — surfacing conflicts in `claim.counter` aligns with §6 "honest pre-verification" principle; trader sees the conflict + makes informed decision. (a) hides information; (c) over-loads queue. (b) is information-conserving + minimal-friction.
- **Cost of wrong call:** brain proposing trade actions that contradict active kill rules = trader confusion + risk of double-execution if both paths fire (e.g., kill_001 active + brain proposes "promote DOWN_TRI×Bank" → trader approves brain proposal not realizing conflict → both rules contradict at next morning_scan). Real safety risk.

**D-3. INTEGRATION-GAP-4 — M-12 false-DEGRADED propagating to brain reasoning.**
- **Action:** Two paths: (a) M-12 fix lands first — `chain_validator` step reorder in `eod_master.yml` (move from step 6 to step 9, post-mining); (b) `brain_reason.py` adds explicit `degraded_input_ignore: ['system_health.warn']` flag during gate execution.
- **Blocking:** Step 5 ship cleanly. Brain's LLM gates read `bridge_state_history.upstream_health` propagated from `system_health.json`; M-12 false-positive DEGRADED labels may distort reasoning.
- **Schedule:** M-12 fix is pure workflow YAML edit (~30-60 min audit + ship); ideally lands before Step 5 design pass.
- **Decision options:** (a) M-12 fix first (cleaner — false positive eliminated at source); (b) brain ignore-flag (workaround — M-12 stays as is, brain handles defensively).
- **Recommendation:** (a) — M-12 is pure workflow YAML edit, low risk, broad benefit (L1 brief + L4 digest + brain all stop seeing false DEGRADED). Workaround in brain leaves the L1/L4 false-DEGRADED label visible to trader (today's digest reads "PROVISIONAL — partial data" when data is actually fresh).
- **Cost of wrong call:** brain LLM gates reason over false DEGRADED context → may suppress proposals that should fire ("don't propose during degraded periods"), or surface phantom degradation alerts to trader. Direct LLM-cost-and-quality concern.

**D-4. PROJECTION-GAP-4 — Brain weekend cadence.**
- **Action:** Lock Mon-Sun daily run vs Mon-Fri only in `brain.yml` cron + `brain_design §2` daily-cycle annotation.
- **Blocking:** Step 6 + 7 ship. `decisions_journal.json` append cadence depends on whether brain runs on days following weekends; design doc doesn't lock.
- **Schedule:** Resolve before Step 6 design pass.
- **Decision options:** (a) **Mon-Sun daily** — brain runs every day at 22:00 IST; weekend runs read stable-by-design Friday-EOD inputs; nightly digest may be empty; `_metadata.warnings` flags staleness; (b) **Mon-Fri only** — brain skips weekends entirely; Monday's run reads Friday-EOD (3-day stale); `weekly_intelligence_latest.json` (Sunday 20:00) only consumed Monday onward.
- **Recommendation:** (a) — daily runs preserve brain's "runs nightly" invariant (§2). Saturday/Sunday runs produce empty or near-empty digests that quietly update `_metadata.warnings: ["no fresh trading day since <date>"]`. Simpler than gating cron + clearer audit trail (decisions_journal has entries every night).
- **Cost of wrong call:** wrong cadence creates inconsistency between cron schedule + decisions_journal expected daily presence. If (b) chosen but weekly_intelligence updates Sunday and brain doesn't read it until Monday, regime_watch view's freshness window has unexplained gap. (a) avoids the gap.

### 7.2 S-4 cron-job.org failover playbook (per spec Addition 2)

**D-5. S-4 ship target.**
- **Action:** Doc-only deliverable `wave5_prerequisites_2026-04-27.md S-4` — failover steps for manually triggering 14+ cron-job.org workflows when service is down. Lists: GitHub Actions UI workflow_dispatch URL per workflow, expected sequencing per CLAUDE.md daily flow, telegram notification fallback if morning_scan misses.
- **Blocking:** Wave 5 Step 6/7 ship cleanly. 16-workflow SPOF post brain.yml addition is operationally heavier than today's 14-workflow concentration.
- **Schedule:** Concurrent with Step 6/7 OR before brain.yml goes live. Not blocking Step 3-5.
- **Decision options:** (a) ship pre-brain.yml (proactive); (b) ship post-brain.yml (reactive — wait for first cron-job.org outage to motivate); (c) skip entirely (accept SPOF risk).
- **Recommendation:** (a) — 16-workflow SPOF is real risk. M-15 evidence (3-of-3 GitHub schedule miss tonight) elevated cron-job.org load-bearing-ness. Ship before brain.yml so failover playbook exists when brain becomes critical.
- **Cost of wrong call:** cron-job.org outage takes out 16 workflows simultaneously without manual playbook = worst-case total system downtime for the trading day. Trader has no Telegram alerts, no PWA bridge state updates, no LTP/stop monitoring. **Highest-impact decision in this list.**

### 7.3 master_check discipline (per spec Addition 3)

**D-6. master_check.yml discipline decision.**
- **Action:** Pick one of three options + update CLAUDE.md to match.
- **Blocking:** Nothing immediate; decision shapes ship discipline going forward.
- **Schedule:** Resolve at end-of-week (Sunday Apr-27) decision boundary.
- **Decision options:** (a) **Restore with strict enforcement** — pre-push git hook blocks unverified commits (CLAUDE.md spec retained as-is + enforcement added); (b) **Relax CLAUDE.md spec** — explicitly endorse "ship-cycle smokes substitute for master_check" matching observed practice (CLAUDE.md updated, no behavior change); (c) **Keep documented + log violations** — no spec change, no enforcement change, just track when discipline drifts (status quo).
- **Recommendation:** (b) — observed practice (per-component smokes in ship cycles, e.g., today's prop_005 + LE-06 + prop_007 + Step 2 each smoke-tested individually) is operationally adequate. CLAUDE.md should reflect reality, not aspirational spec. (a) adds friction without proportional value at single-trader scale; (c) creates ongoing audit-vs-doc drift confusion.
- **Cost of wrong call:** drift between CLAUDE.md + practice creates audit confusion in future sessions ("is master_check enforced or not?"). Wrong-call (a) at single-trader scale = friction that slows ship cadence; wrong-call (b) at growth scale = no enforcement when codebase outgrows single-engineer scope. Today (a) is wrong-shaped.

### 7.4 M-series fix priority order

**D-7. M-12 / M-13 / M-16 sequencing.**
- **Action:** Sequence the three open M-series items.
- **Blocking:** D-3 (M-12 blocks Step 5 cleanly).
- **Schedule:** M-12 ASAP (concurrent with Step 5 design pass); M-16 absorbed during UX-03 retirement; M-13 standalone audit when bandwidth allows.
- **Decision options:** (a) M-12 first → M-16 (UX-03) → M-13; (b) all three bundled in single sweep audit; (c) defer all three to Wave 6+.
- **Recommendation:** (a) — sequenced ship. M-12 is pure workflow YAML edit (low risk, 30-60 min); blocks D-3 so highest priority. M-16 resolves naturally when UX-03 retires legacy `main.py eod` Telegram path; no standalone work needed. M-13 is the trickiest — resolution-pipeline write-path investigation across `outcome_evaluator.py` + `journal.py` + `recover_stuck_signals.py`; medium risk; standalone audit when fresh-headed.
- **Cost of wrong call:** M-12 left longest = D-3 blocked = Step 5 ships with workaround (brain ignore-flag) which leaves L1/L4 false-DEGRADED label visible to trader. M-13 left longest = no known active bug; the schema oddity is defensively guarded by EOD composer (`composers/eod.py:230` `outcome != 'OPEN'` filter); fix is hygiene not safety. M-16 left longest = trader confusion (94 vs 80 in two parallel digests until UX-03 retires).

### 7.5 exit_logic_redesign decision

**D-8. exit_logic_redesign drafting.**
- **Action:** Decide DRAFT vs REJECT for `doc/exit_logic_redesign_v1.md`.
- **Blocking:** Brain Step 5 LLM gates that reason over R-multiple thresholds (per `brain_design §3` tier classifier table). If exit redesign reshapes R-multiple distribution, tier classifier needs recalibration before LLM gates depend on it. Currently locked-in via tonight's brain_design §3 status note (`c278a32`).
- **Schedule:** Fresh-headed dedicated session, no time pressure. Track separately from Wave 5 Steps 3-7. Per session_context note "Path 3 step 2."
- **Decision options:** (a) **DRAFT** — full design doc (~500-800 LOC) covering: Day-6 forced-exit dominance findings (35/36 of Apr-27 resolutions), candidate exit logics (dynamic stops, partial profit-taking, ATR-based exits), shadow strategy via prop_005 parallel-shadow infra (already shipped), migration plan, success metrics, rollback. (b) **REJECT** — prop_005 reframe note in fix_table updates to "exit logic accepted as-is; Day-6 dominance documented but not addressed." brain_design §3 status note retired. Removes the placeholder reference.
- **Recommendation:** (a) DRAFT — Day-6 dominance findings (35/36 of Apr-27 resolutions) are real signal-quality concerns. R-multiple-as-tier-threshold currently distorts brain's classifier (per brain_design §3 status note). Drafting forces design rigor + explicit acceptance of trade-offs. Tonight's prop_005 parallel-shadow infra is the validation tool for the alternatives.
- **Cost of wrong call:** REJECT-when-should-DRAFT = brain's LLM gates use stale R-multiple distribution, tier classifier surfaces wrong tier promotions, downstream proposals incorrect, real money lost. DRAFT-when-should-REJECT = ~3 hours of design time consumed without resulting in shipping work; recoverable. Asymmetric cost favors DRAFT.

### 7.6 HYDRAX Phase 0 timing — OUT OF SCOPE for this audit

**D-9. HYDRAX Phase 0** — per `roadmap.md` Phase 5 (Aug-Sep 2026). Gates on Waves 1-5 stable + 2 weeks observation. **HYDRAX gets its own audit when its phase begins.** Noted here for completeness; no scope projection in this anchor doc. **Cost of wrong call:** premature HYDRAX audit = effort wasted on speculative architecture; deferred HYDRAX audit when phase actually starts = timely, evidence-grounded. Defer is correct.

### 7.7 UI wave kickoff trigger

**D-10. Wave UI kickoff.**
- **Action:** Trigger Wave UI track — IT-01..IT-06 + LE-05 + Session 4 design pass ship together as one coherent track (per `fix_table TIER 4` + Wave UI ship plan).
- **Blocking:** Wave 5 stable. Wave UI design needs production-usage-pattern data (which proposal types fire, how trader reviews, what reasoning depth needed in PWA).
- **Schedule:** Post Wave 5 Steps 3-7 shipped + 1-2 weeks observation in production.
- **Decision options:** (a) immediately after Step 7 ship (rush UI to capture momentum); (b) after brain produces real proposals trader has used + reviewed for ≥1 week (let usage inform UI).
- **Recommendation:** (b) — UI design without real-usage-pattern data = rebuilding. Brain Steps 3-7 produce data that informs proposal-card layout, claim-display priority, [why?] expansion depth. Better to design once with usage data than ship piecemeal.
- **Cost of wrong call:** (a) ships Wave UI faster but with guess-based design; trader uses for a week, identifies gaps, requires v2 redesign. (b) ships slower but right; ~1 week delay vs months of redesign.

### 7.8 colab_sync.yml + diagnostic.yml migration

**D-11. Migration timing for remaining GitHub-schedule weekday workflows.**
- **Action:** Migrate `colab_sync.yml` + `diagnostic.yml` from GitHub schedule to cron-job.org dispatch following eod.yml precedent (commit `2fc1f35`).
- **Blocking:** Nothing immediate; M-15 evidence supports migration but neither workflow is Wave 5 load-bearing.
- **Schedule:** Bundled commit, low risk, ~30 min audit + ship per workflow.
- **Decision options:** (a) **bundle migration** — both workflows in one commit + one cron-job.org dashboard add-pair (parallel to D-5 S-4 playbook); (b) **per-workflow migration** — colab_sync first (data export consumer), diagnostic second; (c) **leave as is** — accept M-15 miss-rate for these two non-critical workflows.
- **Recommendation:** (a) — both workflows scheduled at adjacent UTC times (`45 10` + `0 11`); same context as eod.yml migration. One bundled commit + two cron-job.org dashboard adds is operationally cheaper than two separate ship cycles. M-15 evidence already justifies migration.
- **Cost of wrong call:** GitHub schedule miss continues for these two; both are non-critical (colab_sync = analytics export; diagnostic = health report). Worst case: occasional days where colab_sync data is stale + occasional missing health reports. Not safety-critical. **Lowest-stakes decision in this list.**

---

## Part 8 — Cross-reference index

### 8.1 Source documents read (with section anchors)

| Doc | Sections referenced | LOC |
|---|---|---|
| `doc/bridge_design_v1.md` | §1, §2, §3, §9, §10, §11, §13.1, §13.3, §13.4 | 1494 |
| `doc/brain_design_v1.md` | §1, §2, §3, §4 (Steps 1-8), §5, §6, §7, §8, §10, §11 (Q1-Q6) | 490 |
| `doc/master_audit_2026-04-27.md` | PART 4, PART 6, PART 9, PART 10 (gap catalog), Severity tally, Closure note 2026-04-28 | 991 |
| `doc/fix_table.md` | TIERS 2-10 + change-log + CLOSED HISTORICAL | 696 |
| `doc/wave5_prerequisites_2026-04-27.md` | B-1..B-4, S-1..S-5, N-9, Recommended sequence | 188 |
| `doc/session_context.md` | Bridge Build Status table, Resume-point block, Change log | 313 |
| `doc/roadmap.md` | Phases 1-5 | 77 |
| `doc/reconciliation_ritual.md` | (load-bearing P-01 process — confirmed Phase 2) | 124 |
| `doc/engineering_dock.md` | (stale — confirmed Phase 2; recommend retire per Part 6.3) | 260 |
| `CLAUDE.md` | §1 (Python interpreter), §2 (CWD), §3 (audit-first), §4 (sandbox pattern), §5 (bridge architecture), §7 (commit convention) | (root) |

### 8.2 Workflow inventory (25 YAMLs)

`.github/workflows/`:
- **GitHub schedule:** backup_manager (`0 3 * * 6`), colab_sync (`45 10 * * 1-5`), diagnostic (`0 11 * * 1-5`), gap_report (`0 3 * * 1`), heartbeat (`0 3 * * 1-5`), weekend_summary (`30 3 * * 6`), weekly_intelligence (`30 14 * * 0`)
- **cron-job.org dispatch:** eod_master, eod (post `2fc1f35`), ltp_updater, morning_scan, open_validate, postopen, premarket, scan_watchdog, stop_check, telegram_poll
- **Manual:** deep_debugger, master_check, recover_stuck_signals, register_push, wave2, wave5_m08
- **Push:** deploy_pages, rebuild_html

### 8.3 Today's meaningful commits (chronological, 14 commits)

| Time IST | Hash | Subject |
|---|---|---|
| ~03:00 | `9d4dcb2` | scanner: recover_stuck_signals.py — fix broken _is_trading_day import |
| ~03:00 | `550b5f0` | scanner: prop_005 — promote target multiplier + parallel-shadow infra |
| ~04:00 | `4944c17` | doc: fix_table.md — prop_005 reframe |
| ~04:00 | `0512cd2` | doc: fix_table.md — LE-05 reclassified DEFERRED to Wave UI |
| ~05:00 | `cbdef3d` | doc: session_context.md — Wave 4 closure |
| ~05:00 | `d6ddc01` | infra: B-3 — Anthropic SDK + Messages API test call |
| ~14:30 | `ddd66b7` | doc: fix_table — F-2 diagnosis filed M-12 + M-13 |
| ~14:30 | `10a3fb5` | doc: fix_table — B-2 verification + M-14 |
| ~14:50 | `9336b32` | doc: master_audit — Wave 4 closure gap status |
| ~15:14 | `c278a32` | doc: brain_design — Wave 4 closure drift audit |
| ~19:01 | `a5edc32` | Bridge eod (manual dispatch B-1 verification artifact) |
| ~19:00 | `51448e8` | doc: fix_table — B-1 verified + M-15 + M-16 |
| ~19:30 | `2fc1f35` | infra+doc: eod.yml — migrate GitHub schedule → cron-job.org (M-15 RESOLVED) |
| ~20:18 | `060d7c9` | feat(brain): Wave 5 Step 2 — folder skeleton |

### 8.4 Recent context commits (pre-today, last week)

- `720c127` (2026-04-27 evening) — `doc/brain_design_v1.md` Wave 5 blueprint (closes GAP-33)
- `f9d4746` (2026-04-27) — `.github/workflows/eod.yml` Wave 3 Session D ship (now reversed by `2fc1f35`)
- `7b96a97` (2026-04-27) — `bridge: composers/eod.py + thresholds.py` LE-06 boost demotion warnings
- `c647e94` (2026-04-27) — `scanner: rule_proposer.py + thresholds.py` prop_007 boost demotion proposals
- `034d4f5` (2026-04-27) — `feat: watch_patterns infrastructure + UP_TRI×Choppy WATCH (Phase 1)`
- `c43189a` (2026-04-26) — `bridge: telegram_bot.py — /reject_rule command (Wave 4 Step 1)`
- `19d4146` (2026-04-26) — `bridge: bridge_telegram_eod.py — EOD digest renderer (Wave 3 Session B)`
- `c94e523` (2026-04-26) — `bridge: composers/eod.py + bridge.py wiring — Wave 3 L4 EOD composer skeleton (Session A)`
- `3650f57` (2026-04-27 evening) — `doc: master_audit + wave5_prerequisites — GAP-13 reclassified after PWA grep verification`
- `b1359f1` / `68063d3` / `e4d5d6a` (2026-04-27) — _THIN_FALLBACK constants migration to thresholds.py
- `058f4983` (2026-04-27) — `doc: master audit 2026-04-27 — full project map + brain layer + UI flow`

### 8.5 Quick-jump references

- **Brain design:** `doc/brain_design_v1.md` (full)
- **Bridge design:** `doc/bridge_design_v1.md` (full)
- **Today's gap audit:** `doc/master_audit_2026-04-27.md` PART 10 + Closure note
- **Open work tracker:** `doc/fix_table.md` (29 PENDING + 4 PARTIAL + 4 DEFERRED)
- **Wave 5 prereqs:** `doc/wave5_prerequisites_2026-04-27.md`
- **Session resume point:** `doc/session_context.md` (refresh during batch closeout)
- **P-01 ritual:** `doc/reconciliation_ritual.md` (load-bearing weekly process)
- **Operating conventions:** `CLAUDE.md` (Python interpreter, sandbox pattern, commit convention)

---

_End of project anchor. Single comprehensive reference for present + future + gaps + drift + decisions. Use as the index for any future session that needs to recall the system at this snapshot._
