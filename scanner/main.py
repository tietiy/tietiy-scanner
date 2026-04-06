# ── main.py ──────────────────────────────────────────
# Orchestrator only — calls everything in correct order
# Does not contain detection, scoring, or rendering logic
#
# ── CALL ORDER — DO NOT CHANGE ───────────────────────
# MORNING SCAN:
#  1.  check trading day
#  2.  write_ban_list() — ban_fetcher
#  3.  get_nifty_info()
#  4.  get_sector_momentum()
#  5.  load_universe()
#  6.  fetch_data() per stock — auto_adjust=False
#  7.  detect_signals() — scanner_core
#  8.  detect_second_attempt() — scanner_core
#  9.  enrich_signal() + scorer filter — scorer
#  10. filter_duplicate_pending() — NEW
#  11. filter_signals() — mini_scanner
#  12. write_scan_log() — today only
#  13. write_mini_log() — mini_scanner
#  14. write_rejected_log() — mini_scanner
#  15. append_history() — journal, dedup first
#  16. archive_old_records() — journal
#  17. write_meta() — meta_writer, MUST be last
#  18. build_html() — html_builder, shell only
#  19. send_notifications() — push_sender
#
# STOP CHECK:
#  1. check trading day
#  2. run_stop_check() — stop_alert_writer
#
# EOD:
#  1. check trading day
#  2. run_outcome_evaluation() — outcome_evaluator
#  3. run_eod_update() — eod_prices_writer
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
SCANNER_VERSION = 'v2.0'
APP_VERSION     = '2.0'

# ── IMPORTS ───────────────────────────────────────────
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
from meta_writer   import write_meta, write_holidays
from html_builder  import build_html
from push_sender   import (
    send_notifications, check_dependencies
)
from eod_prices_writer  import run_eod_update
from stop_alert_writer  import run_stop_check
from outcome_evaluator  import run_outcome_evaluation
from ban_fetcher        import write_ban_list

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
            'regime':         regime,
            'regime_score':   regime_score,
            'nifty_close':    round(
                float(closes.iloc[-1]), 2),
            'nifty_price':    round(
                float(closes.iloc[-1]), 2),
            'nifty_change':   round(ret20, 2),
            'ret20':          round(ret20, 2),
            'today':          date.today().strftime(
                                  '%d %b %Y'),
            'sector_leaders': []
        }
    except Exception as e:
        print(f"[main] Nifty info error: {e}")
        return {
            'regime':         'Choppy',
            'regime_score':   0,
            'nifty_close':    0,
            'nifty_price':    0,
            'nifty_change':   0,
            'ret20':          0,
            'today':          date.today().strftime(
                                  '%d %b %Y'),
            'sector_leaders': []
        }


def get_sector_momentum():
    momentum = {}
    for sector, sym in SECTOR_INDICES.items():
        try:
            df = yf.download(
                sym, period='1mo',
                progress=False, auto_adjust=True)
            if isinstance(df.columns,
                          pd.MultiIndex):
                df.columns = [
                    c[0] for c in df.columns]
            closes = df['Close']
            ret    = float(
                (closes.iloc[-1] /
                 closes.iloc[0] - 1) * 100)
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


# ── DUPLICATE PENDING FILTER ──────────────────────────
# Prevents scanner from re-firing a signal that is
# already PENDING in signal_history.json
#
# Rules:
#   Same symbol + same signal type + PENDING = skip
#   Different signal type = allow
#     (TATASTEEL UP_TRI pending → TATASTEEL BULL_PROXY ok)
#   Second attempts have their own dedup logic
#     in detect_second_attempt() — not filtered here
#
# This runs AFTER enrich_signal() and BEFORE
# mini_scanner filter so shadow mode still sees
# all fresh signals but duplicates are suppressed

def _filter_duplicate_pending(signals,
                               history_signals):
    """
    Returns filtered list with duplicate pending
    signals removed.

    A signal is a duplicate if:
      history has a record with same symbol + signal
      AND result == PENDING
      AND attempt_number == 1 (not SA)
    """
    # Build set of pending symbol+signal combos
    pending_set = set()
    for h in history_signals:
        if h.get('result') != 'PENDING':
            continue
        if h.get('attempt_number', 1) != 1:
            continue
        sym = h.get('symbol', '')
        sig = h.get('signal', '')
        if sym and sig:
            pending_set.add(f"{sym}_{sig}")

    if not pending_set:
        return signals  # nothing to filter

    filtered  = []
    skipped   = []

    for sig in signals:
        # Never filter second attempts here
        if sig.get('attempt_number', 1) == 2:
            filtered.append(sig)
            continue

        key = (f"{sig.get('symbol', '')}_"
               f"{sig.get('signal', '')}")

        if key in pending_set:
            skipped.append(key)
        else:
            filtered.append(sig)

    if skipped:
        print(f"[main] Duplicate pending filtered: "
              f"{len(skipped)} signals")
        for k in skipped:
            print(f"[main]   Skip: {k}")

    return filtered
