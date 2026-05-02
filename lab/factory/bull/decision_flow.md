# Bull Regime — Unified Production Decision Flow

**Status:** Executable specification (documentation only; not yet implemented in scanner code).
**Date:** 2026-05-03
**Companion docs:** [`synthesis.md`](synthesis.md),
[`synthesis_llm_analysis.md`](synthesis_llm_analysis.md),
[`PRODUCTION_POSTURE.md`](PRODUCTION_POSTURE.md).

This document specifies the unified Bull regime production decision
flow across all 3 cells (UP_TRI, DOWN_TRI, BULL_PROXY), with sub-regime
gating, KILL rules, and calibrated WR expectations.

**Important caveat:** All 3 Bull cells are **PROVISIONAL_OFF default**
(lifetime-only methodology; no live validation). This decision flow
is a deployment specification for when Bull regime activates live and
provisional filters pass live-validation triggers. Until then, default
behavior is **SKIP all Bull signals**.

---

## Calibrated WR expectations table

The single most important table for trader expectation management:

| Sub-regime | UP_TRI | BULL_PROXY | DOWN_TRI |
|---|---|---|---|
| **recovery_bull** | **60-74%** (filter match) | 58-65% (filter match) | **SKIP** (35.7% — DOWN_TRI's worst) |
| **healthy_bull** | **TAKE_FULL** (~58% baseline) | **62.5%** (filter match: healthy × 20d=high) | **SKIP** (40.5%) |
| **normal_bull** | TAKE_SMALL (~51% — marginal) | **SKIP** (default; activate only on filter match) | **SKIP** (42.6%) |
| **late_bull** | **SKIP** (45.1% — UP_TRI's worst) | SKIP | **65.2%** (filter match: late × wk3) |

**Critical:** All numbers are **lifetime baselines** (no live data
exists). Bull cells are PROVISIONAL_OFF until live validation. When
Bull regime activates and Phase 5 produces winners, expect 20-30pp
selection bias inflation (parallel to Bear UP_TRI's +38.9pp pattern)
— production will see live WRs that may temporarily exceed these
calibrations.

---

## Decision flow (executable pseudo-code)

```python
def bull_regime_action(signal, market_state, phase_status,
                          provisional_enabled=False):
    """
    Unified Bull regime decision flow.

    Args:
        signal: dict with {signal_type, sector, feat_*, day_of_week,
                            day_of_month_bucket, repeat_name_within_6d, ...}
        market_state: dict with {nifty_200d_return_pct,
                                  market_breadth_pct, ...}
        phase_status: "PHASE_5_VALIDATED" | "WATCH" | "RAW" | None
        provisional_enabled: bool — if False (default), all Bull signals
                              SKIP regardless of cell findings

    Returns:
        (action, sizing_modifier, reason_str) tuple where:
            action ∈ {"TAKE_FULL", "TAKE_SMALL", "TAKE_FULL_80", "SKIP", "REJECT"}
            sizing_modifier ∈ [0.0, 1.0]
            reason_str: human-readable audit trail
    """

    # ════════════════════════════════════════════════════════════════
    # STEP 0 — Activation gate (Bull cells PROVISIONAL_OFF)
    # ════════════════════════════════════════════════════════════════

    if not provisional_enabled:
        return ("SKIP", 0.0,
                "Bull cells PROVISIONAL_OFF; manual enable required "
                "(awaiting live validation: Bull regime active ≥10 days "
                "+ ≥30 live signals + matched-WR ≥ 50%)")

    # ════════════════════════════════════════════════════════════════
    # STEP 1 — Universal KILL rules (apply BEFORE sub-regime check)
    # ════════════════════════════════════════════════════════════════

    # vol_climax × BULL_PROXY: universal anti (replicates Bear pattern)
    if (signal.signal_type == "BULL_PROXY"
            and signal.feat_vol_climax_flag is True):
        return ("REJECT", 0.0,
                "vol_climax × BULL_PROXY: capitulation breaks support "
                "(lifetime −4.4pp Bull, −11.0pp Bear; universal anti)")

    # ════════════════════════════════════════════════════════════════
    # STEP 2 — Detect Bull sub-regime
    # ════════════════════════════════════════════════════════════════

    sub = detect_bull_subregime(
        market_state.nifty_200d_return_pct,
        market_state.market_breadth_pct,
    )
    # sub ∈ {"recovery_bull", "healthy_bull", "normal_bull", "late_bull",
    #        "unknown"}

    if sub == "unknown":
        return ("SKIP", 0.0,
                "Bull sub-regime unknown (missing 200d_return or "
                "market_breadth); fail-closed")

    # ════════════════════════════════════════════════════════════════
    # STEP 3 — Per signal-type × sub-regime cascade
    # ════════════════════════════════════════════════════════════════

    if signal.signal_type == "UP_TRI":
        return _bull_uptri_action(signal, sub)

    if signal.signal_type == "BULL_PROXY":
        return _bull_bullproxy_action(signal, sub)

    if signal.signal_type == "DOWN_TRI":
        return _bull_downtri_action(signal, sub)

    return ("SKIP", 0.0, "unknown signal type")


# ─── Per signal-type sub-flow ───────────────────────────────────────

def _bull_uptri_action(signal, sub):
    """Bull UP_TRI per sub-regime."""

    if sub == "recovery_bull":
        # Highest precision: recovery_bull + filter
        if (signal.feat_nifty_vol_regime == "Medium"
                and signal.feat_fvg_unfilled_above_count == "low"):
            return ("TAKE_FULL", 1.0,
                    "Recovery + vol=Med + fvg=low: 74.1% lifetime expected")
        if signal.feat_nifty_vol_regime == "Medium":
            return ("TAKE_FULL", 1.0,
                    "Recovery + vol=Med: 67-72% lifetime expected")
        return ("TAKE_SMALL", 0.5,
                "Recovery_bull baseline 60.2% — TAKE_SMALL without filter match")

    if sub == "healthy_bull":
        # Strong sub-regime; broad TAKE
        if (signal.feat_RSI_14 == "medium"
                and signal.feat_day_of_month_bucket == "wk4"):
            return ("TAKE_FULL", 1.0,
                    "Healthy + RSI=med + wk4: ~68% expected")
        if signal.feat_day_of_month_bucket == "wk4":
            return ("TAKE_FULL", 1.0,
                    "Healthy + wk4: ~65% expected")
        return ("TAKE_FULL", 1.0,
                "Healthy_bull baseline 58.4% — TAKE_FULL")

    if sub == "normal_bull":
        # Marginal: only TAKE on universal anchor match
        if (signal.feat_RSI_14 == "medium"
                and signal.feat_nifty_20d_return_pct == "high"):
            return ("TAKE_SMALL", 0.5,
                    "Normal + RSI=med + 20d=high: ~58% expected")
        return ("SKIP", 0.0,
                "Normal_bull baseline 51.3% — below practical threshold")

    if sub == "late_bull":
        return ("SKIP", 0.0,
                "Late_bull UP_TRI worst cell (45.1% lifetime; topping risk)")

    return ("SKIP", 0.0, f"Bull UP_TRI: {sub} not handled")


def _bull_bullproxy_action(signal, sub):
    """Bull BULL_PROXY per sub-regime."""

    # Sector + month hard SKIPs
    if signal.sector in ("Bank", "Metal"):
        return ("SKIP", 0.0,
                f"Bull BULL_PROXY × {signal.sector}: lifetime -4 to -5.5pp")

    if sub == "recovery_bull":
        return ("TAKE_SMALL", 0.5,
                "Recovery_bull BULL_PROXY: 57.4% lifetime")

    if sub == "healthy_bull":
        # Highest precision: healthy + 20d=high
        if signal.feat_nifty_20d_return_pct == "high":
            return ("TAKE_FULL", 1.0,
                    "Healthy + 20d=high: 62.5% lifetime expected")
        if signal.feat_day_of_month_bucket == "wk4":
            return ("TAKE_SMALL", 0.5,
                    "Healthy + wk4: ~65% lifetime")
        return ("SKIP", 0.0,
                "Healthy_bull BULL_PROXY without filter match")

    if sub == "normal_bull":
        # wk4 universal winner (Bull BULL_PROXY's strongest single feature)
        if signal.feat_day_of_month_bucket == "wk4":
            return ("TAKE_SMALL", 0.5,
                    "Normal + wk4: 60.8% lifetime fallback")
        return ("SKIP", 0.0, "Normal_bull BULL_PROXY without wk4")

    if sub == "late_bull":
        return ("SKIP", 0.0,
                "Late_bull BULL_PROXY: -7.5pp anti")

    return ("SKIP", 0.0, "Bull BULL_PROXY default skip")


def _bull_downtri_action(signal, sub):
    """Bull DOWN_TRI per sub-regime — only late_bull works."""

    if sub != "late_bull":
        return ("SKIP", 0.0,
                f"Bull DOWN_TRI × {sub}: 35-43% (losing zone)")

    # Within late_bull (53% sub-regime baseline)
    if signal.sector in ("FMCG", "Auto"):
        return ("SKIP", 0.0,
                "Late_bull × Auto/FMCG: -4pp lifetime")
    if signal.feat_RSI_14 == "high":
        return ("SKIP", 0.0,
                "RSI=high ANTI for Bull DOWN_TRI (sustained momentum)")
    if signal.feat_nifty_vol_regime != "Low":
        return ("SKIP", 0.0,
                "Late_bull DOWN_TRI requires Low vol")

    # Highest-precision: late × wk3
    if signal.feat_day_of_month_bucket == "wk3":
        return ("TAKE_SMALL", 0.5,
                "Late × wk3: 65.2% lifetime expected")
    if signal.feat_day_of_week == "Mon":
        return ("TAKE_SMALL", 0.5,
                "Late × Mon: ~71% lifetime (small sample)")

    return ("TAKE_SMALL", 0.5,
            "Late_bull DOWN_TRI baseline 53.0%")


# ─── Bull sub-regime detector ──────────────────────────────────────

def detect_bull_subregime(nifty_200d_return_pct, market_breadth_pct):
    """Bull regime tri-modal sub-regime classifier.

    Built in BU1 (lab/factory/bull/subregime/detector.py).

    Tri-modal SKEWED structure:
      • recovery_bull (2.6%): low 200d AND low breadth
                              early-cycle quality leadership; 60.2% UP_TRI
      • healthy_bull (12.5%): mid 200d AND high breadth
                              broad sustained Bull; 58.4% UP_TRI
      • normal_bull (76.4%): everything else
                             baseline-ish; 51.3% UP_TRI
      • late_bull (7.1%): mid 200d AND low breadth
                         narrowing leadership topping; 53.0% DOWN_TRI
    """
    p = nifty_200d_return_pct
    s = market_breadth_pct

    if p is None or pd.isna(p) or s is None or pd.isna(s):
        return "unknown"

    if p < 0.05:
        if s < 0.60:
            return "recovery_bull"
    if 0.05 <= p <= 0.20:
        if s > 0.80:
            return "healthy_bull"
        if s < 0.60:
            return "late_bull"
    return "normal_bull"
```

---

## Decision flow visualization

```
                    ┌───────────────────────────┐
                    │ Bull Signal Arrives       │
                    └──────────┬────────────────┘
                               │
                ┌──────────────▼──────────────┐
                │ STEP 0: Activation gate     │
                │  provisional_enabled = ?    │
                └──────┬───────────────┬──────┘
                       │NO             │YES
                       ▼               ▼
                    SKIP        ┌──────────────┐
                  (DEFAULT)     │ STEP 1: KILL │
                                │  vol_climax  │
                                │  × BULL_PROXY│
                                └──────┬───────┘
                                       │
                                       ▼
                                ┌──────────────────┐
                                │ STEP 2: Sub-regime│
                                │ 200d × breadth   │
                                └─┬────┬────┬────┬─┘
                                  │    │    │    │
                          recovery healthy normal late
                                  │    │    │    │
                                  ▼    ▼    ▼    ▼
                              ┌──────────────────────┐
                              │ STEP 3: per-cell     │
                              │ × per-sub-regime     │
                              │ cascade              │
                              │                      │
                              │ UP_TRI:              │
                              │   recov: TAKE_FULL   │
                              │   healthy: TAKE_FULL │
                              │   normal: TAKE_SMALL │
                              │   late: SKIP         │
                              │                      │
                              │ BULL_PROXY:          │
                              │   recov: TAKE_SMALL  │
                              │   healthy: TAKE_FULL │
                              │   normal: SKIP       │
                              │   late: SKIP         │
                              │                      │
                              │ DOWN_TRI:            │
                              │   recov: SKIP        │
                              │   healthy: SKIP      │
                              │   normal: SKIP       │
                              │   late: TAKE_SMALL   │
                              └──────────────────────┘
```

---

## Trader heuristics (universal across cells)

| Heuristic | Condition | Action |
|---|---|---|
| Repeat-name cap | Same stock fires Bull cell within 6 trading days | downgrade to TAKE_SMALL |
| Day-correlation cap | 3+ Bull signals fire on same day | size each at 80% of normal |
| Max concurrent positions | 5 concurrent Bull positions held | skip new signal until exit |

(These mirror Bear regime trader heuristics; same operational logic
applies regardless of regime.)

---

## KILL rules summary (apply before sub-regime detection)

| Rule | Condition | Reason | Source |
|---|---|---|---|
| BULL_PROXY vol-climax | `vol_climax_flag=True` × BULL_PROXY | Lifetime −4.4pp anti; universal pattern (Bear -11.0pp same direction) | Bull BULL_PROXY cell + Bear synthesis |

Bull regime has fewer hard KILL rules than Bear because:
- Bear had `kill_001` (Bank × DOWN_TRI) — kept for production but
  applies in any regime; not Bull-specific
- Bear had December seasonal kill — not yet identified for Bull
  (Bull cell investigations didn't surface a comparable catastrophic
  month)
- Bear had Health UP_TRI sector kill — Bull UP_TRI's worst sector
  ranking is Energy, but only -2.9pp; not severe enough for hard kill

**Production-ready KILL rules for Bull are sparse.** Most Bull
filtering happens via sub-regime gating + sector/feature SKIPs within
sub-regime branches.

---

## Default behavior

When a Bull signal does not match any take rule:
- **DEFAULT: SKIP**
- Rationale: Bull cells are PROVISIONAL_OFF; lifetime baseline (52%
  UP_TRI / 51% BULL_PROXY / 43% DOWN_TRI) is at-or-below the
  practical edge threshold. Without filter match, expected WR is
  break-even-or-below. Trader-level conservatism preferred.

---

## Provisional filter enablement (manual control)

ALL 3 Bull cells require explicit operator enablement:

| Cell | Provisional filter | Default | Enable when |
|---|---|---|---|
| Bull UP_TRI | recovery + vol=Med + fvg=low → TAKE_FULL | OFF | After Bull regime active ≥10 days + ≥30 live signals confirm filter |
| Bull BULL_PROXY | healthy + 20d=high → TAKE_FULL | OFF | After Bull UP_TRI live-validates first |
| Bull DOWN_TRI | late + wk3 → TAKE_SMALL | OFF | After Bull regime live for full cycle (low priority) |

**Default OFF means all Bull signals SKIP** until trader explicitly
enables. This is the conservative posture — preserves optionality
without committing capital to provisional findings.

---

## Activation triggers

| Trigger | Cell | Effect |
|---|---|---|
| Bull regime classified for ≥10 trading days | All cells | Begin live signal accumulation tracking |
| ≥30 Bull UP_TRI live signals + matched-WR ≥ 50% | Bull UP_TRI | Upgrade PROVISIONAL_OFF → CANDIDATE; consider activation |
| ≥30 Bull BULL_PROXY live signals + matched-WR ≥ 50% | Bull BULL_PROXY | Same |
| ≥30 Bull DOWN_TRI live signals + matched-WR ≥ 55% | Bull DOWN_TRI | Same (higher threshold; baseline below 50%) |
| Bull regime ends without sufficient signals | All cells | Maintain PROVISIONAL_OFF; log gap for next Bull cycle |
| Provisional filter live-WR drops below 45% over rolling 20 trades | Specific cell | Pause cell deployment; investigate sub-regime drift |

---

## Sub-regime stratified WR tracking (production observability)

Production must track sub-regime-stratified WRs separately to detect
drift early:

```python
# Production telemetry per Bull signal:
{
  "signal_type": "UP_TRI",
  "regime": "Bull",
  "subregime_at_signal": "recovery_bull",
  "subregime_confidence": 90.0,
  "expected_wr_lifetime": 0.602,
  "calibrated_wr_range": [0.55, 0.74],
  "outcome": "DAY6_WIN",  # filled in at Day 6
  "phase5_status": "RAW",  # no Phase 5 history during PROVISIONAL_OFF
  "filter_match_tier": "recovery + vol=Med + fvg=low",
  "provisional_filter_active": true,
}
```

Pause production when:
- Recovery_bull UP_TRI live-WR < 50% over rolling 20 trades
- Healthy_bull BULL_PROXY live-WR < 50% over rolling 20 trades
- Late_bull DOWN_TRI live-WR < 50% over rolling 15 trades
- 3 consecutive sub-regime-classified setups fail in any cell
- Detector classifies as "unknown" daily for 3+ trading days
- Bull regime exits without ≥30 live signals (cell stays PROVISIONAL_OFF)

---

## Open questions for production integration

1. **Where does Bull sub-regime detector run?** Production scanner
   currently has NO sub-regime detection layer (3-state regime only:
   Bull/Bear/Choppy). Lab built Bull detector. Integration approach:
   - Option A: per-day in pre-market composer (computes once, shared
     across signals)
   - Option B: per-signal in scanner core (more granular but slower)
   - Recommendation: per-day for v1.

2. **Trader enablement UX.** How does trader toggle
   `bull_uptri_provisional_enabled`? Telegram command? Settings file?
   Recommendation: settings file read by composer at scan time;
   Telegram command for runtime toggle.

3. **Cross-cell precedence.** What if a Bull UP_TRI signal AND a Bull
   DOWN_TRI signal fire same day in the same sub-regime (impossible
   per current logic but worth checking)?

4. **Activation thresholds tightening.** The 30-signal / 50%-match-WR
   threshold is heuristic. Should it be more conservative for Bull
   (which has no live evidence) than for Bear UP_TRI (which had 74
   live signals at 94.6%)? Recommendation: Yes — Bull should require
   higher confidence before live activation given lifetime-only origin.

5. **Default behavior on REGIME_AMBIGUITY between Bull and another
   regime.** Production scanner regime classifier may produce
   borderline classifications (slope just above/below ±0.005).
   Recommendation: SKIP regardless of cell findings on ambiguous days.

---

## Update Log

- **v1 (2026-05-03, LS2):** Initial unified Bull regime decision flow.
  4-step structure (activation gate → KILL → sub-regime → per-cell
  cascade). Calibrated WR expectations table. KILL rules consolidated
  (universal `vol_climax × BULL_PROXY` only). Provisional filter
  enablement flags for all 3 cells (default OFF). Activation triggers
  documented for upgrading PROVISIONAL_OFF → CANDIDATE → DEPLOY.
