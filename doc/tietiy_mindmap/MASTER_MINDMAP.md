# TIE TIY — Master Mind-Map

**Generated:** 2026-05-13
**Read time:** ~20 minutes
**Companion docs:** [01](01_cron_schedule.md) [02](02_workflow_inventory.md) [03](03_daily_timeline.md) [04](04_signal_lifecycle.md) [05](05_module_inventory.md) [06](06_file_io_graph.md) [07](07_decision_flow.md) [08](08_brain_internals.md) [09](09_ui_surfaces.md) [10](10_failure_modes.md)

---

## 1. One-page overview

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                          TIE TIY ─ END-TO-END FLOW                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

  TRIGGERS                  PIPELINE                STATE              SURFACES
  ─────────                 ─────────               ─────              ────────

  cron-job.org      08:45  morning_scan.yml ──┐
  (external SaaS;    │       scanner.main      │
   11 daily fires)   │       run_morning_scan ─┼──► signal_history ◄──┐
                     │                         │    scan_log          │
  GitHub schedule   08:55  premarket.yml      │    meta              │
  (5 daily +         │       bridge L1 ────────┼──► bridge_state ────┐│
   weekend jobs)     │                         │    + _history       ││
                     │                                                │ │
  push / manual     09:32  open_validate.yml ─┘    open_prices       │ │
                     │       open_validator       gap_pct, valid     │ │
                     │                                                │ │
                    09:40  postopen.yml             bridge_state     │ │
                     │       bridge L2 ──────────► (POST_OPEN SDR)   │ │
                     │                                                │ │
                    09:30─15:30 every 5m            ltp_prices ──────┼─┼──► Telegram
                     │     ltp_updater                                │ │     /today /pnl
                     │     stop_check                stop_alerts ─────┼─┼──► /stops /exits
                     │                                                │ │
                    15:35  eod_master.yml (8 steps)                   │ │
                     │     1 backup                                   │ │
                     │     2 eod_prices_writer ───► eod_prices        │ │
                     │     3 outcome_evaluator ───► signal_history    │ │    📨 EOD digest
                     │       (sole post-9:32          (outcomes,     │ │
                     │        mutator!)                MFE,MAE)      │ │
                     │     5 recover_stuck                            │ │
                     │     6 pattern_miner ───────► patterns         │ │
                     │     7 rule_proposer ───────► proposed_rules ◄─┼─┼──► /proposals
                     │     8 chain_validator ─────► system_health    │ │     /approve_rule
                     │                                                │ │      └─► mutates
                     │                                                │ │          mini_scanner_
                    16:15  eod.yml                                    │ │          rules.json
                     │     bridge L4 ───────────► bridge_state       │ │
                     │     (EOD plain-dict SDR)   + _history         │ │
                     │                                                │ │
                    16:15  colab_sync ─────────► colab_export        │ │
                    16:30  diagnostic ─────────► system_health       │ │
                     │                                                │ │
                    22:00  brain.yml                                  │ │
                     │     Step 3 derive  ──────► brain/cohort_health  │
                     │     Step 4 verify         brain/regime_watch    │    ╔════════════╗
                     │     Step 5 LLM gates ───► brain/reasoning_log   ├──► ║   PWA      ║
                     │       (Opus 4.7,          brain/portfolio_exp   │    ║ tietiy.in  ║
                     │        ~$0.05/run)                              │    ║ (read-only,║
                     │     Step 6 unified ─────► brain/unified_props   │    ║  fetches   ║
                     │       top-3 + §5.1                              │    ║  JSON      ║
                     │       conflict detect ──► proposed_rules        │    ║  direct)   ║
                     │       (dual-write kill/                         │    ║            ║
                     │        boost_demote)                            │    ║ ui.js,     ║
                     │                                                 │    ║ app.js,    ║
                    22:05  brain_digest.yml ──── STUB (Step 7 not yet) │    ║ stats.js,  ║
                     │     brain_telegram.py = 6 lines!                │    ║ journal.js,║
                     │     ⚠️ trader does NOT get nightly brain digest │    ║ analysis.js║
                     │                                                 │    ╚════════════╝
  Sun 20:00         weekly_intelligence.yml                            │
                     │     refreshes regime label in                   │
                     │     weekly_intelligence_latest.json             │
                     │     (brain reads this once a week — stale       │
                     │      regime can propagate for 7 days!)          │
                                                                       │
  cron-job.org      every 10m  telegram_poll.yml                       │
                     │       telegram_bot.poll_and_respond ────────────┘
                     │       16 commands (/today /pnl /stops /exits …
                     │                    /approve_rule /reject_rule
                     │                    /proposals /patterns /help)

  ────────────────────────────────────────────────────────────────────────
       19 scheduled workflows  +  9 manual/push     =  29 total .yml files
       37 scanner/*.py  + 9 brain/*  + 25 bridge/*  ≈  19,769 LOC
       ~30 JSON outputs in output/                  +  1 mini_scanner_rules
```

---

## 2. The five most important JSON files (80% of system state)

| # | File | Why it's #1–5 |
|---|---|---|
| **1** | `output/signal_history.json` (706 KB, schema v5) | The single source of truth. Every signal ever generated, every outcome, every PnL. Created by `journal.py`, mutated only by `open_validator` (09:32) and `outcome_evaluator` (15:35). Read by every consumer. If this file is wrong, the entire system is wrong. |
| **2** | `output/bridge_state.json` (247 KB, schema v1) | The trader's "what should I do today" view. Phase, banner, per-signal bucket (TAKE_FULL/TAKE_SMALL/WATCH/SKIP). Rewritten 3× per trading day. The bridge phase status drives the DEGRADED banner. |
| **3** | `data/mini_scanner_rules.json` (8.9 KB, schema v3) | The system's behavior knobs. shadow_mode + boost/kill/warn patterns. The only file that mutates on user action (via `/approve_rule`). |
| **4** | `output/patterns.json` (141 KB, schema v1) + `output/proposed_rules.json` (59 KB, schema v1) | The discovery loop. Patterns mined at 15:35, proposals generated immediately after, both feed brain Step 5/6 and the trader's `/proposals` queue. |
| **5** | `output/brain/unified_proposals.json` (12 KB) | The nightly top-3 — what the brain thinks should change tomorrow. Currently invisible to the trader (Step 7 stub), but it's the future control plane. |

---

## 3. The five most important Python scripts (80% of the work)

| # | Script | Why |
|---|---|---|
| **1** | `scanner/outcome_evaluator.py` (1,215 LOC) | The **sole mutator** of signal_history after 09:32. Resolves every trade. Without it, every signal stays PENDING forever. Most failure-mode-sensitive script in the system. |
| **2** | `scanner/main.py` (1,085 LOC) | The day's starting orchestrator. `run_morning_scan()` calls everything else: scanner_core, scorer, mini_scanner, journal, push_sender, telegram_bot. Largest single commit of the day. |
| **3** | `scanner/telegram_bot.py` (2,915 LOC) | The control plane. Every user action (approve, reject, query) flows through here. 16 commands + 11 broadcasts. The largest single file in the codebase. |
| **4** | `scanner/brain/brain_reason.py` (1,085 LOC) | The only Anthropic LLM integration. 3 gates, cost tracker, history context, circuit breaker. Brain's intelligence lives here. |
| **5** | `scanner/bridge/composers/premarket.py` (646 LOC) | The pre-market decision composer. Wires evidence_collector + bucket_engine + state_writer. Every trading day starts with this composing the day's first bridge_state. |

(Honorable mention: `scanner/stop_alert_writer.py` at 849 LOC for intraday loop, `scanner/journal.py` at 994 LOC as signal_history owner.)

---

## 4. The five most important workflows (the critical path)

In firing order — if any of these miss, the day's pipeline is broken:

| # | Workflow | IST | Why critical |
|---|---|---|---|
| **1** | `morning_scan.yml` | 08:45 | Without it, no signals exist. The day's entire downstream depends on it. |
| **2** | `premarket.yml` | 08:55 | Bridge L1 — without it, no `bridge_state.json` for the day; no Telegram brief. |
| **3** | `open_validate.yml` | 09:32 | Without it, signals never get `actual_open` / `entry_valid` — outcome_evaluator can't resolve them correctly. |
| **4** | `eod_master.yml` | 15:35 | The 8-step EOD chain. Without it, no outcomes resolve, no patterns mined, no proposals generated. |
| **5** | `brain.yml` | 22:00 | Without it, derived views go stale; no nightly cohort/regime/portfolio analysis. |

`telegram_poll.yml` is the silent #6 — without it, the user can't run any `/command`.

---

## 5. Information flow (where data originates → where the user sees it)

```
ORIGINATES                     TRANSFORMS                          USER SEES
──────────                     ───────────                         ─────────

yfinance daily bars   ──► scanner_core.detect()  ──► signal_history ──► Telegram /signals
                                                                        PWA signal table

yfinance 1m intraday  ──► ltp_writer            ──► ltp_prices    ──► Telegram /today /pnl
                                                                        PWA live ticker

bridge composers      ──► bucket_engine 4 gates ──► bridge_state  ──► Telegram premarket/
                          + evidence_collector                          postopen/eod briefs
                                                                        (PWA does NOT show)

stop_check.py         ──► sanity guards         ──► stop_alerts    ──► Telegram urgent alert
                                                                        PWA stop section

outcome_evaluator     ──► 6-bar window scan     ──► signal_history ──► Telegram EOD digest
                                                       (outcomes)       PWA stats panel

pattern_miner         ──► cohort grouping       ──► patterns       ──► Telegram /patterns
                                                                        (PWA invisible)

rule_proposer         ──► pattern → rule        ──► proposed_rules ──► Telegram /proposals
                                                                        (PWA invisible)

brain_derive          ──► 4 deterministic views ──► brain/*.json   ──► (NO surface — Step 7
                                                                        stub means nobody
                                                                        sees this output)

brain_reason          ──► 3 Opus 4.7 gates      ──► brain/         ──► (NO surface)
                                                       reasoning_log
                                                       unified_props

weekly_intelligence   ──► AI roll-up            ──► weekly_intel    ──► Telegram Sunday brief
                                                       regime field   ──► brain reads as
                                                                          authoritative regime
```

**Bottleneck:** brain's output sits in `output/brain/` with no consumer. The whole "smarter every day" loop depends on Step 7 going live.

---

## 6. Control flow (who decides)

| Decision | System or User | Override path |
|---|---|---|
| Universe (which stocks) | System (data/fno_universe.csv) | Manual edit |
| Detect signal | System (scanner_core conditions) | Tune config.py |
| Score | System (scorer.py rules) | Tune config.py |
| Filter | System (mini_scanner overlay rules) | Edit data/mini_scanner_rules.json |
| Bucket assignment | System (bucket_engine 4 gates) | Indirect — approve a kill/boost rule |
| Stop/target hit detection | System (price-driven) | None (price is price) |
| Outcome resolution | System (outcome_evaluator) | recover_stuck_signals.yml |
| Patterns mined | System (pattern_miner) | None |
| Proposed rules generated | System (rule_proposer + brain) | None |
| **Approve a rule** | **User** (`/approve_rule N` via Telegram) | only way to mutate mini_scanner_rules.json |
| **Reject a rule** | **User** (`/reject_rule N` via Telegram) | |
| **Approve a brain proposal** | **User** (designed: `/approve <unified_id>`) | Step 7 stub — currently no path |
| Trade execution | **User** (manual, paper or live) | System never places orders |
| Settings (PIN, push) | **User** (via PWA + register_push.yml) | |

The trader controls **3 things**: rule approval, brain approval (when wired), and actual trade execution. Everything else is automatic.

---

## 7. Hidden dependencies (not obvious from any one file)

1. **The regime label brain reads is set weekly, not daily.** `scanner/brain/brain_derive.py:_derive_regime_watch()` reads `weekly_intelligence_latest.json#regime`. That file is updated only by `weekly_intelligence.yml` on Sunday 20:00 IST. If Sunday's run misses (GH schedule outage), brain reads a stale regime for an entire week.

2. **`eod_master.yml` step ordering matters.** Pattern miner runs **before** chain_validator (M-12 fix). If reordered, chain_validator reads yesterday's `patterns.generated_at` and falsely flags DEGRADED.

3. **L2 bucket-change tracking depends on the L1 dated history file existing.** `bridge_state_history/<date>_PRE_MARKET.json` is consumed by `_history_reader` in postopen. If 30-day cleanup removes it prematurely, or if premarket.yml didn't run, L2 has no L1 reference and silently sets `l1_reference_available: false` — bucket_changed flag becomes unreliable.

4. **Brain's portfolio_exposure primary source is the bridge EOD archive.** Not signal_history. `brain_derive._derive_portfolio_exposure()` reads `bridge_state_history/<as_of_date>_EOD.json#open_positions[]`. Falls back to signal_history if missing, but with a warning. The brain depends on yesterday's bridge eod.yml run having succeeded.

5. **`mini_scanner_rules.json` is the only file that mutates from user action.** Approving a rule via `/approve_rule` mutates `data/mini_scanner_rules.json` (committed by the telegram_poll.yml workflow). This means the trader's actions are recorded as git commits — accidentally useful audit trail.

6. **`signal_history.json` has 4 mutators, not 1.** Conventionally one expects `journal.py` to be the only mutator, but actually: `journal.py` (create), `open_validator.py` (09:32 gap fields), `outcome_evaluator.py` (15:35 + D6B outcomes), `recover_stuck_signals.py` (on-demand). All others including bridge composers and brain are read-only.

7. **cron-job.org schedules are invisible to the repo.** The repo cannot tell you when a workflow is supposed to fire — the schedule lives in an external account. The only signal is the workflow header comment ("cron-job.org @ X:XX IST").

8. **`output/signal_history.backup.json` is a per-mutation backup, not a daily snapshot.** Every call to `journal.log_signal()` writes a new backup first via `_backup_history()`. So 706 KB updated dozens of times per day. The actual disaster-recovery snapshots live in `backups/`.

9. **`/approve_rule` writes to `data/`, not `output/`.** `data/mini_scanner_rules.json` is the only mutating file outside `output/` — a configuration file that's also state. Everywhere else, `data/` is read-only static.

10. **Two Telegram code paths exist.** `scanner/telegram_bot.py` (general broadcasts + polling) AND `scanner/bridge_telegram_{premarket,postopen,eod}.py` (bridge-specific renderers that re-use `_esc` from telegram_bot). The renderers consume only `bridge_state.json`, never the truth files — a deliberate decoupling.

---

## 8. Surprising discoveries

These are things even an experienced operator might not realize about their own system:

### 🔍 SD1 — `brain_digest.yml` fires daily but does nothing
`scanner/brain/brain_telegram.py` is a **6-line docstring-only stub**. The cron-job.org schedule fires the workflow at 22:05 every night, GitHub spawns a runner, Python imports the empty module, exits. **The brain has been producing top-3 proposals into `unified_proposals.json` every night for weeks, but nobody is being told about them.** Step 7 was deferred and the workflow was never disabled — it's been wasting compute minutes for ~2 weeks. Trader would need to manually `cat output/brain/unified_proposals.json` to see brain output.

### 🔍 SD2 — The regime label that drives 80% of bucket decisions is updated WEEKLY
`brain_derive._derive_regime_watch()` reads `output/weekly_intelligence_latest.json#regime#latest#regime`. That file is rewritten only on Sunday 20:00 IST by `weekly_intelligence.yml`. So Tuesday morning's brain run reads Sunday's regime label. If Sunday's run misses (GH schedule outage; documented to happen), Tuesday-Friday-Monday-Tuesday all read the 10-day-old regime. Today's "Choppy stable for 7 days" is from the 2026-05-04 Sunday refresh.

### 🔍 SD3 — `eod.yml` time conflicts: docs say 16:00, code says 16:15
`CLAUDE.md` and `doc/bridge_design_v1.md` describe Bridge L4 as firing at 16:00. The actual `eod.yml` header comment says **16:15** IST. The cron-job.org schedule (invisible to the repo) is the actual source of truth — verify in console. This 15-minute discrepancy could be deliberate (give eod_master more time to finish at 15:35) but isn't documented.

### 🔍 SD4 — `signal_archive.json` is 42 bytes
The archival pipeline (`journal.archive_old_records()`) is supposed to move 90+ day-old records out of `signal_history.json` into `signal_archive.json`. But the archive file is **42 bytes** — essentially empty. Either no records are >90d old yet (system is younger than 90 days), or the archival code never runs, or it runs and silently does nothing. Worth verifying before the file grows past tolerance.

### 🔍 SD5 — High-churn git history during market hours
`ltp_updater.yml` commits every 5 minutes during the trading window (~76 commits/day). Same for `stop_check.yml`. So a typical Mon-Fri produces **150+ commits per day** just from these two workflows. The git log is dominated by `LTP update HH:MM IST` and `Stop check HH:MM IST` entries. (Visible in the startup git status: "00b668bf … 636fd37c … 06736eb3 Stop check 10:57 IST".) Whether `.git` size becomes problematic is worth tracking.

### 🔍 SD6 — The PWA dashboard doesn't know the bridge exists
`output/ui.js` fetches 10 JSON files for display. **`bridge_state.json` is not one of them.** The DEGRADED banner ("LIVE — partial data") lives in bridge_state but the PWA renders its own offline-state banner from service worker network events. The bridge layer was shipped without a PWA consumer. This is a TIE TIY 2.0 dashboard opportunity.

### 🔍 SD7 — Both `eod.yml` and `eod_master.yml` exist with different purposes
`eod_master.yml` (15:35 IST, 271 LOC) = the 8-step EOD chain (outcome evaluator, pattern miner, rule proposer, validator). `eod.yml` (16:15 IST, 120 LOC) = the bridge L4 composer. Easy to confuse. Both fire on every trading day, both commit, both Telegram.

### 🔍 SD8 — `tg_offset.json` is 21 bytes, committed every 10 minutes
The Telegram bot's "last processed update_id" lives in a 21-byte file that gets re-committed every 10 minutes (144 commits/day), 24×7. The git history of this single file is essentially the heartbeat of the polling system.

### 🔍 SD9 — `outcome_evaluator.py` runs TWICE per signal
First time: 15:35 same-day, evaluates whether stop/target hit intraday. Second time (D6B): 09:32 the next morning IF today is Day-6 for some signal. The same script runs in two contexts. open_validator.py at 09:32 internally fires outcome_evaluator's D6B path — so outcome_evaluator is called by 2 different workflows depending on signal age.

### 🔍 SD10 — There is no "is the cron-job.org account alive?" canary
The repo has heartbeat.yml (08:30 GH schedule) and scan_watchdog.yml (09:02 cron-job.org). But neither would fire if cron-job.org itself goes down OR the GitHub auth token cron-job.org uses to dispatch workflows expires. The earliest signal of cron-job.org being dead is the **trader noticing no morning brief at 08:45–08:55**. Time-to-detect: 25+ minutes if the trader is watching, much longer otherwise.

---

## 9. The weakest links (silent-break ranked)

| Rank | Component | Time-to-detect failure |
|---|---|---|
| 1 | cron-job.org account / token | ~25 min (trader noticing) |
| 2 | `weekly_intelligence.yml` miss on Sunday → stale regime all week | up to 7 days |
| 3 | `brain_telegram.py` Step 7 stub (already failing) | **never detected automatically** |
| 4 | yfinance partial data NaN → silent stuck PENDINGs | indefinite |
| 5 | `bridge_state_history/<date>_EOD.json` missing → brain portfolio_exposure fallback | indefinite (warning logged but no alert) |
| 6 | Pattern miner drought (0 patterns) overwrites yesterday's good output | 1 day |
| 7 | Telegram bot token rotation forgotten | whole day |
| 8 | `ANTHROPIC_API_KEY` expired | whole brain run |
| 9 | Push notification VAPID keys expired | indefinite |
| 10 | `signal_archive.json` archival pipeline silently does nothing | unknown |

Full failure-mode catalogue: see [10_failure_modes.md](10_failure_modes.md).

---

## 10. Leverage points (top 3 by impact)

These are concrete, narrow changes that would produce the biggest improvement in signal quality, operator visibility, or system robustness. No code changes implied here — just ranking.

### 🎯 L1 — Ship Step 7 (make `brain_telegram.py` actually send the digest)

**Why it's #1:** The brain is producing high-quality top-3 proposals every night (verified: 3 candidates in `unified_proposals.json` as of 2026-05-12 22:00). The trader has been blind to them for ~2 weeks because `brain_telegram.py` is a 6-line stub. This is a **paid LLM call per night with zero output going to the trader**. Implementing the Step 7 digest unlocks the entire "smarter every day" feedback loop (decisions_journal gets entries → next brain run reads them as context). Cost to ship: hours of work. Value: the brain's entire reason for existing.

**Touched files:** `scanner/brain/brain_telegram.py` (currently 6 lines, needs ~200), `scanner/telegram_bot.py` (wire `/approve <unified_id>` and `/reject <unified_id>` handlers to actually mutate `mini_scanner_rules.json` and `decisions_journal.json`). Workflow `brain_digest.yml` already exists and fires at 22:05.

### 🎯 L2 — Refresh the regime label daily (not weekly)

**Why it's #2:** Today's "8/8 signals SKIP because regime=Choppy" is partly caused by `weekly_intelligence_latest.json#regime` being computed once a week on Sunday. By Tuesday, that label is 2 days stale; by Friday, 5 days. A market that has decisively shifted from Choppy → Bear on Wednesday won't be reflected in brain's bucket gates until next Sunday. This is a structural staleness that the system was designed around (D-4 cadence lock) — but the trader is paying for it daily in SKIPs that should be TAKE_SMALLs.

The cheap fix: have brain_derive read regime from a fresh daily computation (regime_debug.json is already written daily by morning_scan; promote it to authoritative). The expensive fix: also re-run weekly_intelligence's regime classifier daily. Either way: a one-day-stale regime is better than a week-stale one.

**Touched files:** `scanner/brain/brain_derive.py:_derive_regime_watch()` (point at a daily source), possibly extend `scanner/main.py` morning scan to write `output/current_regime.json`. No new workflow needed.

### 🎯 L3 — Connect the PWA to `bridge_state.json` + add a DEGRADED banner

**Why it's #3:** The bridge already produces `phase_status`, `banner.state`, `banner.color`, `banner.message`, `banner.subtext` — exactly the right shape for a header banner. But `output/ui.js` doesn't fetch `bridge_state.json`. So today's "LIVE — partial data, 8 validated, no reclassifications" banner is invisible to the trader unless they happen to open Telegram. The PWA also doesn't show bucket badges per signal (TAKE_FULL/TAKE_SMALL/WATCH/SKIP) — they're available in bridge_state but not rendered.

Adding both costs ~50 lines of UI code and unlocks: (a) trader sees system health at a glance, (b) trader sees today's bucket for every signal alongside the signal table, (c) the foundation for displaying `unified_proposals.json` and `cohort_health.json` panels — i.e., the TIE TIY 2.0 dashboard.

**Touched files:** `output/ui.js` (add fetch of bridge_state.json, render banner, render bucket badges), `output/index.html` (add banner DOM node), maybe `output/app.js` (signal-card bucket display).

---

## Closing note

The TIE TIY system is **structurally coherent** — 19,769 LOC across 75+ files, all wired together by 19 scheduled workflows and 30 JSON files. The major architectural decisions (atomic writes, read-only invariants on signal_history, single-write chokepoint in state_writer, append-only journals in brain, dual-channel Telegram + PWA) are documented and consistently applied. There is very little dead code.

The biggest gap is **observability + the brain output channel**. The brain works, but its output never reaches the trader. The PWA shows yesterday's signals beautifully but doesn't know today's buckets. The trader is mostly piloting from Telegram briefs.

**To make TIE TIY twice as useful with one weekend of work:** ship Step 7 (L1), connect the PWA to bridge_state (L3), and rethink regime cadence (L2). Everything else is incremental.

---

*Full sub-document indices: [01](01_cron_schedule.md) [02](02_workflow_inventory.md) [03](03_daily_timeline.md) [04](04_signal_lifecycle.md) [05](05_module_inventory.md) [06](06_file_io_graph.md) [07](07_decision_flow.md) [08](08_brain_internals.md) [09](09_ui_surfaces.md) [10](10_failure_modes.md)*