# ── END DUPLICATE FILTER ──────────────────────────────


# ── SCAN LOG ──────────────────────────────────────────

def write_scan_log(signals, rejected,
                   scan_date, regime):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_path = os.path.join(
        OUTPUT_DIR, 'scan_log.json')

    def _fmt(s):
        entry = float(s.get('entry_est') or 0)
        stop  = float(s.get('stop')      or 0)
        risk  = abs(entry - stop)
        dirn  = s.get('direction', 'LONG')

        if dirn == 'LONG':
            target = round(entry + 2 * risk, 2)
        else:
            target = round(entry - 2 * risk, 2)

        return {
            'symbol':         s.get('symbol', ''),
            'sector':         s.get('sector', ''),
            'grade':          s.get('grade', 'C'),
            'signal':         s.get('signal', ''),
            'direction':      dirn,
            'age':            s.get('age', 0),
            'score':          s.get('score', 0),
            'entry_est':      round(entry, 2),
            'stop':           round(stop, 2),
            'target_price':   target,
            'atr':            round(float(
                s.get('atr') or 0), 2),
            'pivot_price':    round(float(
                s.get('pivot_price') or 0), 2),
            'pivot_date':     s.get(
                'pivot_date', ''),
            'regime':         s.get('regime', ''),
            'regime_score':   s.get(
                'regime_score', 0),
            'stock_regime':   s.get(
                'stock_regime', 'Choppy'),
            'vol_q':          s.get('vol_q', ''),
            'vol_confirm':    s.get(
                'vol_confirm', False),
            'rs_q':           s.get('rs_q', ''),
            'sec_mom':        s.get('sec_mom', ''),
            'bear_bonus':     s.get(
                'bear_bonus', False),
            'attempt_number': s.get(
                'attempt_number', 1),
            'parent_signal':  s.get(
                'parent_signal', None),
            'parent_date':    s.get(
                'parent_date', None),
            'scan_time':      datetime.utcnow()
                              .strftime('%H:%M IST'),
            'date':           scan_date,
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

    # ── STEP 1: Trading day check ─────────────────
    status = get_market_status()
    if not status['is_trading']:
        print(f"[main] Not a trading day: "
              f"{status['reason']}")
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

    # ── STEP 2: F&O ban list ──────────────────────
    try:
        banned_stocks = write_ban_list()
        print(f"[main] Ban list: "
              f"{len(banned_stocks)} stocks")
    except Exception as e:
        print(f"[main] Ban list error: {e}")
        banned_stocks = []

    # ── STEP 3: Nifty info ────────────────────────
    print("[main] Fetching market data...")
    market_info = get_nifty_info()
    regime      = market_info['regime']
    reg_score   = market_info['regime_score']
    print(f"[main] Regime: {regime} "
          f"Score: {reg_score}")

    # ── STEP 4: Sector momentum ───────────────────
    sector_momentum = get_sector_momentum()
    market_info['sector_leaders'] = \
        get_sector_leaders(sector_momentum)

    # ── STEP 5: Load universe ─────────────────────
    universe   = load_universe()
    sector_map = get_sector_map()
    grade_map  = get_grade_map()
    print(f"[main] Universe: "
          f"{len(universe)} stocks")

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

    history_signals       = load_history()
    fetch_failed          = []
    insufficient_data     = []
    corporate_action_skip = []
    all_raw_signals       = []

    print(f"[main] Scanning "
          f"{len(universe)} stocks...")

    # ── STEP 6-8: Scan each stock ─────────────────
    for sym in universe:
        try:
            if has_recent_corporate_action(sym):
                print(f"[main] CA skip: {sym}")
                corporate_action_skip.append(sym)
                continue

            df, skip_reason = prepare(
                sym, period='1y')

            if df is None:
                if skip_reason == \
                        'insufficient_bars':
                    insufficient_data.append(sym)
                else:
                    fetch_failed.append(sym)
                continue

            sector = sector_map.get(sym, 'Other')
            grade  = grade_map.get(sym, 'C')

            sigs = detect_signals(
                df, sym, sector,
                regime, reg_score,
                sector_momentum,
                nifty_close
            )

            sa_sigs = detect_second_attempt(
                df, sym, sector,
                regime, reg_score,
                sector_momentum,
                history_signals,
                nifty_close
            )

            combined = sigs + sa_sigs

            for sig in combined:
                sig['grade']           = grade
                sig['scanner_version'] = \
                    SCANNER_VERSION
                sym_clean = sym.replace('.NS','')
                sig['is_banned'] = \
                    sym_clean in banned_stocks
                sig = enrich_signal(sig, grade)
                all_raw_signals.append(sig)

        except Exception as e:
            print(f"[main] Scan error {sym}: {e}")
            fetch_failed.append(sym)
            continue

    print(f"[main] Raw signals: "
          f"{len(all_raw_signals)}")

    # ── STEP 9: Filter duplicate pending ──────────
    # Remove signals already PENDING in history
    # Same symbol + same signal type = skip
    # Prevents re-firing of ongoing signals
    all_raw_signals = _filter_duplicate_pending(
        all_raw_signals, history_signals)

    print(f"[main] After dedup filter: "
          f"{len(all_raw_signals)} signals")

    # ── STEP 10: Mini scanner filter ──────────────
    mini_signals, alpha_signals, rejection_log = \
        mini_filter(all_raw_signals)

    print(f"[main] Mini: {len(mini_signals)} | "
          f"Alpha: {len(alpha_signals)} | "
          f"Shadow hits: {len(rejection_log)}")

    mini_ids = {id(s) for s in mini_signals}
    rejected = [s for s in alpha_signals
                if id(s) not in mini_ids]

    # ── STEP 11: Write scan_log.json ──────────────
    scan_date = date.today().isoformat()
    write_scan_log(
        mini_signals, rejected,
        scan_date, regime)

    # ── STEP 12-13: Write mini + rejected logs ────
    write_mini_log(mini_signals)
    write_rejected_log(rejection_log)

    # ── STEP 14: Append to signal_history ─────────
    logged_count = 0
    for sig in mini_signals:
        try:
            log_signal(sig, layer='MINI')
            logged_count += 1
        except Exception as e:
            print(f"[main] Log error "
                  f"{sig.get('symbol','')}: {e}")

    for rej in rejection_log:
        if rej.get('shadow_only', False):
            try:
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

    print(f"[main] Logged {logged_count} signals")

    # ── STEP 15: Archive old records ──────────────
    try:
        archive_old_records()
    except Exception as e:
        print(f"[main] Archive error: {e}")

    # ── STEP 16: Write holidays ───────────────────
    try:
        write_holidays(OUTPUT_DIR)
    except Exception as e:
        print(f"[main] Holidays write error: {e}")

    # ── STEP 17: Write meta.json — MUST BE LAST ───
    try:
        write_meta(
            output_dir            = OUTPUT_DIR,
            market_date           = scan_date,
            regime                = regime,
            universe_size         = len(universe),
            signals_found         = len(mini_signals),
            is_trading_day        = True,
            scanner_version       = SCANNER_VERSION,
            app_version           = APP_VERSION,
            fetch_failed          = fetch_failed,
            insufficient_data     = insufficient_data,
            corporate_action_skip = corporate_action_skip,
            history_record_count  = get_history_count(),
        )
    except Exception as e:
        print(f"[main] Meta write error: {e}")

    # ── STEP 18: Build HTML shell ─────────────────
    try:
        build_html()
    except Exception as e:
        print(f"[main] HTML build error: {e}")

    # ── STEP 19: Push notifications ───────────────
    try:
        if check_dependencies():
            send_notifications(
                signals       = mini_signals,
                regime        = regime,
                universe_size = len(universe),
            )
    except Exception as e:
        print(f"[main] Push error: {e}")

    # ── Telegram morning alert ────────────────────
    try:
        health_s, hw  = get_system_health()
        system_health = {
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
    status = get_market_status()
    if not status['is_trading']:
        return

    print("[main] EOD update starting...")

    try:
        run_outcome_evaluation()
    except Exception as e:
        print(f"[main] Outcome eval error: {e}")

    try:
        run_eod_update()
    except Exception as e:
        print(f"[main] EOD error: {e}")

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
