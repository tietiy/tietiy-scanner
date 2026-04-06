# scanner/telegram_bot.py
# F9: exit-tomorrow alerts
# F10: score shown as X.X/10
# F11: total active count line in morning scan

import os
import json
import requests
from pathlib import Path

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8493010921")


# ─── CORE SEND ────────────────────────────────────────────────────────────────

def send_message(text: str) -> bool:
    if not TELEGRAM_TOKEN:
        print("[telegram] No TELEGRAM_TOKEN — skipping")
        return False
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[telegram] Sent OK ({r.status_code})")
        return True
    except Exception as e:
        print(f"[telegram] Error: {e}")
        return False


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def fmt_score(raw) -> str:
    """F10 — always render score as X.X/10"""
    try:
        s = float(raw)
        if s > 10:          # stored as 0–100
            s = s / 10.0
        return f"{s:.1f}/10"
    except Exception:
        return "—/10"


def sig_emoji(signal_type: str) -> str:
    t = (signal_type or "").upper()
    if "UP"   in t: return "🔺"
    if "DOWN" in t: return "🔻"
    if "BULL" in t: return "🟢"
    return "📌"


# ─── MORNING SCAN ─────────────────────────────────────────────────────────────

def send_morning_scan(signals: list, meta: dict):
    """
    Called by main.py after scan.
    F11: first content line is total active signal count.
    F10: every score shown as X.X/10.
    """
    date_str     = meta.get("market_date", "today")
    regime_label = meta.get("nifty_regime", "")
    active_count = len(signals)                          # F11

    lines = [f"🔔 <b>TIE TIY — {date_str}</b>"]

    if regime_label:
        lines.append(f"📈 Nifty regime: <b>{regime_label}</b>")

    # F11 — total active count always on its own line
    lines.append(f"📊 Active signals: <b>{active_count}</b>")
    lines.append("")

    if active_count == 0:
        lines.append("No signals today. Market watching.")
        send_message("\n".join(lines))
        return

    for sig in signals[:10]:                             # cap display at 10
        symbol  = sig.get("symbol",      "?")
        stype   = sig.get("signal_type", "?")
        age     = sig.get("age",          0)
        entry   = sig.get("entry_price",  0)
        stop    = sig.get("stop_price",   0)
        target  = sig.get("target_price", 0)
        score   = fmt_score(sig.get("score", 0))        # F10
        sector  = sig.get("sector", "")

        rr = 0.0
        if entry and stop and target and (entry - stop) != 0:
            rr = abs(target - entry) / abs(entry - stop)

        sector_tag = f" · {sector}" if sector else ""
        lines.append(
            f"{sig_emoji(stype)} <b>{symbol}</b>{sector_tag} | Age {age}"
        )
        lines.append(
            f"   {stype} | Score: {score} | R:R {rr:.1f}"
        )
        lines.append(
            f"   Entry: {entry:.2f}  Stop: {stop:.2f}  Target: {target:.2f}"
        )
        lines.append("")

    if active_count > 10:
        lines.append(f"…and <b>{active_count - 10}</b> more on the dashboard.")
        lines.append("")

    lines.append("🔗 tietiy.github.io/tietiy-scanner/")
    send_message("\n".join(lines))


# ─── OPEN VALIDATION (9:25 AM) ────────────────────────────────────────────────

def send_open_validation(confirmed: list, rejected: list):
    lines = ["📋 <b>Open Validation — 9:25 AM</b>", ""]

    if confirmed:
        lines.append(f"✅ Entries confirmed: <b>{len(confirmed)}</b>")
        for sig in confirmed:
            symbol     = sig.get("symbol", "?")
            open_price = sig.get("open_price", 0)
            lines.append(f"   • {symbol} @ {open_price:.2f}")
        lines.append("")

    if rejected:
        lines.append(f"❌ Gap rejections: <b>{len(rejected)}</b>")
        for sig in rejected:
            symbol = sig.get("symbol", "?")
            reason = sig.get("rejection_reason", "gap violation")
            lines.append(f"   • {symbol} — {reason}")

    if not confirmed and not rejected:
        lines.append("No signals to validate today.")

    send_message("\n".join(lines))


# ─── STOP ALERT ───────────────────────────────────────────────────────────────

def send_stop_alert(signal: dict):
    symbol = signal.get("symbol", "?")
    stype  = signal.get("signal_type", "?")
    stop   = signal.get("stop_price",  0)
    score  = fmt_score(signal.get("score", 0))          # F10

    text = (
        f"🛑 <b>STOP HIT — {symbol}</b>\n"
        f"Signal: {stype} | Score: {score}\n"
        f"Stop level: {stop:.2f}\n"
        f"Rule: exit at market if not already stopped intraday."
    )
    send_message(text)


# ─── EXIT TOMORROW ALERT (F9) ─────────────────────────────────────────────────

def send_exit_tomorrow(signals: list):
    """
    F9 — called by eod_prices_writer.py for any signal on day 5.
    Rule: exit at open of day 6 = tomorrow 9:15 AM. No exceptions.
    """
    if not signals:
        return

    lines = ["⏰ <b>EXIT TOMORROW — Day 6 Open</b>", ""]
    lines.append(
        f"The following {len(signals)} signal(s) must be closed at "
        f"<b>9:15 AM open tomorrow</b>. No extensions."
    )
    lines.append("")

    for sig in signals:
        symbol  = sig.get("symbol",       "?")
        stype   = sig.get("signal_type",  "?")
        entry   = sig.get("entry_price",   0)
        stop    = sig.get("stop_price",    0)
        target  = sig.get("target_price",  0)
        score   = fmt_score(sig.get("score", 0))        # F10
        ltp     = sig.get("ltp",          None)

        lines.append(f"📌 <b>{symbol}</b> | {stype} | Score: {score}")
        lines.append(f"   Entry: {entry:.2f}  Stop: {stop:.2f}  Target: {target:.2f}")

        if ltp:
            pnl_pct = ((ltp - entry) / entry) * 100 if entry else 0
            at_stop = ltp <= stop
            status  = "⚠️ BELOW STOP" if at_stop else f"P&L: {pnl_pct:+.1f}%"
            lines.append(f"   LTP: {ltp:.2f} | {status}")

        lines.append("")

    lines.append("Rule: exit at open. Do not wait. Do not chase close.")
    send_message("\n".join(lines))


# ─── EOD SUMMARY ──────────────────────────────────────────────────────────────

def send_eod_summary(outcomes: list, still_open: int):
    """Called by eod_prices_writer.py after outcome evaluation."""
    if not outcomes and still_open == 0:
        return

    lines = ["📉 <b>EOD Update</b>", ""]

    resolved = [o for o in outcomes if o.get("outcome")]
    if resolved:
        lines.append(f"Resolved today: <b>{len(resolved)}</b>")
        for o in resolved:
            symbol  = o.get("symbol", "?")
            outcome = o.get("outcome", "?")
            pnl     = o.get("pnl_pct", 0)
            emoji   = "✅" if "WIN" in outcome or "TARGET" in outcome else "❌"
            lines.append(f"   {emoji} {symbol} — {outcome} ({pnl:+.1f}%)")
        lines.append("")

    if still_open:
        lines.append(f"Still open: <b>{still_open}</b> signal(s)")

    send_message("\n".join(lines))


# ─── TEST ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    send_message("✅ <b>TIE TIY</b> — Telegram connection test OK.")
