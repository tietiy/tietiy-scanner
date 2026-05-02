# Bull Regime — Production Posture

**Status:** Bull cell trio investigation COMPLETE. All 3 cells
PROVISIONAL_OFF (lifetime-only methodology). Bull production scanner
pipeline VERIFIED (no bugs found).
**Date:** 2026-05-03
**Branch:** `backtest-lab`
**Scope:** Production deployment specification for Bull regime when it
activates live.
**Companion docs:** [`synthesis.md`](synthesis.md),
[`decision_flow.md`](decision_flow.md),
[`synthesis_llm_analysis.md`](synthesis_llm_analysis.md),
[`bull_uptri/CELL_COMPLETE.md`](../bull_uptri/CELL_COMPLETE.md),
[`bull_downtri/CELL_COMPLETE.md`](../bull_downtri/CELL_COMPLETE.md),
[`bull_bullproxy/CELL_COMPLETE.md`](../bull_bullproxy/CELL_COMPLETE.md),
[`bull_verification/VERIFICATION_REPORT.md`](../bull_verification/VERIFICATION_REPORT.md).

This document specifies how the Bull regime cells should be consumed by
the production scanner / Wave 5 brain layer. It is the contract between
the Lab's cell research and the production decision engine.

---

## Bull regime cells — production readiness (FINAL)

| Cell | Status | Confidence | Sessions | Production action |
|---|---|---|---|---|
| **Bull UP_TRI** | PROVISIONAL_OFF | MEDIUM (lifetime only) | 1 | DEFAULT SKIP; manual enable for `recovery × vol=Med × fvg_low` filter |
| **Bull DOWN_TRI** | PROVISIONAL_OFF | LOW | 1 | DEFAULT SKIP; manual enable for `late_bull × wk3` filter |
| **Bull BULL_PROXY** | PROVISIONAL_OFF | LOW | 1 | DEFAULT SKIP; manual enable for `healthy × 20d=high` filter |

### Initial production deployment scope

**Default for Bull regime activation:** SKIP all Bull signals.

**Manual enablement** (settings flag + Telegram command):
- `bull_uptri_provisional_enabled` (recommend enable first when
  activation triggers met)
- `bull_bullproxy_provisional_enabled` (enable second; requires Bull
  UP_TRI live-validation success)
- `bull_downtri_provisional_enabled` (enable last; lowest priority,
  baseline below 50%)

