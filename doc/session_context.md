# TIE TIY Session Context — Start Here

**Purpose:** Drop-in context for any new Claude session. Read this instead of recalling memory piecemeal.
**Read order:** This file → `fix_table.md` → `engineering_dock.md` → `roadmap.md`
**Last updated:** 2026-04-20

-----

## 30-Second Project Summary

TIE TIY is a personal NSE equity scanner + decision-support system for Abhishek, a discretionary positional trader in India. It scans 188 F&O stocks daily, detects 3 signal types (UP_TRI, DOWN_TRI, BULL_PROXY), scores them 0–10, tracks for 6-day windows, and delivers alerts via Telegram + PWA.

Built solo on iPad via Safari + GitHub web editor + Google Colab. Python + yfinance + GitHub Actions + GitHub Pages. **iPad-only workflow means full file rewrites, no diffs.**

**Repo:** tietiy/tietiy-scanner · **URL:** tietiy.github.io/tietiy-scanner/ · **Chat ID:** 8493010921

-----

## Current Production State (2026-04-20)

|Metric               |Value                                                                |
|---------------------|---------------------------------------------------------------------|
|Phase                |**Phase 2 UNLOCKED**                                                 |
|Live resolved signals|118 (true unique ~86 after -REJ dedup note)                          |
|Win rate             |81% (96W / 22L)                                                      |
|Avg P&L per trade    |+4.02%                                                               |
|Open positions       |58                                                                   |
|Scan days            |9                                                                    |
|Universe             |188 F&O stocks, 14 sectors in CSV                                    |
|Signal types live WR |UP_TRI 95% (n=83), DOWN_TRI 18% (killed via kill_001), BULL_PROXY 75%|
|Active kill rules    |kill_001 (DOWN_TRI+Bank)                                             |
|Shadow mode          |ON — all signals pass, kill_patterns hard-block                      |

**Schema version:** 5 (record-level), 4 (meta).

-----

## Non-Negotiable Trading Rules

- Entry at 9:15 AM IST next trading day after signal detection
- Stop-loss placed immediately at entry
- Exit at open of Day 6
- Max 5% capital per trade
- No moving stop, no adding to position
- Stop hit intraday = exit same day
- R:R 2.0+ strong, 1.5 acceptable, below 1.5 reduce size

-----

## Backtest-Validated Signal Rules (20yr, 110 stocks)

- **UP_TRI:** No EMA50 filter. Ages 0–3 valid. All regimes. ~87–88% WR. Bear regime = highest conviction (avg +4.85%). Stop never hit in backtest.
- **DOWN_TRI:** No regime filter. **Age 0 ONLY.** ~87–89% WR. Edge gone at age 1+. (Live data shows 18% WR — investigation ongoing, kill_001 firing correctly on Bank sector)
- **BULL_PROXY:** Trend filter kept. Ages 0–1 only. ~67% WR. ~20% stop rate. (Live 75% WR, small sample)

-----

## Scoring System

- UP_TRI: Age0=+3, Age1=+2. Bear regime=+3, Bull=+2, Choppy=+1
- DOWN_TRI: +2 flat all regimes
- BULL_PROXY: Bull/Choppy=+1 only
- Quality: vol_confirm+1, sec_leading+1, rs_strong+1, grade_A+1
- Max = 10. stock_regime stored on every signal (not in scoring yet — Phase 3)

-----

## Architecture — Daily Flow

```
08:30 IST  heartbeat.yml           → alive ping to Telegram
08:45 IST  morning_scan.yml        → main.py morning (21 steps)
09:02 IST  scan_watchdog.yml       → verify scan fired
09:15 IST  [MARKET OPENS]          → trader places entries/exits manually
09:27 IST  open_validate.yml       → 9:15 open prices + gap% + D6 resolution
09:30 IST  ltp_updater.yml         → every 5min (staggered)
09:32 IST  stop_check.yml          → every 5min (+2min offset)
15:35 IST  eod_master.yml          → 8-step chain: backup→outcomes→EOD→telegram→chain→patterns→proposals→commit
           Saturdays 09:00         → weekend_summary.yml
           Mondays 08:30           → gap_report.yml
           Sundays 20:00 IST       → weekly_intelligence.yml
```

**Cron triggers:** All via cron-job.org using `workflow_dispatch` (no `schedule:` blocks in YAML, so GitHub cron drift doesn’t apply).

-----

## Trigger Words (Skip Intro, Jump Into Work)

- `apex` / `kabu` → full TIE TIY context
- `morningstar` / `vedu` → GitHub scanner context
- `lucifer` → Colab backtest context
- `fixlog` → bug fix mode
- `uibuild` → UI redesign mode
- `phase2` → Phase 2 build mode

-----

## Working Method (Locked with User)

1. **No code without explicit “start” command.** Audit and discussion are fine; touching files requires green light.
1. **At the start of each fix, Claude lists files needed.** User points or pastes. Then Claude writes the fix once.
1. **If Claude is uncertain mid-fix (weird field, unclear intent), Claude stops and asks.** No guessing.
1. **One cycle per fix, not three.** Ship-then-debug is banned.
1. **All file deliveries are complete rewrites.** No diffs (iPad workflow).
1. **Verify after each fix:** run Master Check manually, confirm green.

-----

## Execution Sequence (Locked)

