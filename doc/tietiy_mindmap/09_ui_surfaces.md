# Dimension 9 — UI / Output Surfaces

**Generated:** 2026-05-13
**Scope:** What the user sees and how. The PWA at `tietiy.in`, the Telegram bot, and what a "TIE TIY 2.0 dashboard" would need to read.

---

## The two user surfaces

```
            ┌─────────────────────────────┐         ┌─────────────────────────────┐
            │       Telegram               │         │     PWA @ tietiy.in         │
            │  (primary control plane)     │         │  (read-mostly dashboard)    │
            │                              │         │                             │
            │  • broadcast alerts          │         │  • signal table             │
            │  • daily briefs              │         │  • per-signal detail        │
            │  • user /commands            │         │  • analysis bundle (SQL.js) │
            │  • approve_rule mutations    │         │  • health dashboard         │
            └──────────────┬───────────────┘         └──────────────┬──────────────┘
                           │                                        │
                           │ writes/reads via                       │ fetches JSON
                           │ scanner/telegram_bot.py                │ from output/*
                           ▼                                        ▼
                  ┌─────────────────────────────────────────────────────┐
                  │              output/ (committed JSON)               │
                  └─────────────────────────────────────────────────────┘
```

The PWA is **display-only**. All trader-side mutations (rule approvals, push registration) flow through Telegram.

---

## PWA: HTML entry points

### `output/index.html` (9.2 KB)
Root PWA page. Cache-busted script loads (timestamps injected by `rebuild_html.yml`):
```
<script src="ui.js?v=202605130317"></script>
<script src="app.js?v=202605130317"></script>
<script src="journal.js?v=202605130317"></script>
<script src="stats.js?v=202605130317"></script>
```
- PWA meta: `apple-mobile-web-app-capable`, `manifest.json` reference
- Service worker registration in `app.js`

### `output/analysis.html` (17 KB)
Analysis dashboard. CDN-loaded SQL.js (1.10.3) + Chart.js (4.4.1). Local script loader (CACHE-01 Plan B) injects `<script>` tags with `?v=Date.now()` for fresh fetches:
- `analysis.js` (engine)
- `analysis/overview.js`
- `analysis/signals.js`
- `analysis/segmentation.js`
- `analysis/post_mortem.js`
- `analysis/advanced.js`

### `output/health.html` (19 KB)
Standalone health dashboard. Auto-refreshes every 60s. Displays `system_health.json` checks (morning_scan, open_validate, eod_update, outcome_eval, pattern_miner, rule_proposer, contra_tracker). Has a GitHub token input for dispatching `diagnostic.yml` manually.

### `output/CNAME` (root, 10 bytes)
`tietiy.in` — confirms GitHub Pages serves at the custom domain.

### `output/manifest.json`
PWA manifest. Provides icons, start_url, theme color.

---

## PWA: service worker (`output/sw.js`, 14 KB)

Cache version: **v8** (bumped to fix data staleness).
- **SHELL_FILES** cached: `index.html`, `manifest.json`, `ui.js`, `app.js`, `journal.js`, `stats.js`
- **DATA_JSON_PATTERNS** never cached (always `cache: 'no-store'`):
  - `signal_history.json`, `meta.json`, `open_prices.json`, `eod_prices.json`, `ltp.json` (note: ltp_prices is the actual filename), `patterns.json`, `system_health.json`, `stop_alerts.json`
- **Broadcasts**:
  - `type='ONLINE'/'OFFLINE'` on network state change
  - `type='DATA_REFRESH'` on activate (SW2 fix forces client reloads)
- **Push notifications**: listener at line 408, click handler at 445, subscription change handler at 475 (VAPID push)

---

## PWA: main bundles

