"""5-gate decision tree per doc/regime_v2_design/04_decision_logic.md.

States: BULL / BULL_RECOVERY / CHOPPY / BEAR_RECOVERY / BEAR

Thresholds documented inline with design-doc references. VIX-missing
degraded mode tightens the Bull gate and suppresses Bull-Recovery
(per design §04 "Edge cases > VIX missing").
"""
from __future__ import annotations

from typing import Dict, Tuple, List


# ----- Gate thresholds (design §04 "Why these specific thresholds") -----
# Bull
BULL_SLOPE_MIN = 0.005                       # design §04 Gate 1
BULL_SLOPE_MIN_NO_VIX = 0.008                # design §04 "VIX missing" edge case
BULL_VIX_MAX = 18.0                          # design §04 Gate 1
# Bear
BEAR_SLOPE_MAX = -0.003                      # design §04 Gate 2 (loosened from v1's -0.005)
BEAR_RET20_MAX = -2.0                        # design §04 Gate 2
BEAR_VIX_MIN = 18.0                          # design §04 Gate 2
# Bull-Recovery
BULLRECOV_RET20_MIN = 3.0                    # design §04 Gate 3
BULLRECOV_VIX_MAX = 20.0                     # design §04 Gate 3 (degraded mode: suppressed)
# Bear-Recovery
BEARRECOV_RET20_MIN = 0.0                    # design §04 Gate 4
# Choppy: residual


