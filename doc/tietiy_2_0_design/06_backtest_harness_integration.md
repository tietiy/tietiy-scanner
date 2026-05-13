# 06 — Backtest Harness Integration

The user wants to use the shadow_ops_v1 harness to backtest the 5 L99 Bull setups before plugging them into TIE TIY 2.0. This document specifies how.

## What shadow_ops_v1 already provides

The branch `shadow_ops_v1` (220 commits ahead of main; consultant-validated; 13 modules) has a forward-time validation harness designed for **one rule** (`rule_019_bear_uptri_hot_refinement`). Modules (per the README I read earlier):

| Module | Purpose |
|---|---|
| `shadow_ops/data_ingest.py` | Daily yfinance refresh; cached OHLCV + Nifty index parquets in `lab/cache/` |
| `shadow_ops/regime_classifier.py` | Computes `regime` + `sub_regime` mirror of scanner classifier |
| `shadow_ops/schemas.py` | 5 event dataclasses: ScanEvent, CandidateSignal, TradeCard, LifecycleEvent, FillSimulation |
| `shadow_ops/journal.py` | Append-only JSONL writer + reader with event_id uniqueness, atomic appends, checksum sidecars |
| `shadow_ops/daily_scan.py` | Per-day scan orchestrator: detect signals, match active rules, emit candidates + trade cards + scan event |
| `shadow_ops/lifecycle.py` | Day-by-day evaluator. Audit-faithful T+1 OPEN entry, no gap-fill, 6-day inclusive D1-D6 hold |
| `shadow_ops/read_model.py` | Regenerates `trade_cards_current.jsonl` from immutable event log |
| `shadow_ops/daily_report.py` | Operator-facing markdown digest |
| `shadow_ops/alerts.py` | Structured alert emission (CRITICAL/WARNING/INFO) + ack sidecars |
| `shadow_ops/pre_scan_check.py` | 8 preconditions verified before each daily scan |
| `shadow_ops/end_of_shadow.py` | Campaign-level review markdown |
| `shadow_ops/bootstrap.py` | Initialize a fresh campaign |
| `shadow_ops/__init__.py` | Module surface |

This is a working harness. Test coverage exists (`shadow_ops/tests/test_end_of_shadow.py`).

## What it does NOT yet handle

| Constraint | Why |
|---|---|
| Only `rule_019` is wired as a SignalDetector | `daily_scan.py` hardcodes rule_019 match logic, not a generic plug-in interface |
| 6-day inclusive D1-D6 hold is hardcoded | L99 spec says 10-day for VCP / EMA20 pullback / etc. |
| No zone-based exits | Per the rule_019 spec, exits are stop-only at swing low; no T1 scale-out, no Chandelier trail |
| No multi-rule per-day scan | The harness expects one rule to drive trade card generation |
| No Fibonacci targets | rule_019 uses fixed-R targets only |
| `regime_classifier.py` is 3-state + sub_regime (hot/warm/cold) | L99 wants 7-state |
| Counterfactual fills assume T+1 OPEN entry, no gap-fill | Need to support different entry styles per detector (e.g. EMA20 pullback enters on bullish-candle-close above EMA9) |

## Generalization plan

The harness becomes the **runner** for any SignalDetector plug-in. The detector defines the trigger; the harness defines the lifecycle.

### Phase 1: Inject the SignalDetector protocol (8 hours)

```python
# Today (shadow_ops_v1/daily_scan.py — simplified)
def daily_scan(run_dir, scan_date):
    for symbol in universe:
        ohlcv = load_ohlcv(symbol, scan_date)
        # HARDCODED rule_019 match logic here
        if matches_rule_019(ohlcv, regime, sub_regime):
            emit_candidate(...)
            
# Generalized (TIE TIY 2.0)
def daily_scan(run_dir, scan_date, detector_registry):
    for symbol in universe:
        ohlcv = load_ohlcv(symbol, scan_date)
        regime = regime_classifier.classify(...)
        for detector in detector_registry.active_for(regime.state):
            for candidate in detector.detect(ohlcv, symbol, sector, regime, ...):
                emit_candidate(candidate)
```

The change is: replace hardcoded match logic with a loop over registered detectors. The `SignalDetector` protocol (per §02) gives the detector ownership of the match logic + zones + rationale.

### Phase 2: Lifecycle parameterization (6 hours)

Each detector declares its hold semantics:

```python
class VcpDetector:
    hold_max_bars = 10
    exit_evaluator = ZoneBasedEvaluator(
        scale_out_at_t1=0.5,
        trail_after_t1=ChandelierExit(period=7, atr_mult=2.5),
        time_exit_bars=10,
    )
```

The `lifecycle.py` reads these from the detector's metadata. No hardcoded 6-day window.

### Phase 3: Multi-detector backtest (6 hours)

```bash
# Campaign config (data/shadow_run.yaml)
campaign_id: vcp_validation_2026_05
start_date: 2026-05-15
end_date: 2026-06-15
detectors:
  - name: vcp
    version: 1.0.0
    config: {max_contractions: 4, vol_dryup_pct: 0.7}
universe: data/fno_universe.csv
regime_classifier: 7state_v1
```

Run via:
```bash
.venv/bin/python -m shadow_ops.bootstrap --config data/shadow_run.yaml
.venv/bin/python -m shadow_ops.daily_scan  --run-dir <run_dir>  # for each day
.venv/bin/python -m shadow_ops.lifecycle   --run-dir <run_dir>  # process exits
.venv/bin/python -m shadow_ops.daily_report --run-dir <run_dir>
.venv/bin/python -m shadow_ops.end_of_shadow --run-dir <run_dir>
```

