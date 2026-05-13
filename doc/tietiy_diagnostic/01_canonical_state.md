# 01 — Canonical State Summary

Source files: `doc/session_context.md`, `doc/fix_table.md`, `data/mini_scanner_rules.json` (read-only).

## Architecture

- Daily flow: 08:30 heartbeat → 08:45 morning_scan → 09:27 open_validate → 9:30+ ltp/stop loops → 15:35 eod_master → **22:00 brain.yml → 22:05 brain_digest.yml**.
- 188 NSE F&O universe.
- 3 signal types: UP_TRI (long), DOWN_TRI (short), BULL_PROXY (long).
- Scoring 0-10 (age + regime + quality bonuses); actions DEPLOY/WATCH/CAUTION/NO_TRADE.
- Mini scanner runs in **shadow_mode** — only `kill_patterns` hard-block.
- **Bridge Layers 1-4** all SHIPPED (Wave 2/3 complete 2026-04-26 → 2026-04-28).
- **Brain Layer 1-7 backend SHIPPED** 2026-04-29; PWA Monster tab (Step 8) deferred to Wave UI pending ≥1 week of trader feedback.

## Live performance baseline (from `output/brain/cohort_health.json`, as-of 2026-04-28)

Total resolved: 181.

| Cohort | n | WR | avg PnL | R-mult | Tier |
|---|---:|---:|---:|---:|---|
| UP_TRI baseline (all) | 131 | 76.7% | +3.85% | — | — |
| BULL_PROXY baseline (all) | 24 | 66.7% | +4.28% | — | — |
| **DOWN_TRI baseline (all)** | **24** | **17.4%** | **−6.20%** | — | — |
| UP_TRI × Bear | 96 | **94.7%** | +5.87% | +0.61 | **M** |
| UP_TRI × Choppy | 35 | **28.6%** | −1.66% | −0.08 | Candidate |
| BULL_PROXY × Bear | 16 | 87.5% | +7.03% | +1.01 | **W** |
| BULL_PROXY × Choppy | 8 | 25.0% | −1.22% | −0.33 | Candidate |
| **DOWN_TRI × Bear** | **21** | **20.0%** | **−6.94%** | **−0.58** | Candidate |
| DOWN_TRI × Choppy | 3 | 0.0% | −1.03% | −0.18 | Candidate |
| DOWN_TRI × Bank (kill_001) | 11 | 0.0% | −11.12% | −0.86 | Candidate |
| UP_TRI × Auto | 15 | 86.7% | +6.50% | +1.07 | **W** |
| UP_TRI × Metal | 15 | 100.0% | +7.68% | +0.85 | **M** |
| UP_TRI × FMCG | 11 | 90.9% | +6.49% | +0.47 | **W** |

## Active rules

- **kill_001:** DOWN_TRI + Bank. Hard-blocks. Evidence: 0/11 WR live, −11.12% avg PnL, 0% MFE. Contra-shadow tracked.
- **watch_001:** UP_TRI × Choppy (info-only warning). Evidence: 36 signals, 31.4% WR (Apr 17 cluster).
- 7 active `boost_patterns` (5 Tier A, 2 Tier B) — all `regime=Bear` cohorts.
- All 7 filter rules (`min_score`, `min_rr`, `regime_alignment`, etc.) are `active: false`.
- `regime_alignment` rule is **PERMANENTLY DISABLED** per design — would block the best signals.

## Non-negotiable trading rules (from session_context)

- Entry 9:15 AM IST next trading day after detection.
- Stop placed immediately at entry.
- Exit at **open of Day 6** (forced time-exit) **unless** rule==`Target2x` (only UP_TRI×Bear today).
- Max 5% capital per trade.
- No moving stop, no adding.
- Stop hit intraday = exit same day.

## Known open investigations (from fix_table)

- **INV-01 (PARTIALLY RESOLVED, monitor):** DOWN_TRI live vs backtest divergence. Apr 6-8 short-squeeze drove 7/9 DOWN_TRI losses (78% of bleed). All resolved DOWN_TRIs were Bear regime. 3 Choppy DOWN_TRIs open were the decisive test (LUPIN/OIL/ONGC).
- **D-8 / exit_logic_redesign_v1.md (NOT YET DRAFTED):** Day-6 forced-exit dominates outcomes; on 2026-04-27, 35/36 resolutions exited via Day 6. R-multiple cohort classification noted as underclassifying because target-hits are rare.
- **prop_001 (DEFERRED):** DOWN_TRI restriction. Gated on Apr 27-29 Choppy DOWN_TRI resolutions.
- **H-04 / D3 (BLOCKED):** kill_001 bank-scope narrowing — pending prop_001.
- **H-06 (PENDING):** sector taxonomy gap (14 CSV tags vs 8 scored).
- **prop_005 (SHIPPED as parallel shadow track):** TARGET_R_MULTIPLE_SHADOW=3.0 computed alongside live 2.0 — not a real fix, infrastructure only.

## Production-fire user actions pending (from session_context)

- `ANTHROPIC_API_KEY` GitHub secret (without it Step 5 LLM gates fail).
- cron-job.org dashboard entries for `brain.yml` (22:00 IST) and `brain_digest.yml` (22:05 IST) and `eod.yml` (16:15 IST).

## Design principles to preserve

1. `signal_history.json` is persistent truth; all other JSONs are overlays.
2. Proof-Gated Approval: every structural change ships with claim + evidence + counter-evidence + expected effect + reversibility.
3. Bridge is **read-only**; only `outcome_evaluator` mutates `signal_history.json`.
4. **Human approval mandatory** for all rule activations — no auto-execute.
5. Confidence gates for rule activation: `n ≥ 20 · confidence ≥ 85% · WR gap ≥ 15% vs baseline`.
