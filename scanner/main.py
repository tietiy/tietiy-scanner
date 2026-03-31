# ── main.py ──────────────────────────────────────────
# Orchestrator only — calls everything in correct order
# Does not contain detection, scoring, or rendering logic
#
# ── CALL ORDER — DO NOT CHANGE ───────────────────────
# MORNING SCAN:
#  1.  check trading day
#  2.  get_nifty_info()
#  3.  get_sector_momentum()
#  4.  load_universe()
#  5.  fetch_data() per stock — auto_adjust=False
#  6.  detect_signals() — scanner_core
#  7.  detect_second_attempt() — scanner_core
#  8.  enrich_signal() + scorer filter — scorer
#  9.  filter_signals() — mini_scanner
#  10. write_scan_log() — today only
#  11. write_mini_log() — mini_scanner
#  12. write_rejected_log() — mini_scanner
#  13. append_history() — journal, dedup first
#  14. archive_old_records() — journal
#  15. write_meta() — meta_writer, MUST be last
#  16. build_html() — html_builder, shell only
#  17. send_notifications() — push_sender
#
# STOP CHECK:
#  1. check trading day
#  2. run_stop_check() — stop_alert_writer
#
# EOD:
#  1. check trading day
#  2. run_eod_update() — eod_prices_writer
# ─────────────────────────────────────────────────────

import sys
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir  = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

import yfinance as yf
import pandas as pd
from datetime import date, datetime

# ── CONFIG ────────────────────────────────────────────
from config import (
    DATA_DIR, OUTPUT_DIR
)

# ── SCANNER VERSION ───────────────────────────────────
# Increment when detection or scoring logic changes
# v2.0 = first fully dynamic build
# v2.x = scoring changes
# v3.x = detection changes
SCANNER_VERSION = 'v2.0'
APP_VERSION     = '2.0'

# ── NEVER TOUCHED IMPORTS ─────────────────────────────
from calendar_utils import (
    is_trading_day, get_market_status,
    next_trading_day, days_until_exit
)
from universe import (
    load_universe, get_sector_map, get_grade_map
)
from scorer import enrich_signal
from telegram_bot import (
    send_morning_alert, send_eod_summary,
    send_stop_alert, send_holiday_notice
)

# ── NEW MODULE IMPORTS ────────────────────────────────
from scanner_core import (
    prepare, detect_signals, detect_second_attempt,
    has_recent_corporate_action
)
from journal import (
    log_signal, log_rejected,
    get_open_trades, get_recent_closed,
    get_system_health, get_summary,
    archive_old_records, load_history,
    get_history_count
)
from mini_scanner import (
    filter_signals as mini_filter,
    write_mini_log, write_rejected_log
)
from meta_writer import write_meta, write_holidays
from html_builder import build_html
from push_sender import (
    send_notifications, check_dependencies
)
from eod_prices_writer import run_eod_update
from stop_alert_writer  import run_stop_check

# ── CONSTANTS ─────────────────────────────────────────
NIFTY_SYMBOL   = "^NSEI"
SECTOR_INDICES = {
    "Bank":    "^NSEBANK",
    "IT":      "^CNXIT",
    "Pharma":  "^CNXPHARMA",
    "Auto":    "^CNXAUTO",
    "Metal":   "^CNXMETAL",
    "Energy":  "^CNXENERGY",
    "FMCG":    "^CNXFMCG",
    "Infra":   "^CNXINFRA",
}


# ── MARKET DATA ───────────────────────────────────────

