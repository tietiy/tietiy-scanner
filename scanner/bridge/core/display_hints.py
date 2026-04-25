"""
Display hints — pure functions computing SDR.display.* fields.

These functions are called by composers when building each SDR. PWA and
Telegram both read SDR.display.* and render accordingly. Compose owns the
hints; Present (PWA/Telegram) owns the rendering. Decoupled.

Pure: no I/O, no state, no side effects. Same inputs → same outputs.

See doc/bridge_design_v1.md §4 (display fields) and §11 (PWA rendering).
"""

from typing import Optional

from scanner.bridge.rules.thresholds import (
    PRIORITY_SKIP,
    PRIORITY_TAKE_FULL,
    PRIORITY_TAKE_SMALL,
    PRIORITY_WATCH,
)


_BUCKET_PRIORITY = {
    "TAKE_FULL":  PRIORITY_TAKE_FULL,
    "TAKE_SMALL": PRIORITY_TAKE_SMALL,
    "WATCH":      PRIORITY_WATCH,
    "SKIP":       PRIORITY_SKIP,
}

_BUCKET_COLOR = {
    "TAKE_FULL":  "green",
    "TAKE_SMALL": "yellow",
    "WATCH":      "neutral",
    "SKIP":       "red",
}

_BUCKET_EMOJI = {
    "TAKE_FULL":  "✅",
    "TAKE_SMALL": "🟡",
    "WATCH":      "👁",
    "SKIP":       "❌",
}

_CHANGED_BUCKET_BUMP = 5
_MAX_SCORE_BUMP = 4
_SCORE_BUMP_BASE = 5  # score above this gets +(score - base), capped at MAX

_WATCH_HIGH_COHORT_N = 10  # WATCH at/above this n → "medium", below → "low"


def get_priority(bucket: str,
                 score: Optional[int] = None,
                 is_changed_bucket: bool = False) -> int:
    """
    Returns card_priority value for sorting in PWA + Telegram.

    Base from thresholds (TAKE_FULL=95, TAKE_SMALL=80, WATCH=50, SKIP=10).
    Score bump: 9→+4, 8→+3, 7→+2, 6→+1, ≤5 or None→+0.
    bucket_changed bump: +5 (so reclassified signals sort to top of new bucket).
    """
    base = _BUCKET_PRIORITY.get(bucket, PRIORITY_SKIP)

    score_bump = 0
    if score is not None:
        score_bump = max(0, min(_MAX_SCORE_BUMP,
                                score - _SCORE_BUMP_BASE))

    changed_bump = _CHANGED_BUCKET_BUMP if is_changed_bucket else 0

    return base + score_bump + changed_bump


def get_color(bucket: str,
              is_changed_bucket: bool = False) -> str:
    """
    Returns card_color_hint string used by PWA renderer.

    TAKE_FULL→green, TAKE_SMALL→yellow, WATCH→neutral, SKIP→red.
    If is_changed_bucket, prepend "changed_" so PWA can render
    a transition indicator.
    """
    color = _BUCKET_COLOR.get(bucket, "neutral")
    if is_changed_bucket:
        return f"changed_{color}"
    return color


def get_emoji(bucket: str) -> str:
    """
    Returns telegram_emoji for the bucket.
    TAKE_FULL→✅, TAKE_SMALL→🟡, WATCH→👁, SKIP→❌.
    """
    return _BUCKET_EMOJI.get(bucket, "")


def get_card_title(symbol: str, signal_type: str) -> str:
    """
    Returns 'SYMBOL • SIGNAL_TYPE' formatted string.
    Example: 'TATAMOTORS • UP_TRI'
    """
    return f"{symbol} • {signal_type}"


def get_card_subtitle(sector: str,
                      regime: str,
                      score: int,
                      tier_label: Optional[str] = None) -> str:
    """
    Returns 'Sector • Regime • Score N' (• tier_label appended if given).
    """
    base = f"{sector} • {regime} • Score {score}"
    if tier_label:
        return f"{base} • {tier_label}"
    return base


def get_confidence_band(bucket: str,
                        exact_cohort_n: Optional[int] = None,
                        has_kill_match: bool = False) -> str:
    """
    Returns confidence band for SDR.learner_hooks.confidence_band.

    Logic:
        TAKE_FULL                   → "high"
        SKIP with kill_match        → "high"
        TAKE_SMALL                  → "medium"
        WATCH, exact_cohort_n >= 10 → "medium"
        WATCH, exact_cohort_n < 10  → "low"
        SKIP without kill_match     → "medium"
        anything else               → "medium"
    """
    if bucket == "TAKE_FULL":
        return "high"
    if bucket == "SKIP":
        return "high" if has_kill_match else "medium"
    if bucket == "TAKE_SMALL":
        return "medium"
    if bucket == "WATCH":
        if (exact_cohort_n is not None
                and exact_cohort_n >= _WATCH_HIGH_COHORT_N):
            return "medium"
        return "low"
    return "medium"


def assemble_display_block(bucket: str,
                           symbol: str,
                           signal_type: str,
                           sector: str,
                           regime: str,
                           score: int,
                           tier_label: Optional[str] = None,
                           is_changed_bucket: bool = False,
                           show_in_main: bool = True,
                           show_in_contra: bool = False) -> dict:
    """
    Builds full SDR.display dict in one call.
    tappable_for_why is always True (every signal has [why?] in Wave 4).
    telegram_priority equals card_priority by design.
    """
    priority = get_priority(
        bucket, score=score, is_changed_bucket=is_changed_bucket)
    return {
        "card_title": get_card_title(symbol, signal_type),
        "card_subtitle": get_card_subtitle(
            sector, regime, score, tier_label=tier_label),
        "card_color_hint": get_color(
            bucket, is_changed_bucket=is_changed_bucket),
        "card_priority": priority,
        "show_in_main_signals_tab": show_in_main,
        "show_in_contra_tab": show_in_contra,
        "tappable_for_why": True,
        "telegram_emoji": get_emoji(bucket),
        "telegram_priority": priority,
    }
