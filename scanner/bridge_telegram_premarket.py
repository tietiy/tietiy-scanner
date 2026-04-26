"""
bridge_telegram_premarket — pre-market brief renderer.

Reads bridge_state.json, renders the L1 PRE_MARKET Telegram message per
doc/bridge_design_v1.md §12.1, sends via the existing telegram_bot
infrastructure.

Thin renderer. NO HTTP / retry / escaping / split logic — all of that
lives in scanner.telegram_bot. This file only:
  - reads bridge_state.json
  - composes a MarkdownV2 string
  - calls telegram_bot.send_message()

CLI:
    python scanner/bridge_telegram_premarket.py
    python scanner/bridge_telegram_premarket.py --state-file output/bridge_state.json
    python scanner/bridge_telegram_premarket.py --dry-run

Exit codes: 0 = sent or skipped (expected non-trading day), 1 = error.

See doc/bridge_design_v1.md §12 (Telegram template), TG-02 (BR-07).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional


# Self-bootstrap so script runs as `python scanner/bridge_telegram_premarket.py`
_SCANNER_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCANNER_DIR not in sys.path:
    sys.path.insert(0, _SCANNER_DIR)

from telegram_bot import (  # noqa: E402
    send_message,
    _esc,
    _p_esc,
    _pwa_keyboard,
)


_BRIDGE_VERSION = "1.0.0"
_BUCKET_ORDER = ("TAKE_FULL", "TAKE_SMALL", "WATCH", "SKIP")
_BUCKET_HEADERS = {
    "TAKE_FULL":  "✅ *TAKE FULL*",
    "TAKE_SMALL": "🟡 *TAKE SMALL*",
    "WATCH":      "👁 *WATCH*",
    "SKIP":       "❌ *SKIP*",
}


# =====================================================================
# Public entry points
# =====================================================================

def send_premarket_brief(state_file: str = "output/bridge_state.json",
                         dry_run: bool = False) -> dict:
    """Read bridge_state.json, render brief, send via Telegram (or
    return rendered string only when dry_run=True)."""
    if not os.path.exists(state_file):
        return {
            "sent": False,
            "phase_status": "UNKNOWN",
            "char_count": 0,
            "signals_rendered": 0,
            "skip_reason": f"state file not found: {state_file}",
            "rendered": "",
        }

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "sent": False,
            "phase_status": "UNKNOWN",
            "char_count": 0,
            "signals_rendered": 0,
            "skip_reason": f"state file malformed JSON: {e}",
            "rendered": "",
        }

    phase_status = state.get("phase_status") or "UNKNOWN"

    if phase_status == "ERROR":
        rendered = _render_emergency_brief(state)
    elif phase_status == "SKIPPED":
        rendered = _render_skipped_brief(state)
    else:
        rendered = _render_brief(state)

    signals = state.get("signals") or []
    signals_rendered = len(signals) if phase_status in ("OK", "DEGRADED") else 0

    if dry_run:
        return {
            "sent": False,
            "phase_status": phase_status,
            "char_count": len(rendered),
            "signals_rendered": signals_rendered,
            "skip_reason": None,
            "rendered": rendered,
        }

    sent = send_message(
        rendered,
        reply_markup=_pwa_keyboard(),
    )
    return {
        "sent": bool(sent),
        "phase_status": phase_status,
        "char_count": len(rendered),
        "signals_rendered": signals_rendered,
        "skip_reason": None if sent else "send_message returned False",
        "rendered": rendered,
    }


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bridge_telegram_premarket",
        description=(
            "Render and send the bridge L1 PRE_MARKET Telegram brief"
        ),
    )
    parser.add_argument("--state-file",
                        default="output/bridge_state.json",
                        help="Path to bridge_state.json")
    parser.add_argument("--dry-run", action="store_true",
                        help=("Render and print to stdout but do "
                              "NOT send to Telegram"))

    args = parser.parse_args(argv)

    result = send_premarket_brief(
        state_file=args.state_file,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("=" * 60)
        print("RENDERED MARKDOWN (dry-run, NOT sent):")
        print("=" * 60)
        print(result["rendered"])
        print("=" * 60)

    log = {
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "level":             "INFO" if result["sent"]
                             or args.dry_run else "ERROR",
        "component":         "bridge_telegram_premarket",
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
    if not result["sent"] and result["skip_reason"]:
        return 1
    return 0


# =====================================================================
# Renderers
# =====================================================================

def _render_brief(state: dict) -> str:
    """Full pre-market brief for OK / DEGRADED phase_status."""
    market_date = state.get("market_date", "")
    banner = state.get("banner") or {}
    banner_message = banner.get("message") or ""
    signals = state.get("signals") or []
    contra = state.get("contra") or {}
    alerts = state.get("alerts") or []

    lines = [_render_header(market_date, banner_message)]

    grouped = _group_by_bucket(signals)

    for bucket in _BUCKET_ORDER:
        rows = grouped.get(bucket, [])
        if not rows:
            continue
        lines.append("")
        n = len(rows)
        bucket_header = (
            f"{_BUCKET_HEADERS[bucket]} \\({_esc(str(n))}\\)"
        )
        lines.append(bucket_header)

        if bucket in ("TAKE_FULL", "TAKE_SMALL"):
            for i, sdr in enumerate(rows):
                if i > 0:
                    # Blank line between signals; none before first
                    lines.append("")
                lines.append(_render_signal(sdr))
        elif bucket == "WATCH":
            symbols = [_esc(_clean_symbol(s.get("symbol")))
                       for s in rows]
            lines.append(", ".join(symbols))
        elif bucket == "SKIP":
            lines.append(
                f"{_esc(str(n))} signals skipped — see PWA for details")

    if not signals:
        lines.append("")
        lines.append(_esc("No new signals today"))

    # Footer dividers
    contra_line = _render_contra_footer(contra)
    alert_line = _render_alerts_footer(alerts)
    if contra_line or alert_line:
        lines.append("")
        lines.append("────")
        if contra_line:
            lines.append(contra_line)
        if alert_line:
            lines.append(alert_line)

    return "\n".join(lines)


def _render_header(market_date: str, banner_message: str) -> str:
    return (
        f"🎯 *Pre\\-market — {_esc(market_date)}*\n"
        f"{_esc(banner_message) if banner_message else ''}"
    )


def _render_signal(sdr: dict) -> str:
    """Single signal block — used for TAKE_FULL and TAKE_SMALL."""
    symbol = _clean_symbol(sdr.get("symbol"))
    sig_type = sdr.get("signal_type", "?")
    sector = sdr.get("sector", "?")
    regime = sdr.get("regime", "?")

    display = sdr.get("display") or {}
    score = _extract_score(display, sdr)
    tier_label = _tier_label(sdr)

    trade = sdr.get("trade_plan") or {}
    entry = trade.get("entry")
    stop = trade.get("stop")
    target = trade.get("target")
    rr = trade.get("rr")

    boost = (sdr.get("evidence") or {}).get("boost_match") or {}
    cohort_n = boost.get("n")
    cohort_wr = boost.get("wr")

    gap = sdr.get("gap_caveat") or {}
    gap_applies = bool(gap.get("applies"))
    gap_pct = gap.get("threshold_pct", 2.0)
    gap_price = gap.get("absolute_threshold_price")

    # Line 1: SYMBOL · SIGNAL_TYPE
    line1 = f"{_esc(symbol)} · {_esc(sig_type)}"

    # Line 2: sector · regime · Score N (· Tier X)
    line2_parts = [
        _esc(sector),
        _esc(regime),
        f"Score {_esc(str(score))}",
    ]
    if tier_label:
        line2_parts.append(tier_label)
    line2 = " · ".join(line2_parts)

    # Line 3: Entry: ₹X · Stop: ₹Y · Target: ₹Z
    line3 = (
        f"Entry: {_p_esc(entry)} · "
        f"Stop: {_p_esc(stop)} · "
        f"Target: {_p_esc(target)}"
    )

    # Line 4: R:R 2.10 · 21/21 WR  (or % if n>30)
    line4 = (
        f"R:R {_rr_str(rr)} · {_wr_str(cohort_n, cohort_wr)} WR"
    )

    block = [line1, line2, line3, line4]

    # Line 5 (optional): gap caveat
    if gap_applies and isinstance(gap_price, (int, float)):
        block.append(_render_gap_caveat(gap_pct, gap_price))

    return "\n".join(block)


def _render_contra_footer(contra: dict) -> Optional[str]:
    """One-line contra status. None if nothing tracking."""
    if not isinstance(contra, dict):
        return None
    active = contra.get("active_rules") or []
    pending = contra.get("pending_shadows") or []
    resolved_recent = contra.get("recent_resolutions") or []

    if not active and not pending:
        return None

    parts = []
    for rule in active:
        if not isinstance(rule, dict):
            continue
        kid = rule.get("kill_id")
        if not kid:
            continue
        n_pending_for = sum(
            1 for s in pending
            if isinstance(s, dict)
            and s.get("kill_rule_id") == kid
        )
        n_resolved_for = sum(
            1 for s in resolved_recent
            if isinstance(s, dict)
            and s.get("kill_rule_id") == kid
        )
        seg = (
            f"{_esc(kid)} at {_esc(str(n_resolved_for))}/30"
        )
        if n_pending_for:
            seg += (
                f", {_esc(str(n_pending_for))} pending"
            )
        parts.append(seg)

    if not parts and pending:
        parts.append(
            f"{_esc(str(len(pending)))} pending shadows")

    if not parts:
        return None

    return "📊 Contra: " + "; ".join(parts)


def _render_alerts_footer(alerts: list) -> Optional[str]:
    """One-line alerts summary. None if no critical/warning alerts."""
    if not isinstance(alerts, list) or not alerts:
        return None

    crit = [a for a in alerts
            if isinstance(a, dict)
            and a.get("severity") == "critical"]
    warn = [a for a in alerts
            if isinstance(a, dict)
            and a.get("severity") == "warning"]

    if not (crit or warn):
        return None

    total = len(crit) + len(warn)
    if total == 1:
        only = (crit + warn)[0]
        msg = only.get("message") or "(no message)"
        return f"⚠️ {_esc(msg)}"

    breakdown = []
    if crit:
        breakdown.append(f"{len(crit)} critical")
    if warn:
        breakdown.append(f"{len(warn)} warning")
    return (
        f"⚠️ Alerts: {_esc(str(total))} "
        f"\\({_esc(', '.join(breakdown))}\\) — see PWA"
    )


def _render_emergency_brief(state: dict) -> str:
    """Short brief for phase_status=ERROR."""
    market_date = state.get("market_date", "")
    banner = state.get("banner") or {}
    subtext = banner.get("subtext") or "see GitHub Actions logs"

    retry_text = ("Will retry on next workflow run. "
                  "Check GitHub Actions logs.")
    return (
        f"🎯 *Pre\\-market — {_esc(market_date)}*\n"
        f"❌ *Bridge compose failed*\n"
        f"Reason: {_esc(subtext)}\n"
        f"{_esc(retry_text)}"
    )


def _render_skipped_brief(state: dict) -> str:
    """Short brief for phase_status=SKIPPED (non-trading day)."""
    market_date = state.get("market_date", "")
    banner = state.get("banner") or {}
    subtext = banner.get("subtext") or "non-trading day"

    return (
        f"🎯 *Pre\\-market — {_esc(market_date)}*\n"
        f"🔕 Market closed today \\({_esc(subtext)}\\)\\.\n"
        f"See you next trading day\\."
    )


# =====================================================================
# Helpers
# =====================================================================

def _group_by_bucket(signals: list) -> dict:
    out = {b: [] for b in _BUCKET_ORDER}
    for s in signals:
        if not isinstance(s, dict):
            continue
        b = s.get("bucket")
        if b in out:
            # Sort within bucket by display.card_priority desc
            out[b].append(s)
    for b in out:
        out[b].sort(
            key=lambda s: (
                -((s.get("display") or {}).get("card_priority") or 0)
            )
        )
    return out


def _clean_symbol(symbol) -> str:
    if not isinstance(symbol, str):
        return "?"
    if symbol.endswith(".NS"):
        return symbol[:-3]
    return symbol


def _extract_score(display: dict, sdr: dict):
    """Score for the line 2. Prefer trade_plan.score over display."""
    plan = sdr.get("trade_plan") or {}
    score = plan.get("score")
    if isinstance(score, (int, float)):
        return int(score)
    return "?"


def _tier_label(sdr: dict) -> Optional[str]:
    """Returns 'Tier A' or 'Tier B' if a boost match exists."""
    evidence = sdr.get("evidence") or {}
    boost = evidence.get("boost_match")
    if not isinstance(boost, dict):
        return None
    tier = boost.get("tier")
    if tier in ("A", "B"):
        return f"Tier {_esc(tier)}"
    return None


def _rr_str(rr) -> str:
    if isinstance(rr, (int, float)):
        return _esc(f"{rr:.2f}")
    return "?"


def _wr_str(n, wr) -> str:
    """Raw count if n<=30, percentage if n>30."""
    if not isinstance(n, (int, float)):
        return "?"
    n_int = int(n)
    if n_int == 0 or not isinstance(wr, (int, float)):
        return "?"
    if n_int <= 30:
        wins = round(wr * n_int)
        return _esc(f"{wins}/{n_int}")
    return _esc(f"{int(round(wr * 100))}%")


def _render_gap_caveat(threshold_pct, threshold_price) -> str:
    # :g strips trailing zeros — 2.0 → "2", 2.5 → "2.5"
    pct_str = _esc(f"{threshold_pct:g}%")
    price_str = _p_esc(threshold_price)
    return f"⚠ Gap \\> {pct_str} \\({price_str}\\) reconsider"


# =====================================================================
# Script entry
# =====================================================================

if __name__ == "__main__":
    sys.exit(main())
