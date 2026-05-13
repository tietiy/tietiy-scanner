# 01 — What Ports Cleanly from Current TIE TIY

Audit of `~/code/tietiy-scanner` `main` branch (and `shadow_ops_v1` where the same module is unchanged) for porting to a TIE TIY 2.0 repo.

## Scoring rubric

| Score | Meaning |
|---|---|
| ⭐ CLEAN PORT | Self-contained, well-typed, no entanglement with broken pieces. Lift as-is. |
| 🔧 PORT WITH ADAPTER | Reusable core logic but tangled with current data shape. Needs a thin adapter. |
| 🔄 REFACTOR | Idea worth keeping but code needs ≥50% rewrite. |
| 🚫 LEAVE BEHIND | Tied to broken or deprecated semantics. Re-derive from scratch. |
| 💀 ZOMBIE | Already disqualified by audits / proven negative-edge. Do not port. |

## Module-by-module

| Module | LOC | Rating | Hours to port | Notes |
|---|---:|---|---:|---|
| `scanner/scanner_core.py` `add_indicators` | ~30 | ⭐ | 0.5 | Pure EMAs/ATR/volume. No deps. |
| `scanner/scanner_core.py` `detect_pivots` | ~25 | ⭐ | 0.5 | Numpy-only pivot detection. |
| `scanner/scanner_core.py` `build_zones` | ~45 | 🔧 | 2 | Already zone-aware but ATR-offset; replace with Fib retracements per L99. |
| `scanner/scanner_core.py` `add_zone_proximity` | ~10 | ⭐ | 0.5 | Zone overlap. Works as-is. |
| `scanner/scanner_core.py` UP_TRI detection | ~60 | 🔧 | 3 | Point-based stop → swap for zone-based stop. Detection logic sound. |
| `scanner/scanner_core.py` BULL_PROXY detection | ~60 | ⭐ | 1 | **+1.13R cohort** in Bear regime. Already zone-anchored stop. Clean port. |
| `scanner/scanner_core.py` DOWN_TRI detection | ~50 | 💀 | 0 | Disqualified: 17.4% WR, no target path. Do not port. |
| `scanner/scanner_core.py` SA detection (UP_TRI_SA, DOWN_TRI_SA) | ~280 | 🚫 | 0 | Second-attempt logic depends on parent stop-out; complexity not justified by data. |
| `scanner/scanner_core.py` `_get_stock_regime` | ~20 | 🚫 | 0 | Per-stock regime via slope is duplicative of market regime; not used downstream. |
| `scanner/scorer.py` `score_signal` | ~60 | 🔄 | 4 | Score formula is reasonable but non-monotonic in practice (AN-04 hypothesis). Re-derive scoring from new signal taxonomy. |
| `scanner/scorer.py` `calc_target` | ~25 | 💀 | 0 | Returns `None` for everything except UP_TRI×Bear. Replace with `calc_zone_target` per Fib framework. |
| `scanner/scorer.py` `get_exit_rule` | ~6 | 💀 | 0 | Hard-coded `Target2x` for UP_TRI×Bear only. Replace with regime-aware target rule. |
| `scanner/scorer.py` `calc_position_size` | ~20 | ⭐ | 1 | Score-based risk tiers. Logic is portable; just plug into new score values. |
| `scanner/mini_scanner.py` `_check_kill_patterns` | ~30 | ⭐ | 0.5 | Pure function. Reusable. |
| `scanner/mini_scanner.py` `_trigger_contra_shadow` | ~20 | ⭐ | 1 | Useful for tracking inverted-trade shadows. |
| `scanner/journal.py` (35 KB) | ~900 | 🔧 | 12 | Owns `signal_history.json`. Schema v5 carries 80+ fields; new schema would be cleaner. Port the **atomic-write + dated-backup** patterns, redesign the record shape. |
| `scanner/outcome_evaluator.py` | ~600 | 🚫 | 0 | Built for Day-6 forced-exit semantics + STOP_HIT/TARGET_HIT. Re-derive for zone-based outcomes. |
| `scanner/open_validator.py` | ~600 | 🔄 | 8 | 9:27 IST gap + entry-valid logic is good. Needs adapter for new schema. |
| `scanner/ltp_writer.py` | ~440 | 🔧 | 6 | yfinance/5paisa abstraction via price_feed.py. Port and modernize. |
| `scanner/stop_alert_writer.py` | ~480 | 🔧 | 6 | Stop-proximity logic is sound; adapt to zones. |
| `scanner/calendar_utils.py` | ~300 | ⭐ | 1 | IST helpers, holiday calendar. Pure utilities. |
| `scanner/main.py` (38 KB orchestrator) | ~1200 | 💀 | 0 | 21-step orchestrator hard-coded to current architecture. Re-derive from new module contracts. |
| `scanner/diagnostic.py` | ~900 | 🔧 | 8 | Multi-mode health check. Useful patterns; needs new check set. |
| `scanner/chain_validator.py` | ~470 | 🔧 | 4 | 7 file-freshness checks. Useful; redesign check list. |
| `scanner/pattern_miner.py` | 539 | 🔄 | 16 | Useful concept (feature-combo mining) but the WR-edge-vs-baseline metric is structurally flawed (R2 §08 — top_positive can be negative-PnL). Rewrite to use absolute-PnL + Wilson-bound. |
| `scanner/rule_proposer.py` | ~500 | 🚫 | 0 | Has produced 31 stale/dangerous proposals (R2 §15). The brain layer's LLM gate path is the intended replacement. |
| `scanner/contra_tracker.py` | ~350 | ⭐ | 3 | Sound design for inverted-shadow tracking. Schema-portable. |
| `scanner/weekly_intelligence.py` | ~500 | 🔧 | 8 | Sunday aggregator. Useful template; redesign aggregations. |
| `scanner/auto_analyst.py` | — | — | 0 | **Doesn't exist on any branch** (phantom doc reference). Do not port. |
| `scanner/brain/brain_input.py` | ~80 | ⭐ | 1 | Truth-file loader. Clean. |
| `scanner/brain/brain_derive.py` | ~700 | 🔧 | 12 | 4 derived views: cohort_health, regime_watch, portfolio_exposure, ground_truth_gaps. Sound but tied to current schema. |
| `scanner/brain/brain_verify.py` | ~900 | ⭐ | 8 | Deterministic guards before LLM gates. Pure functions, well-tested. |
| `scanner/brain/brain_reason.py` | ~1300 | 🔧 | 16 | 3 LLM gates with Opus 4.7. Port the gate framework; redesign inputs/outputs. |
| `scanner/brain/brain_output.py` | ~1000 | 🔧 | 10 | Unified queue + dual-write. Clean architecture; redesign for new schema. |
| `scanner/brain/brain_telegram.py` | ~10 | ⭐ | 0.5 | Trivial wrapper. |
| `scanner/brain/brain_state.py` | ~150 | ⭐ | 2 | State persistence. Clean. |
| `scanner/brain/brain_cli.py` | ~30 | ⭐ | 0.5 | CLI entry. Trivial. |
| `scanner/bridge/core/sdr.py` | ~80 | ⭐ | 1 | Signal Decision Record dataclass. Reusable shape. |
| `scanner/bridge/core/display_hints.py` | ~150 | ⭐ | 2 | Pure functions for SDR.display. |
| `scanner/bridge/core/state_writer.py` | ~120 | ⭐ | 2 | Atomic writes + 30-day retention. Reusable utility. |
| `scanner/bridge/core/error_handler.py` | ~100 | ⭐ | 2 | 3-severity safe_run + emergency state. Reusable. |
| `scanner/bridge/core/bucket_engine.py` | 478 | ⭐ | 6 | 4-gate decision tree. **Architecturally sound; could be the seed of the new ConfluenceGate interface.** |
| `scanner/bridge/core/evidence_collector.py` | ~200 | ⭐ | 3 | Orchestrates 10 queries. Reusable. |
| `scanner/bridge/rules/thresholds.py` | 85 | ⭐ | 1 | Single-source-of-truth constants. Reusable verbatim. |
| `scanner/bridge/rules/validity_checker.py` | ~80 | ⭐ | 2 | Gate 2 R:R + age checks. Reusable. |
| `scanner/bridge/rules/boost_matcher.py` | ~80 | ⭐ | 1 | Gate 3. Reusable. |
| `scanner/bridge/rules/kill_matcher.py` | ~80 | ⭐ | 1 | Gate 1. Reusable. |
| `scanner/bridge/rules/watch_matcher.py` | 107 | ⭐ | 1 | Phase 1 watch_pattern. Reusable. |
| `scanner/bridge/queries/_registry.py` | ~50 | ⭐ | 1 | Plugin auto-discovery. Reusable. |
| `scanner/bridge/queries/q_*.py` (10 query plugins) | ~80 each | ⭐ | 6 | All plugin-shape; reusable as templates. |
| `scanner/bridge/composers/{premarket,postopen,eod}.py` | ~600 each | 🔧 | 18 | Phase-aware composers. Sound design; redesign content for new schema. |
| `scanner/bridge_telegram_*.py` (3 renderers) | ~16 KB each | 🔧 | 12 | MarkdownV2 escape patterns are gold; redesign content. |
| `scanner/universe.py` | ~50 | ⭐ | 0.5 | CSV loader for `data/fno_universe.csv`. Reusable. |
| `scanner/telegram_bot.py` | ~600 | 🔧 | 8 | Telegram poller + 11 command handlers + canonical `_esc`. Port `_esc` verbatim; redesign command set. |

