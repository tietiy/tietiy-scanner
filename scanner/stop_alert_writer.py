# ── stop_alert_writer.py ─────────────────────────────
# Runs every 30 mins during market hours
# via stop_check.yml
# Fetches current intraday prices for open positions
# Flags positions near or at stop level
# Writes stop_alerts.json to output/
# Page shows pulsing ⚠️ badge on affected cards
#
# Lightweight — only fetches open position stocks
# Not a full universe scan
# ─────────────────────────────────────────────────────

import json
import os
import sys
from datetime import date, datetime

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import get_open_trades

# ── PATHS ─────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_HERE)
_OUTPUT  = os.path.join(_ROOT, 'output')
OUT_FILE = os.path.join(_OUTPUT, 'stop_alerts.json')

# ── THRESHOLDS ────────────────────────────────────────
# NEAR_STOP_PCT: within this % of stop = NEAR alert
# AT_STOP_PCT  : within this % of stop = AT alert
# BREACHED     : price crossed stop level
NEAR_STOP_PCT = 2.0   # within 2% of stop
AT_STOP_PCT   = 0.5   # within 0.5% of stop


# ── HELPERS ───────────────────────────────────────────

def _fetch_current_price(symbol, retries=2):
    """
    Fetch current intraday price using 1d/1m interval.
    Falls back to last close if intraday unavailable.

    Returns (current_price, fetch_time) or (None, None)
    """
    for attempt in range(retries + 1):
        try:
            # Try 1-minute data first for live price
            df = yf.download(
                symbol,
                period='1d',
                interval='1m',
                progress=False,
                auto_adjust=False,
            )

            if df is not None and not df.empty:
                if isinstance(
                        df.columns, pd.MultiIndex):
                    df.columns = [
                        c[0] for c in df.columns]

                last_row   = df.iloc[-1]
                price      = float(last_row['Close'])
                fetch_time = datetime.utcnow().strftime(
                    '%H:%M IST')
                return price, fetch_time

            # Fallback to daily
            df = yf.download(
                symbol,
                period='5d',
                interval='1d',
                progress=False,
                auto_adjust=False,
            )

            if df is not None and not df.empty:
                if isinstance(
                        df.columns, pd.MultiIndex):
                    df.columns = [
                        c[0] for c in df.columns]
                price      = float(
                    df.iloc[-1]['Close'])
                fetch_time = datetime.utcnow().strftime(
                    '%H:%M IST')
                return price, fetch_time

        except Exception as e:
            print(f"[stop_alert] Fetch attempt "
                  f"{attempt+1} failed {symbol}: {e}")

    return None, None


def _assess_alert_level(trade, current_price):
    """
    Assess how close current price is to stop.

    For LONG:
        Price falling toward stop
        Breached = price <= stop
        AT      = price within AT_STOP_PCT of stop
        NEAR    = price within NEAR_STOP_PCT of stop

    For SHORT:
        Price rising toward stop
        Breached = price >= stop
        AT      = price within AT_STOP_PCT of stop
        NEAR    = price within NEAR_STOP_PCT of stop

    Returns:
        alert_level  : 'BREACHED'/'AT'/'NEAR'/'SAFE'
        pct_from_stop: float — % distance from stop
        pnl_pct      : float — current unrealized P&L
        pnl_r        : float — P&L in R multiples
        note         : str
    """
    try:
        stop      = float(trade.get('stop', 0) or 0)
        entry     = float(
            trade.get('entry', 0)
            or trade.get('scan_price', 0) or 0)
        direction = trade.get('direction', 'LONG')

        if stop <= 0 or entry <= 0:
            return ('UNKNOWN', None, None, None,
                    'Missing stop or entry')

        # Risk per share
        if direction == 'LONG':
            risk = entry - stop
        else:
            risk = stop - entry

        if risk <= 0:
            return ('UNKNOWN', None, None, None,
                    'Invalid risk calculation')

        # Distance from stop as %
        pct_from_stop = round(
            abs(current_price - stop) /
            stop * 100, 2)

        # P&L
        if direction == 'LONG':
            pnl_pct = round(
                (current_price - entry) /
                entry * 100, 2)
            pnl_r   = round(
                (current_price - entry) / risk, 2)
        else:
            pnl_pct = round(
                (entry - current_price) /
                entry * 100, 2)
            pnl_r   = round(
                (entry - current_price) / risk, 2)

        # Alert level assessment
        if direction == 'LONG':
            if current_price <= stop:
                return ('BREACHED',
                        pct_from_stop,
                        pnl_pct, pnl_r,
                        f"⚠️ STOP BREACHED — "
                        f"Price ₹{current_price:.2f} "
                        f"below stop ₹{stop:.2f} — "
                        f"Exit immediately")

            diff_pct = (
                (current_price - stop) /
                stop * 100)

            if diff_pct <= AT_STOP_PCT:
                return ('AT',
                        pct_from_stop,
                        pnl_pct, pnl_r,
                        f"🔴 AT STOP — "
                        f"Price ₹{current_price:.2f} "
                        f"within 0.5% of stop "
                        f"₹{stop:.2f}")

            if diff_pct <= NEAR_STOP_PCT:
                return ('NEAR',
                        pct_from_stop,
                        pnl_pct, pnl_r,
                        f"🟡 NEAR STOP — "
                        f"Price ₹{current_price:.2f} "
                        f"within 2% of stop "
                        f"₹{stop:.2f}")

        elif direction == 'SHORT':
            if current_price >= stop:
                return ('BREACHED',
                        pct_from_stop,
                        pnl_pct, pnl_r,
                        f"⚠️ STOP BREACHED — "
                        f"Price ₹{current_price:.2f} "
                        f"above stop ₹{stop:.2f} — "
                        f"Exit immediately")

            diff_pct = (
                (stop - current_price) /
                stop * 100)

            if diff_pct <= AT_STOP_PCT:
                return ('AT',
                        pct_from_stop,
                        pnl_pct, pnl_r,
                        f"🔴 AT STOP — "
                        f"Price ₹{current_price:.2f} "
                        f"within 0.5% of stop "
                        f"₹{stop:.2f}")

            if diff_pct <= NEAR_STOP_PCT:
                return ('NEAR',
                        pct_from_stop,
                        pnl_pct, pnl_r,
                        f"🟡 NEAR STOP — "
                        f"Price ₹{current_price:.2f} "
                        f"within 2% of stop "
                        f"₹{stop:.2f}")

        # Safe
        return ('SAFE',
                pct_from_stop,
                pnl_pct, pnl_r,
                f"✅ Safe | "
                f"₹{current_price:.2f} | "
                f"{pnl_r:+.2f}R")

    except Exception as e:
        print(f"[stop_alert] Assess error: {e}")
        return ('UNKNOWN', None, None, None,
                'Assessment error')


