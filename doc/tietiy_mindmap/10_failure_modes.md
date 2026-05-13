# Dimension 10 — Failure Modes & Silent Breaks

**Generated:** 2026-05-13
**Scope:** For each component, where can it fail silently — fail without setting off a Telegram alert?

A failure is "silent" when:
- The workflow runs but produces stale/empty output, OR
- The workflow doesn't run at all and nobody notices, OR
- A downstream consumer reads the empty/stale output and proceeds as if everything is fine.

---

## The hierarchy of canaries

```
cron-job.org   ─────► GitHub Actions API  ─────► Workflow YAML
   │                       │                       │
   │ no alert if dead      │ no alert if           │ alerts via
   │                       │ rate-limited          │ alert_failure.py
   │                       │                       │
   ▼                       ▼                       ▼
heartbeat.yml (GH schedule, 08:30) ── single canary ──► Telegram
   │
   │  ⚠️ but heartbeat itself uses GH schedule (known unreliable)
   ▼
scan_watchdog.yml ── checks morning_scan landed ──► Telegram
```

There is **no canary** for cron-job.org itself. If the external cron service goes down, nothing in the repo notices. The earliest signal is the trader noticing no morning brief.

---

## Failure mode inventory

### Layer 1 — Trigger layer (cron-job.org + GH schedule)

| Failure | Detection latency | Notified? | Notes |
|---|---|---|---|
| cron-job.org account expires / credentials invalid | Whole day silent (~24h until trader notices missing 08:45 brief) | **No** | The single biggest silent-break risk |
| cron-job.org single-job disabled (e.g., bumped manually) | Whole day for that workflow | **No** | scan_watchdog will catch missing morning_scan; nothing catches missing premarket/postopen/eod |
| GH schedule misses fire (documented 2026-04-28 outage) | Per-workflow until noticed | **No** | Mitigated by migrating to cron-job.org for critical jobs (M-15) |
| GitHub auth token expires (used by cron-job.org→GH API) | Whole day silent | **No** | Token rotation has no calendar reminder in the repo |
| GitHub Actions API rate-limited | Per-call | **No** | scan_watchdog falls back to Pages meta.json (G1) |

### Layer 2 — Workflow execution

| Failure | Detection latency | Notified? |
|---|---|---|
| Workflow YAML invalid (e.g., recent edit broke `on:` block) | Push-time validation by GH | Yes (GH email) but trader may miss |
| Workflow fires but Python entry crashes early | Same-day | **Mostly Yes** via `alert_failure.py` Telegram broadcast, but only if the failure step is wrapped in `if: failure()` |
| `actions/checkout@v4` fails (git clone) | Same-day | Yes |
| `setup-python@v5` fails | Same-day | Yes |
| `pip install -r requirements.txt` fails | Same-day | Yes |
| The Python script silently produces empty output (no exception) | **None** | **No** |
| `git commit` fails (no changes to commit) | Same-day | Yes if step has `if: failure()` |
| `git push` fails (rate limit / auth) | Same-day | Mixed — some workflows retry; others alert |
| Concurrency cancel-in-progress kills run mid-write | Per-run | **No** — partial commit can leave stale data |

### Layer 3 — Python script

| Failure | Detection latency | Notified? |
|---|---|---|
| yfinance returns NaN / empty / wrong shape | Per-symbol | **Mostly No** — `fetch_failed` list in meta.json, but no Telegram alert |
| outcome_evaluator reads NaN close → returns UNKNOWN | Per-signal | **No** (EP3 fix prevents false HIT but signal stays PENDING longer) |
| signal_history.json corrupted mid-write | Whole system | Partial — atomic write via `os.rename`, but no SHA verify |
| Schema migration silently drops fields | Per-signal | **No** — journal.py uses `setdefault` for new fields; old fields not validated |
| Anthropic API timeout / 5xx | Per-gate | **No** — single retry, then `gates_skipped_due_to_failure` logged but no Telegram |
| Anthropic API quota exhausted (circuit breaker hits $5) | Single run | **No** — flagged in reasoning_log but no alert |
| Anthropic auth failure | Single run | **No** — no retry; entire brain silently produces no proposals |
| Pattern miner produces 0 patterns (drought) | Daily | **No** — empty patterns.json overwritten as "valid" |
| Rule proposer produces 0 proposals | Daily | **No** |
| Telegram bot 401 (auth) / 429 (rate limit) | Per-message | **No** — exception caught in `_get_updates`/`send_message`, logged but no fallback |
| Telegram bot polling crashes mid-window | 10 min until next poll | Recovers next cycle; user commands during outage are queued and processed late |

### Layer 4 — Data layer

