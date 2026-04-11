# scanner/main.py
# Orchestrator only — calls everything in correct order
# Does not contain detection, scoring, or rendering logic
#
# D1 FIX: market_info now populated with active_signals_count
#         + scan_time before send_morning_scan call
# B2 FIX: run_eod() passes load_history() to send_eod_summary
#         not just get_open_trades()
# WEEKEND FIX: Non-trading days now write valid scan_log.json
#              to prevent health check failures from stale data
# M4 FIX: Skip if already scanned today (for retry crons)
# M5 FIX: Auto-sync active count if mismatch detected
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

from config import (DATA_DIR, OUTPUT_DIR)

SCANNER_VERSION = 'v2.0'
APP_VERSION     = '2.0'

from calendar_utils import (
    is_trading_day, get_market_status,
    next_trading_day, days_until_exit
)
from universe import (
    load_universe, get_sector_map, get_grade_map
)
from scorer import enrich_signal
from telegram_bot import (
    send_morning_scan, send_eod_summary,
    send_stop_alert
)
from scanner_core import (
    prepare, detect_signals,
    detect_second_attempt,
    has_recent_corporate_action
)
from journal import (
    log_signal, log_rejected,
    get_open_trades, get_recent_closed,
    get_system_health, get_summary,
    archive_old_records, load_history,
    get_history_count,
    get_active_signals_count,
    backfill_target_prices,
    backfill_generation_flags,
    ensure_archive_exists,
)
from mini_scanner import (
    filter_signals as mini_filter,
    write_mini_log, write_rejected_log
)
from meta_writer   import (write_meta, write_holidays)
from html_builder  import build_html
from push_sender   import (send_notifications, check_dependencies)
from eod_prices_writer  import run_eod_update
from stop_alert_writer  import run_stop_check
from outcome_evaluator  import run_outcome_evaluation
from ban_fetcher        import write_ban_list

# ── CONSTANTS ─────────────────────────────────────────
NIFTY_SYMBOL   = "^NSEI"
SECTOR_INDICES = {
    "Bank":   "^NSEBANK",
    "IT":     "^CNXIT",
    "Pharma": "^CNXPHARMA",
    "Auto":   "^CNXAUTO",
    "Metal":  "^CNXMETAL",
    "Energy": "^CNXENERGY",
    "FMCG":   "^CNXFMCG",
    "Infra":  "^CNXINFRA",
}


# ── SHADOW MODE CHECK ─────────────────────────────────
def _is_shadow_mode():
    try:
        rules_path = os.path.join(
            parent_dir, 'data', 'mini_scanner_rules.json')
        with open(rules_path, 'r') as f:
            rules = json.load(f)
        return rules.get('shadow_mode', True)
    except Exception:
        return True


# ── M4: SKIP-IF-DONE CHECK ────────────────────────────
def _already_scanned_today():
    """
    Returns True if scan_log.json exists with today's date
    and has signals or explicitly marked complete.
    Used by retry crons to skip if primary scan succeeded.
    """
    scan_log_path = os.path.join(OUTPUT_DIR, 'scan_log.json')
    today_str = date.today().isoformat()
    
    if not os.path.exists(scan_log_path):
        return False
    
    try:
        with open(scan_log_path, 'r') as f:
            data = json.load(f)
        
        if data.get('date') != today_str:
            return False
        
        if data.get('is_trading_day', True):
            if 'count' in data:
                print(f"[main] Already scanned today "
                      f"({data.get('count', 0)} signals) — skipping")
                return True
        else:
            print("[main] Already processed today "
                  "(non-trading day) — skipping")
            return True
        
        return False
        
    except Exception as e:
        print(f"[main] Skip check error: {e}")
        return False


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
            (closes.iloc[-1] / closes.iloc[-20] - 1) * 100)
        regime_score = (
             2 if ret20 >  5 else
             1 if ret20 >  2 else
            -1 if ret20 < -2 else 0)

        return {
            'regime':         regime,
            'regime_score':   regime_score,
            'nifty_close':    round(float(closes.iloc[-1]), 2),
            'nifty_price':    round(float(closes.iloc[-1]), 2),
            'nifty_change':   round(ret20, 2),
            'ret20':          round(ret20, 2),
            'today':          date.today().strftime('%d %b %Y'),
            'market_date':    date.today().isoformat(),
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
            'today':          date.today().strftime('%d %b %Y'),
            'market_date':    date.today().isoformat(),
            'sector_leaders': []
        }


