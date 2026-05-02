# Bear Regime — Production Posture

**Status:** COMPLETE for all 3 cells; production deployment posture
varies per cell (1 deployment-ready, 2 DEFERRED with provisional filters).
**Date:** 2026-05-02 night (updated post-BULL_PROXY cell completion)
**Branch:** `backtest-lab`
**Scope:** Wave 5 brain integration handoff specification for Bear regime
**Companion docs:** [`synthesis.md`](synthesis.md),
[`decision_flow.md`](decision_flow.md),
[`synthesis_llm_analysis.md`](synthesis_llm_analysis.md).

This document specifies how the Bear regime cells should be consumed by
the production scanner / Wave 5 brain layer. It is the contract between
the Lab's cell research and the production decision engine.

---

## Bear regime cells — production readiness (FINAL)

| Cell | Status | Confidence | Sessions | Production action |
|---|---|---|---|---|
| **Bear UP_TRI** | ✅ COMPLETE | HIGH (lifetime-validated) | 3 | Sub-regime gated; **shadow-deployment-ready** |
| **Bear DOWN_TRI** | DEFERRED | LOW | 1 | kill_001 + provisional wk2/wk3 filter (default OFF) |
| **Bear BULL_PROXY** | DEFERRED | LOW | 1 | Provisional HOT-only filter (default OFF) |

### Initial production deployment scope

**Primary:** Bear UP_TRI cell with sub-regime gating per [`decision_flow.md`](decision_flow.md).

**Secondary (default OFF):**
- Bear DOWN_TRI provisional filter (wk2/wk3 + non-Bank → TAKE_SMALL).
  Manual enable only after ≥30 more live signals validate the filter.
- Bear BULL_PROXY provisional filter (HOT sub-regime only → TAKE_SMALL).
  Manual enable only after Bear UP_TRI deployment success.

**Universal KILL rules** (apply regardless of cell deployment status):
- kill_001 — Bank × Bear DOWN_TRI → REJECT (already in production)
- vol_climax × Bear BULL_PROXY → REJECT (new from BULL_PROXY P2)
- December × Bear UP_TRI → SKIP (lifetime −25pp catastrophic)
- Health × Bear UP_TRI → SKIP (lifetime hot 32.4% — only sector where hot fails)

---

## Sub-regime detector requirement

Production scanner must compute the daily Bear sub-regime label before
per-signal action determination.

### Detector specification

Source: `lab/factory/bear/subregime/detector.py`

```python
def detect_bear_subregime(nifty_vol_percentile_20d, nifty_60d_return_pct):
    """Tri-modal Bear sub-regime classifier.
    Returns one of: "hot", "warm", "cold", "unknown".
    """
    vp = nifty_vol_percentile_20d
    n60 = nifty_60d_return_pct
    if vp is None or n60 is None:
        return "unknown"
    if vp > 0.70:
        if n60 < -0.10:
            return "hot"     # late-stage capitulation
        elif n60 < 0:
            return "warm"    # volatile bottoming (S2 finding)
        else:
            return "cold"    # high vol but recovering
    return "cold"            # low vol → cold default
```

### Where it runs

**Once per trading day**, in the pre-market composer (8:55 IST), as part
of universe-level state computation. The label is shared across all
Bear UP_TRI signals fired that day.

### Output format

`output/current_subregime.json` (extended from Choppy detector spec):

```json
{
  "scan_date": "2026-05-02",
  "primary_regime": "Bear",
  "subregime_per_regime": {
    "Bear": {
      "label": "hot",
      "confidence": 75.0,
      "vol_percentile": 0.825,
      "nifty_60d_return": -0.142,
      "expected_wr_range": "65-75%"
    },
    "Choppy": {...},
    "Bull": {...}
  }
}
```

### Failure modes

| Failure | Handling |
|---|---|
| `nifty_vol_percentile_20d` missing | label = "unknown"; default to most conservative cascade (treat as cold no-match → SKIP) |
| `nifty_60d_return_pct` missing | label = "unknown"; same handling |
| Edge case: vol_percentile = 0.70 exactly | strict `>` → cold (boundary favors safety) |
| Edge case: 60d_return = -0.10 exactly | strict `<` → warm (boundary favors warm-not-hot) |

