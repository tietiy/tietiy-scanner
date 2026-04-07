# scanner/telegram_bot.py
# F9:  exit-tomorrow alerts
# F10: score shown as X.X/10
# F11: total active count line in morning scan
# C1:  fixed field names — entry/stop/target/signal
# C2:  fixed signal type field name
# W1:  EOD pnl_pct None safety (also in main.py)
# ─────────────────────────────────────────────────────

import os
import requests

TELEGRAM_TOKEN   = os.environ.get(
    "TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID", "8493010921")


# ── CORE SEND ─────────────────────────────────────────

def send_message(text: str) -> bool:
    if not TELEGRAM_TOKEN:
        print("[telegram] No TELEGRAM_TOKEN "
              "— skipping")
        return False
    url     = (f"https://api.telegram.org/"
               f"bot{TELEGRAM_TOKEN}/sendMessage")
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(
            url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[telegram] Sent OK "
              f"({r.status_code})")
        return True
    except Exception as e:
        print(f"[telegram] Error: {e}")
        return False


# ── HELPERS ───────────────────────────────────────────

def fmt_score(raw) -> str:
    """F10 — always render score as X.X/10"""
    try:
        s = float(raw)
        if s > 10:
            s = s / 10.0
        return f"{s:.1f}/10"
    except Exception:
        return "—/10"


def fmt_price(val) -> str:
    """Safe price formatter — never crashes on None"""
    try:
        f = float(val)
        if f > 0:
            return f"₹{f:.2f}"
        return "—"
    except Exception:
        return "—"


def fmt_pnl(val) -> str:
    """Safe P&L formatter"""
    try:
        f = float(val)
        return f"{f:+.1f}%"
    except Exception:
        return "—"


def sig_emoji(signal_type: str) -> str:
    t = (signal_type or "").upper()
    if "UP"   in t: return "🔺"
    if "DOWN" in t: return "🔻"
    if "BULL" in t: return "🟢"
    return "📌"


def _resolve_price(sig, *fields):
    """
    Try multiple field names in order.
    Returns float > 0 or 0.0.
    Prevents 0.00 showing in Telegram.
    """
    for field in fields:
        val = sig.get(field)
        if val is not None:
            try:
                f = float(val)
                if f > 0:
                    return f
            except Exception:
                continue
    return 0.0


def _calc_rr(entry, stop, target,
             direction='LONG'):
    """Safe R:R calculation"""
    try:
        risk   = abs(entry - stop)
        reward = abs(target - entry)
        if risk <= 0:
            return 0.0
        return round(reward / risk, 1)
    except Exception:
        return 0.0


# ── MORNING SCAN ──────────────────────────────────────

def send_morning_scan(signals: list,
                      meta: dict):
    """
    Called by main.py after scan.
    F11: first content line = total active count.
    F10: every score shown as X.X/10.
    C1:  correct field names for prices.
    C2:  correct field name for signal type.
    """
    date_str = meta.get(
        "market_date", "today")

    # C2 FIX — meta uses 'regime' not 'nifty_regime'
    regime_label = meta.get("regime", "")

    active_count = len(signals)

    lines = [
        f"🔔 <b>TIE TIY — {date_str}</b>"]

    if regime_label:
        lines.append(
            f"📈 Nifty: <b>{regime_label}</b>")

    # F11 — total active count
    lines.append(
        f"📊 Active signals: "
        f"<b>{active_count}</b>")
    lines.append("")

    if active_count == 0:
        lines.append(
            "No signals today. Market watching.")
        send_message("\n".join(lines))
        return

    for sig in signals[:10]:
        symbol = (sig.get("symbol") or "?") \
                 .replace(".NS", "")
        sector = sig.get("sector", "")

        # C2 FIX — field is 'signal' not
        # 'signal_type'
        stype  = sig.get("signal", "?")
        age    = sig.get("age", 0)
        score  = fmt_score(sig.get("score", 0))
        regime = sig.get("regime", "")
        direction = sig.get("direction", "LONG")

        # C1 FIX — correct field name priority
        # entry: actual_open → scan_price → entry
        # stop:  stop
        # target: target_price
        entry  = _resolve_price(
            sig,
            'actual_open',
            'scan_price',
            'entry',
            'entry_est')
        stop   = _resolve_price(
            sig, 'stop')
        target = _resolve_price(
            sig, 'target_price')

        rr = _calc_rr(
            entry, stop, target, direction)

        bear_flag = " 🔥" \
            if sig.get("bear_bonus") else ""
        sector_tag = \
            f" · {sector}" if sector else ""
        regime_tag = \
            f" · {regime}" if regime else ""

        lines.append(
            f"{sig_emoji(stype)} "
            f"<b>{symbol}</b>"
            f"{sector_tag}"
            f"{regime_tag} | "
            f"Age {age}"
            f"{bear_flag}"
        )
        lines.append(
            f"   {stype} | "
            f"Score: {score} | "
            f"R:R {rr}x"
        )
        lines.append(
            f"   Entry: {fmt_price(entry)}  "
            f"Stop: {fmt_price(stop)}  "
            f"Target: {fmt_price(target)}"
        )
        lines.append("")

    if active_count > 10:
        lines.append(
            f"…and <b>{active_count - 10}"
            f"</b> more on the dashboard.")
        lines.append("")

    lines.append(
        "🔗 tietiy.github.io/tietiy-scanner/")
    send_message("\n".join(lines))


# ── OPEN VALIDATION ───────────────────────────────────