def get_sector_momentum():
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
                (closes.iloc[-1] / closes.iloc[0] - 1) * 100)
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
def filter_duplicate_pending(signals, history_signals):
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
        return signals

    filtered = []
    skipped  = []

    for sig in signals:
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
        print(f"[main] Duplicate pending "
              f"filtered: {len(skipped)} signals")
        for k in skipped:
            print(f"[main]   Skip: {k}")

    return filtered


# ── SCAN LOG ──────────────────────────────────────────
def write_scan_log(signals, rejected, scan_date, regime,
                   is_trading_day=True):
    """
    Writes scan_log.json.
    WEEKEND FIX: Now accepts is_trading_day flag to write
    valid but empty scan_log on non-trading days.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_path = os.path.join(OUTPUT_DIR, 'scan_log.json')

    def _fmt(s):
        entry = float(s.get('entry_est') or
                      s.get('entry')     or
                      s.get('scan_price') or 0)
        stop  = float(s.get('stop') or 0)
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
            'atr':            round(float(s.get('atr') or 0), 2),
            'pivot_price':    round(float(
                                  s.get('pivot_price') or 0), 2),
            'pivot_date':     s.get('pivot_date', ''),
            'regime':         s.get('regime', ''),
            'regime_score':   s.get('regime_score', 0),
            'stock_regime':   s.get('stock_regime', 'Choppy'),
            'vol_q':          s.get('vol_q', ''),
            'vol_confirm':    bool(s.get('vol_confirm', False)),
            'rs_q':           s.get('rs_q', ''),
            'sec_mom':        s.get('sec_mom', ''),
            'bear_bonus':     s.get('bear_bonus', False),
            'attempt_number': s.get('attempt_number', 1),
            'parent_signal':  s.get('parent_signal', None),
            'parent_date':    s.get('parent_date', None),
            'scan_time':      datetime.utcnow()
                              .strftime('%H:%M UTC'),
            'date':           scan_date,
            'scanner_version': SCANNER_VERSION,
        }

    data = {
        'date':           scan_date,
        'scan_date':      scan_date,
        'scan_time':      datetime.utcnow().strftime('%H:%M UTC'),
        'regime':         regime,
        'count':          len(signals),
        'is_trading_day': is_trading_day,
        'signals':        [_fmt(s) for s in signals],
        'rejected':       [_fmt(s) for s in rejected],
    }

    with open(log_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"[main] scan_log.json written → "
          f"{len(signals)} signals, "
          f"{len(rejected)} rejected, "
          f"trading_day={is_trading_day}")


# ── MORNING SCAN ──────────────────────────────────────
def run_morning_scan():

    # ── M4: Skip if already scanned today ─────────────
    if _already_scanned_today():
        return

    # ── STEP 1: Trading day check ──────────────────────
    status = get_market_status()
    if not status['is_trading']:
        print(f"[main] Not a trading day: {status['reason']}")
        market_info = get_nifty_info()

        try:
            ensure_archive_exists()
        except Exception as e:
            print(f"[main] Archive init: {e}")

        write_holidays(OUTPUT_DIR)

        # ── WEEKEND FIX: Write valid scan_log.json ─────
        # This prevents health check failures from stale data
        scan_date = date.today().isoformat()
        write_scan_log(
            signals=[],
            rejected=[],
            scan_date=scan_date,
            regime=market_info['regime'],
            is_trading_day=False
        )

        write_meta(
            output_dir           = OUTPUT_DIR,
            market_date          = date.today().isoformat(),
            regime               = market_info['regime'],
            universe_size        = 0,
            signals_found        = 0,
            active_signals_count = get_active_signals_count(),
            is_trading_day       = False,
            scanner_version      = SCANNER_VERSION,
            app_version          = APP_VERSION,
            history_record_count = get_history_count(),
        )
        build_html()

        # ── Telegram: Non-trading day notification ─────
        print(f"[main] Non-trading day complete — "
              f"{status['reason']}")
        return

    print("[main] Trading day confirmed — starting morning scan")

    # ── STEP 1b: Ensure archive exists ────────────────
    try:
        ensure_archive_exists()
    except Exception as e:
        print(f"[main] Archive init error: {e}")

    # ── STEP 1c: Backfill target prices ───────────────
    try:
        backfill_target_prices()
    except Exception as e:
        print(f"[main] Backfill error: {e}")

    # ── STEP 1d: Backfill generation flags ────────────
    try:
        backfill_generation_flags()
    except Exception as e:
        print(f"[main] Generation backfill error: {e}")

    # ── STEP 2: F&O ban list ───────────────────────────
    try:
        banned_stocks = write_ban_list()
        print(f"[main] Ban list: {len(banned_stocks)} stocks")
    except Exception as e:
        print(f"[main] Ban list error: {e}")
        banned_stocks = []

    # ── STEP 3: Nifty info ────────────────────────────
    print("[main] Fetching market data...")
    market_info = get_nifty_info()
    regime      = market_info['regime']
    reg_score   = market_info['regime_score']
    print(f"[main] Regime: {regime} Score: {reg_score}")

    # ── STEP 4: Sector momentum ───────────────────────
    sector_momentum = get_sector_momentum()
    market_info['sector_leaders'] = \
        get_sector_leaders(sector_momentum)

    # ── STEP 5: Load universe ─────────────────────────
    universe   = load_universe()
    sector_map = get_sector_map()
    grade_map  = get_grade_map()
    print(f"[main] Universe: {len(universe)} stocks")

    try:
        nifty_df = yf.download(
            NIFTY_SYMBOL, period='3mo',
            progress=False, auto_adjust=True)
        if isinstance(nifty_df.columns, pd.MultiIndex):
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

    print(f"[main] Scanning {len(universe)} stocks...")

    # ── STEP 6-8: Scan each stock ─────────────────────
    for sym in universe:
        try:
            if has_recent_corporate_action(sym):
                print(f"[main] CA skip: {sym}")
                corporate_action_skip.append(sym)
                continue

            df, skip_reason = prepare(sym, period='1y')

            if df is None:
                if skip_reason == 'insufficient_bars':
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
                sig['scanner_version'] = SCANNER_VERSION
                sym_clean = sym.replace('.NS', '')
                sig['is_banned'] = sym_clean in banned_stocks
                sig = enrich_signal(sig, grade)
                all_raw_signals.append(sig)

        except Exception as e:
            print(f"[main] Scan error {sym}: {e}")
            fetch_failed.append(sym)
            continue

    print(f"[main] Raw signals: {len(all_raw_signals)}")

    # ── STEP 9: Filter duplicate pending ──────────────
    all_raw_signals = filter_duplicate_pending(
        all_raw_signals, history_signals)
    print(f"[main] After dedup filter: "
          f"{len(all_raw_signals)} signals")

    # ── STEP 10: Mini scanner filter ──────────────────
    mini_signals, alpha_signals, rejection_log = \
        mini_filter(all_raw_signals)

    print(f"[main] Mini: {len(mini_signals)} | "
          f"Alpha: {len(alpha_signals)} | "
          f"Shadow hits: {len(rejection_log)}")

    mini_ids = {id(s) for s in mini_signals}
    rejected = [s for s in alpha_signals
                if id(s) not in mini_ids]

    # ── STEP 11: Write scan_log.json ──────────────────
    scan_date = date.today().isoformat()
    write_scan_log(
        mini_signals, rejected, scan_date, regime,
        is_trading_day=True
    )

    # ── STEP 12-13: Write mini + rejected logs ─────────
    write_mini_log(mini_signals)
    write_rejected_log(rejection_log)

    # ── STEP 14: Append TOOK signals to history ────────
    logged_count = 0
    for sig in mini_signals:
        try:
            log_signal(sig, layer='MINI')
            logged_count += 1
        except Exception as e:
            print(f"[main] Log error "
                  f"{sig.get('symbol','')}: {e}")

    # ── BUG 2 FIX: Shadow rejection logging ───────────
    shadow_mode_on = _is_shadow_mode()

    if shadow_mode_on:
        print(f"[main] Shadow mode ON — "
              f"no REJECTED records created "
              f"({len(rejection_log)} shadow hits recorded "
              f"in rejected_log.json only)")
    else:
        mini_took_keys = {
            (s.get('symbol', ''), s.get('signal', ''))
            for s in mini_signals
        }
        rej_logged = 0
        for rej in rejection_log:
            if rej.get('shadow_only', True):
                continue

            rej_key = (
                rej.get('symbol', ''),
                rej.get('signal',  '')
            )
            if rej_key in mini_took_keys:
                continue

            try:
                orig = next(
                    (s for s in all_raw_signals
                     if s.get('symbol') == rej.get('symbol')
                     and s.get('signal') == rej.get('signal')),
                    None)
                if orig:
                    log_rejected(
                        orig,
                        rej.get('rejection_reason', 'unknown'),
                        rej.get('rejection_filter', 'unknown'),
                        rej.get('threshold', None)
                    )
                    rej_logged += 1
            except Exception:
                pass

        print(f"[main] Rejected records logged: {rej_logged}")

    print(f"[main] Logged {logged_count} TOOK signals")

    # ── STEP 15: Archive old records ──────────────────
    try:
        archive_old_records()
    except Exception as e:
        print(f"[main] Archive error: {e}")

    # ── STEP 16: Write holidays ───────────────────────
    try:
        write_holidays(OUTPUT_DIR)
    except Exception as e:
        print(f"[main] Holidays write error: {e}")

    # ── STEP 17: Write meta.json — MUST BE LAST ────────
    # M5 FIX: Verify active count matches reality
    active_now = get_active_signals_count()
    
    try:
        fresh_history = load_history()
        actual_pending = len([
            s for s in fresh_history
            if s.get('result') == 'PENDING'
            and s.get('action') == 'TOOK'
        ])
        if actual_pending != active_now:
            print(f"[main] M5 FIX: Active count mismatch — "
                  f"journal says {active_now}, "
                  f"actual is {actual_pending}")
            active_now = actual_pending
    except Exception as e:
        print(f"[main] M5 count verify error: {e}")

    try:
        write_meta(
            output_dir            = OUTPUT_DIR,
            market_date           = scan_date,
            regime                = regime,
            universe_size         = len(universe),
            signals_found         = len(mini_signals),
            active_signals_count  = active_now,
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

    # ── STEP 18: Build HTML shell ──────────────────────
    try:
        build_html()
    except Exception as e:
        print(f"[main] HTML build error: {e}")

    # ── STEP 19: Push notifications ───────────────────
    try:
        if check_dependencies():
            send_notifications(
                signals       = mini_signals,
                regime        = regime,
                universe_size = len(universe),
            )
    except Exception as e:
        print(f"[main] Push error: {e}")

    # ── STEP 20: Telegram morning alert ───────────────
    # D1 FIX: populate active_signals_count + scan_time
    # into market_info before passing to send_morning_scan
    try:
        market_info['active_signals_count'] = active_now
        market_info['signals_found']        = len(mini_signals)
        market_info['scan_time'] = (
            datetime.now().strftime('%I:%M %p IST'))
        send_morning_scan(mini_signals, market_info)
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

    # B2 FIX: pass full load_history() to send_eod_summary
    # not just open trades — resolved signals need to show
    try:
        all_history  = load_history()
        open_count   = len(get_open_trades())

        _numeric_fields = (
            'pnl_pct', 'pnl_rs',
            'mfe_pct', 'mae_pct',
            'score', 'adjusted_rr'
        )
        safe_history = []
        for t in all_history:
            safe_t = dict(t)
            for k in _numeric_fields:
                if safe_t.get(k) is None:
                    safe_t[k] = 0.0
            for k in ('symbol', 'signal', 'regime',
                      'direction', 'sector', 'grade'):
                if safe_t.get(k) is None:
                    safe_t[k] = '—'
            safe_history.append(safe_t)

        send_eod_summary(safe_history, open_count)
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
        print("Usage: python main.py [morning|stops|eod]")