**Universal KILL rules** (apply if/when Bull cells activate):
- `vol_climax × BULL_PROXY` → REJECT (universal pattern, replicates
  Bear's −11.0pp finding; Bull is −4.4pp same direction)

---

## Bull production scanner — verification status

Per `lab/factory/bull_verification/VERIFICATION_REPORT.md` (V1-V4):

| Component | Verdict | Evidence |
|---|---|---|
| NIFTY regime classifier (Bull) | ✓ WORKS | 10/10 historical Bull days correctly classified |
| Signal generators (UP_TRI/DOWN_TRI/BULL_PROXY) | ✓ WORKS | 112 signals across 2 historical Bull windows |
| Scoring (`enrich_signal`) | ✓ WORKS | 0 errors; math verified manually on 10 samples |
| `regime` tag propagation | ✓ WORKS | All signals carry `regime='Bull'` correctly |
| Sector momentum classifier | ✓ WORKS | Leading/Lagging/Neutral assignments produced |

**No bugs found. No blockers for Bull regime activation.**

---

## Sub-regime detector requirement

Production scanner must compute the daily Bull sub-regime label before
per-signal action determination.

### Detector specification

Source: `lab/factory/bull/subregime/detector.py` (built in BU1)

```python
def detect_bull_subregime(nifty_200d_return_pct, market_breadth_pct):
    """Tri-modal Bull sub-regime classifier.
    Returns one of: "recovery_bull", "healthy_bull", "normal_bull",
                    "late_bull", "unknown".

    Distribution:
      recovery_bull: ~2.6% of lifetime (smallest tail)
      healthy_bull:  ~12.5%
      normal_bull:   ~76.4% (bulk)
      late_bull:     ~7.1%
    """
    p = nifty_200d_return_pct
    s = market_breadth_pct
    if p is None or s is None:
        return "unknown"
    if p < 0.05 and s < 0.60:
        return "recovery_bull"
    if 0.05 <= p <= 0.20:
        if s > 0.80:
            return "healthy_bull"
        if s < 0.60:
            return "late_bull"
    return "normal_bull"
```

### Where it runs

**Once per trading day**, in pre-market composer (similar to Bear
detector). Inputs: NIFTY 200-day return + market breadth pct.

```
9:15 IST: market opens
9:20 IST: scanner initialization
  → fetch NIFTY OHLCV (already happening)
  → compute nifty_200d_return_pct (already in feature pipeline)
  → compute market_breadth_pct (already in feature pipeline)
  → call detect_bull_subregime() ← NEW deployment item
  → write current_bull_subregime to current_subregime.json
```

### Output format

`output/current_subregime.json` (extended from existing structure):
```json
{
  "scan_date": "2026-05-03",
  "primary_regime": "Bull",
  "subregime_per_regime": {
    "Bear": {"label": "...", ...},
    "Bull": {
      "label": "recovery_bull",
      "confidence": 90.0,
      "nifty_200d_return": 0.04,
      "market_breadth_pct": 0.55,
      "expected_wr_range": "60-74% (UP_TRI filter match)"
    },
    "Choppy": {"label": "...", ...}
  }
}
```

### Failure modes

| Failure | Handling |
|---|---|
| `nifty_200d_return_pct` missing (early year edge case) | Bull detector returns "unknown"; fail-closed → SKIP cascade |
| `market_breadth_pct` missing | Same: "unknown" + SKIP |
| Bull regime activates before detector deployed | Production has no sub-regime — defaults all Bull signals to "unknown" → SKIP. Production scanner currently has 3-state regime only; Bull detector is required pre-activation. |

---

## Per-signal decision flow (Bull cells, when activated)

See `decision_flow.md` for full pseudo-code. Top-level structure:

```
1. Activation gate: provisional_enabled? → if no, SKIP
2. KILL: vol_climax × BULL_PROXY → REJECT
3. Detect Bull sub-regime
4. Per signal-type × sub-regime cascade (per decision_flow.md)
```

---

## Calibrated WR expectations (HONEST — no live data)

| Filter | Lifetime WR | Calibrated production |
|---|---|---|
| **UP_TRI: recovery_bull + vol=Med + fvg_low** | 74.1% on n=390 | 60-74% (large lifetime-warming uncertainty) |
| **UP_TRI: recovery_bull + vol=Med** | ~70% (n=39) | 60-72% |
| **UP_TRI: healthy_bull baseline** | 58.4% (n=4,764) | 55-62% |
| **UP_TRI: normal_bull + filter** | ~58% | 53-60% |
| **BULL_PROXY: healthy + 20d=high** | 62.5% on n=128 | 58-66% |
| **BULL_PROXY: wk4 alone (broader)** | 60.8% on n=707 | 56-64% |
| **DOWN_TRI: late × wk3** | 65.2% on n=253 | 60-70% |
| Unfiltered Bull | 51-52% | ~52% (≈ coin flip) |

**Critical:** When Bull regime activates and Phase 5 produces winners,
expect 20-30pp inflation initially (parallel to Bear UP_TRI's +38.9pp
pattern). Live WR may temporarily exceed these calibrations before
mean-reverting.

---

## Documented gaps for Bull regime activation

### Gap 1 — 0 Bull-specific boost_patterns in mini_scanner_rules.json

`data/mini_scanner_rules.json:boost_patterns` has 7 entries, ALL
`regime: "Bear"`. No Bull-specific entries.

**Impact:** Bull signals receive only base scoring (Age + Bull regime
+ Vol + SecLead). No nuanced sub-regime / sector adjustments from
boost_patterns layer.

**Severity:** LOW for shadow deployment; MEDIUM for full live
deployment.

**Action required (when Bull regime activates + 30+ live signals
validate):** Add 3-5 Bull boost_patterns from Lab cell findings:
```json
{"signal": "UP_TRI", "sector": null, "regime": "Bull",
 "tier": "B (provisional)", "conviction_tag": "TAKE_FULL",
 "reason": "Bull UP_TRI recovery_bull sub-regime + vol=Med + fvg_low → 74% lifetime"},
{"signal": "BULL_PROXY", "sector": null, "regime": "Bull",
 "tier": "B (provisional)", "conviction_tag": "TAKE_FULL",
 "reason": "Bull BULL_PROXY healthy + 20d=high → 62.5% lifetime"},
{"signal": "DOWN_TRI", "sector": null, "regime": "Bull",
 "tier": "B (provisional)", "conviction_tag": "TAKE_SMALL",
 "reason": "Bull DOWN_TRI late × wk3 → 65.2% lifetime"}
```

### Gap 2 — Sub-regime detector not in production scanner

Lab built Bull sub-regime detector
(`lab/factory/bull/subregime/detector.py`). Production scanner has no
sub-regime detection layer (3-state regime only: Bull/Bear/Choppy).

**Impact:** Without sub-regime detection, Bull signals can't be gated
by recovery/healthy/normal/late cells. Production decision flow falls
back to baseline Bull scoring.

**Severity:** MEDIUM (blocks activation of provisional filters).

**Action required (pre-activation):** Integrate Bull sub-regime
detector into production scanner via:
- Pre-market composer (per-day classification)
- Output to `current_subregime.json`
- `bridge_state.json` extended with current sub-regime
- Decision flow per `decision_flow.md`

Estimated effort: 2-4 hours.

### Gap 3 — `target_price=None` on Bull signals (by design)

`scorer.py:get_exit_rule()` returns `Target2x` only for
`signal=='UP_TRI' AND regime=='Bear'`; everything else returns `Day6`.
Bull signals get `target_price=None` (Day6 exit, no fixed target).

**Severity:** LOW (same behavior as Choppy regime; trader is
acclimated; Telegram/PWA presumably handle this case).

**Status:** by-design; no fix needed for Bull verification scope.

### Gap 4 — Sonnet's 5 untested scenarios from Bull verification critique

Per `bull_verification/bull_verification_critique.md`:

| Scenario | Description | Severity |
|---|---|---|
| State persistence across regime transitions | Aged signal from Bear day encountering Bull regime next day | MEDIUM |
| Volume filter absence case | Below-1.5x volume Bull breakouts; verify suppression | LOW |
| Sector rotation edge cases | Single sector-leading stock with flat sector peers | LOW |
| Regime classifier jitter at boundaries | Boundary values for slope/breadth | LOW |
| BULL_PROXY first-Bull-day trigger | +3% spike day still 8% below 200d MA | MEDIUM |

**Action required (pre-activation):** Tests for items 1 and 5
(state-persistence + first-Bull-day BULL_PROXY) should be written
before Bull regime activates live. Items 2-4 are lower priority and
can be deferred.

### Gap 5 — Bull cells require live validation gating (different from Bear UP_TRI)

Bear UP_TRI cell had 74 live signals at 94.6% WR before lifetime
validation; production deployment posture is "shadow-deployment-ready
with live evidence + lifetime caveats". Bull cells have 0 live signals;
production posture is "PROVISIONAL_OFF default, awaiting live
validation".

**Impact:** Bull activation requires more disciplined gating than Bear
required.

**Action required:** Define explicit live-WR thresholds for upgrading
PROVISIONAL_OFF → CANDIDATE → DEPLOY:
- Bull UP_TRI: 30+ live signals + matched-WR ≥ 50% on filter
- Bull BULL_PROXY: same + Bull UP_TRI live success first
- Bull DOWN_TRI: 30+ live signals + matched-WR ≥ 55% (higher bar; baseline below 50%)

---

## Bull vs Bear vs Choppy regime comparison

All three regimes have been comprehensively investigated. Architectural
parallels and differences:

| Property | Choppy | Bear | Bull |
|---|---|---|---|
| Sub-regime structure | tri-modal | tri-modal | **tri-modal SKEWED** |
| Primary axis | `vol_percentile` | `vol_percentile` | **`nifty_200d_return`** |
| Secondary axis | `market_breadth` | `nifty_60d_return` | **`market_breadth`** |
| Sub-regime balance | balanced (~70/30) | balanced (~60/40) | **skewed (~76/24)** |
| Cells investigated | 3 (UP_TRI/DOWN_TRI/BULL_PROXY) | 3 | 3 |
| Cells reaching HIGH confidence | 1 (UP_TRI v2) | 1 (UP_TRI v3) | **0 (all PROVISIONAL_OFF)** |
| Cells DEFERRED/PROVISIONAL_OFF | 1 (DOWN_TRI) | 2 (DOWN_TRI + BULL_PROXY) | **3 (all)** |
| Cells KILLED | 1 (BULL_PROXY) | 0 | 0 |
| Live evidence | 91+11+13=115 signals | 74+11+13=98 signals | **0 signals** |
| Phase 5 selection bias | varies | +26.3pp residual (Bear UP_TRI) | n/a (no live) |

### Cross-regime architectural framework (preview)

#### Universal patterns confirmed (3/3 regimes)

1. **Tri-modal sub-regime structure.** Every regime has 2 edge tails
   plus a baseline basin. Choppy: quiet/balance/stress; Bear:
   hot/warm/cold; Bull: recovery/healthy/normal/late.

2. **Primary axis = regime definition, secondary axis = risk flavor.**
   Each regime's primary axis defines the regime; secondary axis
   modulates within. Choppy primary = vol (chop), Bear primary = vol
   (panic), Bull primary = 200d_return (maturity). Secondary axes
   vary.

3. **Per-regime sub-regime detectors with regime-specific axes is the
   correct architectural pattern.** Don't unify; each regime needs
   its own detector.

#### Universal patterns confirmed (2/3 regimes)

4. **`vol_climax × BULL_PROXY` anti-feature is universal.** Bear
   −11.0pp + Bull −4.4pp (Choppy BULL_PROXY KILL'd, can't test).
   Capitulation breaks support; mechanism-intrinsic.

5. **Direction-flip pattern (UP_TRI vs DOWN_TRI inversion on regime
   anchor).** Bear: nifty_60d=low UP_TRI +14.1pp / DOWN_TRI -4.1pp.
   Bull: nifty_200d_return=high UP_TRI -2.1pp / DOWN_TRI +1.5pp.
   Choppy untested.

6. **Bullish-cell direction-alignment within regime.** Bear UP_TRI +
   BULL_PROXY share signature (compression-coil). Bull UP_TRI +
   BULL_PROXY share signature (recovery-best/late-worst). Choppy not
   directly tested — but Choppy F1 finding pattern would parallel.

7. **Calendar inversion across direction.** Bear: bullish wk4 winner /
   bearish wk2 winner. Bull: bullish wk4 winner / bearish wk3 winner.
   Different mid-month winners per regime; same direction inversion.

#### Regime-specific patterns (NO transfer)

8. **Cross-regime feature transfer DOES NOT work.** 0/3 Bear UP_TRI
   top patterns qualify in Bull UP_TRI. Each cell + regime pair has
   its own filter signature.

9. **DOWN_TRI lifetime baseline below 50% in Bear (46.1%) and Bull
   (43.4%).** Universal contrarian-short hostility — DOWN_TRI is a
   narrow exhaustion bet, not a general short signal.

10. **`52w_high_distance` direction INVERTS across Bear vs Bull
    BULL_PROXY**. Bear prefers far-from-highs (beaten down); Bull
    prefers near-highs (breakout-of-resistance). Different mechanisms.

---

## Cross-regime synthesis future work (optional)

A dedicated cross-regime synthesis session would consolidate findings
across all 9 cells (3 regimes × 3 cells) into:

1. Universal architectural patterns (the 7 above)
2. Regime-specific patterns (the 3 above)
3. Production rule schema implications
4. Universal vs regime-specific feature library
5. "Recovery/transitional zones" cross-regime test (does every regime
   have a transitional quality cell?)

**Status:** Not required for Bull regime activation. Could be done
post-Bull-activation when live data accumulates across regimes.

---

## Open questions for production integration

1. **Sub-regime detector deployment timing.** Per-day pre-market
   composer (computes once, shared across signals) vs per-signal.
   **Recommendation:** per-day for v1.

2. **Trader enablement UX.** How does trader toggle
   `bull_uptri_provisional_enabled`? Telegram command? Settings file?
   **Recommendation:** settings file + Telegram command for runtime
   toggle (parallel to Bear cells' UX).

3. **Cross-cell precedence handling.**
   - Phase-5 hierarchy override: not applicable for Bull (no Phase 5
     yet)
   - Cap stacking: take MOST conservative single cap (no
     multiplication)
   - Max position cap: skip new signal; don't force-close existing

4. **Activation threshold tightening.** Bull cells should require
   higher confidence than Bear UP_TRI given lifetime-only origin:
   - Bull UP_TRI: 30+ signals + matched-WR ≥ 50% (filter)
   - Bull BULL_PROXY: same + Bull UP_TRI live-success first
   - Bull DOWN_TRI: 30+ signals + matched-WR ≥ 55% (higher bar)

5. **Calibrated WR display in Telegram digest.** Show "expected
   60-74%" alongside each Bull signal? Risk: anchoring trader to a
   range. Benefit: manages emotional response when Bull regime first
   produces signals after months of Bear/Choppy.

6. **First-Bull-day trader experience.** When Bull regime activates
   live (after months of Bear/Choppy), trader sees Bull signals in
   Telegram for first time. What should the system communicate?
   **Recommendation:** Pre-activation Telegram brief: "Bull regime
   classified live for first time. Bull cells PROVISIONAL_OFF
   default. Manual enablement available — review
   PRODUCTION_POSTURE.md activation triggers before enabling."

7. **Schema design for cell variety.** Production rule schema must
   handle 5 cell types:
   - filter+cascade (Bear UP_TRI)
   - DEFERRED with provisional (Bear DOWN_TRI / BULL_PROXY)
   - PROVISIONAL_OFF (all 3 Bull cells)
   - KILL (Choppy BULL_PROXY)
   - shadow-deployment-ready (Bear UP_TRI v3)

---

## Pre-activation action list

Before Bull regime activates live:

| # | Action | Owner | Required for |
|---|---|---|---|
| 1 | Verify Bull pipeline functionality (V1-V4 verification) | DONE | n/a (complete) |
| 2 | Build Bull sub-regime detector for production scanner integration | scanner team | pre-activation |
| 3 | Write tests for Sonnet's 5 untested scenarios (Gap 4) | scanner team | pre-activation |
| 4 | Define provisional Bull boost_patterns for mini_scanner_rules.json | lab + trader | pre-activation |
| 5 | Trader briefed on calibrated WR (60-74% best filter, ≈52% baseline) | trader | pre-activation |
| 6 | Decision flow integration into scanner main flow | scanner team | activation |
| 7 | Telegram digest shows Bull-specific WR expectations | brain team | activation |
| 8 | First-Bull-day Telegram brief drafted | brain team | activation |
| 9 | Activation triggers documented (30 signals + WR thresholds) | trader | activation |
| 10 | First Bull signal sees-the-light test (shadow mode + manual trader review) | brain + trader | live gate |

Items 1-5 are pre-activation prep. Items 6-10 are activation-day work.

---

## Summary

**Bull regime cell investigation COMPLETE** — all 3 cells investigated;
synthesis published; production posture documented; pipeline verified.

| Cell | Production Status |
|---|---|
| Bull UP_TRI | **PROVISIONAL_OFF** with provisional `recovery × vol=Med × fvg_low` filter (74% lifetime) |
| Bull DOWN_TRI | **PROVISIONAL_OFF** with provisional `late × wk3` filter (65% lifetime) |
| Bull BULL_PROXY | **PROVISIONAL_OFF** with provisional `healthy × 20d=high` filter (62.5% lifetime) |

Bull production scanner pipeline FUNCTIONALLY VERIFIED (per
`lab/factory/bull_verification/VERIFICATION_REPORT.md`). 0 bugs, 0
blockers.

Production WR target (HONEST): **60-74% on best-filter Bull UP_TRI**,
not artificially inflated. Bull cells are PROVISIONAL_OFF until live
validation occurs. When Bull regime activates and Phase 5 produces
winners, expect 20-30pp temporary inflation before mean-reverting.

**Universal KILL rules** (apply across cells):
- vol_climax × BULL_PROXY (universal anti-feature)

**Lab pipeline now COMPLETE** — 3 regimes × 3 cells = 9 cells
investigated; all synthesized; cross-regime architectural framework
documented.

**Next session candidate:**
- Cross-regime synthesis (consolidate 9 cells into universal vs
  regime-specific architectural patterns)
- OR Sonnet's 5 Bull scenarios investigation (state-persistence,
  first-Bull-day BULL_PROXY, etc.)
- OR Wait for Bull regime to return live; activate cells as triggers
  fire