def get_nifty_info():
    """
    Fetch Nifty regime, price, change.
    Returns safe defaults on failure.
    """
    try:
        df = yf.download(
            NIFTY_SYMBOL, period='3mo',
            progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        closes     = df['Close']
        ema50      = closes.ewm(span=50).mean()
        slope      = ema50.diff(10) / ema50.shift(10)
        above      = closes > ema50
        last_slope = float(slope.iloc[-1])
        last_above = bool(above.iloc[-1])

        if last_slope > 0.005 and last_above:
            regime = 'Bull'
        elif last_slope < -0.005 and not last_above:
            regime = 'Bear'
        else:
            regime = 'Choppy'

        ret20 = float(
            (closes.iloc[-1] / closes.iloc[-20] - 1)
            * 100)
        regime_score = (
             2 if ret20 >  5 else
             1 if ret20 >  2 else
            -1 if ret20 < -2 else 0)

        return {
            'regime':        regime,
            'regime_score':  regime_score,
            'nifty_close':   round(float(closes.iloc[-1]), 2),
            'nifty_price':   round(float(closes.iloc[-1]), 2),
            'nifty_change':  round(ret20, 2),
            'ret20':         round(ret20, 2),
            'today':         date.today().strftime(
                                 '%d %b %Y'),
            'sector_leaders': []
        }
    except Exception as e:
        print(f"[main] Nifty info error: {e}")
        return {
            'regime':        'Choppy',
            'regime_score':  0,
            'nifty_close':   0,
            'nifty_price':   0,
            'nifty_change':  0,
            'ret20':         0,
            'today':         date.today().strftime(
                                 '%d %b %Y'),
            'sector_leaders': []
        }


def get_sector_momentum():
    """
    Fetch 1-month momentum for each sector index.
    Returns Neutral on failure for any sector.
    """
    momentum = {}
    for sector, sym in SECTOR_INDICES.items():
        try:
            df = yf.download(
                sym, period='1mo',
                progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            closes = df['Close']
            ret    = float(
                (closes.iloc[-1] / closes.iloc[0] - 1)
                * 100)
            momentum[sector] = (
                'Leading' if ret >  2 else
                'Lagging' if ret < -2 else
                'Neutral')
        except Exception:
            momentum[sector] = 'Neutral'
    return momentum


def get_sector_leaders(momentum):
    sorted_s = sorted(
        momentum.items(),
        key=lambda x: (
            0 if x[1] == 'Leading' else
            1 if x[1] == 'Neutral' else 2))
    return [s[0] for s in sorted_s[:3]]


# ── SCAN LOG ──────────────────────────────────────────

def write_scan_log(signals, rejected, scan_date,
                   regime):
    """
    Writes scan_log.json — today's signals only.
    Overwrites every scan.
    Contains full signal detail for frontend.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_path = os.path.join(OUTPUT_DIR, 'scan_log.json')

    # Build full signal records for frontend
    def _fmt(s):
        return {
            # Identity
            'symbol':          s.get('symbol', ''),
            'sector':          s.get('sector', ''),
            'grade':           s.get('grade', 'C'),
            'signal':          s.get('signal', ''),
            'direction':       s.get('direction', ''),
            'age':             s.get('age', 0),
            'score':           s.get('score', 0),

            # Price
            'entry_est':       round(float(
                                   s.get('entry_est')
                                   or 0), 2),
            'stop':            round(float(
                                   s.get('stop')
                                   or 0), 2),
            'atr':             round(float(
                                   s.get('atr')
                                   or 0), 2),
            'pivot_price':     round(float(
                                   s.get('pivot_price')
                                   or 0), 2),
            'pivot_date':      s.get('pivot_date', ''),

            # Context
            'regime':          s.get('regime', ''),
            'regime_score':    s.get('regime_score', 0),
            'vol_q':           s.get('vol_q', ''),
            'vol_confirm':     s.get('vol_confirm',
                                     False),
            'rs_q':            s.get('rs_q', ''),
            'sec_mom':         s.get('sec_mom', ''),
            'bear_bonus':      s.get('bear_bonus',
                                     False),

            # Second attempt
            'attempt_number':  s.get('attempt_number',
                                     1),
            'parent_signal':   s.get('parent_signal',
                                     None),
            'parent_date':     s.get('parent_date',
                                     None),

            # Scan metadata
            'scan_time':       datetime.utcnow().strftime(
                                   '%H:%M IST'),
            'date':            scan_date,
            'scanner_version': SCANNER_VERSION,
        }

    data = {
        'date':     scan_date,
        'regime':   regime,
        'count':    len(signals),
        'signals':  [_fmt(s) for s in signals],
        'rejected': [_fmt(s) for s in rejected],
    }

    with open(log_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"[main] scan_log.json written → "
          f"{len(signals)} signals, "
          f"{len(rejected)} rejected")


# ── MORNING SCAN ──────────────────────────────────────

def run_morning_scan():
    """
    Full morning scan — runs at 8:45 AM IST.
    Follows exact call order documented at top of file.
    """

    # ── STEP 1: Trading day check ─────────────────
    status = get_market_status()
    if not status['is_trading']:
        print(f"[main] Not a trading day: "
              f"{status['reason']}")

        # Still write meta and HTML on holidays
        # Page shows "Market closed today" banner
        market_info = get_nifty_info()
        write_holidays(OUTPUT_DIR)
        write_meta(
            output_dir      = OUTPUT_DIR,
            market_date     = date.today().isoformat(),
            regime          = market_info['regime'],
            universe_size   = 0,
            signals_found   = 0,
            is_trading_day  = False,
            scanner_version = SCANNER_VERSION,
            app_version     = APP_VERSION,
            history_record_count = get_history_count(),
        )
        build_html()
        try:
            send_holiday_notice(status['reason'])
        except Exception:
            pass
        return

    print("[main] Trading day confirmed — "
          "starting morning scan")

    # ── STEP 2: Nifty info ────────────────────────
    print("[main] Fetching market data...")
    market_info = get_nifty_info()
    regime      = market_info['regime']
    reg_score   = market_info['regime_score']
    print(f"[main] Regime: {regime} "
          f"Score: {reg_score}")

    # ── STEP 3: Sector momentum ───────────────────
    sector_momentum = get_sector_momentum()
    market_info['sector_leaders'] = \
        get_sector_leaders(sector_momentum)

    # ── STEP 4: Load universe ─────────────────────
    universe    = load_universe()
    sector_map  = get_sector_map()
    grade_map   = get_grade_map()
    print(f"[main] Universe: {len(universe)} stocks")

    # ── Fetch Nifty close series for RS calc ──────
    try:
        nifty_df = yf.download(
            NIFTY_SYMBOL, period='3mo',
            progress=False, auto_adjust=True)
        if isinstance(nifty_df.columns,
                      pd.MultiIndex):
            nifty_df.columns = [
                c[0] for c in nifty_df.columns]
        nifty_close = nifty_df['Close']
    except Exception:
        nifty_close = None

    # ── Load history for second attempt detection ─
    history_signals = load_history()

    # ── Tracking lists for meta.json ─────────────
    fetch_failed         = []
    insufficient_data    = []
    corporate_action_skip = []

    # ── STEP 5+6+7: Scan each stock ───────────────
    all_raw_signals = []
    print(f"[main] Scanning {len(universe)} stocks...")

    for sym in universe:
        try:
            # Corporate action check
            if has_recent_corporate_action(sym):
                print(f"[main] CA skip: {sym}")
                corporate_action_skip.append(sym)
                continue

            # Fetch data — auto_adjust=False
            # prepare() now returns (df, reason)
            df, skip_reason = prepare(sym, period='1y')

            if df is None:
                if skip_reason == 'insufficient_bars':
                    insufficient_data.append(sym)
                else:
                    fetch_failed.append(sym)
                continue

            sector = sector_map.get(sym, 'Other')
            grade  = grade_map.get(sym, 'C')

            # ── STEP 6: detect_signals ────────────
            sigs = detect_signals(
                df, sym, sector,
                regime, reg_score,
                sector_momentum,
                nifty_close
            )

            # ── STEP 7: detect_second_attempt ─────
            sa_sigs = detect_second_attempt(
                df, sym, sector,
                regime, reg_score,
                sector_momentum,
                history_signals,
                nifty_close
            )

            # Combine first + second attempt signals
            combined = sigs + sa_sigs

            # Enrich with grade + scanner version
            for sig in combined:
                sig['grade']          = grade
                sig['scanner_version'] = SCANNER_VERSION
                sig = enrich_signal(sig, grade)
                all_raw_signals.append(sig)

        except Exception as e:
            print(f"[main] Scan error {sym}: {e}")
            fetch_failed.append(sym)
            continue

    print(f"[main] Raw signals: "
          f"{len(all_raw_signals)}")

    # ── STEP 8: Mini scanner filter ───────────────
    # Shadow mode — everything passes for now
    # Rejection reasons logged for future analysis
    mini_signals, alpha_signals, rejection_log = \
        mini_filter(all_raw_signals)

    print(f"[main] Mini: {len(mini_signals)} | "
          f"Alpha: {len(alpha_signals)} | "
          f"Shadow hits: {len(rejection_log)}")

    # ── STEP 9: Write scan_log.json ───────────────
    # Rejected = alpha signals not in mini
    # In shadow mode these are same — keep for future
    mini_ids  = {id(s) for s in mini_signals}
    rejected  = [s for s in alpha_signals
                 if id(s) not in mini_ids]

    scan_date = date.today().isoformat()
    write_scan_log(
        mini_signals, rejected,
        scan_date, regime)

    # ── STEP 10: Write mini_log.json ─────────────
    write_mini_log(mini_signals)

    # ── STEP 11: Write rejected_log.json ─────────
    write_rejected_log(rejection_log)

    # ── STEP 12: Append to signal_history.json ───
    logged_count = 0
    for sig in mini_signals:
        try:
            log_signal(sig, layer='MINI')
            logged_count += 1
        except Exception as e:
            print(f"[main] Log error "
                  f"{sig.get('symbol','')}: {e}")

    # Log shadow rejections for stats analysis
    for rej in rejection_log:
        if rej.get('shadow_only', False):
            try:
                # Find original signal dict
                orig = next(
                    (s for s in all_raw_signals
                     if s.get('symbol') ==
                     rej.get('symbol')), None)
                if orig:
                    log_rejected(
                        orig,
                        rej.get('rejection_reason',
                                'unknown'),
                        rej.get('rejection_filter',
                                'unknown'),
                        rej.get('threshold', None)
                    )
            except Exception:
                pass

    print(f"[main] Logged {logged_count} signals "
          f"to history")

    # ── STEP 13: Archive old records ─────────────
    try:
        archive_old_records()
    except Exception as e:
        print(f"[main] Archive error: {e}")

    # ── STEP 14: Write nse_holidays.json ─────────
    try:
        write_holidays(OUTPUT_DIR)
    except Exception as e:
        print(f"[main] Holidays write error: {e}")

    # ── STEP 15: Write meta.json — MUST BE LAST ──
    try:
        write_meta(
            output_dir           = OUTPUT_DIR,
            market_date          = scan_date,
            regime               = regime,
            universe_size        = len(universe),
            signals_found        = len(mini_signals),
            is_trading_day       = True,
            scanner_version      = SCANNER_VERSION,
            app_version          = APP_VERSION,
            fetch_failed         = fetch_failed,
            insufficient_data    = insufficient_data,
            corporate_action_skip = corporate_action_skip,
            history_record_count = get_history_count(),
        )
    except Exception as e:
        print(f"[main] Meta write error: {e}")

    # ── STEP 16: Build HTML shell ─────────────────
    try:
        build_html()
    except Exception as e:
        print(f"[main] HTML build error: {e}")

    # ── STEP 17: Send push notifications ──────────
    try:
        if check_dependencies():
            send_notifications(
                signals       = mini_signals,
                regime        = regime,
                universe_size = len(universe),
            )
    except Exception as e:
        print(f"[main] Push error: {e}")

    # ── Telegram (existing — unchanged) ───────────
    try:
        summary        = get_summary()
        health_s, hw   = get_system_health()
        system_health  = {
            'health':    health_s,
            'health_wr': hw,
        }
        send_morning_alert(
            mini_signals, market_info,
            [], get_open_trades(), system_health
        )
    except Exception as e:
        print(f"[main] Telegram error: {e}")

    print(f"[main] Morning scan complete — "
          f"{len(mini_signals)} signals | "
          f"Regime: {regime} | "
          f"Failed: {len(fetch_failed)} | "
          f"CA skip: {len(corporate_action_skip)}")


# ── STOP CHECK ────────────────────────────────────────

def run_morning_stop_check():
    """
    Intraday stop check — runs every 30 mins.
    Delegates entirely to stop_alert_writer.py.
    """
    status = get_market_status()
    if not status['is_trading']:
        return

    print(f"[main] Stop check — "
          f"{datetime.now().strftime('%H:%M')}")
    try:
        run_stop_check()
    except Exception as e:
        print(f"[main] Stop check error: {e}")


# ── EOD UPDATE ────────────────────────────────────────

def run_eod():
    """
    EOD update — runs at 3:35 PM IST.
    Delegates entirely to eod_prices_writer.py.
    """
    status = get_market_status()
    if not status['is_trading']:
        return

    print("[main] EOD update starting...")
    try:
        run_eod_update()
    except Exception as e:
        print(f"[main] EOD error: {e}")

    # Telegram EOD summary (existing — unchanged)
    try:
        market_info  = get_nifty_info()
        open_trades  = get_open_trades()
        health_s, hw = get_system_health()
        send_eod_summary(
            open_trades, [], market_info)
    except Exception as e:
        print(f"[main] Telegram EOD error: {e}")

    print("[main] EOD complete.")


# ── ENTRY POINT ───────────────────────────────────────

if __name__ == '__main__':
    mode = (sys.argv[1]
            if len(sys.argv) > 1
            else 'morning')

    if mode == 'morning':
        run_morning_scan()
    elif mode == 'stops':
        run_morning_stop_check()
    elif mode == 'eod':
        run_eod()
    else:
        print(f"[main] Unknown mode: {mode}")
        print("Usage: python main.py "
              "[morning|stops|eod]")
