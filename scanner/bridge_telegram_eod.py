"""
bridge_telegram_eod — EOD digest renderer.

Reads bridge_state.json (EOD), renders the digest per design doc §12.3,
sends via the existing telegram_bot infrastructure.

Always fires on trading day (mirror L1 unconditional pattern). Section-
level skipping handles the conditionality:
  - SKIPPED phase  → short "market closed" notice
  - ERROR phase    → short-circuit (workflow notify-on-failure handles)
  - OK / DEGRADED  → full digest, sections auto-skip when empty

Thin renderer. NO HTTP / retry / escaping / split logic — all of that
lives in scanner.telegram_bot. This file only:
  - reads bridge_state.json
  - composes a MarkdownV2 string by assembling section renderers
  - calls telegram_bot.send_message()

CLI:
    python scanner/bridge_telegram_eod.py
    python scanner/bridge_telegram_eod.py --state-file output/bridge_state.json
    python scanner/bridge_telegram_eod.py --dry-run

Exit codes: 0 = sent / SKIPPED / dry-run / ERROR-short-circuit; 1 =
state missing / malformed / send failed.

See doc/bridge_design_v1.md §12.3 (EOD digest template), §13 (workflow).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional


# Self-bootstrap so script runs as `python scanner/bridge_telegram_eod.py`
_SCANNER_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCANNER_DIR not in sys.path:
    sys.path.insert(0, _SCANNER_DIR)

from telegram_bot import (  # noqa: E402
    send_message,
    _esc,
    _pwa_keyboard,
)


# Outcome → (emoji, verb) display mapping. Unknown outcomes fall back
# to (❓, outcome.upper()).
_OUTCOME_DISPLAY = {
    "TARGET_HIT": ("✅", "WON"),
    "DAY6_WIN":   ("✅", "WON"),
    "STOP_HIT":   ("🟡", "STOPPED"),
    "DAY6_LOSS":  ("🟡", "STOPPED"),
    "DAY6_FLAT":  ("⏸",  "FLAT"),
}


# =====================================================================
# Public entry
# =====================================================================

def send_eod_digest(state_file: str = "output/bridge_state.json",
                    dry_run: bool = False) -> dict:
    """Read bridge_state.json (EOD), render the digest, send via
    Telegram (or just return rendered string in dry_run mode).

    Returns dict with the same keys as the L1/L2 renderers:
        sent, phase_status, char_count, signals_rendered, skip_reason,
        rendered.
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

    # === ERROR phase: short-circuit. Workflow's notify-on-failure
    # step handles user notification. ===
    if phase_status == "ERROR":
        return _result(
            False, phase_status, "",
            skip_reason=(
                "phase_status=ERROR (workflow notify-on-failure "
                "handles user alert)"
            ),
        )

    # === SKIPPED phase: short market-closed notice ===
    if phase_status == "SKIPPED":
        rendered = _render_skipped_brief(state)
        return _maybe_send(rendered, phase_status, 0,
                           dry_run=dry_run)

    # === Main render path: full digest (OK or DEGRADED) ===
    rendered = _render_digest(state)
    signals_rendered = len(state.get("signals") or [])
    return _maybe_send(rendered, phase_status, signals_rendered,
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
        prog="bridge_telegram_eod",
        description=(
            "Render and send the bridge L4 EOD Telegram digest"
        ),
    )
    parser.add_argument("--state-file",
                        default="output/bridge_state.json",
                        help="Path to bridge_state.json")
    parser.add_argument("--dry-run", action="store_true",
                        help=("Render and print to stdout but do "
                              "NOT send to Telegram"))

    args = parser.parse_args(argv)

    result = send_eod_digest(
        state_file=args.state_file,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("=" * 60)
        print("RENDERED MARKDOWN (dry-run, NOT sent):")
        print("=" * 60)
        print(result["rendered"] or "(empty)")
        print("=" * 60)

    log = {
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "level":             "INFO" if result["sent"]
                             or args.dry_run
                             or result["skip_reason"] else "ERROR",
        "component":         "bridge_telegram_eod",
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
    if result["sent"]:
        return 0
    if result["phase_status"] == "ERROR":
        return 0

    # Real failures: state file missing, malformed, send_message=False
    return 1


# =====================================================================
# Top-level renderers
# =====================================================================

def _render_digest(state: dict) -> str:
    """Main digest path (phase_status in {OK, DEGRADED}).

    Assembles non-None section strings with appropriate spacing.
    Order per design §12.3:
      header
      [resolutions]
      [pattern_updates]
      [proposals]
                                      ← blank line separator
      open_positions
      [contra]
    """
    market_date = state.get("market_date", "")
    phase_status = state.get("phase_status", "")
    signals = state.get("signals") or []
    summary = state.get("summary") or {}
    alerts = state.get("alerts") or []
    contra = state.get("contra") or {}

    parts = [_render_header(market_date, phase_status)]

    # Body sections — resolutions / patterns / proposals (each Optional)
    body = []
    res = _render_resolutions_section(signals)
    if res:
        body.append(res)
    pat = _render_pattern_updates_section(summary)
    if pat:
        body.append(pat)
    prop = _render_proposals_section(alerts)
    if prop:
        body.append(prop)

    # Body sections separated by blank lines for readability
    if body:
        parts.append("\n\n".join(body))

    # Footer sections — open positions (always) + contra (optional)
    open_line = _render_open_positions_section(summary)
    contra_line = _render_contra_section(contra, market_date)

    if open_line or contra_line:
        # Blank line separator between body and footer
        footer = []
        if open_line:
            footer.append(open_line)
        if contra_line:
            footer.append(contra_line)
        parts.append("\n".join(footer))

    return "\n\n".join(parts)


def _render_skipped_brief(state: dict) -> str:
    """Short notice when phase_status=SKIPPED (non-trading day)."""
    market_date = state.get("market_date", "")
    return (
        f"📊 *EOD — {_esc(market_date)}*\n"
        f"🔕 Market closed today — no EOD\\."
    )


# =====================================================================
# Section renderers — each returns Optional[str]; None means "skip"
# =====================================================================

def _render_header(market_date: str, phase_status: str) -> str:
    """📊 *EOD [(partial data)] — YYYY-MM-DD*"""
    if phase_status == "DEGRADED":
        return (
            f"📊 *EOD \\(partial data\\) — {_esc(market_date)}*"
        )
    return f"📊 *EOD — {_esc(market_date)}*"


def _render_resolutions_section(signals: list) -> Optional[str]:
    """'Today's signals resolved:' label + one line per resolution.

    Returns None if signals is empty (header bar handles "no
    resolutions" via banner; we don't double-state it here).
    """
    if not isinstance(signals, list) or not signals:
        return None

    lines = [_esc("Today's signals resolved:")]
    for sdr in signals:
        if not isinstance(sdr, dict):
            continue
        lines.append(_render_resolution_line(sdr))
    return "\n".join(lines)


def _render_pattern_updates_section(summary: dict) -> Optional[str]:
    """'Pattern updates:' label + one line per update.

    Reads summary.pattern_updates[]. Each entry is a dict with at
    minimum a 'message' field. Session A doesn't populate this list —
    Session C will, with boost demotion warnings + tier holdings.
    Returns None when empty.
    """
    if not isinstance(summary, dict):
        return None
    updates = summary.get("pattern_updates") or []
    if not isinstance(updates, list) or not updates:
        return None

    lines = [_esc("Pattern updates:")]
    for upd in updates:
        if not isinstance(upd, dict):
            continue
        msg = upd.get("message")
        if not isinstance(msg, str) or not msg:
            continue
        lines.append(_esc(msg))
    if len(lines) == 1:
        return None
    return "\n".join(lines)


def _render_proposals_section(alerts: list) -> Optional[str]:
    """'Proposals:' label + one line per proposal-drafted alert.

    Reads alerts[] filtered by kind=='proposal_drafted'. Session A
    doesn't emit these alerts; future session in eod.py composer will.
    Returns None when none found.
    """
    if not isinstance(alerts, list) or not alerts:
        return None

    drafted = [
        a for a in alerts
        if isinstance(a, dict)
        and a.get("kind") == "proposal_drafted"
    ]
    if not drafted:
        return None

    lines = [_esc("Proposals:")]
    for a in drafted:
        msg = a.get("message")
        if not isinstance(msg, str) or not msg:
            continue
        lines.append(_esc(msg))
    if len(lines) == 1:
        return None
    return "\n".join(lines)


def _render_open_positions_section(summary: dict) -> str:
    """'Open positions: N' — always renders (even N=0 is information).

    Session B refinement: omit the '(M exit tomorrow)' detail. Tomorrow
    requires trading-day awareness; track as Session B+ enhancement.
    """
    if not isinstance(summary, dict):
        n = 0
    else:
        n = summary.get("open_positions_count") or 0
    return f"{_esc('Open positions:')} {_esc(str(n))}"


def _render_contra_section(contra: dict, market_date: str) -> Optional[str]:
    """'🔄 Contra: ...' line. Skip if no resolutions today AND no
    active rules.

    Format: "🔄 Contra: N resolved. SYMBOL VERB +X.X%. kill_id n=N."
    Pieces drop gracefully when their data isn't present.
    """
    if not isinstance(contra, dict):
        return None

    resolutions = contra.get("recent_resolutions") or []
    if not isinstance(resolutions, list):
        resolutions = []
    today_resolutions = [
        r for r in resolutions
        if isinstance(r, dict)
        and r.get("resolved_date") == market_date
    ]

    active = contra.get("active_rules") or []
    if not isinstance(active, list):
        active = []

    if not today_resolutions and not active:
        return None

    # Build pieces as plain strings; _esc the whole body once at the
    # end so that reserved characters (=, ., +, -, _) introduced by
    # literals between piece tokens get escaped uniformly.
    pieces: list = []

    if today_resolutions:
        n_res = len(today_resolutions)
        pieces.append(f"{n_res} resolved")

        # Surface first resolution's outcome as exemplar (no per-
        # resolution emoji here — only the 🔄 prefix carries an emoji,
        # per design §12.3 example "🔄 Contra: 1 resolved. AXISBANK
        # WON +3.1%. kill_001 n=15.")
        first = today_resolutions[0]
        ex_sym = _clean_symbol(first.get("symbol"))
        ex_outcome = first.get("outcome")
        ex_pnl = first.get("pnl_pct")
        _, verb = _outcome_to_display(ex_outcome)
        if isinstance(ex_pnl, (int, float)):
            pieces.append(f"{ex_sym} {verb} {ex_pnl:+.1f}%")
        else:
            pieces.append(f"{ex_sym} {verb}")

    # First active rule's progress
    if active:
        first_rule = active[0]
        if isinstance(first_rule, dict):
            kid = first_rule.get("kill_id")
            n_count = first_rule.get("n")
            if kid and isinstance(n_count, (int, float)):
                pieces.append(f"{kid} n={int(n_count)}")
            elif kid:
                pieces.append(f"{kid} active")

    if not pieces:
        return None

    full_body = ". ".join(pieces) + "."
    return f"🔄 Contra: {_esc(full_body)}"


# =====================================================================
# Per-resolution line
# =====================================================================

def _render_resolution_line(sdr: dict) -> str:
    """{emoji} {SYMBOL} {VERB} {pnl:+.1f}%"""
    symbol = _clean_symbol(sdr.get("symbol"))
    outcome_block = sdr.get("outcome") or {}
    outcome = outcome_block.get("outcome")
    pnl = outcome_block.get("pnl_pct")

    emoji, verb = _outcome_to_display(outcome)
    pnl_str = _format_pnl(pnl)

    if pnl_str:
        return (
            f"{emoji} {_esc(symbol)} {_esc(verb)} {pnl_str}"
        )
    # No pnl available — render without it
    return f"{emoji} {_esc(symbol)} {_esc(verb)}"


# =====================================================================
# Helpers
# =====================================================================

def _outcome_to_display(outcome) -> tuple:
    """(emoji, verb) for an outcome string. Unknown → (❓, upper)."""
    if outcome in _OUTCOME_DISPLAY:
        return _OUTCOME_DISPLAY[outcome]
    if isinstance(outcome, str) and outcome:
        return ("❓", outcome.upper())
    return ("❓", "?")


def _clean_symbol(symbol) -> str:
    if not isinstance(symbol, str):
        return "?"
    if symbol.endswith(".NS"):
        return symbol[:-3]
    return symbol


def _format_pnl(pnl) -> str:
    """'+5.2%' or '-2.4%' (MarkdownV2-escaped) or '' if non-numeric."""
    if not isinstance(pnl, (int, float)):
        return ""
    return _esc(f"{pnl:+.1f}") + "%"


# =====================================================================
# Script entry
# =====================================================================

if __name__ == "__main__":
    sys.exit(main())
