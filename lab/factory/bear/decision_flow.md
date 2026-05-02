# Bear Regime — Unified Production Decision Flow

**Status:** Executable specification (documentation only; not yet implemented in scanner code).
**Date:** 2026-05-02 night
**Companion docs:** [`synthesis.md`](synthesis.md),
[`synthesis_llm_analysis.md`](synthesis_llm_analysis.md),
[`PRODUCTION_POSTURE.md`](PRODUCTION_POSTURE.md).

This document specifies the unified Bear regime production decision flow
across all 3 cells (UP_TRI, DOWN_TRI, BULL_PROXY), with sub-regime gating,
KILL rules, and calibrated WR expectations.

---

## Calibrated WR expectations table

The single most important table for trader expectation management:

| Sub-regime | UP_TRI | BULL_PROXY | DOWN_TRI |
|---|---|---|---|
| **Hot Bear** | **68%** (lifetime hot 68.3%) | **64%** (provisional HOT, lifetime 63.7%) | **SKIP** (no edge in current sub-regime) |
| **Warm Bear** | **TAKE_FULL** (live evidence 95% n=42) | **SKIP** (insufficient evidence outside HOT) | **SKIP** |
| **Cold Bear** | filter cascade (~63% on Tier 1) | **SKIP** | wk2/wk3 + non-Bank → ~50-55% (provisional) |

**Critical:** Live observed WRs are inflated by Phase 5 selection bias.
Production expectations must be calibrated to lifetime baselines + sub-regime
structure, NOT to live observations:

| Cell | Live observed | Calibrated production |
|---|---|---|
| Bear UP_TRI | 94.6% | **65-75% in hot/warm**; ~63% on cold Tier 1 |
| Bear BULL_PROXY | 84.6% | **65-75% on HOT only**; SKIP otherwise |
| Bear DOWN_TRI | 18.2% | wk2/wk3 + non-Bank: **~50-55%**; otherwise SKIP |

---

## Decision flow (executable pseudo-code)

