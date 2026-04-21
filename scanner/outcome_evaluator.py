# ── outcome_evaluator.py ─────────────────────────────
# Evaluates signal outcomes using 6-day OHLC window
#
# PRIOR FIXES (kept intact):
#   B FIX  — entry fallback chain
#   C FIX  — tracking_start set once only
#   E FIX  — verbose OPEN signal logging
#   OE4    — Day 6 uses OPEN price not CLOSE
#   DI3    — MFE/MAE uses actual_open first
#   PNL    — pnl_pct calculated on resolve
#   F1     — post-TARGET_HIT shadow tracking
#   F2     — shadow data fields in schema
#   V1     — skip entry_valid=False
#   TR3    — effective_tracking_end for holiday Day 6
#   HC5    — SA parent outcome propagation
#   H12/13 — failure_reason classifier
#   OE1 (old) — r_multiple hard caps
#   OE2 (old) — early return for terminal outcomes
#   OE3    — STOP_HIT pnl_pct forced negative
#
# PHASE 2 SESSION 2 FIXES:
#   EOD1   — Read eod_prices.json FIRST for OHLC data.
#   EOD2   — data_quality tagging on resolution.
#   D6A    — Day 6 OPEN price reads open_prices.json FIRST.
#
# SESSION 3 ADDITION (Apr 19 2026):
#   CS3    — Resolve contra_shadow.json entries at Day 6.
#
# SESSION A FIX (Apr 21 2026):
#   C-03 (reader side) — _resolve_contra_shadows now
#            reads fields that contra_tracker actually
#            writes.
#
# CRIT-02 FIX (Apr 21 2026 night):
#   _load_eod_prices() now handles new schema written
#   by eod_prices_writer.py CRIT-01 fix.
#
#   Old schema (broken — was being read incorrectly):
#     {date, fetched_at, results: [{symbol,close,...}]}
#     ↑ outcome_evaluator was reading top-level keys
#     as "symbols" — len() returned 8 (metadata count)
#     instead of actual symbol count.
#
#   New schema (CRIT-01):
#     {
#       date, fetched_at, results: [...],
#       ohlc_by_symbol: {           ← read this
#         "TCS.NS": {
#           "2026-04-21": {open,high,low,close}
#         }
#       },
#       schema_version: 2
#     }
#
#   Adapter logic:
#     1. If schema_version >= 2 → read ohlc_by_symbol directly
#     2. Else if results[] present → convert to nested dict
#        (handles transition period + first day after fix)
#     3. Else return {} (file invalid/empty)
#
#   This allows correct primary-source reading and
#   eliminates yfinance dependency for resolved-day data.
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime, timedelta

import yfinance as yf
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from journal import (
    load_history, _save_json,
    _backup_history, HISTORY_FILE
)

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

HOLIDAYS_FILE      = os.path.join(_OUTPUT, 'nse_holidays.json')
EOD_PRICES_FILE    = os.path.join(_OUTPUT, 'eod_prices.json')
OPEN_PRICES_FILE   = os.path.join(_OUTPUT, 'open_prices.json')
CONTRA_SHADOW_FILE = os.path.join(_OUTPUT, 'contra_shadow.json')

FLAT_PCT = 0.5

_TERMINAL_OUTCOMES = {
    'STOP_HIT',
    'TARGET_HIT',
    'DAY6_WIN',
    'DAY6_LOSS',
    'DAY6_FLAT',
}


# ── HOLIDAY HELPERS ───────────────────────────────────

def _load_holidays():
    try:
        with open(HOLIDAYS_FILE, 'r') as f:
            data = json.load(f)
        return data.get('holidays', [])
    except Exception:
        return []


def _is_trading_day(date_obj, holidays):
    if date_obj.weekday() >= 5:
        return False
    return date_obj.strftime(
        '%Y-%m-%d') not in holidays


def _next_trading_day(d, holidays):
    cur = d
    for _ in range(14):
        if _is_trading_day(cur, holidays):
            return cur
        cur += timedelta(days=1)
    return cur


def _get_entry_date(detection_date_str, holidays):
    cur = datetime.strptime(
        detection_date_str,
        '%Y-%m-%d').date() + timedelta(days=1)
    for _ in range(30):
        if _is_trading_day(cur, holidays):
            return cur
        cur += timedelta(days=1)
    return cur