| Failure | Detection latency | Notified? |
|---|---|---|
| signal_history.json grows past tolerance | None | **No** — no size cap enforced; archive_old_records moves >90d records but ad-hoc |
| signal_history.json schema_version drift | None | **No** — readers all expect v5 |
| eod_prices.json schema_version mismatch | Outcome_evaluator EOD1 path | Handled (CRIT-02 adapter, v1+v2) |
| ltp_prices.json stale (writer crashed) | Telegram /pnl shows stale ltp | **No** — UI shows fetch_time but no staleness alert |
| stop_alerts_sent.json doesn't reset daily | Duplicate alerts | Visible to trader; not auto-recovered |
| `tg_offset.json` reset (deleted / replaced) | Re-processes all queued updates | Visible (duplicate command responses) |
| mini_scanner_rules.json malformed (JSON parse fail) | Mini-scanner crashes | Yes (workflow fails) |
| weekly_intelligence_latest.json doesn't refresh on Sunday | Brain reads stale regime for the entire week | **No** — brain happily reads last-known value |

### Layer 5 — Bridge layer

| Failure | Detection latency | Notified? |
|---|---|---|
| bridge_state.json missing or corrupt | bridge_telegram_*.py reads → returns early | Yes (function returns early, but no positive alert that compose succeeded) |
| `bridge_state_history/<date>_PRE_MARKET.json` missing for L2 | L2 has no L1 reference; `bucket_changed` cannot be detected | **No** — postopen.compose() degrades silently, marks `l1_reference_available: false` in audit |
| `bridge_state_history/<date>_EOD.json` missing for brain portfolio_exposure | Brain falls back to signal_history | Visible in `portfolio_exposure.json` via warning code `eod_archive_missing` |
| 30-day history cleanup deletes a date prematurely | None | **No** |
| `should_send_telegram=false` AND a critical bucket-change happened that the logic didn't classify | Trader doesn't get alerted | **No** — depends on classification quality |

### Layer 6 — Telegram bot

| Failure | Detection latency | Notified? |
|---|---|---|
| Telegram bot token rotated without updating GH Secrets | Whole day silent | **No** |
| Telegram bot blocked / banned by user | Per-message 403 | **No** |
| Network blocked from GH Actions runners to api.telegram.org | Whole batch silent | **No** |
| Markdown V2 escape leak (CLAUDE.md §5) | One specific message | Yes — the message fails to parse; Telegram returns 400 |

### Layer 7 — PWA / GitHub Pages

| Failure | Detection latency | Notified? |
|---|---|---|
| deploy_pages.yml fails (build / artifact issue) | PWA shows stale content | **No** |
| Service worker cache too aggressive | User sees stale page | Mostly avoided (cache: 'no-store' for data JSON) — but shell files cached |
| CNAME drift / DNS issue | Site unreachable | **No** |
| Push notification subscription expired | User stops getting push alerts | **No** |
| GitHub Pages CDN lag | meta.json shows old timestamp; scan_watchdog G1 mitigates by hitting Actions API first | **No alert; mitigation only** |

### Layer 8 — Brain layer

| Failure | Detection latency | Notified? |
|---|---|---|
| Brain produces 0 proposals (all gated) | None | **No** — empty unified_proposals.json overwrites yesterday's |
| `ANTHROPIC_API_KEY` not set in GH Secrets | First run fails | **Mostly No** — Step 5 logs "gates_skipped_due_to_failure" but no Telegram |
| Brain Step 5 LLM returns malformed JSON (after retry) | Per-gate | Logged to reasoning_log, no alert |
| Brain Step 6 conflict surfacing verify-fails | Drops candidate | Logged to verification_failures.json (1000-entry cap), no alert |
| `decisions_journal.json` corrupts or grows too large | None | **No** — append-only forever, no monitoring |

### Layer 9 — Cross-cutting

| Failure | Detection latency | Notified? |
|---|---|---|
| Git history grows past repo size limit (large output/colab_export.json) | Future commits fail | Yes (push failure) |
| Disk full on GH runner (high churn) | Random workflow failure | Yes |
| One-shot migration (wave*_migration.py) leaves repo in half-state | Manual run | Yes (workflow alerts), but partial state may persist |
| Hooks (.git/hooks) interfere | Manual user action | **No** — outside CI |

---

## The weakest links — ranked by time-to-detect