```python
def bear_regime_action(signal, market_state, phase_status):
    """
    Unified Bear regime decision flow.

    Args:
        signal: dict with {signal_type, sector, feat_*, day_of_week,
                            day_of_month_bucket, repeat_name_within_6d, ...}
        market_state: dict with {nifty_vol_percentile_20d,
                                  nifty_60d_return_pct, ...}
        phase_status: "PHASE_5_VALIDATED" | "WATCH" | "RAW" | None

    Returns:
        (action, sizing_modifier, reason_str) tuple where:
            action ∈ {"TAKE_FULL", "TAKE_SMALL", "TAKE_FULL_80", "SKIP", "REJECT"}
            sizing_modifier ∈ [0.0, 1.0]
            reason_str: human-readable audit trail
    """

    # ════════════════════════════════════════════════════════════════
    # STEP 1 — KILL rules (apply BEFORE sub-regime check)
    # ════════════════════════════════════════════════════════════════

    # kill_001 — Bank sector × Bear DOWN_TRI rejection
    if signal.signal_type == "DOWN_TRI" and signal.sector == "Bank":
        return ("REJECT", 0.0,
                "kill_001: Bank × Bear DOWN_TRI (live 0/6 wins; lifetime "
                "Bank 45% vs non-Bank 46.4%)")

    # vol_climax kills BULL_PROXY (capitulation breaks support)
    if (signal.signal_type == "BULL_PROXY"
            and signal.feat_vol_climax_flag is True):
        return ("REJECT", 0.0,
                "vol_climax × BULL_PROXY: capitulation breaks support "
                "(lifetime -11.0pp, BULL_PROXY anti)")

    # Calendar mismatch — December for UP_TRI (catastrophic per S1)
    if signal.signal_type == "UP_TRI" and signal.month == 12:
        return ("SKIP", 0.0,
                "December × Bear UP_TRI: -25pp lifetime catastrophic")

    # Sector mismatch — Health × UP_TRI (hot WR 32.4%; the only
    # sector where Bear UP_TRI hot sub-regime FAILS)
    if signal.signal_type == "UP_TRI" and signal.sector == "Health":
        return ("SKIP", 0.0,
                "Health × Bear UP_TRI hostile: lifetime hot 32.4%")

    # ════════════════════════════════════════════════════════════════
    # STEP 2 — Detect Bear sub-regime
    # ════════════════════════════════════════════════════════════════

    sub = detect_bear_subregime(
        market_state.nifty_vol_percentile_20d,
        market_state.nifty_60d_return_pct,
    )
    # sub ∈ {"hot", "warm", "cold", "unknown"}

    # Regime ambiguity filter (per Sonnet 4.5 BS1 critique):
    # Suppress trades within 5% of threshold to avoid whipsaw
    if _is_borderline(market_state.nifty_vol_percentile_20d,
                          market_state.nifty_60d_return_pct):
        return ("SKIP", 0.0,
                "Regime ambiguity: detector score within 5% of "
                "hot/cold threshold; whipsaw protection")

    # ════════════════════════════════════════════════════════════════
    # STEP 3 — Phase 5 hierarchy override
    # ════════════════════════════════════════════════════════════════

    if phase_status == "PHASE_5_VALIDATED":
        # Phase-5 validated signals execute regardless of sub-regime
        sizing = 1.0 if sub in ("hot", "warm") else 0.5
        return ("TAKE_FULL" if sizing == 1.0 else "TAKE_SMALL",
                sizing, f"Phase-5 override; sub-regime={sub}")

    # ════════════════════════════════════════════════════════════════
    # STEP 4 — Per signal-type × sub-regime cascade
    # ════════════════════════════════════════════════════════════════

    if signal.signal_type == "UP_TRI":
        return _bear_uptri_action(signal, sub)

    if signal.signal_type == "BULL_PROXY":
        return _bear_bullproxy_action(signal, sub)

    if signal.signal_type == "DOWN_TRI":
        return _bear_downtri_action(signal, sub)

    return ("SKIP", 0.0, "unknown signal type")


# ─── Per signal-type sub-flow ───────────────────────────────────────

def _bear_uptri_action(signal, sub):
    """Bear UP_TRI per sub-regime."""

    if sub == "hot":
        # Apply trader heuristics
        if signal.repeat_name_within_6d:
            return ("TAKE_SMALL", 0.5, "Hot UP_TRI but repeat-name cap")
        if signal.same_day_count >= 3:
            return ("TAKE_FULL", 0.8,
                    "Hot UP_TRI but day-correlation cap (80% sizing)")
        return ("TAKE_FULL", 1.0,
                "Hot Bear UP_TRI (calibrated 65-75% expected WR)")

    if sub == "warm":
        return ("TAKE_FULL", 1.0,
                "Warm Bear UP_TRI: live evidence n=42 95% WR; lifetime "
                "untested but mechanism aligns with hot")

    # sub == "cold"
    if (signal.feat_day_of_month_bucket == "wk4"
            and signal.feat_swing_high_count_20d == "low"):
        return ("TAKE_FULL", 1.0,
                "Cold Tier 1: wk4 × swing_high=low (lifetime 61.4% on n=3374)")

    return ("SKIP", 0.0,
            "Cold Bear UP_TRI without Tier 1 match — edge collapses to ~50%")


def _bear_bullproxy_action(signal, sub):
    """Bear BULL_PROXY per sub-regime — DEFERRED with provisional HOT-only filter."""

    if sub == "hot":
        # Provisional filter — manual enable required (default off)
        if not signal.bear_bullproxy_provisional_enabled:
            return ("SKIP", 0.0,
                    "BULL_PROXY DEFERRED — provisional HOT filter not enabled")
        return ("TAKE_SMALL", 0.5,
                "Hot Bear BULL_PROXY provisional (lifetime 63.7%; calibrated 65-75%)")

    # warm or cold → SKIP per cell verdict (insufficient evidence outside HOT)
    return ("SKIP", 0.0,
            f"BULL_PROXY in {sub} sub-regime: SKIP (cell verdict)")


def _bear_downtri_action(signal, sub):
    """Bear DOWN_TRI per sub-regime — DEFERRED with provisional filter."""

    # Bank already rejected by kill_001 in STEP 1

    # Provisional Verdict A: wk2/wk3 + non-Bank only
    if signal.feat_day_of_month_bucket in ("wk2", "wk3"):
        # Optional: enable only if explicit
        if not signal.bear_downtri_provisional_enabled:
            return ("SKIP", 0.0,
                    "DOWN_TRI DEFERRED — wk2/wk3 provisional filter not enabled")
        return ("TAKE_SMALL", 0.5,
                "DOWN_TRI provisional (wk2/wk3 + non-Bank); lifetime 53.6% on n=1446")

    return ("SKIP", 0.0,
            "DOWN_TRI in wk1/wk4 — provisional filter rejects")


# ─── Sub-regime detector + ambiguity filter ─────────────────────────

HOT_VOL_THRESHOLD = 0.70
HOT_RETURN_THRESHOLD = -0.10
AMBIGUITY_MARGIN = 0.05  # ±5% from threshold


def detect_bear_subregime(vol_percentile_20d, nifty_60d_return):
    """Tri-modal Bear sub-regime classifier.

    hot:  vol > 0.70 AND 60d_return < -0.10
    warm: vol > 0.70 AND -0.10 ≤ 60d_return < 0
    cold: vol ≤ 0.70 OR 60d_return ≥ 0
    """
    vp = vol_percentile_20d
    n60 = nifty_60d_return
    if vp is None or n60 is None:
        return "unknown"
    if vp > HOT_VOL_THRESHOLD:
        if n60 < HOT_RETURN_THRESHOLD:
            return "hot"
        elif n60 < 0:
            return "warm"
        else:
            return "cold"
    return "cold"


def _is_borderline(vp, n60):
    """Regime ambiguity filter — within 5% of any threshold."""
    if vp is None or n60 is None:
        return True
    near_vol_threshold = abs(vp - HOT_VOL_THRESHOLD) < AMBIGUITY_MARGIN
    near_return_threshold = abs(n60 - HOT_RETURN_THRESHOLD) < AMBIGUITY_MARGIN
    near_zero_return = abs(n60) < AMBIGUITY_MARGIN
    return near_vol_threshold or near_return_threshold or near_zero_return
```