def classify_regime(features: Dict, *, use_vix: bool = True) -> Tuple[str, float, List[Dict]]:
    """Apply the 5-gate decision tree to a feature dict.

    Args:
        features: dict produced by features.feature_dict_at() — keys include
            above_ema50, above_ema200, slope_10d_ema50, ret20_pct,
            realized_vol_20d_pct, india_vix, vix_change_10d_pct.
        use_vix: when True and india_vix is not None, gates use VIX-inclusive
            thresholds. When False or VIX missing, falls back to degraded mode.

    Returns:
        (state, confidence, gate_trace) — state is one of the 5 enum strings;
        confidence is a float 0-1 reflecting how strongly the gate matched
        (all required conditions satisfied = 1.0); gate_trace is a list of
        dicts (one per gate) recording the evaluation.
    """
    # Detect VIX availability
    vix = features.get("india_vix")
    vix_available = vix is not None and not _is_nan(vix)
    effective_use_vix = use_vix and vix_available
    degraded_mode = not effective_use_vix

    trace: List[Dict] = []

    above_e50 = bool(features.get("above_ema50", False))
    above_e200 = bool(features.get("above_ema200", False))
    slope = features.get("slope_10d_ema50")
    ret20 = features.get("ret20_pct")

    # If core features missing, return Unknown → Choppy
    if slope is None or _is_nan(slope) or ret20 is None or _is_nan(ret20):
        trace.append({"gate": "INSUFFICIENT_DATA", "matched": True, "reason": "slope or ret20 NaN"})
        return ("CHOPPY", 0.0, trace)

    # --- Gate 1: BULL (most restrictive) ---
    # retune2 Fix E: Sonnet review showed VIX-degraded BULL gate too strict;
    # new-ATH rally Aug 2025-Feb 2026 stayed CHOPPY. In degraded mode, accept
    # either (a) loose slope>0.004 OR (b) strong ret20>3%. Structural reqs
    # (above_ema50 + above_ema200 + ret20>0) stay as joint gates.
    bull_slope_min = BULL_SLOPE_MIN if effective_use_vix else BULL_SLOPE_MIN_NO_VIX
    bull_structural = above_e50 and above_e200 and ret20 > 0
    if effective_use_vix:
        bull_momentum_ok = slope > bull_slope_min
        bull_match = bull_structural and bull_momentum_ok and vix < BULL_VIX_MAX
        bull_conds = {
            "above_ema50": above_e50,
            "above_ema200": above_e200,
            "slope_gt_threshold": slope > bull_slope_min,
            "ret20_gt_0": ret20 > 0,
            "vix_lt_18": vix < BULL_VIX_MAX,
        }
    else:
        # retune2 Fix E: degraded-mode momentum check is slope OR ret20 strong
        bull_slope_degraded_min = 0.004
        bull_ret20_strong = 3.0
        bull_momentum_ok = (slope > bull_slope_degraded_min) or (ret20 > bull_ret20_strong)
        bull_match = bull_structural and bull_momentum_ok
        bull_conds = {
            "above_ema50": above_e50,
            "above_ema200": above_e200,
            "ret20_gt_0": ret20 > 0,
            "degraded_momentum_ok": bull_momentum_ok,
            "_detail": {
                "slope_gt_0004": slope > bull_slope_degraded_min,
                "ret20_gt_3": ret20 > bull_ret20_strong,
            }
        }
    trace.append({"gate": "BULL", "matched": bull_match, "conditions": bull_conds,
                  "degraded_mode": degraded_mode})
    if bull_match:
        return ("BULL", 1.0, trace)

    # --- Gate 2: BEAR (memo-driven) ---
    # retune3 BEAR_SEMANTIC_MEMO Q2 implementation.
    # Required AND: above_ema50=False (structural).
    # Required OR (any one): slope<-0.003 (Fix I, loosened from -0.005),
    #                       ret20<-3% (loosened from -2%),
    #                       dd_from_50d_high<-8% (Fix J, new).
    # Disqualifying: above_ema200=True AND not >=2 OR conditions
    #                AND dd_from_50d_high > -10%.
    dd_from_50d_high = features.get("dd_from_50d_high_pct")
    if dd_from_50d_high is None or _is_nan(dd_from_50d_high):
        dd_from_50d_high = 0.0  # no drawdown evidence

    or_slope = slope < BEAR_SLOPE_MAX  # -0.003
    or_ret20 = ret20 < -3.0           # tightened from -2.0
    or_drawdown = dd_from_50d_high < -8.0
    or_conditions_met = sum([or_slope, or_ret20, or_drawdown])

    structural_ok = not above_e50
    # Disqualifying — long-cycle Bull still intact AND not deep
    long_cycle_bull = above_e200
    extreme_dd = dd_from_50d_high < -10.0
    if long_cycle_bull and or_conditions_met < 2 and not extreme_dd:
        bear_disqualified = True
    else:
        bear_disqualified = False

    bear_conds = {
        "above_ema50_false": structural_ok,
        "or_slope_lt_neg003": or_slope,
        "or_ret20_lt_neg3": or_ret20,
        "or_drawdown_gt_8pct": or_drawdown,
        "or_count": or_conditions_met,
        "disqualified_long_cycle_bull": bear_disqualified,
    }
    if effective_use_vix:
        bear_conds["vix_gt_18"] = vix > BEAR_VIX_MIN
        bear_conds["vix_gt_15"] = vix > 15.0  # not a hard fail in memo; informational

    bear_match = structural_ok and (or_conditions_met >= 1) and (not bear_disqualified)
    trace.append({"gate": "BEAR", "matched": bear_match, "conditions": bear_conds,
                  "degraded_mode": degraded_mode})
    if bear_match:
        return ("BEAR", 1.0, trace)

    # --- Gate 3: BULL_RECOVERY ---
    # Per design §04 "Edge cases > VIX missing": Gate 3 cannot fire without VIX.
    if effective_use_vix:
        bullrecov_conds = {
            "above_ema50": above_e50,
            "slope_gt_0": slope > 0,
            "slope_le_005": slope <= BULL_SLOPE_MIN,
            "ret20_gt_3": ret20 > BULLRECOV_RET20_MIN,
            "vix_lt_20": vix < BULLRECOV_VIX_MAX,
        }
        bullrecov_match = all(bullrecov_conds.values())
        trace.append({"gate": "BULL_RECOVERY", "matched": bullrecov_match,
                      "conditions": bullrecov_conds})
        if bullrecov_match:
            return ("BULL_RECOVERY", 1.0, trace)
    else:
        trace.append({"gate": "BULL_RECOVERY", "matched": False,
                      "reason": "suppressed_vix_missing"})

    # --- Gate 4: BEAR_RECOVERY (memo Q4 driven) ---
    # retune3 BEAR_SEMANTIC_MEMO Q4:
    # - above_ema50 = False (still below short-cycle reference)
    # - slope > -0.001 (not actively declining)
    # - EITHER ret20 > 0 (positive 20d return)
    # - OR above_50d_low > +5% (bounced ≥5% off 50-day low — Fix K)
    above_50d_low = features.get("above_50d_low_pct")
    if above_50d_low is None or _is_nan(above_50d_low):
        above_50d_low = 0.0

    br_slope_ok = slope > -0.001         # not actively declining
    br_ret20_or_bounce = (ret20 > BEARRECOV_RET20_MIN) or (above_50d_low > 5.0)

    bearrecov_conds = {
        "above_ema50_false": not above_e50,
        "slope_gt_neg0001": br_slope_ok,
        "ret20_gt_0_or_bounce_gt_5pct": br_ret20_or_bounce,
    }
    bearrecov_match = (not above_e50) and br_slope_ok and br_ret20_or_bounce
    trace.append({"gate": "BEAR_RECOVERY", "matched": bearrecov_match,
                  "conditions": bearrecov_conds})
    if bearrecov_match:
        return ("BEAR_RECOVERY", 1.0, trace)

    # --- Gate 5: CHOPPY (residual) ---
    trace.append({"gate": "CHOPPY", "matched": True, "reason": "residual_fall_through"})
    return ("CHOPPY", 1.0, trace)


def _is_nan(x) -> bool:
    """NaN detector that doesn't require numpy import in caller."""
    try:
        return x != x  # NaN is the only value that is != itself
    except Exception:
        return False
