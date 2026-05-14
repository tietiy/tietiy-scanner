# Brain Review — 2026-05-14

Read-only enumeration of brain artifacts on disk. No interpretation beyond what each file states; user-action items at the bottom.

## Artifacts inventory

| Path | Size | Last modified | Source |
|---|---|---|---|
| `output/proposed_rules.json` | 68.8K | 2026-05-14 17:19 | brain (run 2026-05-14 10:05Z) |
| `output/patterns.json` | 150.4K | 2026-05-14 17:19 | pattern-miner (267 patterns) |
| `output/contra_shadow.json` | 41.8K | 2026-05-14 17:19 | brain |
| `output/system_health.json` | 0.9K | 2026-05-14 17:19 | brain |
| `output/regime_debug.json` | 4.8K | 2026-05-14 17:19 | regime classifier debug log |
| `output/weekly_intelligence_latest.json` | 4.1K | 2026-05-10 15:30 | **STALE** (4 days old) |
| `output/brain/unified_proposals.json` | 12.5K | 2026-05-13 22:48 | brain run 2026-05-13_2201 |
| `output/brain/cohort_health.json` | 15.9K | 2026-05-13 22:48 | brain |
| `output/brain/regime_watch.json` | 0.8K | 2026-05-13 22:48 | brain |
| `output/brain/portfolio_exposure.json` | 1.9K | 2026-05-13 22:48 | brain |
| `output/brain/reasoning_log.json` | 62.5K | 2026-05-13 22:48 | brain reasoning trace |
| `output/brain/ground_truth_gaps.json` | 0.4K | 2026-05-13 22:48 | brain |
| `output/brain/decisions_journal.json` | 0.2K | 2026-04-29 03:06 | empty (0 entries) |
| `output/cohort_health.json` (root) | — | **MISSING** | — |

Two distinct brain runs visible:
- Top-level files (`proposed_rules.json`, `patterns.json`, …) — generated 2026-05-14 10:05Z (today 15:35 IST), the EOD master run.
- `output/brain/*` — generated 2026-05-13 22:01 IST (yesterday's nightly brain).
The discrepancy is expected: top-level files come from the GitHub Actions EOD job, `output/brain/` from the local nightly run.

## proposed_rules.json — status detail

| Metric | Count |
|---|---|
| Total proposals | 81 |
| Pending | **47** |
| Approved | 0 |
| Rejected | 30 |
| Already active | 4 |
| New today (2026-05-14) | **3** |
| New yesterday (2026-05-13) | 4 |
| Generated at | 2026-05-14T10:05:52Z |

### 3 new proposals today

All three are Energy-sector / Choppy-regime variants — likely duplicated views of the same underlying pattern at three different granularities.

| ID | Pattern | Action | Tier | WR | n | Edge_pp | Insight |
|---|---|---|---|---|---|---|---|
| prop_079 | regime=Choppy + sector=Energy | warn | preliminary | 50.0% | 16 | -11.1pp | UP_TRI baseline 61.1% |
| prop_080 | regime=Choppy + sector=Energy + age=0 | warn | preliminary | 50.0% | 16 | -11.1pp | same |
| prop_081 | regime=Choppy + sector=Energy + grade=B | warn | preliminary | 50.0% | 16 | -11.1pp | same |

Action is `warn` (not `kill`), tier is `preliminary` (n=16). Not high-priority for approval.

## Other notable file contents

- `output/brain/regime_watch.json`: current_regime=Choppy, stability=stable, days_in_regime=7, `weekly_intelligence_age_days=5` — weekly_intelligence is stale.
- `output/brain/cohort_health.json`: 32 cohorts tracked, 291 total resolved signals, 4 baselines.
- `output/brain/portfolio_exposure.json`: 45 open positions, 3 signal types, 10 sectors, 1 regime (Choppy). 4 concentrations flagged.
- `output/brain/unified_proposals.json`: 3 proposals from the 2026-05-13 nightly. Independent stream from `proposed_rules.json`.
- `output/brain/ground_truth_gaps.json`: thin_rules=0, thin_patterns=0 — no coverage gaps.
- `output/brain/decisions_journal.json`: 0 entries (created 2026-04-29, never written to).
- `output/system_health.json`: overall=**warn**, alerts=[] (warn without explicit alert message — check the `checks` dict if investigating).
- `output/weekly_intelligence_latest.json`: 4 days stale (generated 2026-05-10). Weekly intel run schedule may have lapsed.

## What needs user action

1. **47 pending proposals** sit unreviewed; only 3 are new today. The other 44 are accumulating since 2026-04-24. No high-urgency item here, but the queue is large.
2. **Weekly intelligence is 4 days stale** — the regime watch view explicitly flags `weekly_intelligence_age_days=5`. If a weekly run is supposed to happen Sundays, last Sunday (May 10) was the latest and the next is May 17. Currently expected.
3. **system_health.json overall=warn** but no alerts populated — worth a glance at the `checks` dict to see which sub-check is degraded.
4. **decisions_journal.json empty** since creation — if it's supposed to be appended-to, the appender may be silently broken; if not used, no action.

Nothing here is an emergency. The kill_002 first production day is the more important watch item — tracked in `output/kill_002_tracking.json` (Task A).