---

## Decision flow visualization

```
                        ┌────────────────────┐
                        │ Bear Signal Arrives│
                        └──────────┬─────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ STEP 1: KILL rules          │
                    │  • Bank × DOWN_TRI → REJECT │
                    │  • vol_climax × BULL_PROXY  │
                    │  • Dec × UP_TRI → SKIP      │
                    │  • Health × UP_TRI → SKIP   │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │ STEP 2: Detect sub-regime    │
                    │ vol_percentile × 60d_return  │
                    └──┬────────┬───────┬──────┬───┘
                       │        │       │      │
                  borderline   hot    warm   cold
                       │        │       │      │
                       ▼        ▼       ▼      ▼
                   SKIP      ┌──┴───┐  STEP 4 STEP 4
                  (whip-     │      │  per     per
                  saw)       │      │  type    type
                             │      │
                          STEP 3: Phase-5 override
                             │      │
                          ┌──┴──┐   ┌─┴────┐
                          ▼     ▼   ▼      ▼
                    Phase-5  Raw  Phase-5 Raw
                    →TAKE  STEP 4  →TAKE  STEP 4
                             │            │
                             ▼            ▼
            ┌────────────────────────────────────────────┐
            │ STEP 4: per signal-type × sub-regime       │
            │                                            │
            │  UP_TRI hot   → TAKE_FULL (caps applied)   │
            │  UP_TRI warm  → TAKE_FULL (live evidence)  │
            │  UP_TRI cold  → Tier 1 cascade or SKIP     │
            │                                            │
            │  BULL_PROXY hot  → TAKE_SMALL (provisional)│
            │  BULL_PROXY *    → SKIP (cell DEFERRED)    │
            │                                            │
            │  DOWN_TRI wk2/wk3 + non-Bank → TAKE_SMALL  │
            │  DOWN_TRI *  → SKIP (cell DEFERRED)        │
            └────────────────────────────────────────────┘
```

---

## Trader heuristics applied (universal across cells)

| Heuristic | Condition | Action |
|---|---|---|
| Repeat-name cap | Same stock fires Bear cell within 6 trading days | downgrade to TAKE_SMALL |
| Day-correlation cap | 3+ Bear signals fire on same day | size each at 80% of normal |
| Max concurrent positions | 5 concurrent Bear positions held | skip new signal until exit |

