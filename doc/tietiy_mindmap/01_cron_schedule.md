# Dimension 1 — Cron Schedule & Workflow Trigger Map

**Generated:** 2026-05-13
**Scope:** Every external (cron-job.org) and internal (GitHub `schedule:`) trigger that wakes a `.github/workflows/*.yml` file.

---

## 1. The trigger taxonomy

TIE TIY has **three** ways a workflow can fire:

| Mechanism | Owner | How to inspect | Reliability |
|---|---|---|---|
| **cron-job.org** | External SaaS (user account) | Console at cron-job.org | High; redundant against GH-schedule outages |
| **GitHub `schedule:` cron** | GitHub Actions runner | `.github/workflows/*.yml` `on.schedule[].cron` | Best-effort; drift + outages documented (2026-04-28) |
| **`push:` / `workflow_dispatch` (manual)** | Git push or human click | UI / repo events | Deterministic when fired |

Note: every workflow that *says* "cron-job.org @ X:XX IST" in its header comment actually declares only `on: workflow_dispatch:` in YAML. The schedule lives in cron-job.org, not in the repo. That is why grepping the `.yml` files alone undercounts active schedules.

---

## 2. Daily IST timeline (Mon–Fri, trading day)

ASCII timeline of one trading day, every fire-time marked. `>>` denotes a workflow trigger; `==` denotes a sustained loop.

```
00:00 ── (idle) ────────────────────────────────────────────────────────────
       │
03:00  │ 03:00 UTC = 08:30 IST
08:30 >> heartbeat.yml          [GH schedule '0 3 * * 1-5']        ☁ alive ping, banned-stocks
08:30 >> gap_report.yml         [GH schedule '0 3 * * 1']  (Mon only)
       │
08:45 >> morning_scan.yml       [cron-job.org]   ─── critical: 188-stock scan
08:55 >> premarket.yml          [cron-job.org]   ─── Bridge L1 PRE_MARKET
09:02 >> scan_watchdog.yml      [cron-job.org]   ─── verify morning_scan landed
       │
09:15 ── MARKET OPEN ──────────────────────────────────────────────────────
       │
09:32 >> open_validate.yml      [cron-job.org]   ─── 9:15 actual_open + gap%
09:40 >> postopen.yml           [cron-job.org]   ─── Bridge L2 POST_OPEN
       │
09:30 ══ ltp_updater.yml        [cron-job.org */5 04-10 * * 1-5]   ←─── every 5m
09:32 ══ stop_check.yml         [cron-job.org 2-57/5 04-10 * * 1-5] ←─── every 5m (offset +2)
       │     ↑
       │     (both loops continue throughout the trading day)
       │
?? ── ?? ══ telegram_poll.yml   [cron-job.org every 10m, 24×7]
       │
15:30 ── MARKET CLOSE ─────────────────────────────────────────────────────
15:35 >> eod_master.yml         [cron-job.org]   ─── 8-step chain: outcome_eval, miner, proposer, validator
16:15 >> eod.yml                [cron-job.org]   ─── Bridge L4 EOD digest
16:30 >> diagnostic.yml         [GH schedule '0 11 * * 1-5']  (also manual)
       │
22:00 >> brain.yml              [cron-job.org Mon-Sun]   ─── derive→verify→reason→output
22:05 >> brain_digest.yml       [cron-job.org Mon-Sun]   ─── unified_proposals → Telegram
       │
23:59 ── (idle) ────────────────────────────────────────────────────────────
```

### Weekend additions

```
Sat 08:30 IST  >> backup_manager.yml        [GH schedule '0 3 * * 6']
Sat 09:00 IST  >> weekend_summary.yml       [GH schedule '30 3 * * 6']
Sun 20:00 IST  >> weekly_intelligence.yml   [GH schedule '30 14 * * 0']
Mon-Sun 22:00  >> brain.yml                 (runs every day)
Mon-Sun 22:05  >> brain_digest.yml          (runs every day)
24×7 every 10m >> telegram_poll.yml         (responds to /commands)
```