---

## Per-signal decision flow (Bear UP_TRI)

Production scanner integration with per-signal Bear UP_TRI logic:

```python
def bear_uptri_action(signal, market_state, phase_status):
    """
    Returns: ("TAKE_FULL"|"TAKE_SMALL"|"SKIP", sizing_modifier, reason)
    """

    # 1. Mismatch rules (universal — apply regardless of sub-regime)
    if signal.sector == "Health":
        return ("SKIP", 0.0,
                "Health UP_TRI hostile in Bear hot (lifetime 32.4%)")
    if signal.month == 12:
        return ("SKIP", 0.0,
                "December catastrophic for Bear UP_TRI (-25pp lifetime)")

    # 2. Sub-regime detection
    sub = detect_bear_subregime(
        market_state.nifty_vol_percentile_20d,
        market_state.nifty_60d_return_pct,
    )

    # 3. Phase-5 hierarchy override
    if phase_status == "PHASE_5_VALIDATED":
        sizing = 1.0 if sub in ("hot", "warm") else 0.5
        return ("TAKE_FULL" if sizing == 1.0 else "TAKE_SMALL",
                sizing, f"Phase-5 override; sub-regime={sub}")

    # 4. Standard cascade
    if sub == "hot":
        # Trader heuristics
        if signal.repeat_name_within_6d:
            return ("TAKE_SMALL", 0.5, "hot but repeat-name cap")
        if signal.same_day_count >= 3:
            return ("TAKE_FULL", 0.8, "hot but day-correlation cap")
        return ("TAKE_FULL", 1.0, "hot Bear UP_TRI")

    if sub == "warm":
        return ("TAKE_FULL", 1.0,
                "warm Bear UP_TRI (live evidence: n=42 95% WR)")

    # cold
    if (signal.feat_day_of_month_bucket == "wk4"
            and signal.feat_swing_high_count_20d == "low"):
        return ("TAKE_FULL", 1.0,
                "cold Tier 1: wk4 × swing_high=low (61.4% lifetime)")

    return ("SKIP", 0.0,
            "cold sub-regime, no Tier 1 match — edge collapses to ~50%")
```

---

## Honest WR calibration for the trader