---

## KILL rules summary (apply before sub-regime)

| Rule | Condition | Reason | Source |
|---|---|---|---|
| kill_001 | Bank sector × Bear DOWN_TRI | Live 0/6 + lifetime Bank 45% vs non-Bank 46.4% | Bear DOWN_TRI cell |
| BULL_PROXY vol-climax | vol_climax_flag=True × BULL_PROXY | Lifetime −11.0pp anti; capitulation breaks support | Bear BULL_PROXY cell |
| December UP_TRI | December month × Bear UP_TRI | Lifetime −25pp catastrophic | Bear UP_TRI cell S1 |
| Health UP_TRI | Health sector × Bear UP_TRI | Lifetime hot 32.4% (only sector where hot fails) | Bear UP_TRI cell S1 |

These are universal: applied BEFORE sub-regime detection, BEFORE Phase
5 hierarchy override. They reflect lifetime-validated structural
mismatches.

---

## Default behavior

When a Bear signal does not match any take rule:
- **DEFAULT: SKIP**
- Rationale: Bear regime cells are narrow-edge structurally. Without
  filter match, expected WR is at-or-below lifetime baseline (50-55%
  range across cells). Trader-level conservatism preferred over
  unfiltered exposure.

---

## Provisional filter enablement (manual control)

Two cells (DOWN_TRI, BULL_PROXY) require explicit operator enablement
of provisional filters:

| Cell | Provisional filter | Default | Enable when |
|---|---|---|---|
| Bear DOWN_TRI | wk2/wk3 + non-Bank → TAKE_SMALL | OFF | After 30+ more live signals confirm filter |
| Bear BULL_PROXY | HOT-only → TAKE_SMALL | OFF | After Bear UP_TRI deployment success |

Default OFF means the cells produce SKIP on all signals until trader
explicitly enables. This is the conservative posture — preserves
optionality without committing capital to provisional findings.

---

## Sub-regime stratified WR tracking (production observability)

Per Sonnet 4.5 BS1 critique, production must track sub-regime-stratified
WRs separately to detect drift early:

```python
# Production telemetry per signal:
{
  "signal_type": "UP_TRI",
  "subregime_at_signal": "hot",
  "subregime_confidence": 75.0,
  "expected_wr": 0.68,
  "calibrated_wr_range": [0.65, 0.75],
  "outcome": "DAY6_WIN",  # filled in at Day 6
  "phase5_status": "PHASE_5_VALIDATED",
  "kill_rule_triggered": null,
  "filter_match_tier": "broad-band",
}
```

Pause production when:
- Hot-Bear WR rolls below 60% over 40 trades (2σ below 70% mean)
- Cold-Tier-1 WR drops below 50% over 30 trades
- 3 consecutive sub-regime-classified setups fail
- Detector classifies as "borderline" daily for 3+ trading days

---

## Open questions for production integration

1. **Where does sub-regime detector run?** Per-day pre-market composer
   (computes once, shared across signals) or per-signal (slower but
   captures intraday regime shifts)?

2. **Phase-5 status field — where stored?** Currently in
   `combinations_live_validated.parquet`; production scanner needs
   query-ready access at signal time.

3. **Provisional filter enablement UX.** How does trader toggle
   `bear_downtri_provisional_enabled` and `bear_bullproxy_provisional_enabled`
   flags? Telegram command? Settings file?

4. **Trader heuristics implementation location.** Repeat-name cap and
   day-correlation cap require state lookup (recent signals same-name,
   same-day). Scanner main loop or Wave 5 brain layer?

5. **Calibrated WR display.** Should Telegram digest show "expected
   65-75%" alongside each signal, or risk anchoring trader to a range?

---

## Update Log

- **v1 (2026-05-02 night, BS2):** Initial unified Bear regime decision
  flow. 4-step structure (KILL → sub-regime detection → Phase-5
  override → per-cell cascade). Calibrated WR expectations table.
  KILL rules consolidated from all 3 cells. Provisional filter
  enablement flags for DOWN_TRI/BULL_PROXY.