def _get_nth_trading_day(start_date, n, holidays):
    count = 1
    cur   = start_date
    while count < n:
        cur += timedelta(days=1)
        if _is_trading_day(cur, holidays):
            count += 1
    return cur


def _count_trading_days(start_date, end_date, holidays):
    count = 0
    cur   = start_date
    while cur <= end_date:
        if _is_trading_day(cur, holidays):
            count += 1
        cur += timedelta(days=1)
    return count


# ── CRIT-02: SCHEMA ADAPTER ───────────────────────────

def _load_eod_prices():
    """
    CRIT-02 FIX: Now handles BOTH old and new schemas.

    Returns: { symbol: { date_str: {open,high,low,close} } }

    New schema (eod_prices_writer.py CRIT-01, schema_v2):
      Reads `ohlc_by_symbol` nested dict directly.

    Old schema (legacy results[] only):
      Converts results[] array → nested dict.
      Used for transition period / files written before
      CRIT-01 deployment. Open price falls back to close
      since old schema didn't store open.

    Returns empty dict if file unreadable or invalid.
    """
    try:
        with open(EOD_PRICES_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[outcome] eod_prices.json not readable: {e}")
        return {}

    # Validate top-level structure
    if not isinstance(data, dict):
        print(f"[outcome] eod_prices.json malformed "
              f"— expected dict, got {type(data)}")
        return {}

    schema_version = data.get('schema_version', 1)

    # ── New schema (v2+) — read ohlc_by_symbol ────
    if schema_version >= 2:
        ohlc_dict = data.get('ohlc_by_symbol', {})
        if isinstance(ohlc_dict, dict) and ohlc_dict:
            print(f"[outcome] eod_prices loaded "
                  f"(schema v{schema_version}): "
                  f"{len(ohlc_dict)} symbols")
            return ohlc_dict
        else:
            print(f"[outcome] eod_prices schema v{schema_version} "
                  f"but ohlc_by_symbol empty/missing")
            # Fall through to results[] conversion as safety net

    # ── Old schema fallback — convert results[] ───
    results = data.get('results', [])
    if not isinstance(results, list) or not results:
        print(f"[outcome] eod_prices has no usable data "
              f"(schema_v={schema_version}, "
              f"results={len(results) if isinstance(results, list) else 'N/A'})")
        return {}

    file_date = data.get('date')
    if not file_date:
        print(f"[outcome] eod_prices missing 'date' field "
              f"— cannot convert results[]")
        return {}

    # Convert flat results[] to nested {symbol:{date:{ohlc}}}
    converted = {}
    skipped = 0

    for entry in results:
        if not isinstance(entry, dict):
            skipped += 1
            continue

        sym = entry.get('symbol')
        if not sym:
            skipped += 1
            continue

        close = entry.get('close')
        if close is None:
            skipped += 1
            continue

        # Open may be None in old schema → fall back to close
        open_  = entry.get('open')  if entry.get('open')  is not None else close
        high   = entry.get('high')  if entry.get('high')  is not None else close
        low    = entry.get('low')   if entry.get('low')   is not None else close

        try:
            converted.setdefault(sym, {})[file_date] = {
                'open':  float(open_),
                'high':  float(high),
                'low':   float(low),
                'close': float(close),
            }
        except (ValueError, TypeError):
            skipped += 1
            continue

    print(f"[outcome] eod_prices converted from old schema: "
          f"{len(converted)} symbols ({skipped} skipped)")

    return converted


def _load_open_prices():
    """Load open_prices.json — populated at 9:27 AM
    by open_validator.py. Contains 9:15 open price
    per symbol per date.
    Schema: { date: ..., results: [{symbol, actual_open}] }
    """
    try:
        with open(OPEN_PRICES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[outcome] open_prices.json not readable: {e}")
        return {}


def _build_ohlc_from_eod(symbol, start_date, end_date,
                         eod_prices, open_prices):
    """
    EOD1: Build DataFrame-compatible OHLC from
    eod_prices.json and open_prices.json, avoiding
    yfinance entirely.

    eod_prices is now ALWAYS in nested format thanks to
    _load_eod_prices() adapter (CRIT-02 fix).
    Schema: { symbol: { date_str: {open,high,low,close} } }

    Returns DataFrame with same shape as yfinance output
    (columns: Open, High, Low, Close; index: timestamps).
    Returns None if insufficient data available.
    """
    symbol_eod = eod_prices.get(symbol, {})

    if not symbol_eod:
        return None

    # open_prices.json may be either:
    #   (a) {date, results:[{symbol, actual_open}]} (current)
    #   (b) {symbol: {date_str: open}} (legacy)
    # Build a quick lookup that handles both.
    symbol_opens = {}
    if isinstance(open_prices, dict):
        # Schema (a)
        if 'results' in open_prices and 'date' in open_prices:
            file_date = open_prices.get('date')
            for r in open_prices.get('results', []):
                if isinstance(r, dict) and r.get('symbol') == symbol:
                    ao = r.get('actual_open')
                    if ao is not None:
                        symbol_opens[file_date] = ao
        # Schema (b) fallback
        elif symbol in open_prices:
            symbol_opens = open_prices.get(symbol, {})

    rows = {}
    cur = start_date
    while cur <= end_date:
        date_str = cur.strftime('%Y-%m-%d')
        eod_row  = symbol_eod.get(date_str)

        if eod_row:
            open_price = (
                symbol_opens.get(date_str)
                or eod_row.get('open')
                or eod_row.get('close')
            )
            rows[pd.Timestamp(cur)] = {
                'Open':  float(open_price),
                'High':  float(eod_row.get('high',
                                            eod_row.get('close'))),
                'Low':   float(eod_row.get('low',
                                            eod_row.get('close'))),
                'Close': float(eod_row.get('close')),
            }
        cur += timedelta(days=1)

    if not rows:
        return None

    df = pd.DataFrame.from_dict(rows, orient='index')
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def _fetch_ohlc_yfinance(symbol, start_date,
                         end_date, retries=2):
    fetch_start = start_date - timedelta(days=3)
    fetch_end   = end_date   + timedelta(days=3)

    for attempt in range(retries + 1):
        try:
            df = yf.download(
                symbol,
                start       = fetch_start.strftime('%Y-%m-%d'),
                end         = fetch_end.strftime('%Y-%m-%d'),
                progress    = False,
                auto_adjust = False,
            )
            if df is None or df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]

            df.index = pd.to_datetime(df.index, errors='coerce')
            if df.index.tzinfo:
                df.index = df.index.tz_localize(None)

            start_ts = pd.Timestamp(start_date)
            end_ts   = pd.Timestamp(end_date)
            df = df[(df.index >= start_ts) &
                    (df.index <= end_ts)]

            if df.empty:
                continue
            return df

        except Exception as e:
            print(f"[outcome] yfinance error {symbol}: {e}")
    return None


def _fetch_ohlc(symbol, start_date, end_date,
                eod_prices, open_prices):
    """
    EOD1: Primary source is eod_prices.json (now correctly
    parsed via CRIT-02 adapter).
    Falls back to yfinance only if eod_prices is
    insufficient. Returns (df, source_tag) tuple.
    source_tag is used by EOD2 for data_quality tagging.
    """
    df_eod = _build_ohlc_from_eod(
        symbol, start_date, end_date,
        eod_prices, open_prices)

    if df_eod is not None and not df_eod.empty:
        rows_needed = _count_trading_days(
            start_date, min(end_date, date.today()),
            _load_holidays())
        if len(df_eod) >= rows_needed:
            return df_eod, 'eod_primary'
        print(f"[outcome] {symbol} — eod_prices "
              f"has {len(df_eod)} rows, needs "
              f"{rows_needed}. Falling back to yfinance.")

    df_yf = _fetch_ohlc_yfinance(symbol, start_date, end_date)
    if df_yf is not None and not df_yf.empty:
        return df_yf, 'yfinance_primary'

    if df_eod is not None and not df_eod.empty:
        print(f"[outcome] {symbol} — yfinance failed, "
              f"using partial eod_prices data "
              f"({len(df_eod)} rows) as recovery fallback")
        return df_eod, 'recovery_close_fallback'

    return None, 'no_data'


# ── HELPERS ───────────────────────────────────────────

def _calculate_target(entry, stop, direction):
    try:
        entry = float(entry)
        stop  = float(stop)
        risk  = abs(entry - stop)
        if risk <= 0:
            return None
        if direction == 'LONG':
            return round(entry + 2 * risk, 2)
        else:
            return round(entry - 2 * risk, 2)
    except Exception:
        return None


def _resolve_entry(signal):
    for field in [
        'actual_open',
        'scan_price',
        'entry',
        'entry_est',
    ]:
        val = signal.get(field)
        if val is not None:
            try:
                f = float(val)
                if f > 0:
                    return f
            except Exception:
                continue
    return None


def _calc_pnl_pct(entry, outcome_price, direction):
    try:
        entry         = float(entry)
        outcome_price = float(outcome_price)
        if entry <= 0:
            return None
        if direction == 'LONG':
            return round((outcome_price - entry) / entry * 100, 2)
        else:
            return round((entry - outcome_price) / entry * 100, 2)
    except Exception:
        return None


def _calc_r_multiple(entry, stop, outcome_price,
                     direction, outcome_type=None):
    if outcome_type == 'STOP_HIT':
        return -1.0
    if outcome_type == 'TARGET_HIT':
        return 2.0

    try:
        entry         = float(entry)
        stop          = float(stop)
        outcome_price = float(outcome_price)
        risk          = abs(entry - stop)
        if risk <= 0:
            return None
        if direction == 'LONG':
            pnl = outcome_price - entry
        else:
            pnl = entry - outcome_price
        return round(pnl / risk, 2)
    except Exception:
        return None


def _classify_failure_reason(signal, outcome,
                             exit_day, mae_pct):
    age         = int(signal.get('age', 0) or 0)
    vol_confirm = signal.get('vol_confirm', False)
    sec_leading = signal.get('sec_leading', False)
    rs_strong   = signal.get('rs_strong', False)
    bear_bonus  = signal.get('bear_bonus', False)
    stock_regime= (signal.get('stock_regime') or '')
    mkt_regime  = (signal.get('regime') or '')
    entry_valid = signal.get('entry_valid')
    gap_pct     = abs(float(signal.get('gap_pct') or 0))
    mae         = float(mae_pct or 0)
    sig_type    = (signal.get('signal') or '')

    if outcome == 'TARGET_HIT':
        if bear_bonus and age == 0:
            return 'Bear regime fresh breakout — highest conviction setup'
        elif vol_confirm and sec_leading:
            return 'Volume confirmed + sector leading — strong alignment'
        elif vol_confirm and rs_strong:
            return 'Volume confirmed + strong RS — momentum behind move'
        elif vol_confirm:
            return 'Volume confirmed breakout — clean directional move'
        else:
            return 'Price reached target in 6 days'

    if outcome == 'DAY6_WIN':
        if bear_bonus:
            return 'Bear regime — gradual move held through 6 days'
        return 'Gradual move to target — held through full window'

    if outcome == 'STOP_HIT':
        if entry_valid is False:
            return 'Gap at open invalidated entry — trade was not taken'
        if exit_day == 1 and gap_pct > 2.0:
            return 'Gapped through stop at open — Day 1 gap risk'
        if mae > 10:
            return 'Heavy move against position — event or regime shock'
        if mae > 5:
            return 'Strong directional move against — stop correctly hit'
        if mae < 2.5:
            return 'Stop hit by normal volatility — stop may be too tight'
        return 'Directional move against — stop hit'

    if outcome == 'DAY6_LOSS':
        if not vol_confirm:
            return 'Breakout without volume — weak setup, no follow-through'
        if age > 1:
            return 'Late entry — breakout momentum was already stale'
        if (stock_regime and mkt_regime
                and stock_regime.upper() != mkt_regime.upper()):
            return 'Stock and market regime misaligned — no confirmation'
        if 'DOWN_TRI' in sig_type:
            return 'Short setup failed to follow through in 6 days'
        return 'No directional move in 6 days — setup did not trigger'

    if outcome == 'DAY6_FLAT':
        if not vol_confirm:
            return 'Price moved without volume — false breakout absorbed'
        if age > 0:
            return 'Aged setup — edge reduced by time at entry'
        return 'Market absorbed the breakout — no net direction in 6 days'

    return None


# ── D6A: DAY 6 OPEN PRICE RESOLVER ────────────────────

def _resolve_day6_open(symbol, effective_tracking_end,
                       ohlc, open_prices):
    """
    D6A: Day 6 open price lookup.
    Primary:   open_prices.json (today only, written 9:27 AM)
    Secondary: ohlc dataframe (yfinance or eod-derived)

    open_prices.json schema:
      { "date": "YYYY-MM-DD", "results": [{symbol, actual_open}, ...] }

    Returns (day6_open, source) tuple.
    """
    date_str = effective_tracking_end.strftime('%Y-%m-%d')

    # Primary: open_prices.json — only if today matches Day 6
    if (open_prices.get('date') == date_str):
        for entry in open_prices.get('results', []):
            if entry.get('symbol') == symbol:
                ao = entry.get('actual_open')
                if ao is not None:
                    try:
                        return float(ao), 'open_prices'
                    except Exception:
                        pass

    # Secondary: ohlc dataframe
    if ohlc is not None and not ohlc.empty:
        day6_ts = pd.Timestamp(effective_tracking_end)
        if day6_ts in ohlc.index:
            try:
                return float(ohlc.loc[day6_ts, 'Open']), 'ohlc'
            except Exception:
                pass

    return None, 'unavailable'


# ── EVALUATE SINGLE SIGNAL ────────────────────────────

def _evaluate_signal(signal, holidays,
                     eod_prices, open_prices):

    current_outcome = signal.get('outcome', 'OPEN')
    if current_outcome in _TERMINAL_OUTCOMES:
        return signal

    sym       = signal.get('symbol', '')
    direction = signal.get('direction', 'LONG')
    det_date  = signal.get('date', '')
    stop_val  = signal.get('stop', None)

    entry = _resolve_entry(signal)
    stop  = float(stop_val) if stop_val else None

    if not sym or not det_date or not entry or not stop:
        print(f"[outcome] Skip {sym} — missing fields "
              f"entry={entry} stop={stop}")
        return signal

    if not signal.get('target_price'):
        target = _calculate_target(entry, stop, direction)
        if target:
            signal['target_price'] = target
    else:
        try:
            target = float(signal['target_price'])
        except Exception:
            target = _calculate_target(entry, stop, direction)
            if target:
                signal['target_price'] = target

    if not target:
        print(f"[outcome] Skip {sym} — cannot calculate target")
        return signal

    try:
        entry_date   = _get_entry_date(det_date, holidays)
        tracking_end = _get_nth_trading_day(entry_date, 6, holidays)
    except Exception as e:
        print(f"[outcome] Date error {sym}: {e}")
        return signal

    effective_tracking_end = _next_trading_day(tracking_end, holidays)
    if effective_tracking_end != tracking_end:
        print(f"[outcome] {sym} — tracking_end {tracking_end} "
              f"is holiday, rolling to {effective_tracking_end}")

    today = date.today()

    if not signal.get('tracking_start'):
        signal['tracking_start'] = entry_date.strftime('%Y-%m-%d')
    if not signal.get('tracking_end'):
        signal['tracking_end'] = tracking_end.strftime('%Y-%m-%d')

    signal['effective_exit_date'] = \
        effective_tracking_end.strftime('%Y-%m-%d')

    if today < entry_date:
        print(f"[outcome] {sym} — entry {entry_date} not reached")
        return signal

    # EOD1: Primary = eod_prices, fallback = yfinance
    fetch_end = min(today, effective_tracking_end)
    ohlc, data_source = _fetch_ohlc(
        sym, entry_date, fetch_end, eod_prices, open_prices)

    if ohlc is None or ohlc.empty:
        print(f"[outcome] {sym} — no OHLC data from any source")
        return signal

    real_exit_outcome = None
    real_exit_date    = None
    real_exit_price   = None
    real_exit_day     = None
    max_fav           = 0.0
    max_adv           = 0.0

    scan_end_ts = pd.Timestamp(tracking_end)

    for ts, row in ohlc.iterrows():
        if ts > scan_end_ts:
            break
        try:
            high  = float(row['High'])
            low   = float(row['Low'])
            close = float(row['Close'])
        except Exception:
            continue

        if direction == 'LONG':
            fav = (high  - entry) / entry * 100
            adv = (entry - low)   / entry * 100
        else:
            fav = (entry - low)   / entry * 100
            adv = (high  - entry) / entry * 100

        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)

        if direction == 'LONG':
            stop_hit   = low  <= stop
            target_hit = high >= target
        else:
            stop_hit   = high >= stop
            target_hit = low  <= target

        if stop_hit and real_exit_outcome is None:
            real_exit_outcome = 'STOP_HIT'
            real_exit_date    = ts.date()
            real_exit_price   = round(stop, 2)
            real_exit_day     = _count_trading_days(
                entry_date, ts.date(), holidays)
            print(f"[outcome] {sym} → STOP_HIT Day {real_exit_day}")
            break

        if target_hit and real_exit_outcome is None:
            real_exit_outcome = 'TARGET_HIT'
            real_exit_date    = ts.date()
            real_exit_price   = round(target, 2)
            real_exit_day     = _count_trading_days(
                entry_date, ts.date(), holidays)
            print(f"[outcome] {sym} → TARGET_HIT Day {real_exit_day} "
                  f"— continuing for Day 6 shadow")

    # ── DAY 6 EXIT ─ D6A: open_prices first ──────────
    day6_open        = None
    day6_source      = None
    post_target_move = None

    if today >= effective_tracking_end:
        day6_open, day6_source = _resolve_day6_open(
            sym, effective_tracking_end, ohlc, open_prices)

        if day6_open is None:
            print(f"[outcome] {sym} — Day 6 open unavailable "
                  f"for {effective_tracking_end}")
        else:
            print(f"[outcome] {sym} — Day 6 open ₹{day6_open:.2f} "
                  f"via {day6_source}")

            if (real_exit_outcome == 'TARGET_HIT'
                    and real_exit_price):
                raw_move = ((day6_open - real_exit_price)
                            / real_exit_price * 100)
                post_target_move = round(
                    raw_move if direction == 'LONG' else -raw_move, 2)
                print(f"[outcome] {sym} → post_target_move: "
                      f"{post_target_move:+.1f}%")

            if real_exit_outcome is None:
                move_pct = (day6_open - entry) / entry * 100
                if direction == 'SHORT':
                    move_pct = -move_pct

                if move_pct > FLAT_PCT:
                    real_exit_outcome = 'DAY6_WIN'
                elif move_pct < -FLAT_PCT:
                    real_exit_outcome = 'DAY6_LOSS'
                else:
                    real_exit_outcome = 'DAY6_FLAT'

                real_exit_date  = effective_tracking_end
                real_exit_price = round(day6_open, 2)
                real_exit_day   = 6

                print(f"[outcome] {sym} → {real_exit_outcome} "
                      f"move {move_pct:+.1f}% Day6 open "
                      f"₹{day6_open:.2f}")

    if real_exit_outcome:
        pnl_pct = _calc_pnl_pct(
            entry, real_exit_price, direction)

        if real_exit_outcome == 'STOP_HIT':
            if pnl_pct is not None and pnl_pct > 0:
                print(f"[outcome] OE3 fix {sym} — "
                      f"STOP_HIT had positive pnl "
                      f"{pnl_pct}%, forcing negative")
                pnl_pct = -abs(pnl_pct)

        r_multiple = _calc_r_multiple(
            entry=entry, stop=stop,
            outcome_price=real_exit_price,
            direction=direction,
            outcome_type=real_exit_outcome,
        )

        failure_reason = _classify_failure_reason(
            signal=signal, outcome=real_exit_outcome,
            exit_day=real_exit_day,
            mae_pct=round(max_adv, 2))

        signal['outcome']        = real_exit_outcome
        signal['outcome_date']   = str(real_exit_date)[:10]
        signal['outcome_price']  = real_exit_price
        signal['pnl_pct']        = pnl_pct
        signal['r_multiple']     = r_multiple
        signal['mfe_pct']        = round(max_fav, 2)
        signal['mae_pct']        = round(max_adv, 2)
        signal['exit_type']      = real_exit_outcome
        signal['exit_day']       = real_exit_day
        signal['failure_reason'] = failure_reason

        # EOD2: data_quality tagging
        signal['data_quality_resolve'] = data_source
        if day6_source:
            signal['day6_source'] = day6_source

        if day6_open is not None:
            signal['day6_open'] = round(day6_open, 2)
        if post_target_move is not None:
            signal['post_target_move'] = post_target_move

        days_to = _count_trading_days(
            entry_date,
            real_exit_date if isinstance(real_exit_date, date)
            else effective_tracking_end,
            holidays)
        signal['days_to_outcome'] = days_to

    else:
        days_so_far = _count_trading_days(
            entry_date, today, holidays)
        print(f"[outcome] {sym} {signal.get('signal','')} — "
              f"Day {days_so_far}/6 OPEN | "
              f"MFE:+{max_fav:.1f}% MAE:-{max_adv:.1f}%")
        if max_fav > 0 or max_adv > 0:
            signal['mfe_pct'] = round(max_fav, 2)
            signal['mae_pct'] = round(max_adv, 2)

    return signal


