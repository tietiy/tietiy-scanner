# 16 — Mini Scanner Rules Audit

Source: `data/mini_scanner_rules.json` (218 lines, schema_v3, generated_at 2026-04-25). Read in full during Round 1; this report focuses on the **gaps** and **never-activated rules**.

## Top-level state

```
shadow_mode: true       — all filter rules inactive; everything passes (only kill_patterns hard-block)
kill_patterns: 1 active
warn_patterns: []       — placeholder, never used in Phase 1
watch_patterns: 1 active
boost_patterns: 7 active
```

## The 7 filter rules — all inactive

| Rule | Active | Description |
|---|---|---|
| `min_score` | ❌ false | threshold=7. "DO NOT activate until 30 resolved signals show score correlates with WR." |
| `min_rr` | ❌ false | threshold=2.0. |
| `regime_alignment` | ❌ false (**permanently**) | "PERMANENTLY DISABLED — backtest proves Bear regime UP_TRI is highest conviction trade." |
| `require_volume` | ❌ false | "Do not activate until Phase 1 shows volume correlates with WR." |
| `grade_gate` | ❌ false | allowed=[A,B,C]. Phase 2 candidate. |
| `clean_air` | ❌ false | Phase 2 candidate. |
| `delivery_volume` | ❌ false | Phase 3 only; requires NSE Bhavcopy scraping. |

**All filter rules have been INACTIVE since the mini_scanner was shipped.** The scanner has been in pure shadow_mode for the entire 30-day observation window. Only `kill_patterns` and (informational) `watch_patterns` have actually been doing anything.

## Active kill_pattern (1)

`kill_001`: DOWN_TRI × Bank. Hard-block. 0/11 WR, −11.12% avg P&L, MFE 0%. `contra_shadow_tracked: true`.

## Active watch_pattern (1)

`watch_001`: UP_TRI × Choppy (sector wildcard). 36 signals, 31.4% WR. Source: `output/eod_anomaly_2026-04-27.md`. Informational only.

## Active boost_patterns (7)

| ID | Cohort | n | WR | Tier | Conviction |
|---|---|---:|---:|---|---|
| `win_001` | UP_TRI × Auto × Bear | 21 | 100% | A | TAKE_FULL |
| `win_002` | UP_TRI × FMCG × Bear | 19 | 100% | A | TAKE_FULL |
| `win_003` | UP_TRI × IT × Bear | 18 | 100% | A | TAKE_FULL |
| `win_004` | UP_TRI × Metal × Bear | 15 | 100% | A | TAKE_FULL |
| `win_005` | UP_TRI × Pharma × Bear | 13 | 100% | A | TAKE_FULL (under floor; flagged for review at n≥15) |
| `win_006` | UP_TRI × Infra × Bear | 12 | 87.5% | B | TAKE_FULL |
| `win_007` | BULL_PROXY × ANY × Bear | 16 | 87.5% | B | TAKE_FULL (notes: exclude Bank if kill_001 widens) |

**Observations:**
- All 7 boosts are Bear-regime cohorts. **No Bull boost.** **No Choppy boost.** This matches the empirical reality (Bear is the paying regime).
- 5 of 7 are Tier A (TAKE_FULL). 2 are Tier B (TAKE_FULL).
- Notice the mini_scanner_rules schema allows `tier=B` but the conviction_tag is still TAKE_FULL. This is a **legacy schema artifact** from when "tier B" meant "Tier B-TAKE_FULL" rather than "Tier B-TAKE_SMALL". The brain layer's newer schema (`unified_proposals.json`) correctly maps Tier B → TAKE_SMALL.

## Rules that should have fired on recent dates but didn't

Per Round 1 + Round 2 evidence:

1. **A kill_pattern targeting DOWN_TRI broadly (any sector)** would have prevented 23 of the 24 DOWN_TRI losses (the Pharma/Chem outliers are the only signals that wouldn't be blocked). The data has supported this since at least early April — `proposed_rules.json` has multiple proposals targeting Energy+DOWN_TRI but never DOWN_TRI sector-null.

2. **A warn_pattern (or kill) targeting UP_TRI × Choppy** would have flagged the 100% Choppy portfolio concentration. `watch_001` is informational only — it doesn't change bucket or alert. The 35 UP_TRI×Choppy signals at 28.6% WR all entered the live portfolio.

3. **The boost_pattern for UP_TRI × Bear × Bank (n=8, 100% WR per pattern_miner emerging tier)** has not been promoted. Pattern miner found `signal=UP_TRI_regime=Bear_sector=Bank` at 100% WR n=8, but the cohort sits as emerging (n<10). With the prop_005-006-007 kill_BULL_PROXY proposals also pending, the system has no positive boost candidate for the Bear+Bank long side.

## Deprecated / commented-out rules

None visible. The 7 inactive filter rules in `rules{}` are all still present in the JSON — they were never deleted, just kept inactive. They could activate via `/approve_rule` flipping `active: true`. Currently the active set is empty.

## Schema drift

- `boost_patterns` carry `tier=A` or `tier=B` plus `conviction_tag=TAKE_FULL` independent of tier. The newer brain-layer schema separates these (Tier A → TAKE_FULL, Tier B → TAKE_SMALL).
- `kill_patterns` have `contra_shadow_tracked: true/false`. Only `kill_001` is tracked.
- `watch_patterns` is the newest section (Phase 1, added 2026-04-27). Its schema is informational only, no `tier`, no `conviction_tag`. Multiple watches can match a signal; all warnings render.

## Verdict

**`mini_scanner_rules.json` is the trader's primary control plane**, and currently it's running with:
- 7 filter rules disabled (shadow mode)
- 1 active hard-block (kill_001)
- 1 active info-warning (watch_001)
- 7 active boosts (all Bear-regime)

This is consistent with the design ("shadow mode collects data before activating rules"). The gap is that **after 30 days of data collection, no filter rules have moved to active**, despite multiple cohorts now having confidence-gate-passing evidence (UP_TRI×Choppy meets the n≥20 + WR-gap≥15% gate as a *negative* cohort, but no Tier-negative filter rule exists to activate it as).

A defensible Round 2 action would be: **introduce a `negative_boost_pattern` or `watch_kill_pattern` rule type** that acts as a soft-kill (down-grades conviction to SKIP) for cohorts that meet the n≥20 + WR-gap≥15% gate on the loss side. Then the system's own evidence translates to action without needing a hard `kill_pattern` (which the user is reluctant to add for broad-scope cohorts).