## Aggregate effort to port

Sum of "hours to port" column (CLEAN + ADAPTER + REFACTOR only; skipping ZOMBIE and LEAVE BEHIND):

| Bucket | Modules | Hours |
|---|---:|---:|
| ⭐ Clean ports | 30 modules | ~52 |
| 🔧 Port with adapter | 14 modules | ~123 |
| 🔄 Refactor (≥50% rewrite) | 4 modules | ~36 |
| **Total port effort** | **48 modules** | **~211 hours** |

At 30 productive hours/week: **~7 weeks** of pure porting work. Add design + test + integration + new-feature build (V5 gate, Fib framework, 5 Bull setups, 7-state regime, self-learning brain): another 4-8 weeks.

## Highest-value clean ports

If TIE TIY 2.0 is built, these are the foundation:

1. **`bridge/core/bucket_engine.py`** — Already implements a 4-gate decision tree with thresholds, evidence consensus, and clean separation of concerns. **Could be the literal seed of the ConfluenceGate interface.** ~6 hours to integrate.
2. **`bridge/rules/thresholds.py`** — Single-file source of all numeric constants. ~1 hour.
3. **`bridge/core/{sdr, state_writer, error_handler, display_hints}`** — Reusable utilities. ~7 hours total.
4. **`brain/brain_verify.py`** — Deterministic pre-LLM guards. ~8 hours.
5. **`calendar_utils.py`** — IST + trading-day calendar. ~1 hour.