| Rank | Failure | Time-to-detect | Why bad |
|---|---|---|---|
| 1 | cron-job.org account silently disabled | ~24h (trader noticing missing brief) | Brings down 11 workflows in one move |
| 2 | weekly_intelligence.yml miss on Sunday → brain reads stale regime all week | 7 days | Cascades into wrong bucketing daily |
| 3 | brain Step 7 stub (brain_telegram is no-op) | **Never auto-detected** | Trader doesn't know they aren't seeing brain proposals |
| 4 | yfinance partial failure (some symbols NaN) | Indefinite | Signals stay PENDING; only outcome_evaluator at 15:35 partially recovers via eod_prices |
| 5 | `bridge_state_history/<date>_EOD.json` missing → brain portfolio_exposure falls back to signal_history silently | Indefinite | Concentration metrics computed from less-accurate fallback |
| 6 | Pattern miner drought (0 patterns mined) | Daily | Empty patterns.json overwrites previous good one; rule_proposer also empties |
| 7 | Telegram bot token rotation forgotten | Whole day | No second channel — push notifications are PIN-gated and used only by mobile devices |
| 8 | GitHub Secrets ANTHROPIC_API_KEY expired/rotated | Whole brain run | No proposals; nobody knows until 22:05 silence |
| 9 | Repo size limit hit | Hours/days | Future commits fail; runner alerts visible |
| 10 | Postopen `should_send_telegram=false` covers up a regression | Whole day | Edge case-specific |

---

## How the system would currently detect a total outage

If everything stopped firing at midnight tonight, here's what the trader would see in chronological order:

| 08:30 IST | No heartbeat ping in Telegram | suspicion level: medium |
| 08:45 IST | No morning_scan summary | suspicion level: high |
| 08:55 IST | No bridge_telegram_premarket brief | suspicion level: certain |
| 09:30 IST | No LTP refresh visible in PWA | confirms outage |
| 16:15 IST | No EOD digest | confirms |

In other words: **the first 25 minutes are the only chance to catch a failure proactively**, and only if the trader is reading Telegram. There is no proactive page or external monitor.

---

## Mitigations that exist

| Mitigation | Where | What it catches |
|---|---|---|
| `alert_failure.py` Telegram broadcast | every workflow's `if: failure()` step | workflow-level Python crashes |
| `scan_watchdog.yml` | dispatched at 09:02 | morning_scan miss |
| G1/G9 Wave 4 fixes in scan_watchdog | scan_watchdog.yml | CDN lag, dedup |
| Atomic writes (`os.rename`) | journal.py, state_writer.py, brain_state.py | mid-write corruption |
| Schema version field in 8+ JSON files | journal, eod_prices_writer, patterns, etc. | reader-side migration adapters |
| Backup snapshots | backup_manager.yml + eod_master step 1 | restore source-of-truth |
| `signal_history.backup.json` | journal.py before every mutation | undo last day's writes |
| CRIT-02 schema adapter | outcome_evaluator | legacy eod_prices schema |
| EP3 NaN guard | eod_prices_writer | yfinance returning NaN at 1 AM |
| BX8 dedup persist | stop_alert_writer | repeat-alert spam |
| G2/G6 sanity check | stop_alert_writer | bad-data ghost stops |
| chain_validator (CRIT-03) | eod_master step 8 | post-chain anomaly detection (sets system_health.json) |
| circuit breaker | brain_reason.py | LLM cost runaway |

---

## Mitigations that DON'T exist yet (gaps)

1. **No external uptime monitor.** No third-party service pings cron-job.org or the Pages site. The repo is self-monitoring, which fails for trigger-layer outages.
2. **No SLA dashboard.** `system_health.json` exists but is one-shot per day; no rolling history of "% of expected fires that succeeded in the last 7 days."
3. **No anomaly alert on JSON shape.** Empty `proposed_rules.json` or empty `patterns.json` is treated as valid data; no "expected at least 5 patterns/day; got 0".
4. **No "regime stale" warning.** If `weekly_intelligence_latest.json` hasn't updated in >10 days, no alert.
5. **No "brain proposals stale" warning.** unified_proposals.json could be 5 days old and the PWA wouldn't show it.
6. **No deploy_pages alert.** A Pages deploy failure is invisible.
7. **No Telegram delivery confirmation.** `send_*` functions don't verify the message landed (just that the API call succeeded).
8. **No DNS / CNAME check.** If tietiy.in DNS breaks, neither the bot nor any GH workflow notices.
9. **No "cron-job.org last-fire" tracker.** Each workflow could record its last-fire time in a small file; absent any file update for >24h could be a heartbeat. Not implemented.
10. **No staleness alert on signal_history.** If outcome_evaluator silently writes nothing, PENDING signals just stay PENDING — there's no "signals stuck for X days" alert.

---

## Recommendations (defer; documentation-only)

For a future hardening pass:
- Add a `cron-job.org last-fire` heartbeat file written by every workflow; a separate daily check workflow alerts if any file is >25h stale.
- Add an external uptime monitor (UptimeRobot etc.) for tietiy.in.
- Promote `chain_validator.system_health` from a daily one-shot to a rolling 7-day view visible in PWA.
- Add "regime staleness" warning that fires if `weekly_intelligence_latest.json` is older than 8 days.
- Add Telegram delivery confirmation by reading the Telegram API response and logging message_id.
- Make `brain_telegram` (Step 7) functional so brain proposals reach the trader.
- Add anomaly alert when `len(patterns)` or `len(proposed_rules.proposals)` drops to 0.
