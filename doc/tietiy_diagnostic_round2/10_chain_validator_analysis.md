# 10 — Chain Validator

Source: `scanner/chain_validator.py` (~470 LOC, first 120 read for header). Output: `output/system_health.json`.

## Purpose

Observability layer for the daily intelligence chain. Reads side-effect files (not git logs) to validate that each step of `eod_master.yml` produced expected output. Runs at step 6 of `eod_master.yml` (per M-12 it should be later — known cosmetic bug).

## Seven checks performed

| Check | Reads | Pass criterion |
|---|---|---|
| 1. morning_scan | `meta.json` | `market_date == today AND signals_found > 0` (or non-trading day) |
| 2. open_validate | `open_prices.json` | date is today |
| 3. eod_update | `eod_prices.json` | today's date present |
| 4. outcome_eval | `signal_history.json` | mtime today |
| 5. pattern_miner | `patterns.json` | `generated_at` today |
| 6. rule_proposer | `proposed_rules.json` | `generated_at` today |
| 7. contra_tracker | `contra_shadow.json` | structurally valid (existence-only on no-fire days) |

## Live state (last run 2026-04-28 10:06 UTC)

```
overall: warn
checks:
  morning_scan:   ok    "Scanned 188 stocks, 6 signals"
  open_validate:  ok    "2 opens validated"
  eod_update:     warn  "No symbol has 2026-04-28 data yet"
  outcome_eval:   ok    "286 records, 94 pending, 192 resolved"
  pattern_miner:  warn  "Last run: 2026-04-27"
  rule_proposer:  warn  "Last run: 2026-04-27"
  contra_tracker: ok    "2 shadows (R:0 P:2)"
alerts: []
```

Three of seven checks are WARN. None ERROR. M-12 (step ordering) explains pattern_miner + rule_proposer staleness on validation read — they actually ran fine ~125 ms later but chain_validator already cached the previous-day timestamps.

## Gating behavior

**Chain validator is purely observability — it does NOT gate signal acceptance.** Its `system_health.json` is read by:
- L1 premarket Telegram brief (renders "DEGRADED" subtitle in the morning brief banner)
- Future PWA health card (not yet built per session_context)
- Brain's `cohort_health.json` references it indirectly via the `r_multiple_under_day6_dominance` warning

Even on `overall: error`, the scanner still runs the next day. The validator only informs the operator.

## What it has caught

From the live state above:
- The M-12 step-ordering daily false-positive (chain_validator runs before pattern_miner writes today's file → reads yesterday's timestamp → fires WARN). Fix proposed but not shipped.
- `eod_update` WARN today because EOD prices weren't yet computed when chain_validator ran (timing race).

What it has **not** caught (because it doesn't check these):
- The 31 stale/dangerous proposals in `proposed_rules.json` (no semantic validation, just freshness).
- The 3 PENDING brain proposals that expired 2026-05-06 (the brain layer is outside the validator's check set).
- The Choppy regime conflation in `regime_debug.json`.

## Verdict

**Chain validator works as designed — observability, not gating.** Its main limitation is that it doesn't surface anything past "file is fresh". A useful Round 2 extension would be to add a semantic check that scans `proposed_rules.json` for proposals targeting signal=null (broad-scope kills) — these are unsafe by definition and should warn before any operator runs `/approve_rule prop_011`.