# ── MAIN FUNCTION ─────────────────────────────────────

def run_stop_check():
    """
    Main entry point. Called by stop_check.yml.

    Workflow:
    1. Load all open positions from signal_history.json
    2. Fetch current intraday price for each
    3. Assess distance from stop
    4. Categorise: BREACHED / AT / NEAR / SAFE
    5. Write stop_alerts.json
    """

    os.makedirs(_OUTPUT, exist_ok=True)

    today      = date.today().isoformat()
    check_time = datetime.utcnow().strftime('%H:%M IST')

    print(f"[stop_alert] Starting stop check "
          f"at {check_time}")

    # Load open positions
    open_trades = get_open_trades()

    if not open_trades:
        print("[stop_alert] No open positions")
        _write_empty(today, check_time)
        return

    print(f"[stop_alert] Checking "
          f"{len(open_trades)} open positions")

    alerts        = []
    fetch_failed  = []
    breached_count = 0
    at_count       = 0
    near_count     = 0
    safe_count     = 0

    for trade in open_trades:
        symbol    = trade.get('symbol', '')
        signal    = trade.get('signal', '')
        direction = trade.get('direction', 'LONG')
        entry     = trade.get('entry', None)
        stop      = trade.get('stop', None)
        sig_date  = trade.get('date', today)

        if not symbol:
            continue

        # Fetch current price
        current_price, fetch_time = \
            _fetch_current_price(symbol)

        if current_price is None:
            print(f"[stop_alert] "
                  f"Fetch failed: {symbol}")
            fetch_failed.append(symbol)
            alerts.append({
                'symbol':        symbol,
                'signal':        signal,
                'signal_date':   sig_date,
                'direction':     direction,
                'entry':         entry,
                'stop':          stop,
                'current_price': None,
                'alert_level':   'UNKNOWN',
                'pct_from_stop': None,
                'pnl_pct':       None,
                'pnl_r':         None,
                'note':          'Price fetch failed',
                'check_time':    check_time,
            })
            continue

        # Assess alert level
        (alert_level,
         pct_from_stop,
         pnl_pct,
         pnl_r,
         note) = _assess_alert_level(
            trade, current_price)

        # Count by level
        if alert_level == 'BREACHED':
            breached_count += 1
        elif alert_level == 'AT':
            at_count += 1
        elif alert_level == 'NEAR':
            near_count += 1
        elif alert_level == 'SAFE':
            safe_count += 1

        # Only include non-safe in alerts list
        # Safe positions included for full picture
        alerts.append({
            'symbol':        symbol,
            'signal':        signal,
            'signal_date':   sig_date,
            'direction':     direction,
            'entry':         entry,
            'stop':          stop,
            'current_price': round(current_price, 2),
            'alert_level':   alert_level,
            'pct_from_stop': pct_from_stop,
            'pnl_pct':       pnl_pct,
            'pnl_r':         pnl_r,
            'note':          note,
            'check_time':    fetch_time or check_time,
        })

        print(f"[stop_alert] {symbol} | "
              f"₹{current_price:.2f} | "
              f"{alert_level} | "
              f"Stop: ₹{stop}")

    # Separate active alerts from safe
    active_alerts = [
        a for a in alerts
        if a['alert_level'] in
        ('BREACHED', 'AT', 'NEAR')
    ]

    # Write stop_alerts.json
    output = {
        'date':           today,
        'check_time':     check_time,
        'open_positions': len(open_trades),
        'breached_count': breached_count,
        'at_count':       at_count,
        'near_count':     near_count,
        'safe_count':     safe_count,
        'fetch_failed':   fetch_failed,
        'has_alerts':     len(active_alerts) > 0,
        'alerts':         alerts,
    }

    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"[stop_alert] Done → "
          f"BREACHED:{breached_count} "
          f"AT:{at_count} "
          f"NEAR:{near_count} "
          f"SAFE:{safe_count} "
          f"FAILED:{len(fetch_failed)}")


def _write_empty(today, check_time):
    """
    Write empty stop_alerts.json
    when no open positions.
    """
    output = {
        'date':           today,
        'check_time':     check_time,
        'open_positions': 0,
        'breached_count': 0,
        'at_count':       0,
        'near_count':     0,
        'safe_count':     0,
        'fetch_failed':   [],
        'has_alerts':     False,
        'alerts':         [],
    }
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print("[stop_alert] Empty stop_alerts.json written")


# ── ENTRY POINT ───────────────────────────────────────
if __name__ == '__main__':
    run_stop_check()