## Backtest result format (for "should I plug this in?" decision)

`shadow_ops/end_of_shadow.py` produces `<run_dir>/review.md`. Augment it with these decision-support sections:

```
# Campaign: vcp_validation_2026_05 — Review

## 1. Process integrity
- Trading days observed: 23 / 23 expected
- Cards proposed: 14
- Cards entered (T+1 OPEN): 12 (2 gap-invalidated)
- Cards resolved: 10 (2 still ACTIVE on review day)
- All cards walked lifecycle correctly: YES / NO
- Operator overrides logged: 0

## 2. Edge (per regime)
| Regime | n | WR | avg R | Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| Stable-Bull | 6 | 83% | +1.2 | 1.4 | -1.1R |
| Inflecting-Bear→Bull | 3 | 67% | +0.8 | 0.9 | -0.7R |
| Stable-Choppy | 3 | 33% | -0.3 | -0.4 | -2.1R |

## 3. Counterfactual fills
- Average slippage: -0.12% (entry); -0.08% (exit)
- Gap-invalidated rate: 14% (2 of 14)
- All fills deterministic? YES (verified via SHA)

## 4. CPCV (Lopez de Prado)
- 5×5 folds with 5-bar embargo
- Per-fold WR: 0.55, 0.68, 0.71, 0.62, 0.59
- No fold below 0.40: PASS
- t-statistic of average vs null: 2.31 (p=0.02)
- Brier score: 0.18 (well-calibrated: <0.25)
- ECE: 0.07 (well-calibrated: <0.10)

## 5. Decision-support flags
- PROCESS-VALIDATED: ✅
- EDGE-POSITIVE in intended regimes (Bull, Inflecting→Bull): ✅
- NO catastrophic loss (max DD < 3R): ✅
- Sample size adequate for statistical significance (n>=10): borderline (n=12)

## 6. Recommendation
RECOMMEND: paper-trade 4 weeks, then small-live (1% risk) 4 weeks.
DO NOT plug into TIE TIY 2.0 active config until small-live cumulative R > 0.
```

The detector's "validation passed" is a structured assertion in the review:
- PROCESS-VALIDATED (mechanical correctness)
- EDGE-POSITIVE in intended regimes
- NO catastrophic loss in CPCV
- Adequate sample size

ALL FOUR must be true to enable the detector in production via `data/plugins.yaml`.

## Integration with TIE TIY 2.0 plug-in registry

The same `SignalDetector` Python class definition runs in both modes:

- **Live mode** (TIE TIY 2.0 `core/orchestrator`): `detector.detect()` called nightly; positive results enter `signal_history.json`; bridge composes; brain analyzes.
- **Shadow mode** (`shadow_ops/daily_scan`): `detector.detect()` called per backtest day; results enter `<run_dir>/events.jsonl`; lifecycle simulates exits; review summarizes.

The detector's `enabled` flag in `plugins.yaml` controls live participation. Backtest campaigns ALWAYS run shadow-mode regardless of `enabled`.

**This is the key insight from the §02 contracts: one detector class, two runners.**

## Per-setup backtest budget (5 L99 setups)

Per §07 of the prior feasibility report:

| Setup | Build | Backtest | Paper | Small-live | Total to deployable |
|---|---:|---:|---:|---:|---:|
| EMA20 pullback | 8h | 1w | 4w | 4w | ~9 weeks |
| VCP breakout | 16h | 1w | 4w | 4w | ~10 weeks |
| Bull flag | 12h | 1w | 4w | 4w | ~10 weeks |
| Darvas box | 14h | 2w (sparse) | 6w | 4w | ~13 weeks |
| Cup-and-handle | 16h | 2w (sparse) | 6w | 4w | ~14 weeks |

Parallelized build + sequential graduate-to-live: first detector ready at week 9, all 5 by week 14.

## What I need from the user before backtest harness work begins

Three decisions that need to be locked, not guessed:

1. **Hold-time defaults:** L99 says 6-10 days for VCP, 10 for EMA20, 7 for Bull flag, 15 for Darvas, 15 for Cup-handle. Are these correct for NSE F&O on Indian holiday calendar? Or should they be tuned per stock liquidity?

2. **Position-sizing per detector:** Today's scoring scales to 1%/3%/5% risk via score buckets. Does the same scale apply to new detectors? Or do they each have their own risk per trade?

3. **Universe filtering per detector:** Should VCP fire on all 188 stocks? Or only liquid mega-caps? Darvas was validated on Nifty Midcap 50 per Patil 2024; the universe matters.

If these are unanswered, the backtest results are not directly comparable across detectors.

## Effort

| Task | Hours |
|---|---:|
| Generalize `daily_scan.py` for plug-in detectors | 8 |
| Lifecycle parameterization (per-detector hold + exit logic) | 6 |
| Multi-detector campaign config (`shadow_run.yaml`) | 4 |
| Augment `end_of_shadow.py` review with decision-support sections | 8 |
| CPCV implementation (purged + embargo) | 12 |
| Brier / ECE / bootstrap CI calibration metrics | 6 |
| Sample backtest run for validation (e.g. EMA20 pullback) | 4 |
| **Total harness generalization** | **~48 hours** |

Plus the 66 hours of new-detector code per §07 of feasibility. Plus per-detector compute time (40h aggregate across 5 setups for the initial CPCV pass).

**Grand total backtest-related effort: ~150 hours.** Spread over 14 weeks parallel + sequential.
