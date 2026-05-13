# 07 — Integration Points

What in the system reads regime today, what needs updating in v2.

## Map of regime consumers

### 1. `scanner/main.py:get_nifty_info()` (writer)
**Today:** the regime classifier itself. Writes `regime` into the signal dict that scanner_core consumes.
**v2:** extended to write F1-F9 features + v2 regime. v1 fields stay in place for shadow comparison.

### 2. `scanner/scanner_core.py:detect_signals()` (consumer at scan time)
**Today (line 270):** `stock_regime = _get_stock_regime(...)` per-stock + `nifty_pct_today` from market regime. The `regime` field on each emitted signal is the per-stock regime (Bull/Bear/Choppy per the stock's own EMA50 slope).

**Important:** This per-stock regime is COMPUTED LOCALLY in scanner_core, NOT the same as the market regime in `get_nifty_info()`. **v2 design impact: extend `_get_stock_regime` to use v2 logic for per-stock too** — adds consistency across the system.

**Files touched in v2:** `scanner_core.py:_get_stock_regime()` (~50 LOC change in Phase 5).

### 3. `scanner/scorer.py` (consumer)
**Today:** `score_signal()` uses regime in the score computation. UP_TRI × Bear gets +3 pts, UP_TRI × Bull gets +2, etc. (per `doc/tietiy_mindmap/04_signal_lifecycle.md` scoring breakdown).

**v2 impact:** add scoring for 2 new regimes (Bull-Recovery, Bear-Recovery). Initial proposal:
- UP_TRI × Bear: +3 (preserved)
- UP_TRI × Bear-Recovery: +2 (new — recovery is positive context for longs, but less than steady Bear)
- UP_TRI × Bull-Recovery: +2 (new)
- UP_TRI × Bull: +2 (preserved)
- UP_TRI × Choppy: +1 (preserved)
- DOWN_TRI × Bear: +2 (preserved, though DOWN_TRI is broken)
- DOWN_TRI × any other regime: +0 or N/A
- BULL_PROXY × Bear: +1 (preserved)
- BULL_PROXY × Bull-Recovery: +1 (new — mirror of UP_TRI behavior)

**Files touched in v2:** `scorer.py` score-table updates (~20 LOC) in Phase 5.

### 4. `scanner/mini_scanner.py` (consumer of rules)
**Today:** reads `data/mini_scanner_rules.json`. Each rule has optional `regime` field. mini_scanner matches regime field against signal's regime.

**v2 impact:** no code change required. The matcher already uses string equality on regime field. v2 just emits different string values.

**Files touched in v2:** zero code. But `data/mini_scanner_rules.json` may add new boost/kill entries with `regime=Bear-Recovery` etc. (post-validation).

### 5. `scanner/journal.py` (writer of signal_history)
**Today:** stores `regime` field on each signal record at scan time.

**v2 impact:** add `regime_v2` field alongside `regime` for forward-only attribution. Historical signals keep v1 regime; new signals get both.

**Files touched in v2:** `journal.py` schema extension (~5 LOC) in Phase 5. Optionally a schema_version bump to v6.

### 6. `scanner/outcome_evaluator.py` (consumer)
**Today:** reads regime from signal_history to compute cohort stats. Does not re-classify.

**v2 impact:** no change. Reads whatever was written by journal.py.

### 7. `scanner/bridge/composers/premarket.py`, `postopen.py`, `eod.py` (consumers)
**Today:** read `regime` field from signal_history + sometimes from a market context source.

**v2 impact:** primary regime source for bridge briefs becomes `output/regime_features.json` (the new v2 file). Read pattern:
- v2 transition pending? → show "regime is shifting to X" in brief
- v2 stable regime? → display as today's regime
- Per-signal regime in brief → still uses signal's stored regime (signal_history.regime or regime_v2 field)

**Files touched in v2:** `premarket.py`, `postopen.py`, `eod.py` regime references (~30 LOC total) in Phase 5.

### 8. `scanner/bridge/core/bucket_engine.py` (consumer)
**Today:** Gate 4 (evidence consensus) reads regime baseline cohort stats from `q_regime_baseline.py`.

**v2 impact:** `q_regime_baseline.py` uses the new v2 regime label when querying cohort_health. Otherwise no change.

**Files touched in v2:** `q_regime_baseline.py` (~10 LOC).

### 9. `scanner/bridge/queries/q_regime_baseline.py` (consumer)
**Today:** computes per-regime baseline WR from signal_history.

**v2 impact:** queries on `regime_v2` field. Falls back to `regime` field for historical signals lacking v2 attribution.

**Files touched in v2:** 1 file, ~10 LOC.

### 10. `scanner/brain/brain_derive.py:_derive_regime_watch()` (PRIMARY CONSUMER)
**Today (line 348-405):** reads `weekly_intelligence_latest.json#regime#latest#regime` as authoritative.

**v2 impact:** **the central change.** Read from `output/regime_features.json#regime` instead. This is the L2 leverage point from `doc/tietiy_mindmap/MASTER_MINDMAP.md`.

**Files touched in v2:** `brain_derive.py:_derive_regime_watch()` reimplementation (~30 LOC). Phase 5.

### 11. `scanner/brain/brain_reason.py:_run_regime_shift_detector()` (consumer)
**Today:** LLM gate that examines `regime_watch.json` distribution + reasoning_log history. Emits `regime_alert` proposals.

**v2 impact:** input becomes richer — `regime_features.json` includes `regime_pending` and `confidence_pending`. LLM prompt can incorporate the pending-state context. Major improvement to gate sensitivity.

**Files touched in v2:** `brain_reason.py:_run_regime_shift_detector()` prompt update (~20 LOC) in Phase 5.

### 12. `scanner/weekly_intelligence.py` (writer of weekly_intel)
**Today:** weekly aggregator that produces `weekly_intelligence_latest.json`. Brain currently reads from this.

**v2 impact:** continues to run weekly. Its regime field stays for backward compat. Brain stops reading from it. weekly_intelligence becomes one of many sources, not the authoritative regime source.

**Files touched in v2:** zero. Just deprecated as regime source.

### 13. `scanner/telegram_bot.py` + `scanner/bridge_telegram_*.py` (consumers)
**Today:** display regime in `/status`, `/health`, morning brief, etc. Read from meta.json or bridge_state.json.

**v2 impact:** displayed regime comes through bridge_state.json (which now reads from regime_features.json). No direct change to telegram_bot.

**Files touched in v2:** zero direct changes (downstream from bridge).

### 14. PWA (`output/ui.js`, `output/app.js`)
**Today:** does not read regime (per `doc/tietiy_mindmap/09_ui_surfaces.md` Section 1.4 — PWA blindness gap).

**v2 impact:** part of Stage 2 Day 4 PWA work, not regime v2 scope. Mentioned for completeness.

## Backward compatibility during shadow window (Phase 4)

For the 10-trading-day shadow window:

| Consumer | Reads from |
|---|---|
| brain_derive._derive_regime_watch() | **v1** (`weekly_intelligence_latest.json#regime#latest`) — unchanged |
| bridge composers | **v1** regime field on signals — unchanged |
| mini_scanner | **v1** regime gate string match — unchanged |
| `output/regime_features.json` writer | **v2** classifier output — parallel write only |
| shadow monitor script | reads both v1 and v2, logs comparison |

Production behavior identical to today during shadow. Only `regime_features.json` is new (read by nobody in production except the monitor).

## Backward compatibility post-promotion (Phase 5+)

After v2 promoted:

| Consumer | Reads from |
|---|---|
| brain_derive._derive_regime_watch() | **v2** `regime_features.json` — primary path |
| brain_derive fallback | reads `weekly_intelligence_latest.json` if v2 file missing/stale (transition safety net) |
| bridge composers | **v2** regime via bridge_state.json |
| mini_scanner | **v2** regime gate (Bear, Bull, Bull-Recovery, Bear-Recovery, Choppy) |
| historical signal_history records | retain `regime` (v1) field; new `regime_v2` field added for new signals |
| cohort_health (brain) | groups by `regime` field on signals (which is v1 for historical, v2 for new) — careful here |

### The cohort_health attribution gotcha

After promotion, cohort_health computes WR per (signal_type × regime). Historical signals have v1 regime; new signals have v2 regime. This creates a **mixed regime taxonomy** in cohort_health for ~6 months until enough v2-tagged resolved signals accumulate.

**Mitigation:** for the 6-month transition, brain emits cohort_health under BOTH `regime` (v1) and `regime_v2` axes. Operator can compare. Eventually drop `regime` cohort axis when sample size on v2 axis is sufficient (n ≥ 50 per cell).

## Summary of files touched in v2

| Phase | File | Change |
|---|---|---|
| Phase 1 | `scanner/main.py` | ~30 LOC (extend get_nifty_info + _log_regime_debug) |
| Phase 1 | `scanner/regime_classifier_v2.py` | NEW ~250 LOC |
| Phase 1 | `tests/test_regime_classifier_v2.py` | NEW ~150 LOC |
| Phase 2 | `scripts/backfill_regime_v2.py` | NEW ~100 LOC |
| Phase 3 | `scripts/validate_regime_v2.py` | NEW ~200 LOC |
| Phase 3 | `doc/regime_v2_design/known_inflections.md` | NEW manual list |
| Phase 4 | `scripts/regime_v2_shadow_monitor.py` | NEW ~80 LOC |
| Phase 5 | `scanner/brain/brain_derive.py` | ~30 LOC change |
| Phase 5 | `scanner/scorer.py` | ~20 LOC change (scoring for new regimes) |
| Phase 5 | `scanner/scanner_core.py` | ~50 LOC change (per-stock regime v2) |
| Phase 5 | `scanner/journal.py` | ~5 LOC change (schema v6) |
| Phase 5 | `scanner/bridge/composers/{premarket,postopen,eod}.py` | ~30 LOC change |
| Phase 5 | `scanner/bridge/queries/q_regime_baseline.py` | ~10 LOC change |
| Phase 5 | `scanner/brain/brain_reason.py` | ~20 LOC prompt update |
| Phase 5 | `data/mini_scanner_rules.json` | data update only |
| Phase 5 | `scanner/config.py` | ~3 LOC USE_REGIME_V2 flag |

**Total: ~1,000 LOC of new + ~200 LOC of modified.** Consistent with Phase estimates in `06_implementation_plan.md`.

## Cron / workflow changes

- **No new GitHub workflows needed.** v2 runs inside existing morning_scan.yml.
- `weekly_intelligence.yml` continues to run weekly (just no longer authoritative regime source).
- `brain.yml` reads from `regime_features.json` post-Phase 5 — no workflow change, just code change.