---

## 3. Schedule source-of-truth table

For each workflow, the actual configured schedule. `IST = UTC + 5:30`.

| Workflow | Mechanism | Cron / IST time | Active days | Verified from |
|---|---|---|---|---|
| `morning_scan.yml` | cron-job.org | 08:45 IST | Mon-Fri | header comment line 7 |
| `premarket.yml` | cron-job.org | 08:55 IST | Mon-Fri | header line 5 |
| `scan_watchdog.yml` | cron-job.org | ~09:02 IST | Mon-Fri | (per first audit subagent — verify in cron-job.org console) |
| `open_validate.yml` | cron-job.org | 09:32 IST | Mon-Fri | header line 6 |
| `postopen.yml` | cron-job.org | 09:40 IST | Mon-Fri | header line 6 |
| `ltp_updater.yml` | cron-job.org | `*/5 04-10 * * 1-5` UTC = 09:30–15:30 IST every 5m | Mon-Fri | header line 12 |
| `stop_check.yml` | cron-job.org | `2-57/5 04-10 * * 1-5` UTC = +2 min offset | Mon-Fri | per first audit subagent |
| `telegram_poll.yml` | cron-job.org | every 10 min, 24×7 | All | header comment |
| `eod_master.yml` | cron-job.org | 15:35 IST | Mon-Fri | header line |
| `eod.yml` | cron-job.org | 16:15 IST | Mon-Fri | header (note: bridge_design_v1 §13.4 lists 16:00; **header says 16:15**) |
| `diagnostic.yml` | GH schedule | `0 11 * * 1-5` UTC = 16:30 IST | Mon-Fri | YAML `on.schedule` |
| `brain.yml` | cron-job.org | 22:00 IST | **Mon-Sun (all 7 days)** | header line 4 |
| `brain_digest.yml` | cron-job.org | 22:05 IST | Mon-Sun | header line 6 |
| `heartbeat.yml` | GH schedule | `0 3 * * 1-5` UTC = 08:30 IST | Mon-Fri | YAML |
| `gap_report.yml` | GH schedule | `0 3 * * 1` UTC = 08:30 IST | Mon only | YAML |
| `backup_manager.yml` | GH schedule | `0 3 * * 6` UTC = 08:30 IST Saturday | Sat | YAML |
| `weekend_summary.yml` | GH schedule | `30 3 * * 6` UTC = 09:00 IST Sat | Sat | YAML |
| `weekly_intelligence.yml` | GH schedule | `30 14 * * 0` UTC = 20:00 IST Sun | Sun | YAML |
| `colab_sync.yml` | GH schedule | `45 10 * * 1-5` UTC = 16:15 IST | Mon-Fri | YAML |
| `deploy_pages.yml` | `push:` (path-filtered) | on commit to `output/` | All | YAML |
| `rebuild_html.yml` | `push:` (output/*.js, *.html) | on commit | All | YAML |
| `master_check.yml` | manual | workflow_dispatch only | — | YAML |
| `deep_debugger.yml` | manual | workflow_dispatch only | — | YAML |
| `recover_stuck_signals.yml` | manual | workflow_dispatch only | — | YAML |
| `register_push.yml` | manual | workflow_dispatch only | — | YAML |
| `wave2.yml` | manual (legacy migration) | workflow_dispatch | — | YAML |
| `wave5_m08.yml` | manual (legacy migration) | workflow_dispatch | — | YAML |
| `lab_ms1_fetch.yml` | manual (Lab branch) | workflow_dispatch | — | YAML |
| `eod_update.yml.bak` | none | preserved as escape-hatch | — | filename suffix |

**Active scheduled workflows: 19** (12 cron-job.org + 7 GitHub schedule)
**Manual / push / disabled: 9**

---

## 4. Why cron-job.org instead of GitHub `schedule:`?

From `doc/bridge_design_v1.md §13.4` and `doc/master_audit_2026-04-27.md`:

> On **2026-04-28**, all three GitHub-schedule weekday workflows (`eod.yml`, `colab_sync.yml`, `diagnostic.yml`) silently failed to fire while all six cron-job.org workflows fired cleanly. Wave 5 made `eod.yml` load-bearing (brain reads `bridge_state_history/<date>_EOD.json`), so the team migrated `eod.yml` from GH schedule → cron-job.org dispatch. The trade-off is a new SPOF: cron-job.org itself.

Lock M-15: precision-critical & business-critical workflows fire via cron-job.org. Drift-tolerant weekly/monthly workflows stay on GH `schedule:`. The failover playbook (S-4 in wave5_prerequisites) is still **pending**.

---

## 5. Gaps in the daily timeline

Periods during the trading day with no scheduled workflow (other than the LTP/stop check loops):

| Gap | IST window | Notes |
|---|---|---|
| **Open → first composer** | 09:15 → 09:32 | 17 min — gap_evaluation has to wait for open_validate.yml at 09:32 |
| **Postopen → close** | 09:40 → 15:30 | 5h 50m of intraday — only LTP loop + stop check; no signal generation, no re-bucketing, no regime re-evaluation |
| **Close → EOD master** | 15:30 → 15:35 | 5 min — outcome_evaluator does not see the 15:30 close until 15:35 fires |
| **EOD master → bridge EOD** | 15:35 → 16:15 | 40 min — eod_master must finish chain before bridge digest can read it |
| **Bridge EOD → brain** | 16:15 → 22:00 | ~6h dead window — no derived-view refresh until 22:00 |
| **Brain → next morning scan** | 22:05 → 08:45 | ~10.5h overnight |

Implication: the system is fast & alert during morning + post-close, then **idle for 10 hours overnight**. If a fix or rule activation needs to propagate, it waits for the 08:45 scan.

---

## 6. cron-job.org schedules (NOT in this repo)

These exist only in the external cron-job.org account. The repo cannot tell you they exist; only the workflow header comments hint at them. Verify in the cron-job.org dashboard:

```
08:45 IST  →  POST  https://api.github.com/repos/.../actions/workflows/morning_scan.yml/dispatches
08:55 IST  →  ...   .../premarket.yml/dispatches
09:02 IST  →  ...   .../scan_watchdog.yml/dispatches
09:30 IST  →  ...   .../ltp_updater.yml/dispatches   (every 5m till 15:30)
09:32 IST  →  ...   .../stop_check.yml + open_validate.yml
09:40 IST  →  ...   .../postopen.yml/dispatches
15:35 IST  →  ...   .../eod_master.yml/dispatches
16:15 IST  →  ...   .../eod.yml/dispatches
22:00 IST  →  ...   .../brain.yml/dispatches
22:05 IST  →  ...   .../brain_digest.yml/dispatches
every 10m  →  ...   .../telegram_poll.yml/dispatches
```

**Failure mode:** if cron-job.org credentials expire, the GitHub token expires, or cron-job.org goes down — every cron-job.org-driven workflow stops silently. `heartbeat.yml` (GH schedule) is the canary, but heartbeat itself fires off GH schedule which is known unreliable. See Dimension 10 for the full failure-mode catalogue.

---

## 7. Critical-path workflows (the ones that, if they fail, break the system)

In firing order:

1. `morning_scan.yml` — without it, no signals exist
2. `premarket.yml` — without it, no `bridge_state.json` for the day
3. `eod_master.yml` — without it, no outcomes resolve, no patterns mined
4. `eod.yml` — without it, brain can't read `bridge_state_history/<date>_EOD.json`
5. `brain.yml` — without it, no derived views or proposals refresh

Everything else is supplementary (alerts, dashboards, weekly recaps).
