# 11 — Weekly Intelligence

Source: `scanner/weekly_intelligence.py`. Output: `output/weekly_intelligence_latest.json`. Schedule: Sun 20:00 IST via `weekly_intelligence.yml` (GitHub native schedule).

## Purpose

Once-weekly aggregator that consumes:
- `patterns.json` → top validated patterns
- `proposed_rules.json` → pending + already-active proposals
- `contra_shadow.json` → kill-shadow inverted-trade tracker
- `regime_debug.json` → week's regime distribution
- `system_health.json` → daily chain status
- `mini_scanner_rules.json` → active kill rules
- AI suggestions (template-based, not LLM)

Output is the Sunday Telegram digest (long-form) used to orient the trader for the week ahead.

## Live content of `weekly_intelligence_latest.json`

- `generated_at: 2026-04-26T16:26:20Z`
- `week_range: ["2026-04-19", "2026-04-26"]`

### Baselines (from embedded patterns block)

| Signal | n | WR | Avg PnL |
|---|---:|---:|---:|
| UP_TRI | 83 | 95.2% | +6.18% |
| BULL_PROXY | 21 | 66.7% | +4.51% |
| DOWN_TRI | 21 | 19.0% | −7.00% |

### Top validated patterns (3 shown)

1. `age=0_grade=B` — 64.3% WR, n=70, edge −30.9pp (negative)
2. `regime=Bear_sector=Bank` — 47.6% WR, n=21, edge +28.6pp (positive — but see §08 for the WR-edge-with-negative-PnL paradox)
3. `age=0` — 66.7% WR, n=75, edge −28.5pp (negative)

### Proposals snapshot (10 total)

- 6 PENDING (prop_001-prop_005 + later) — kill Energy (×4 duplicates), kill BULL_PROXY (×1), prop_005 kill BULL_PROXY (n=11, WR 45.5%, edge −21.2pp)
- 4 already_active — kill DOWN_TRI×Bank (kill_001 equivalents, duplicates of the same rule)

### Regime week

- `days_logged: 5` — ALL Choppy
- `avg_slope: −0.00007` (essentially zero)
- `avg_ret20: +5.09%` (recovery underway)
- `latest (2026-04-24): slope=+0.0036, ret20=+7.38, above_ema50=true, classified_as=Choppy`

### Health

- `overall: warn`
- `checks_passed: 3, checks_failed: 2`

### Kill rules

- `kill_001` only.

### Contra tracker

- `total: 1, resolved: 0, pending: 1, unlock_threshold: 30` (need 29 more resolved shadows to unlock decision).

## Number of weekly reports on disk

Only ONE weekly report present:
```
output/weekly_intelligence_latest.json  (2026-04-26)
```

No `weekly_intelligence_2026-04-19.json`, no `weekly_intelligence_2026-04-12.json`, etc. The script appears to overwrite `_latest.json` rather than archiving dated copies. Backups dir has `signal_history.2026-04-2[4|5|7|8].json` but no weekly_intelligence backups.

Per `session_context.md`, the schedule is "Sundays 20:00 IST via weekly_intelligence.yml". So we should have had runs on:
- Sun 2026-04-19
- Sun 2026-04-26 (on disk)
- Sun 2026-05-03 (the `git log` shows a commit `chore: weekly intelligence report 2026-05-03 17:13 UTC [skip ci]` on `main` — but the JSON wasn't merged into this branch)
- Sun 2026-05-10 (would be the most recent; not on disk)

So **on this branch (`shadow_ops_v1`)**, only one weekly report is preserved. The 2026-05-03 report exists on `main` (per the commit message) but hasn't been merged.

## What 4 weeks of reports would say collectively

Since only one report exists here, I cannot compose a 4-week trajectory. From the single Apr-26 report alone:
- The system was already in 5-day Choppy stretch with positive slope (post-Bear recovery indicators).
- 6 proposals were sitting in PENDING — and the next brain run (Apr 29) would add 3 more LLM-judged proposals on top.
- Health was WARN, not green, suggesting the chain was already showing freshness issues.

## Verdict

**Weekly intelligence works mechanically, but its outputs aren't archived for trend analysis.** The Sunday-only cadence means the operator gets a snapshot once a week, but the dataset can't answer "is the WR trending down week-over-week?" without manual diffing across `signal_history` backups. The brain layer's daily snapshots in `output/brain/history/` partially fix this for cohort-level views but not for weekly aggregate.
