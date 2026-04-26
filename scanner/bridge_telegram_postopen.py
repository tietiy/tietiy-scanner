"""
bridge_telegram_postopen — post-open conditional alert renderer.

Reads bridge_state.json (POST_OPEN), and IF the composer flagged
should_send_telegram=True, renders the L2 alert per design doc §12.2
and sends via the existing telegram_bot infrastructure.

Single source of truth: the composer decides when to fire (gap_breach
OR bucket_change). This script just respects that flag.

Thin renderer. NO HTTP / retry / escaping / split logic — all of that
lives in scanner.telegram_bot. This file only:
  - reads bridge_state.json
  - filters qualifying signals (bucket_changed OR gap_severity=severe)
  - composes a MarkdownV2 string
  - calls telegram_bot.send_message()

CLI:
    python scanner/bridge_telegram_postopen.py
    python scanner/bridge_telegram_postopen.py --state-file output/bridge_state.json
    python scanner/bridge_telegram_postopen.py --dry-run

Exit codes: 0 = sent, skipped legitimately (no changes / non-trading
day / phase ERROR — workflow's notify-on-failure handles ERROR),
1 = state missing / malformed / send failed.

See doc/bridge_design_v1.md §12.2 (POST_OPEN Telegram template),
TG-02 (BR-07).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional


# Self-bootstrap so script runs as `python scanner/bridge_telegram_postopen.py`
_SCANNER_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCANNER_DIR not in sys.path:
    sys.path.insert(0, _SCANNER_DIR)

from telegram_bot import (  # noqa: E402
    send_message,
    _esc,
    _pwa_keyboard,
)


# Bucket ordering (TAKE_FULL highest conviction, SKIP lowest)
_BUCKET_RANK = {
    "TAKE_FULL":  0,
    "TAKE_SMALL": 1,
    "WATCH":      2,
    "SKIP":       3,
}


# =====================================================================
# Public entry
# =====================================================================

def send_postopen_brief(state_file: str = "output/bridge_state.json",
                        dry_run: bool = False) -> dict:
    """Read bridge_state.json, render the L2 alert when warranted, send
    via Telegram (or just return rendered string in dry_run mode).

    Returns dict with the same keys as the L1 renderer's response.
    """
    if not os.path.exists(state_file):
        return _result(False, "UNKNOWN", "",
                       skip_reason=f"state file not found: {state_file}")

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        return _result(False, "UNKNOWN", "",
                       skip_reason=f"state file malformed JSON: {e}")

    phase_status = state.get("phase_status") or "UNKNOWN"

    # === ERROR phase: short-circuit, workflow's notify-on-failure
    # step handles the actual user notification. ===
    if phase_status == "ERROR":
        return _result(
            False, phase_status, "",
            skip_reason=(
                "phase_status=ERROR (workflow notify-on-failure "
                "handles user alert)"
            ),
        )

    # === SKIPPED phase: render a short L2-specific notice ===
    if phase_status == "SKIPPED":
        rendered = _render_skipped_brief(state)
        return _maybe_send(rendered, phase_status, 0,
                           dry_run=dry_run)

    # === should_send_telegram=False: no qualifying changes; no message ===
    if not state.get("should_send_telegram"):
        return _result(
            False, phase_status, "",
            skip_reason=(
                "should_send_telegram=False "
                "(no qualifying changes)"
            ),
        )

    # === Main render path: alert with qualifying signals ===
    qualifying = _qualifying_signals(state.get("signals") or [])
    rendered = _render_alert(state, qualifying)

    return _maybe_send(rendered, phase_status, len(qualifying),
                       dry_run=dry_run)


def _maybe_send(rendered: str,
                phase_status: str,
                signals_rendered: int,
                dry_run: bool) -> dict:
    if dry_run:
        return _result(False, phase_status, rendered,
                       signals_rendered=signals_rendered)
    sent = send_message(rendered, reply_markup=_pwa_keyboard())
    return _result(
        bool(sent), phase_status, rendered,
        signals_rendered=signals_rendered,
        skip_reason=None if sent else "send_message returned False",
    )


def _result(sent: bool,
            phase_status: str,
            rendered: str,
            *,
            signals_rendered: int = 0,
            skip_reason: Optional[str] = None) -> dict:
    return {
        "sent":             sent,
        "phase_status":     phase_status,
        "char_count":       len(rendered),
        "signals_rendered": signals_rendered,
        "skip_reason":      skip_reason,
        "rendered":         rendered,
    }


# =====================================================================
# CLI
# =====================================================================

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bridge_telegram_postopen",
        description=(
            "Render and send the bridge L2 POST_OPEN Telegram alert "
            "(conditional)"
        ),
    )
    parser.add_argument("--state-file",
                        default="output/bridge_state.json",
                        help="Path to bridge_state.json")
    parser.add_argument("--dry-run", action="store_true",
                        help=("Render and print to stdout but do "
                              "NOT send to Telegram"))

    args = parser.parse_args(argv)

    result = send_postopen_brief(
        state_file=args.state_file,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("=" * 60)
        print("RENDERED MARKDOWN (dry-run, NOT sent):")
        print("=" * 60)
        print(result["rendered"] or "(empty — no qualifying changes)")
        print("=" * 60)

    log = {
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "level":             "INFO" if result["sent"]
                             or args.dry_run
                             or result["skip_reason"] else "ERROR",
        "component":         "bridge_telegram_postopen",
        "sent":              result["sent"],
        "dry_run":           args.dry_run,
        "phase_status":      result["phase_status"],
        "char_count":        result["char_count"],
        "signals_rendered":  result["signals_rendered"],
        "skip_reason":       result["skip_reason"],
    }
    print(json.dumps(log, default=str))

    if args.dry_run:
        return 0

    # Skip cases that exit cleanly:
    #   - phase_status=ERROR (workflow handles)
    #   - phase_status=SKIPPED with successful send
    #   - should_send_telegram=False (no qualifying changes)
    if result["sent"]:
        return 0
    if result["phase_status"] == "ERROR":
        return 0
    if result["skip_reason"] and "should_send_telegram=False" \
            in result["skip_reason"]:
        return 0
    if result["skip_reason"] and "no qualifying" in result["skip_reason"]:
        return 0

    # Real failures: state file missing, malformed, send_message=False
    return 1


# =====================================================================
# Filter + sort
# =====================================================================

def _qualifying_signals(signals: list) -> list:
    """Return signals where bucket_changed=True OR
    gap_severity='severe'. Sorted per spec:
      0. force-skips (bucket flipped due to entry_still_valid=False)
      1. other downgrades
      2. upgrades
      3. gap-breach-only (bucket held but severity=severe)
    Within each priority: alphabetical by symbol.
    """
    out = []
    for s in signals:
        if not isinstance(s, dict):
            continue
        bucket_changed = bool(s.get("bucket_changed"))
        gap_eval = (s.get("evidence") or {}).get("gap_evaluation") or {}
        is_severe = gap_eval.get("gap_severity") == "severe"
        if bucket_changed or is_severe:
            out.append(s)
    out.sort(key=_sort_key)
    return out


def _sort_priority(sdr: dict) -> int:
    bucket_changed = bool(sdr.get("bucket_changed"))
    gap_eval = (sdr.get("evidence") or {}).get("gap_evaluation") or {}

    if bucket_changed:
        # Force-skip path: composer set entry_still_valid=False
        if gap_eval.get("entry_still_valid") is False:
            return 0

        prev = sdr.get("previous_bucket")
        new  = sdr.get("bucket")
        prev_idx = _BUCKET_RANK.get(prev, 99)
        new_idx  = _BUCKET_RANK.get(new, 99)
        if new_idx > prev_idx:
            return 1   # other downgrade
        if new_idx < prev_idx:
            return 2   # upgrade
        return 1       # tier shuffle within same level — treat as downgrade
    return 3           # gap-breach-only (bucket held, severity=severe)


def _sort_key(sdr: dict):
    return (_sort_priority(sdr), sdr.get("symbol") or "")


# =====================================================================
# Renderers
# =====================================================================

def _render_alert(state: dict, qualifying: list) -> str:
    """Main alert path: header + subhead + per-signal blocks."""
    market_date = state.get("market_date", "")
    phase_status = state.get("phase_status", "")
    bucket_changes = int(state.get("bucket_changes") or 0)
    gap_breaches = int(state.get("gap_breaches") or 0)

    lines = [_render_header(market_date, phase_status)]

    subhead = _render_subhead(bucket_changes, gap_breaches)
    if subhead:
        lines.append(subhead)

    # Defensive: if filter unexpectedly emptied (counters say >0 but
    # no qualifying SDRs), leave a single explanation line so the
    # message isn't a bare header.
    if not qualifying:
        lines.append("")
        lines.append(
            _esc("(no qualifying signals — composer counters may be "
                 "out of sync with SDR fields)"))
        return "\n".join(lines)

    for sdr in qualifying:
        lines.append("")
        if sdr.get("bucket_changed"):
            lines.append(_render_three_line(sdr))
        else:
            lines.append(_render_one_line(sdr))

    return "\n".join(lines)


def _render_header(market_date: str, phase_status: str) -> str:
    """⚠️ *Post-open alert [(partial data)] — YYYY-MM-DD*"""
    if phase_status == "DEGRADED":
        # `(partial data)` has parens that need escaping; whole tag is dynamic
        return (
            f"⚠️ *Post\\-open alert "
            f"\\(partial data\\) — {_esc(market_date)}*"
        )
    return f"⚠️ *Post\\-open alert — {_esc(market_date)}*"


def _render_subhead(bucket_changes: int, gap_breaches: int) -> str:
    """N reclassified[, K gap breach[es]]. Empty if both zero."""
    parts = []
    if bucket_changes > 0:
        parts.append(
            f"{_esc(str(bucket_changes))} reclassified")
    if gap_breaches > 0:
        word = "gap breach" if gap_breaches == 1 else "gap breaches"
        parts.append(
            f"{_esc(str(gap_breaches))} {word}")
    return ", ".join(parts)


def _render_three_line(sdr: dict) -> str:
    """3-line template for bucket_changed=True (per spec §12.2):

        SYMBOL gapped X.X% above|below scan_price.
        L1 was {prev}. L2 reclassifies to {new}.
        If you entered: consider position management.
    """
    symbol = _clean_symbol(sdr.get("symbol"))
    direction = (sdr.get("direction") or "LONG").upper()
    gap_eval = (sdr.get("evidence") or {}).get("gap_evaluation") or {}
    gap_pct = gap_eval.get("gap_pct")

    pct_str = (
        _esc(f"{gap_pct:+.1f}")
        if isinstance(gap_pct, (int, float))
        else "?"
    )
    direction_word = _direction_word(direction, gap_pct)
    prev_bucket = sdr.get("previous_bucket") or "?"
    new_bucket = sdr.get("bucket") or "?"

    return (
        f"{_esc(symbol)} gapped {pct_str}% "
        f"{_esc(direction_word)}\\.\n"
        f"L1 was {_esc(prev_bucket)}\\. "
        f"L2 reclassifies to {_esc(new_bucket)}\\.\n"
        f"If you entered: consider position management\\."
    )


def _render_one_line(sdr: dict) -> str:
    """1-line template for gap-breach-only (bucket held, severity=severe):

        SYMBOL gapped X.X% above|below scan_price (severe — already SKIP).
    """
    symbol = _clean_symbol(sdr.get("symbol"))
    direction = (sdr.get("direction") or "LONG").upper()
    gap_eval = (sdr.get("evidence") or {}).get("gap_evaluation") or {}
    gap_pct = gap_eval.get("gap_pct")

    pct_str = (
        _esc(f"{gap_pct:+.1f}")
        if isinstance(gap_pct, (int, float))
        else "?"
    )
    direction_word = _direction_word(direction, gap_pct)
    bucket = sdr.get("bucket") or "?"

    return (
        f"{_esc(symbol)} gapped {pct_str}% "
        f"{_esc(direction_word)} "
        f"\\(severe — already {_esc(bucket)}\\)\\."
    )


def _render_skipped_brief(state: dict) -> str:
    """Short L2 notice when phase_status=SKIPPED (non-trading day)."""
    market_date = state.get("market_date", "")
    return (
        f"🔕 *Post\\-open — {_esc(market_date)}*\n"
        f"Market closed today — L2 not run\\."
    )


# =====================================================================
# Helpers
# =====================================================================

def _direction_word(direction: str, gap_pct) -> str:
    """Render the actual price-movement direction (not adverse/favorable).

    open_validator's gap_pct is direction-adjusted (positive = adverse
    for the trade direction). Translate back to actual price movement:

        LONG:  gap_pct > 0 → actual_open ABOVE scan_price (adverse for LONG)
        LONG:  gap_pct < 0 → actual_open BELOW scan_price
        SHORT: gap_pct > 0 → actual_open BELOW scan_price (adverse for SHORT)
        SHORT: gap_pct < 0 → actual_open ABOVE scan_price
    """
    if not isinstance(gap_pct, (int, float)):
        return "from scan_price"
    if direction == "SHORT":
        return "below scan_price" if gap_pct > 0 else "above scan_price"
    # default LONG
    return "above scan_price" if gap_pct > 0 else "below scan_price"


def _clean_symbol(symbol) -> str:
    if not isinstance(symbol, str):
        return "?"
    if symbol.endswith(".NS"):
        return symbol[:-3]
    return symbol


# =====================================================================
# Script entry
# =====================================================================

if __name__ == "__main__":
    sys.exit(main())