### `ui.js` (61 KB)
- Renders: offline banner, signal cards, tabs (Today / Active / Completed / Stats), header
- Fetches: `banned_stocks.json`, `eod_prices.json`, `ltp_prices.json`, `meta.json`, `mini_log.json`, `nse_holidays.json`, `open_prices.json`, `scan_log.json`, `signal_history.json`, `stop_alerts.json`
- **Does NOT fetch `bridge_state.json`** — the DEGRADED banner in bridge_state is invisible to the PWA today

### `app.js` (62 KB)
- Core app: signal table rendering, filtering, sorting, signal-detail modal
- Service worker registration (line 2051)
- Push notification setup (line 1930): prompts for 4-digit PIN, calls `reg.pushManager.subscribe()`, stores in `localStorage['tietiy_push_sub']`
- VAPID_PUBLIC_KEY loaded from window
- No Telegram dispatch from PWA — user must use the Telegram app

### `journal.js` (62 KB)
- P&L tracking, position management
- Similar JSON fetch pattern to ui.js

### `stats.js` (49 KB)
- Statistics dashboard (Win Rate, Avg P&L)
- Listens to service worker `DATA_REFRESH` messages (SW2)
- Forces reload of `signal_history.json` on receipt

---

## PWA: analysis bundle (SQL.js powered)

### `analysis.js` (36 KB) — engine
- Seeds `window.AN` with today, wrFragment, currentDate
- Loads SQLite via `initSqlJs()`, initializes DB from bundled schema
- Boots remaining bundles after all parse

### Plugin bundles
- `analysis/overview.js` (17 KB) — WR by regime, sector, signal type (SQL queries against signal_history)
- `analysis/signals.js` (12 KB) — Detailed signal table with outcome drill-down
- `analysis/segmentation.js` (10 KB) — Cohort analysis (n, WR, edge by pattern)
- `analysis/post_mortem.js` (8.9 KB) — Failure-reason classification
- `analysis/advanced.js` (9.3 KB) — A/B testing, regime correlation

All run against signal_history.json loaded into in-browser SQLite — fast queryable analytics.

---

## PWA: what it does NOT show

Visible gaps that a TIE TIY 2.0 dashboard would close:

1. **No DEGRADED banner** for bridge phase_status. `bridge_state.json` has the field (`phase_status: "DEGRADED"`, `banner.message: "LIVE — partial data"`) but ui.js doesn't read it.
2. **No bucket badges** on signals. The PWA shows `score` but not `TAKE_FULL` / `TAKE_SMALL` / `WATCH` / `SKIP`.
3. **No brain output**. `unified_proposals.json` is never fetched. Cohort_health, regime_watch, portfolio_exposure are invisible in the PWA.
4. **No proposal queue UI**. `proposed_rules.json` is invisible; trader must use Telegram `/proposals`.
5. **No live ban list display.** It's fetched but only used as a flag, not as a banner ("FII activity blocked these 3 stocks today").
6. **No regime-shift alerting.** Brain's `regime_shift_detector` produces output, but no UI surfaces it.
7. **No weekly_intelligence digest.** File exists but the PWA doesn't render it.
8. **No contra_shadow tracking.** Research file invisible to the PWA.

---

## Telegram bot interface

### `scanner/telegram_bot.py` (2,915 LOC)

The single largest module in the codebase. Two kinds of API surface:

#### A) Broadcast (workflow → Telegram)
Functions called from various workflows. Workflow loads relevant JSON, passes it to the function, function formats Markdown and POSTs to Telegram Bot API.