|Order|Session      |Contents                                                                     |Status  |
|-----|-------------|-----------------------------------------------------------------------------|--------|
|1    |**Session A**|9 items: C-01 through C-04, C-05 deferred, D1, M-11, L-05, UX-01, P-01       |PENDING |
|2    |**Session B**|10 items: C-05, H-03, H-08, H-09, M-01, M-06, M-07, UX-02, UX-03, UX-05      |PENDING |
|3    |**Session 4**|UI build — 12 items (UI2–UI12) per memory entry 29                           |PENDING |
|4    |**Session C**|Quality + polish — D3, H-06, H-07, M-02, M-05, M-08, UX-04, L-01 through L-04|PENDING |
|—    |Phase 3+     |F2, F3, M-09, M-10, P-02, P-03, D6, D7, UX-06                                |DEFERRED|

**See `fix_table.md` for the full 39-item execution plan.**

-----

## Critical Open Incidents (as of Apr 20)

Five silent-breakage items blocking the intelligence loop. Must be fixed before auto-apply or contra promotion can work.

1. **C-01** — `contra_tracker` writes to wrong directory (relative path)
1. **C-02** — `rule_proposer` reads/writes wrong directory (same class of bug)
1. **C-03** — Contra shadow writer/reader schema mismatch
1. **C-04** — `/approve_rule` command broken (tuple vs dict)
1. **C-05** — `eod_prices.json` schema mismatch, primary-source optimization dead

These were all introduced in Apr 20 ship (contra_tracker + rule_proposer) or never worked since EOD1 was designed. See `fix_table.md` for fix approach.

-----

## Key Design Principles

1. `signal_history.json` is persistent truth. All other JSONs are overlays.
1. `price_feed.py` abstraction: yfinance now, 5paisa as plug-in swap later (one-line config).
1. Mini scanner shadow mode collects data before activating rules. Don’t activate on insufficient n.
1. Confidence gates before any rule activation: n≥20, confidence≥85%, WR gap≥15% vs baseline.
1. Atomic writes critical for `signal_history.json` integrity.
1. Every ship has a defined rollback path (e.g., `eod_update.yml.bak`).

-----

## Files You Will Need To See Frequently

### Orchestration

- `scanner/main.py` — 500+ line orchestrator, 21 steps
- `scanner/config.py` — constants, paths, price source toggle
- `scanner/calendar_utils.py` — trading day / holiday / next-trading-day helpers
- `scanner/universe.py` — CSV loader

### Detection / Scoring

- `scanner/scanner_core.py` — signal detection (UP_TRI, DOWN_TRI, BULL_PROXY, SA variants)
- `scanner/scorer.py` — 0–10 score with quality bonuses
- `scanner/mini_scanner.py` — shadow-mode filter + kill_patterns enforcement

### Persistence

- `scanner/journal.py` — owns `signal_history.json` + `signal_archive.json`
- `scanner/meta_writer.py` — `meta.json` + `nse_holidays.json`
- `scanner/backup_manager.py` — dated backups

### Outcome / Price

- `scanner/outcome_evaluator.py` — resolves OPEN signals, writes outcome fields
- `scanner/open_validator.py` — 9:15 open price, gap%, entry_valid, D6B trigger
- `scanner/ltp_writer.py` — LTP fetch every 5min
- `scanner/stop_alert_writer.py` — stop proximity, breach alerts
- `scanner/eod_prices_writer.py` — 3:35 EOD OHLC snapshot
- `scanner/price_feed.py` — yfinance/5paisa abstraction (currently only ltp_writer uses it)

### Intelligence (Apr 20 ship — 3 of 5 broken)

- `scanner/pattern_miner.py` — discovers edges/failures in resolved signals ✓
- `scanner/chain_validator.py` — system health report (needs C-05 fix)
- `scanner/contra_tracker.py` — **BROKEN C-01+C-03**
- `scanner/rule_proposer.py` — **BROKEN C-02**
- `scanner/weekly_intelligence.py` — ✓
- `scanner/auto_analyst.py` — planned, not yet built

### Delivery

- `scanner/telegram_bot.py` — 11 message types + command handler (**C-04 in `_respond_approve_rule`**)
- `scanner/html_builder.py` — writes index.html shell with cache-bust
- `scanner/push_sender.py` — VAPID web push
- `output/ui.js`, `app.js`, `journal.js`, `stats.js`, `sw.js` — PWA frontend

### Recovery / Diagnostic

- `scanner/recover_stuck_signals.py` + `.github/workflows/recover_struck_signals.yml` (note typo — L-05)
- `scanner/diagnostic.py` — multi-mode health check
- `scanner/deep_debugger.py` — signal forensics

-----

## Verification Infrastructure Reality Check

- `verify_fixes.py` / `verify_fixes.yml` — **DO NOT EXIST.** Planned Phase 2 item, never built.
- AICREDITS_API_KEY — **NOT SET.** Planned AI audit integration, not live.
- Master Check (`master_check.yml`) covers: Tier 1 syntax, Tier 2 imports, Tier 3 safe execution + 7 inline checks. **No logic validation layer.**
- After each code change: run Master Check → confirm green → that’s the current verification gate.

-----

## Behavioral Gap (P-01) — The Biggest Vision Risk

Roadmap success metric: “Positive P&L tracked in personal Google Sheet, correlated with scanner’s claimed outcomes.”

**This is not happening yet.** Scanner claims 81% WR but no broker-statement correlation exists. Until this ritual is established (weekly 15 min, 3-column sheet), the 90-day validation phase cannot complete.

**P-01 is a behavioral fix, not a code fix.** Priority for Session A.

-----

## What To Say At Session Start

If you (the user) land in a new chat with a fresh Claude and want to skip the full recall:

> “Read `doc/session_context.md` then `doc/fix_table.md` in the project knowledge. Then [your task].”

Or use a trigger word — `apex`, `phase2`, `fixlog` — which memory entry 1 decodes into the same context.

-----

## Change Log

|Date      |Change                                               |
|----------|-----------------------------------------------------|
|2026-04-20|Initial creation post-master-audit. Locked with user.|