## What absolutely must NOT port

- ❌ DOWN_TRI detector (17.4% WR; no target path; no profitable sub-population at n≥10).
- ❌ `scorer.calc_target` and `get_exit_rule` (only handle UP_TRI×Bear).
- ❌ `main.py` orchestrator (38 KB hard-coded to current schema).
- ❌ `outcome_evaluator.py` (built for Day-6 forced-exit; new system uses zone exits + time-exit at day 10).
- ❌ `rule_proposer.py` (has produced 31 stale/dangerous proposals; brain replaces).
- ❌ `auto_analyst.py` (doesn't exist anywhere; phantom doc reference).
- ⚠️ Pattern miner's "top_positive" labeling logic (R2 §08 — can label losing cohorts positive).
- ⚠️ Existing UP_TRI×Bear and BULL_PROXY×Bear cohorts as-is. The shadow_ops_v1 Phase 3 audits explicitly disqualified all current UP_TRI/BULL_PROXY rules — the cohorts may be **zombies** (apparent edge from sample bias). New TIE TIY 2.0 should re-audit these from scratch before depending on the published 94.7% WR / +1.13R numbers.

## Rating for the proven cohorts (the user's specific ask)

- **UP_TRI detector** (Bear regime, 94.7% WR / +0.61R live): code is portable (🔧, 3 hours) but **the cohort's published edge is under audit dispute**. shadow_ops_v1 Phase 3 process audits (rule_019_bear_uptri_hot_refinement) accepted ONLY a narrowed subset (sub_regime=hot). The current open-ended UP_TRI×Bear at full universe may not survive the same audits. Treat the 94.7% as a *production-observed* number that needs re-validation under purged-CPCV + embargo before becoming a TIE TIY 2.0 first principle.
- **BULL_PROXY detector** (+1.13R Bear): code is clean (⭐, 1 hour), but again, no Phase 3 audit exists. Per the architecture doc line 100: "Zero deployable Bull-regime rules survive W3 + Phase 3" — and BULL_PROXY×Bear, despite being a long signal, lives in Bear regime so the audit qualification ambiguity is real. Same caveat.