def send_open_validation(confirmed: list,
                          rejected: list):
    lines = [
        "📋 <b>Open Validation — 9:25 AM</b>",
        ""]

    if confirmed:
        lines.append(
            f"✅ Entries confirmed: "
            f"<b>{len(confirmed)}</b>")
        for sig in confirmed:
            symbol     = (
                sig.get("symbol") or "?") \
                .replace(".NS", "")
            open_price = _resolve_price(
                sig,
                'actual_open',
                'open_price',
                'scan_price')
            lines.append(
                f"   • {symbol} @ "
                f"{fmt_price(open_price)}")
        lines.append("")

    if rejected:
        lines.append(
            f"❌ Gap rejections: "
            f"<b>{len(rejected)}</b>")
        for sig in rejected:
            symbol = (
                sig.get("symbol") or "?") \
                .replace(".NS", "")
            reason = sig.get(
                "rejection_reason",
                "gap violation")
            lines.append(
                f"   • {symbol} — {reason}")

    if not confirmed and not rejected:
        lines.append(
            "No signals to validate today.")

    send_message("\n".join(lines))


# ── STOP ALERT ────────────────────────────────────────

def send_stop_alert(signal: dict):
    symbol = (signal.get("symbol") or "?") \
             .replace(".NS", "")

    # C2 FIX — field is 'signal' not 'signal_type'
    stype  = signal.get("signal", "?")
    stop   = _resolve_price(signal, 'stop')
    score  = fmt_score(signal.get("score", 0))
    level  = signal.get("alert_level", "NEAR")

    icon = "🚨" if level == "BREACHED" else "⚠️"

    text = (
        f"{icon} <b>STOP ALERT — {symbol}</b>\n"
        f"Level: {level}\n"
        f"Signal: {stype} | Score: {score}\n"
        f"Stop level: {fmt_price(stop)}\n"
        f"Rule: exit at market if stop "
        f"breached intraday."
    )
    send_message(text)


# ── EXIT TOMORROW ALERT (F9) ──────────────────────────

def send_exit_tomorrow(signals: list):
    """
    F9 — called for any signal on Day 5.
    Rule: exit at open of Day 6 = tomorrow 9:15 AM.
    """
    if not signals:
        return

    lines = [
        "⏰ <b>EXIT TOMORROW — Day 6 Open</b>",
        ""]
    lines.append(
        f"The following <b>{len(signals)}</b> "
        f"signal(s) must be closed at "
        f"<b>9:15 AM open tomorrow</b>. "
        f"No extensions.")
    lines.append("")

    for sig in signals:
        symbol = (sig.get("symbol") or "?") \
                 .replace(".NS", "")

        # C2 FIX — field is 'signal'
        stype  = sig.get("signal", "?")
        score  = fmt_score(
            sig.get("score", 0))
        direction = sig.get(
            "direction", "LONG")

        entry  = _resolve_price(
            sig,
            'actual_open',
            'scan_price',
            'entry',
            'entry_est')
        stop   = _resolve_price(
            sig, 'stop')
        target = _resolve_price(
            sig, 'target_price')
        ltp    = _resolve_price(
            sig, 'ltp') or None

        lines.append(
            f"📌 <b>{symbol}</b> | "
            f"{stype} | Score: {score}")
        lines.append(
            f"   Entry: {fmt_price(entry)}  "
            f"Stop: {fmt_price(stop)}  "
            f"Target: {fmt_price(target)}")

        if ltp:
            try:
                pnl_pct = (
                    (ltp - entry) / entry * 100
                    if entry > 0 else 0)
                if direction == 'SHORT':
                    pnl_pct = -pnl_pct
                at_stop = (
                    ltp <= stop
                    if direction == 'LONG'
                    else ltp >= stop)
                status = (
                    "⚠️ AT/BELOW STOP"
                    if at_stop
                    else fmt_pnl(pnl_pct))
                lines.append(
                    f"   LTP: {fmt_price(ltp)}"
                    f" | {status}")
            except Exception:
                pass

        lines.append("")

    lines.append(
        "Rule: exit at open. "
        "Do not wait. Do not chase close.")
    send_message("\n".join(lines))


# ── EOD SUMMARY ───────────────────────────────────────

def send_eod_summary(outcomes: list,
                     still_open: int):
    """
    Called by main.py run_eod() after evaluation.
    W1 FIX — None safety already handled in main.py
    before this function is called. Additional
    safety here as second layer.
    """
    if not outcomes and still_open == 0:
        return

    lines = ["📉 <b>EOD Update</b>", ""]

    resolved = [
        o for o in outcomes
        if o.get("outcome") and
        o.get("outcome") != "OPEN"
    ]

    if resolved:
        lines.append(
            f"Resolved today: "
            f"<b>{len(resolved)}</b>")
        for o in resolved:
            symbol  = (
                o.get("symbol") or "?") \
                .replace(".NS", "")
            outcome = o.get("outcome", "?")
            pnl     = fmt_pnl(
                o.get("pnl_pct", 0))
            emoji   = (
                "✅"
                if "WIN" in outcome
                or "TARGET" in outcome
                else "❌")
            lines.append(
                f"   {emoji} {symbol} — "
                f"{outcome} ({pnl})")
        lines.append("")

    if still_open:
        lines.append(
            f"Still open: "
            f"<b>{still_open}</b> signal(s)")

    send_message("\n".join(lines))


# ── TEST ──────────────────────────────────────────────

if __name__ == "__main__":
    send_message(
        "✅ <b>TIE TIY</b> — "
        "Telegram connection test OK.")