Production scanner should communicate WR expectations to the trader at
signal time. Use these calibrated ranges (NOT live April 2026's 94.6%):

| Sub-regime | Expected production WR |
|---|---|
| hot Bear UP_TRI | **65-75%** (lifetime hot 68.3%; live includes Phase-5 selection bias) |
| warm Bear UP_TRI | **70-90%** (live evidence n=42 95.2%; lifetime warm cohort untested) |
| cold + Tier 1 (wk4 × swing_high=low) | **58-65%** (lifetime cold Tier 1 61.4%) |
| cold no Tier 1 | SKIP (edge ≈ 50%) |

### Trader emotional preparation

The cell has been operating at 94.6% WR in live data. Production at scale
will run at 65-75% WR in hot conditions. **This means more drawdowns,
larger losing streaks, and higher emotional stress** than the live
window suggested.

Expected losing-streak distributions (rough — at 70% WR):
- 1-loss streaks: frequent
- 2-loss streaks: ~9% of streaks (vs 0.3% at 94% WR)
- 3-loss streaks: ~2.7% (vs <0.1% at 94% WR)

Trader should prepare for **3-4 consecutive losing trades** to be a
normal occurrence in production, not a sign the system is broken.

---

## Risk management requirements

### Position sizing rules (per-signal)

| Action | Sizing | Stop-loss policy |
|---|---|---|
| TAKE_FULL in hot/warm | full position | tight (1×ATR below entry) |
| TAKE_FULL in cold + Tier 1 | full position | wider (1.5×ATR) — cold has more variance |
| TAKE_SMALL (any reason) | half position | normal (1×ATR) |
| TAKE_FULL_80 (day correlation) | 80% position | normal (1×ATR) |

### Portfolio-level rules

1. **Max 5 concurrent Bear UP_TRI positions** (across all sub-regimes).
   In hot/warm conditions, signals fire frequently; without cap, portfolio
   becomes single-strategy single-day-correlated.

2. **Day-correlation cap.** If 3+ Bear UP_TRI signals fire on the same
   day, size each at 80% of normal.

3. **Repeat-name cap.** If a stock fires Bear UP_TRI within 6 trading
   days of a previous Bear UP_TRI signal in the same name, downgrade
   to TAKE_SMALL regardless of sub-regime.

4. **Sub-regime transition handling.** When sub-regime exits hot
   (Bear regime weakening), close OPEN Bear UP_TRI positions opportunistically.
   Do NOT enter new positions in cold without Tier 1 match.

5. **December portfolio freeze.** Suspend Bear UP_TRI scanning entirely
   in December — the −25pp lifetime lift makes the cell uneconomic.

---

## Integration points with existing scanner

### Reads from existing infrastructure

The cell consumes these existing scanner outputs:
- `scanner/main.py` — Phase 5 validation status per signal
- `output/feature_pipeline/*` — 114-feature library values per signal
- `output/regime_classifier.json` — primary regime label (Bear/Choppy/Bull)
- NIFTY OHLCV → derived: vol_percentile_20d, 60d_return

### Writes to existing infrastructure

- `output/current_subregime.json` (new file; PRE_MARKET composer writes)
- `output/bridge_state.json` (existing) — extend with `bear_uptri_action`
  field per signal
- `decisions_journal.jsonl` (Wave 5) — log per-signal action + reason
  for Bayesian learning

### Bridge composer integration

```python
# composers/premarket.py — extend existing pre-market composer
def compose_premarket(scan_date):
    # ... existing logic ...

    # NEW: compute sub-regime labels for active regimes
    nifty_state = get_nifty_universe_state(scan_date)
    subregime_labels = {
        "Bear": detect_bear_subregime(
            nifty_state.vol_percentile_20d,
            nifty_state.nifty_60d_return,
        ),
        "Choppy": detect_choppy_subregime(...),
        "Bull": ...,
    }

    state["subregime_per_regime"] = subregime_labels
    write_state(state, scan_date)
```

### Per-signal action emission

```python
# scanner/main.py or barcode_match.py — extend per-signal logic
def emit_signal_action(signal, market_state, phase_status):
    if signal.regime == "Bear" and signal.signal_type == "UP_TRI":
        action, sizing, reason = bear_uptri_action(
            signal, market_state, phase_status)
    elif signal.regime == "Choppy" and signal.signal_type == "UP_TRI":
        # Existing Choppy UP_TRI logic
        ...
    # ... other cells ...

    return action, sizing, reason
```

---

## Wave 5 brain integration handoff

### Brain digest format extension

Bear UP_TRI signals in the daily Telegram digest should include:
- Signal action (TAKE_FULL / TAKE_SMALL / SKIP)
- Sub-regime label (hot / warm / cold)
- Expected WR range ("65-75%" / "70-90%" / etc.)
- Decision reason (audit trail)

### Approval / rejection handlers

The `/approve` and `/reject` Telegram handlers should respect sub-regime
gating:
- If trader approves a SKIP'd signal (manual override), log to journal
  with `override_subregime` flag
- If trader rejects a TAKE_FULL signal, log to journal with rejection
  reason; brain learning should incorporate over time

### Smarter-every-day reasoning_log

The brain's reasoning_log should track:
- Per-day sub-regime classifications
- Actual outcomes vs expected WR ranges
- Sector/calendar override hits
- Phase-5 validation status flow

This enables periodic recalibration: if hot Bear UP_TRI's 30-day WR
drops below 60%, surface as a cell health alert.

---

## Open questions / future work

### Bear regime broader

1. **Bear DOWN_TRI cell** — apply 5-step methodology. Per T3 plan,
   ~3 sessions of work. Expected outcome: DEFERRED (live n=11 too thin)
   or narrow filter found.

2. **Bear BULL_PROXY cell** — third Bear cell. Live n=13 at 84.6% WR.
   Apply same methodology. Expect HIGH live confidence with significant
   lifetime gap.

3. **Bear regime synthesis** — once all 3 cells complete, build
   regime-wide L1-L5 (analogous to Choppy synthesis). Cross-cell
   patterns may emerge.

### Architectural

1. **Vol_percentile universality** — Sonnet 4.5 questioned whether vol
   is the right primary axis for Bear and Bull. Run feature importance
   per regime to validate or refute.

2. **Bear detector v2 with warm zone** — currently the detector
   classifies based on hard thresholds. Lifetime warm cohort is
   untested. Quarterly Phase-5 re-runs will populate.

3. **Soft thresholds + Phase-5 hierarchy** — Sonnet 4.5 recommended
   replacing hard thresholds with confidence scores. Defer to v2
   detector work.

### Production observability

1. **Sub-regime stability metrics** — how often does the daily label
   flip? Day-to-day stability measures detector quality.

2. **Per-sub-regime WR tracking** — production should track 30-day
   rolling WR per sub-regime to catch regime drift.

3. **Sector × sub-regime WR matrix** — populate from production data
   to validate S1 lifetime stratification holds in current regime.

---

## Files in scope for production deployment

When Wave 5 brain integration occurs, these files become production
inputs (read-only from production code, lab can update via factory work):

| Lab file | Production consumer | Update cadence |
|---|---|---|
| `lab/factory/bear/subregime/detector.py` | composer/premarket.py | per cell session |
| `lab/factory/bear_uptri/playbook.md` | barcode_match.py logic | per cell session |
| `lab/factory/bear_uptri/lifetime/synthesis.md` | reference doc | per cell session |
| `lab/factory/bear/PRODUCTION_POSTURE.md` | this file (handoff spec) | per Bear regime change |

Bear DOWN_TRI and BULL_PROXY playbooks will be added when those cells
complete.

---

## Production deployment checklist

Before Wave 5 brain enables Bear UP_TRI cell logic:

- [ ] Bear sub-regime detector deployed in pre-market composer
- [ ] `current_subregime.json` writes confirmed in scan logs
- [ ] Per-signal `bear_uptri_action()` integrated into scanner main flow
- [ ] Telegram digest extended with sub-regime label + expected WR range
- [ ] Trader briefed on calibrated WR expectations (65-75%, NOT 94.6%)
- [ ] Risk-management rules (sizing, repeat-name, day-correlation) coded
- [ ] December freeze logic implemented
- [ ] Health sector exclusion logic implemented
- [ ] First production run shadow-mode (log decisions but don't act) for
  ≥10 trading days
- [ ] Compare shadow-mode actions to manual trader review; calibrate

After successful shadow run → enable live Bear UP_TRI cell production.

---

## Known gaps surfaced in final review (Sonnet 4.5 critique)

The following gaps were surfaced in S3 review and should be addressed
before live (non-shadow) production deployment. See
`lab/factory/bear_uptri/_v3_review.md` for full critique.

### Gap 1 — Warm zone WR calibration is statistically dishonest

The warm zone calibration (70-90% expected) is based on n=42 at 95.2%
WR. Binomial 95% CI on 40/42 is **84-99%**, not 70-90%.

**Action required:** Either (a) trust the data and use 80-95% expected
WR for warm (collapsing toward hot's 65-75%), OR (b) collapse warm
into hot until lifetime warm cohort accumulates ≥200 signals via
quarterly Phase-5 re-runs.

**Recommendation:** Option (b) — treat warm as "hot pending validation".
Use hot's 65-75% expected WR. Don't reward unverified single-window
performance with optimistic calibration.

### Gap 2 — Rule precedence ambiguity in multi-cap scenarios

Concrete unresolved scenarios:
1. **Phase-5 + Health sector**: Phase-5 says execute; Health mismatch
   says SKIP. Which wins?
2. **December + Phase-5 + hot regime**: All three conflict.
3. **Day-correlation cap + repeat-name cap**: Do they stack
   multiplicatively (0.8 × 0.5 = 40% size) or take the most
   conservative (0.5)?
4. **Max position cap (5) + Phase-5 hot Tier 1**: Force closure or
   skip the new signal?

**Action required:** Define precedence hierarchy in scanner code. Per
S2 architectural critique:
```
Phase-5 hierarchy override > sector mismatch > calendar mismatch > sub-regime cascade
```
Cap stacking: take MOST conservative single cap (no multiplication).
Max position: skip new signal; do not force-close existing positions.

### Gap 3 — Exit rules + stops not specified per sub-regime

The cell specifies entry gating and sizing per sub-regime but says
nothing about exits. Open questions:
- Same stop ATR multiplier across sub-regimes?
- If sub-regime shifts mid-trade (hot → cold), does the position
  exit early or hold to target?
- Hold-time variation across sub-regimes (hot may mean-revert in 2
  days; cold+Tier 1 may need 5)?

**Action required:** Build exit logic appendix to v3 playbook. Default
provisional rules:
- All sub-regimes: 1×ATR initial stop, exit at signal-day low
- Hold horizon: D5 default (per Bear UP_TRI Phase 4 evidence)
- Mid-trade sub-regime shift: tighten stop to entry, hold to first
  profit target

### Gap 4 — Signal strength tiering within sub-regime missing

Within hot, all signals get TAKE_FULL — but a hot+Phase-5+Tier 1
signal is stronger than hot+no-Phase-5+no-Tier-1. The 2×2 combinatorial
matrix is unspecified.

**Action required:** Build signal strength matrix:

| Hot/Warm | Phase-5 | Tier 1 (wk4 × swing) | Action | Sizing |
|---|---|---|---|---|
| ✓ | ✓ | ✓ | TAKE_FULL+ | full + bonus |
| ✓ | ✓ | ✗ | TAKE_FULL | full |
| ✓ | ✗ | ✓ | TAKE_FULL | full |
| ✓ | ✗ | ✗ | TAKE_NORMAL | full |

This needs lifetime evidence per cell — defer to L4 stratification
revisit in next session.

### Gap 5 — Performance monitoring + pause triggers missing

No "halt deployment for audit" criteria specified. Production drift
detection rules:

**Required pause triggers:**
- Hot regime WR < 60% over rolling 40 trades (2σ below 70%)
- Cold + Tier 1 WR < 50% over rolling 30 trades
- Any sub-regime experiences 5+ consecutive losses
- Detector classification flips daily for 3+ consecutive trading days

When triggered: pause new Bear UP_TRI entries, surface in Telegram
brain digest, manual review by trader.

### Gap 6 — Warm zone boundary dead zone undefined

`60d_return = -0.0001` is technically warm; `+0.0001` is cold. Same
economic state, different cascade. Tiny return changes shouldn't flip
TAKE_FULL → SKIP.

**Action required:** Define dead zone:
- `−0.02 < 60d_return < 0` → classify as cold for conservative
  execution (avoid boundary flicker on near-zero returns)

### Gap 7 — Regime stability filter missing

Bear sub-regime can flicker on 2-3% vol changes. A signal entered in
hot may transition to cold mid-trade.

**Action required:** Add stability filter:
- Require 3+ consecutive trading days in same sub-regime before
  switching production posture
- OR use 5-day rolling average of vol_percentile and 60d_return as
  detector inputs (smooths daily noise)

---

## Pre-deployment action list

Before Wave 5 brain enables Bear UP_TRI cell production:

| # | Action | Owner | Required for |
|---|---|---|---|
| 1 | Sub-regime detector deployed in pre-market composer | scanner team | initial |
| 2 | `current_subregime.json` writes confirmed | scanner team | initial |
| 3 | `bear_uptri_action()` integrated into scanner main flow | scanner team | initial |
| 4 | Telegram digest extended with sub-regime + WR range | brain team | initial |
| 5 | Trader briefed on 65-75% calibration (NOT 94.6%) | trader | initial |
| 6 | Risk-management rules (sizing, repeat-name, day-correlation) coded | scanner team | initial |
| 7 | December freeze logic | scanner team | initial |
| 8 | Health sector exclusion | scanner team | initial |
| 9 | **GAP 1: Decide warm calibration (collapse vs trust)** | trader + lab | pre-live |
| 10 | **GAP 2: Code rule precedence + cap stacking** | scanner team | pre-live |
| 11 | **GAP 3: Define exit rules per sub-regime** | trader + lab | pre-live |
| 12 | **GAP 5: Performance monitoring + pause triggers** | brain team | pre-live |
| 13 | **GAP 6: Warm boundary dead zone** | scanner team | pre-live |
| 14 | **GAP 7: Regime stability filter** | scanner team | pre-live |
| 15 | First production run shadow-mode for ≥10 trading days | brain + trader | live gate |

Items 1-8 are minimum required to start shadow mode. Items 9-14 must
be addressed before live (non-shadow) deployment.

---

## Bear vs Choppy regime comparison

Both regimes have been comprehensively investigated. Architectural
parallels and differences:

| Property | Choppy | Bear |
|---|---|---|
| Sub-regime structure | tri-modal (quiet / balance / stress) | tri-modal (hot / warm / cold) |
| Primary axis | `nifty_vol_percentile_20d` | `nifty_vol_percentile_20d` (shared) |
| Secondary axis | `market_breadth_pct` (cross-section) | `nifty_60d_return_pct` (longitudinal) |
| Cells investigated | 3 (UP_TRI / DOWN_TRI / BULL_PROXY) | 3 (UP_TRI / DOWN_TRI / BULL_PROXY) |
| Cells reaching HIGH confidence | 1 (UP_TRI v2) | 1 (UP_TRI v3) |
| Cells DEFERRED | 1 (DOWN_TRI) | 2 (DOWN_TRI + BULL_PROXY) |
| Cells KILLED | 1 (BULL_PROXY) | 0 (BULL_PROXY DEFERRED, not KILL) |
| Live-vs-lifetime gap (UP_TRI) | F1 +23pp → +1.7pp lifetime | +38.9pp |
| Phase 5 yield | UP_TRI 22% match rate | UP_TRI 100% validation, 0 BULL_PROXY combos |

### Architectural pattern (per Sonnet 4.5 BS1 critique)

> **"Primary axis = regime definition, secondary axis = risk flavor"**

- Choppy is defined by directionless oscillation → primary axis is vol
  (high vol = violent chop, low vol = dull chop) and secondary is breadth
  (cross-sectional sync vs rotation).
- Bear is defined by sustained decline → primary axis is vol (panic vs
  grind) and secondary is 60d_return (oversold vs capitulation).
- Bull (predicted) will use trend_persistence × leadership_concentration.

The tri-modal structure (extremes matter; tails behave differently) appears
universal. **Per-regime sub-regime detectors with regime-specific axes is
the correct architectural pattern.** Don't unify.

---

## Bull regime preparation notes

Bull regime work is the natural next phase. Key differences from Bear
work:

### No live Bull data (currently)

Apr-May 2026 has 0 Bull-classified live signals. All Bull cell
investigation must be **lifetime-only** (similar to Bear DOWN_TRI's
0-Phase-5-winners fallback):

- Skip Phase 5 winners-vs-rejected differentiator step (no winners exist)
- Use lifetime stratification + sub-regime detection from start
- Provisional findings only; production deployment awaits Bull regime
  return + ≥30 live signals
- Expected ~3-5 sessions per cell (faster than Bear due to no Phase 5
  step)

### Predicted Bull architecture (from Bear UP_TRI S2 critique)

Per Sonnet 4.5 architecture review of Bear detector:

| Bull cell candidate | Primary axis hypothesis | Secondary axis hypothesis |
|---|---|---|
| Bull UP_TRI | trend_persistence_60d | leadership_concentration |
| Bull DOWN_TRI | (likely contrarian short — defer until live) | — |
| Bull BULL_PROXY | trend_persistence_60d | sector momentum dispersion |

### Cross-cell predictions for Bull (from BS1 LLM analysis)

Sonnet 4.5 predicted these patterns will **replicate in Bull regime**
with different features:

1. **Same-feature direction-flip across cells** will replicate. Predicted
   feature: `pullback_depth` or `consolidation_duration` will show
   opposite preferences across Bull breakout cells vs Bull retracement
   cells.

2. **Calendar inversion across direction** may flip in Bull regime.
   Bullish cells in Bear preferred wk4 (month-end rebalancing flow);
   Bull regime may shift this.

3. **Hot Bull sub-regime** (predicted: very high trend_persistence +
   broad leadership) should favor LONG positions universally — same as
   Hot Bear pattern.

4. **vol_climax** will likely remain anti for BULL_PROXY across regimes
   (capitulation breaks support — mechanism-intrinsic).

### Bull regime cell sequence plan (proposed, awaiting confirmation)

| Cell | Priority | Estimated sessions | Rationale |
|---|---|---|---|
| Bull UP_TRI | First | 2-3 | Methodology proven in bullish-direction setups (parallel to Bear UP_TRI) |
| Bull BULL_PROXY | Second | 2 | Likely strong cell (lifetime data should show clean structure); tests cross-cell direction-flip prediction |
| Bull DOWN_TRI | Third | 1-2 | Likely DEFERRED (contrarian short in Bull) — apply Bear DOWN_TRI lessons |
| Bull regime synthesis | Fourth | 1 | Cross-cell consolidation; comparison to Bear/Choppy |

**Total estimated Bull regime work:** 6-9 sessions over 1-2 weeks.

### Phase 4.5 cluster analysis recommendation (from BS1 LLM)

Before Bull regime work, consider implementing **Phase 4.5: Cluster
Analysis** in the Lab pipeline. After Phase 4 walk-forward, take all
combinations with 4+ profitable trades (not 8+) and run hierarchical
clustering on feature vectors. If a cluster of 3-4 similar combinations
collectively achieves 12+ trades with consistent performance, promote
the cluster centroid to Phase 5.

This addresses the "rare-but-robust" cell problem (Bear BULL_PROXY's 0
Phase 5 combos) by capturing fragmented evidence that the current 8-trade
threshold misses.

---

## Open questions for production integration

1. **Sub-regime detector deployment timing.** Per-day pre-market composer
   (computes once, shared across signals) or per-signal (slower but
   captures intraday regime shifts)? Recommendation: per-day for v1.

2. **Phase-5 status field — where stored?** Currently in
   `combinations_live_validated.parquet`; production scanner needs
   query-ready access at signal time.

3. **Provisional filter enablement UX.** How does trader toggle
   `bear_downtri_provisional_enabled` and `bear_bullproxy_provisional_enabled`
   flags? Telegram command? Settings file? Recommendation: settings file
   read by composer at scan time.

4. **Trader heuristics implementation location.** Repeat-name cap and
   day-correlation cap require state lookup (recent signals same-name,
   same-day). Scanner main loop or Wave 5 brain layer? Recommendation:
   brain layer (already does signal aggregation).

5. **Calibrated WR display in Telegram digest.** Show "expected 65-75%"
   alongside each signal? Risk: anchoring trader to a range. Benefit:
   manages emotional response to drawdowns.

6. **Schema design for cell variety.** UP_TRI is filter+cascade;
   DOWN_TRI is provisional+kill_extension; BULL_PROXY is provisional
   HOT-only. How to express all 3 in unified scanner schema?

7. **Default behavior config.** Skip-on-unmatched (conservative) or
   take-small-on-unmatched (capture more)? Recommendation: skip-on-unmatched
   as v1 default; allow override via settings.

---

## Summary

**Bear regime cell investigation COMPLETE** — all 3 cells investigated;
synthesis published; production posture documented.

| Cell | Production Status |
|---|---|
| Bear UP_TRI | **Shadow-deployment-ready** with sub-regime gating |
| Bear DOWN_TRI | DEFERRED with provisional filter (default OFF) |
| Bear BULL_PROXY | DEFERRED with provisional filter (default OFF) |

Production WR target: **65-75% for hot/warm Bear UP_TRI**, NOT 94.6%.
Trader expectation calibration is critical — the live window included
significant Phase-5 selection bias not reproducible at scale.

Sub-regime detector is deterministic, O(1), runs once per scan day.
Failure mode is fail-closed (unknown sub-regime → SKIP cascade).

Universal KILL rules (apply across all 3 cells regardless of deployment
status):
- kill_001 (Bank × DOWN_TRI), already in production
- vol_climax × BULL_PROXY
- December × UP_TRI
- Health × UP_TRI

**Next session:** Bull regime cell investigation begins. Per the
architectural recommendations:
- Apply Bear UP_TRI's 5-step methodology adapted for lifetime-only
  (no live Bull data currently)
- Build Bull sub-regime detector early (predicted axes: trend_persistence
  × leadership_concentration)
- Test cross-cell direction-flip prediction in Bull cells
- Expect 6-9 sessions across all Bull cells + synthesis

The Lab now has a **proven cross-regime methodology** and architectural
pattern for sub-regime structure. Choppy and Bear regimes establish
the template; Bull regime work tests its generality.