def _propagate_sa_outcome(history, parent_id, parent_outcome):
    updated = 0
    for sig in history:
        if sig.get('sa_parent_id') == parent_id:
            if sig.get('sa_parent_outcome') != parent_outcome:
                sig['sa_parent_outcome'] = parent_outcome
                updated += 1
                print(f"[outcome] SA propagate: "
                      f"{sig.get('symbol','')} "
                      f"sa_parent_outcome={parent_outcome}")
    return updated


# ── CS3 — CONTRA SHADOW RESOLUTION ───────────────────

def _shadow_field(shadow, *names):
    for n in names:
        v = shadow.get(n)
        if v is not None:
            return v
    return None


def _resolve_contra_shadows(holidays, eod_prices,
                            open_prices):
    if not os.path.exists(CONTRA_SHADOW_FILE):
        print("[contra] No contra_shadow.json yet — "
              "nothing to resolve")
        return

    try:
        with open(CONTRA_SHADOW_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[contra] Load error: {e}")
        return

    shadows = data.get('shadows', [])
    if not shadows:
        print("[contra] No shadows to process")
        return

    unresolved = [
        s for s in shadows
        if s.get('outcome') is None
        or s.get('outcome') == 'OPEN'
    ]

    if not unresolved:
        print(f"[contra] All {len(shadows)} shadows "
              f"already resolved")
        return

    print(f"[contra] Evaluating {len(unresolved)} "
          f"contra shadows...")

    today          = date.today()
    resolved_count = 0
    updates        = 0
    skipped_fields = 0

    for shadow in unresolved:
        sym       = shadow.get('symbol', '')
        shadow_id = shadow.get('id', '')
        det_date  = shadow.get('date', '')

        inverted_dir = _shadow_field(
            shadow, 'direction', 'inverted_direction') or 'LONG'
        original_dir = _shadow_field(
            shadow, 'original_direction',
            'origin_signal_direction') or 'SHORT'
        entry_raw    = _shadow_field(
            shadow, 'entry', 'entry_est')

        if not sym or entry_raw is None or not det_date:
            skipped_fields += 1
            print(f"[contra] Skip {shadow_id} — "
                  f"missing fields "
                  f"(sym={sym!r}, entry={entry_raw!r}, "
                  f"date={det_date!r})")
            continue

        try:
            entry = float(entry_raw)
        except Exception:
            skipped_fields += 1
            print(f"[contra] Skip {shadow_id} — "
                  f"entry not numeric: {entry_raw!r}")
            continue

        try:
            entry_date    = _get_entry_date(det_date, holidays)
            tracking_end  = _get_nth_trading_day(
                entry_date, 6, holidays)
            effective_end = _next_trading_day(
                tracking_end, holidays)
        except Exception as e:
            print(f"[contra] Date error {shadow_id}: {e}")
            continue

        shadow['effective_exit_date'] = \
            effective_end.strftime('%Y-%m-%d')

        if today < effective_end:
            days_left = (effective_end - today).days
            print(f"[contra] {sym} ({shadow_id}) — "
                  f"Day 6 in {days_left} days")
            continue

        ohlc, _ = _fetch_ohlc(
            sym, entry_date, effective_end,
            eod_prices, open_prices)

        day6_open, day6_source = _resolve_day6_open(
            sym, effective_end, ohlc, open_prices)

        if day6_open is None:
            print(f"[contra] {sym} ({shadow_id}) — "
                  f"Day 6 open unavailable")
            continue

        pnl_pct = _calc_pnl_pct(
            entry, day6_open, inverted_dir)

        if pnl_pct is None:
            continue

        if pnl_pct > FLAT_PCT:
            outcome = 'CONTRA_WIN'
        elif pnl_pct < -FLAT_PCT:
            outcome = 'CONTRA_LOSS'
        else:
            outcome = 'CONTRA_FLAT'

        shadow['outcome']       = outcome
        shadow['outcome_date']  = effective_end.strftime(
            '%Y-%m-%d')
        shadow['outcome_price'] = round(day6_open, 2)
        shadow['pnl_pct']       = pnl_pct
        shadow['day6_source']   = day6_source
        shadow['resolved_at']   = datetime.utcnow().isoformat() + 'Z'

        print(f"[contra] {sym} ({shadow_id}) → "
              f"{outcome} {pnl_pct:+.2f}% "
              f"(inverted {original_dir}→{inverted_dir})")

        resolved_count += 1
        updates += 1

    if skipped_fields > 0:
        print(f"[contra] Skipped {skipped_fields} shadows "
              f"due to missing fields (check writer schema)")

    if updates > 0:
        data['shadows']    = shadows
        data['updated_at'] = datetime.utcnow().isoformat() + 'Z'

        total_resolved = sum(
            1 for s in shadows
            if s.get('outcome') is not None
            and s.get('outcome') != 'OPEN')
        wins = sum(
            1 for s in shadows
            if s.get('outcome') == 'CONTRA_WIN')

        tmp = CONTRA_SHADOW_FILE + '.tmp'
        try:
            with open(tmp, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp, CONTRA_SHADOW_FILE)
            print(f"[contra] Saved — resolved this run: "
                  f"{resolved_count}. Total resolved: "
                  f"{total_resolved} (wins: {wins})")
        except Exception as e:
            print(f"[contra] Save failed: {e}")
    else:
        print("[contra] No updates")


# ── MAIN FUNCTION ─────────────────────────────────────

def run_outcome_evaluation():
    print("[outcome] Starting evaluation (v4 - CRIT-02 schema adapter)...")

    holidays = _load_holidays()
    if not holidays:
        print("[outcome] Warning — no holidays loaded")

    # CRIT-02: _load_eod_prices now returns nested dict
    # via schema adapter. Always {symbol:{date:{ohlc}}}.
    eod_prices  = _load_eod_prices()
    open_prices = _load_open_prices()
    print(f"[outcome] eod_prices ready: "
          f"{len(eod_prices)} symbols (post-adapter)")

    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[outcome] Cannot load history: {e}")
        return

    history = data.get('history', [])

    open_signals = [
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result') == 'PENDING'
        and s.get('entry_valid') is not False
        and s.get('outcome', 'OPEN') not in _TERMINAL_OUTCOMES
    ]

    invalid_skipped = len([
        s for s in history
        if s.get('outcome', 'OPEN') == 'OPEN'
        and s.get('result') == 'PENDING'
        and s.get('entry_valid') is False
    ])
    if invalid_skipped > 0:
        print(f"[outcome] Skipping {invalid_skipped} signals "
              f"with entry_valid=False")

    if not open_signals:
        print("[outcome] No open signals")
        try:
            _resolve_contra_shadows(
                holidays, eod_prices, open_prices)
        except Exception as e:
            print(f"[contra] Non-fatal error: {e}")
        return

    print(f"[outcome] Evaluating {len(open_signals)} signals...")

    resolved      = 0
    updated       = 0
    sa_propagated = 0
    source_counts = {'eod_primary': 0,
                     'yfinance_primary': 0,
                     'recovery_close_fallback': 0,
                     'no_data': 0}

    history_map = {s.get('id'): i for i, s in enumerate(history)}

    for signal in open_signals:
        sig_id = signal.get('id', '')
        before = signal.get('outcome', 'OPEN')

        updated_sig = _evaluate_signal(
            signal.copy(), holidays, eod_prices, open_prices)

        after = updated_sig.get('outcome', 'OPEN')

        src = updated_sig.get('data_quality_resolve')
        if src in source_counts:
            source_counts[src] += 1

        if sig_id in history_map:
            idx = history_map[sig_id]
            history[idx] = updated_sig
            updated += 1

            if after != 'OPEN' and before == 'OPEN':
                resolved += 1

                if after == 'TARGET_HIT':
                    history[idx]['result'] = 'WON'
                elif after == 'STOP_HIT':
                    history[idx]['result'] = 'STOPPED'
                elif after in ('DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT'):
                    history[idx]['result'] = 'EXITED'

                n = _propagate_sa_outcome(history, sig_id, after)
                sa_propagated += n

    if updated > 0:
        data['history'] = history
        _backup_history()
        try:
            _save_json(HISTORY_FILE, data)
            print(f"[outcome] Done — resolved:{resolved} "
                  f"updated:{updated} sa_propagated:{sa_propagated}")
            print(f"[outcome] Sources: {source_counts}")
        except Exception as e:
            print(f"[outcome] Save failed: {e}")
    else:
        print("[outcome] No updates needed")

    try:
        _resolve_contra_shadows(
            holidays, eod_prices, open_prices)
    except Exception as e:
        print(f"[contra] Non-fatal error: {e}")


if __name__ == '__main__':
    run_outcome_evaluation()