| Function | LOC anchor | Triggered by | What it sends |
|---|---|---|---|
| `send_morning_scan(signals, meta)` | 1308 | morning_scan.yml | scan results brief |
| `send_morning_brief(...)` | 876 | morning_scan.yml | pre-market summary |
| `send_open_validation(...)` | 1407 | open_validate.yml | gap caveat verdicts |
| `send_stop_alert(signal)` | 1490 | stop_check.yml | urgent stop/target hit |
| `send_exit_tomorrow(signals, meta, ltp_prices)` | 1534 | (morning) | exits due today + tomorrow |
| `send_eod_summary(outcomes, meta)` | 1656 | eod_master.yml | resolved signals + PnL + failure_reason |
| `send_heartbeat(meta)` | 1791 | heartbeat.yml | alive ping |
| `send_workflow_failure(workflow_name, url)` | 1846 | on workflow failure | alert + URL |
| `send_weekend_summary(stats)` | 1873 | weekend_summary.yml | weekly recap |
| `send_pattern_report()` | 2132 | (manual) | top patterns |
| `send_weekly_intelligence(message)` | 2208 | weekly_intelligence.yml | Sunday intelligence |
| `send_digest(output_dir)` | 2516 | (composite) | post-EOD digest |

Each function uses `_esc()` for MarkdownV2 escaping (reserved chars `\_*[]()~`>#+-=|{}.!`).

#### B) Polling (Telegram → user commands)
`telegram_poll.yml` (every 10 min) calls `telegram_poll_runner.py:run()`, which loads meta + signal_history + ltp_prices and calls `poll_and_respond()`:

`poll_and_respond(meta, history, ltp_prices, window_minutes=35)` (line 370):
- `_get_updates()` reads `tg_offset.json` for the last `update_id+1`
- Advances offset after each processed update
- Per-command try/except (TG-01) so one crashing handler doesn't kill the poll
- Returns count of processed commands

#### Command handlers (16 total)

| Command | Handler | Reads | Mutates |
|---|---|---|---|
| `/status` | `_respond_status` (415) | meta.json | — |
| `/signals` | `_respond_signals` (417) | signal_history | — |
| `/stats` | `_respond_stats` (419) | signal_history | — |
| `/health` | `_respond_health` (421) | meta + system_health | — |
| `/today` | `_respond_today` (423) | signal_history + ltp_prices | — |
| `/exits` | `_respond_exits` (426) | signal_history + ltp_prices | — |
| `/stops` | `_respond_stops` (428) | signal_history + ltp_prices + stop_alerts | — |
| `/pnl` | `_respond_pnl` (430) | signal_history + ltp_prices | — |
| `/approve <id>` | `_respond_approve` (432) | brain/unified_proposals | (would mutate; Step 7 not wired) |
| `/reject <id> [reason]` | `_respond_reject` (434) | brain/unified_proposals | (would mutate; Step 7 not wired) |
| `/explain <id>` | `_respond_explain` (436) | signal_history | — |
| `/approve_rule <id>` | `_respond_approve_rule` (438) | proposed_rules | **mutates `data/mini_scanner_rules.json`** |
| `/reject_rule <id>` | `_respond_reject_rule` (440) | proposed_rules | mutates `proposed_rules.json` status |
| `/proposals` | `_respond_proposals` (442) | proposed_rules | — |
| `/patterns` | `_respond_patterns` (444) | patterns | — |
| `/help` | `_respond_help` (446) | — | — |

#### Key design observations
- `/approve` / `/reject` (brain unified) **designed but not implemented** — handlers exist but the Step 7 wiring to mutate `mini_scanner_rules.json` is deferred.
- `/approve_rule` / `/reject_rule` (legacy) **works today** for `proposed_rules.json` entries.
- All commands fetch their JSON via the poll_runner pre-load (not live during command processing) — so `/today` data is up to 10 min old.

---

## Push notifications (separate channel)

### `scanner/push_sender.py` (336 LOC)
- Sends web-push notifications via VAPID keys + service worker
- Subscriptions stored in `output/subscriptions.json` (file not currently in repo listing — possibly gitignored or not yet generated)
- PIN gating: only PIN-verified devices receive
- Called from `main.py` after morning scan completes
- Independent of Telegram

### `register_push.yml`
Manual workflow that accepts a subscription payload from the PWA + a PIN hash, appends to subscriptions.json.

---

## Bridge Telegram renderers (separate from telegram_bot.py)

| File | Purpose | Fires when |
|---|---|---|
| `scanner/bridge_telegram_premarket.py` (~530 LOC) | Render PRE_MARKET brief from bridge_state.json | premarket.yml @ 08:55 — always |
| `scanner/bridge_telegram_postopen.py` (~431 LOC) | Render POST_OPEN alert from bridge_state.json | postopen.yml @ 09:40 — conditional on `should_send_telegram` |
| `scanner/bridge_telegram_eod.py` (~492 LOC) | Render EOD digest from bridge_state.json | eod.yml @ 16:15 — always |

These import `_esc` from `telegram_bot.py` (M-08 Wave 5.1 consolidation) and use a structured renderer pattern: header → per-bucket sections → caveats → contra → alerts footer.

The escape pattern is critical (CLAUDE.md line 89): any literal between two `_esc()` calls is a MarkdownV2 leak vector for `= . + - _`. Pattern: build the message in plain strings, `_esc` the whole body once at the end.

---

## What a "TIE TIY 2.0 dashboard" would need

Going beyond what the PWA shows today:

| Section | Source files | Notes |
|---|---|---|
| **Status banner** | bridge_state.json (banner.state, color, message) | currently invisible to ui.js |
| **Signal cards** | signal_history.json + ltp_prices.json + bridge_state.json (bucket per signal) | bucket badges missing today |
| **Brain top-3 panel** | output/brain/unified_proposals.json | invisible today |
| **Cohort health table** | output/brain/cohort_health.json | Tier S/M/W badges |
| **Regime watch** | output/brain/regime_watch.json | + last shift date |
| **Portfolio exposure** | output/brain/portfolio_exposure.json | concentration cells |
| **Pending proposals queue** | proposed_rules.json + brain/unified_proposals.json | dual-source merge |
| **Decisions journal** | output/brain/decisions_journal.json | trader history |
| **Live stops** | stop_alerts.json | already in PWA |
| **System health** | system_health.json | already in health.html |
| **Weekly recap card** | weekly_intelligence_latest.json | invisible today |
| **Pattern explorer** | patterns.json | Tier validated/preliminary |
| **Contra shadow** | contra_shadow.json | research view |
| **Day timeline** | meta.json + workflow state | what workflow ran when |

10 new sources to integrate. Most are already committed to `output/` and served by GH Pages — the PWA just needs to fetch and render them.

---

## Surface comparison

|  | PWA | Telegram | Brain |
|---|---|---|---|
| **Real-time signal table** | ✅ ui.js | ❌ (snapshot only via /today) | — |
| **Real-time LTP** | ✅ ltp_prices.json | ✅ /stops /pnl | — |
| **Bucket assignment** | ❌ | ❌ | (in bridge_state) |
| **Stop alerts** | ✅ stop_alerts.json | ✅ broadcasts | — |
| **Pattern discovery** | ❌ | ✅ /patterns | (input) |
| **Rule proposals** | ❌ | ✅ /proposals /approve_rule | (output via dual-write) |
| **Brain proposals** | ❌ | ❌ (Step 7 stub) | ✅ unified_proposals |
| **Cohort health** | ❌ | ❌ | ✅ cohort_health.json |
| **Regime watch** | ❌ | (weekly digest only) | ✅ regime_watch.json |
| **Portfolio exposure** | ❌ | ❌ | ✅ portfolio_exposure |
| **Weekly intelligence** | ❌ | ✅ Sunday broadcast | (input) |
| **System health** | ✅ health.html | ✅ /health | (input) |
| **Trade execution** | ❌ | ❌ — **manual only** | — |
| **Settings / config** | ❌ | ✅ /approve_rule mutates mini_scanner_rules.json | — |

The pattern: **Telegram is the control plane** (input + commands), **PWA is the display plane** (output viewing), **Brain is the analysis plane** (proposals). The three don't fully connect today; specifically the brain's output is stuck in `output/brain/` without a digest channel or PWA view.
