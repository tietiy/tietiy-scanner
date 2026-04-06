# ── scanner_core.py ──────────────────────────────────
# Signal detection engine
# Detects UP_TRI, DOWN_TRI, BULL_PROXY, SA signals
#
# ADDED: _get_stock_regime() for individual stock regime
#        stock_regime field on every signal dict
# S3 FIX: vol_confirm cast to bool() — prevents numpy
#         bool_ being serialised as string "True"/"False"
# ─────────────────────────────────────────────────────

import numpy as np
import pandas as pd
import yfinance as yf
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    PIVOT_LOOKBACK, ATR_PERIOD, EMA_FAST, EMA_MID,
    EMA_SLOW, ZONE_ATR, SMC_COOLDOWN, STOP_MULT,
    BP_CLOSE_POS_MIN, BP_LOWER_WICK_MIN,
)

ZONE_PROXIMITY_ATR = ZONE_ATR


# ── CORPORATE ACTION CHECK ────────────────────────────

def has_recent_corporate_action(symbol, days=60):
    try:
        ticker  = yf.Ticker(symbol)
        actions = ticker.actions
        if actions is None or actions.empty:
            return False
        cutoff = pd.Timestamp.now() - \
                 pd.Timedelta(days=days)
        if actions.index.tzinfo:
            actions.index = \
                actions.index.tz_localize(None)
        recent = actions[actions.index >= cutoff]
        if recent.empty:
            return False
        if 'Stock Splits' in recent.columns:
            if (recent['Stock Splits'] != 0).any():
                return True
        return False
    except Exception:
        return False


# ── DATA FETCH ────────────────────────────────────────

def prepare(symbol, period='1y'):
    try:
        df = yf.download(
            symbol, period=period,
            progress=False,
            auto_adjust=False)
        if df is None or df.empty:
            return None, 'empty_data'
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        for col in ['Open','High','Low',
                    'Close','Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col], errors='coerce')
        df.index = pd.to_datetime(
            df.index, errors='coerce')
        if df.index.tzinfo:
            df.index = df.index.tz_localize(None)
        df = df[df.index.notna()]
        df.dropna(subset=['Close'], inplace=True)
        if len(df) < 60:
            return None, 'insufficient_bars'
        return df, None
    except Exception as e:
        print(f"Download failed {symbol}: {e}")
        return None, 'download_failed'


# ── INDICATORS ────────────────────────────────────────

def add_indicators(df):
    df = df.copy()
    df['ema20']  = df['Close'].ewm(
        span=EMA_FAST,  adjust=False).mean()
    df['ema50']  = df['Close'].ewm(
        span=EMA_MID,   adjust=False).mean()
    df['ema200'] = df['Close'].ewm(
        span=EMA_SLOW,  adjust=False).mean()
    pc  = df['Close'].shift(1)
    tr  = pd.concat([
        df['High'] - df['Low'],
        (df['High'] - pc).abs(),
        (df['Low']  - pc).abs(),
    ], axis=1).max(axis=1)
    df['atr']    = tr.ewm(
        span=ATR_PERIOD, adjust=False).mean()
    df['atrS']   = df['atr'].clip(lower=1e-6)
    df['vavg20'] = df['Volume'].rolling(20).mean()
    rng = (df['High'] - df['Low']).clip(lower=1e-6)
    df['bar_range'] = rng
    df['close_pos'] = (
        df['Close'] - df['Low']) / rng
    e50  = df['ema50']
    e200 = df['ema200']
    df['bull']   = e50 > e200
    df['bear']   = e50 < e200
    df['isBull'] = df['bull']
    df['isBear'] = df['bear']
    return df


# ── INDIVIDUAL STOCK REGIME ───────────────────────────

def _get_stock_regime(df):
    try:
        closes     = df['Close']
        ema50      = closes.ewm(span=50).mean()
        slope      = ema50.diff(10) / ema50.shift(10)
        above      = closes > ema50
        last_slope = float(slope.iloc[-1])
        last_above = bool(above.iloc[-1])

        if last_slope > 0.005 and last_above:
            return 'Bull'
        elif last_slope < -0.005 and not last_above:
            return 'Bear'
        else:
            return 'Choppy'
    except Exception:
        return 'Choppy'


# ── PIVOT DETECTION ───────────────────────────────────

def detect_pivots(df, lookback=None):
    if lookback is None:
        lookback = PIVOT_LOOKBACK
    n     = len(df)
    lows  = df['Low'].values
    highs = df['High'].values
    pl    = np.zeros(n, dtype=bool)
    ph    = np.zeros(n, dtype=bool)
    for i in range(lookback, n - lookback):
        if lows[i] == \
                lows[i-lookback:i+lookback+1].min():
            pl[i] = True
        if highs[i] == \
                highs[i-lookback:i+lookback+1].max():
            ph[i] = True
    df = df.copy()
    df['pivot_low']  = pl
    df['pivot_high'] = ph
    return df


# ── ZONE BUILDER ──────────────────────────────────────

def build_zones(df):
    n      = len(df)
    close  = df['Close'].values
    high   = df['High'].values
    low    = df['Low'].values
    atrS   = df['atrS'].values
    isBull = df['isBull'].values
    isBear = df['isBear'].values
    pl     = df['pivot_low'].values
    ph     = df['pivot_high'].values
    szH    = np.full(n, np.nan)
    szL    = np.full(n, np.nan)
    rzH    = np.full(n, np.nan)
    rzL    = np.full(n, np.nan)
    sB     = np.zeros(n, dtype=bool)
    sp = np.nan; sb_ = -999
    rp = np.nan; rb_ = -999
    for i in range(n):
        atr = atrS[i]
        if pl[i]:
            nl = low[i]
            if (np.isnan(sp) or nl > sp or
                    (i - sb_) > 120):
                sp = nl; sb_ = i
        if ph[i]:
            nh = high[i]
            if np.isnan(rp) or (i - rb_) > 120:
                rp = nh; rb_ = i
            elif isBull[i] and nh > rp:
                rp = nh; rb_ = i
            elif isBear[i] and nh < rp:
                rp = nh; rb_ = i
        if not np.isnan(sp):
            szH[i] = sp + 0.5 * atr
            szL[i] = sp - 0.1 * atr
        if not np.isnan(rp):
            rzH[i] = rp + 0.1 * atr
            rzL[i] = rp - 0.5 * atr
        if not np.isnan(szH[i]):
            sB[i] = (close[i] - szH[i]) / atr < -0.5
    df = df.copy()
    df['szH'] = szH; df['szL'] = szL
    df['rzH'] = rzH; df['rzL'] = rzL
    df['sBroken'] = sB
    return df


# ── ZONE PROXIMITY ────────────────────────────────────

def add_zone_proximity(df):
    atr = df['atrS']
    df['nearSZ'] = (
        ~df['sBroken'] & ~df['isBear'] & (
            ((df['Low']  <= df['szH']) &
             (df['High'] >= df['szL'])) |
            ((df['Low'] - df['szH']).abs()
             <= atr * ZONE_PROXIMITY_ATR)
        )
    )
    return df


# ── SIGNAL DETECTION ──────────────────────────────────

def detect_signals(df, symbol, sector,
                   regime, regime_score,
                   sector_momentum,
                   nifty_close=None):

    df           = add_indicators(df)
    df           = detect_pivots(df)
    df           = build_zones(df)
    df           = add_zone_proximity(df)
    stock_regime = _get_stock_regime(df)

    n        = len(df)
    last_bar = n - 1
    closes   = df['Close'].values
    opens    = df['Open'].values
    highs    = df['High'].values
    lows     = df['Low'].values
    atr_v    = df['atrS'].values
    ema50v   = df['ema50'].values
    pl_v     = df['pivot_low'].values
    ph_v     = df['pivot_high'].values
    szL_v    = df['szL'].values
    nSZ_v    = df['nearSZ'].values
    signals  = []

    LB = PIVOT_LOOKBACK

    def get_vol_rs(pb):
        avg_vol = df['Volume'].iloc[
            max(0, pb-20):pb].mean()
        sig_vol = df['Volume'].iloc[pb]
        vr      = sig_vol / avg_vol \
                  if avg_vol > 0 else 1
        vol_q   = ('High'    if vr > 1.5 else
                   'Thin'    if vr < 0.7 else
                   'Average')
        # ── S3 FIX: cast to bool() ────────────────
        vol_confirm = bool(vr >= 1.2)
        rs_q = 'Neutral'
        if pb >= 20 and nifty_close is not None:
            try:
                nidx = nifty_close.index.get_loc(
                    df.index[pb], method='nearest')
                if nidx >= 20:
                    s_r = (closes[pb] /
                           closes[max(0, pb-20)] - 1)
                    n_r = (
                        float(nifty_close.iloc[nidx]) /
                        float(nifty_close.iloc[nidx-20])
                        - 1)
                    d   = (s_r - n_r) * 100
                    rs_q = ('Strong' if d > 3 else
                            'Weak'   if d < -3 else
                            'Neutral')
            except Exception:
                pass
        return vol_q, vol_confirm, rs_q

    # ── UP TRIANGLE — ages 0-3 ────────────────────
    for age in range(0, 4):
        pb = last_bar - age - LB
        if pb < LB or pb >= n:
            continue
        if not pl_v[pb]:
            continue
        atr = atr_v[pb]
        if np.isnan(atr) or atr <= 0:
            continue
        pivot_px  = lows[pb]
        entry_est = closes[last_bar]
        stop      = round(
            pivot_px - STOP_MULT * atr, 2)
        if stop >= entry_est:
            continue
        vq, vc, rq = get_vol_rs(pb)
        signals.append({
            'symbol':        symbol,
            'sector':        sector,
            'signal':        'UP_TRI',
            'direction':     'LONG',
            'age':           age,
            'pivot_date':    df.index[pb].strftime(
                                 '%Y-%m-%d'),
            'pivot_price':   round(pivot_px, 2),
            'entry_est':     round(entry_est, 2),
            'stop':          stop,
            'atr':           round(atr, 2),
            'regime':        regime,
            'regime_score':  regime_score,
            'vol_q':         vq,
            'vol_confirm':   vc,
            'rs_q':          rq,
            'sec_mom':       sector_momentum.get(
                                 sector, 'Neutral'),
            'bear_bonus':    bool(regime == 'Bear'),
            'stock_regime':  stock_regime,
        })

    # ── DOWN TRIANGLE — age 0 only ────────────────
    pb = last_bar - 0 - LB
    if LB <= pb < n and ph_v[pb]:
        atr = atr_v[pb]
        if not (np.isnan(atr) or atr <= 0):
            pivot_px  = highs[pb]
            entry_est = closes[last_bar]
            stop      = round(
                pivot_px + STOP_MULT * atr, 2)
            if stop > entry_est:
                vq, vc, rq = get_vol_rs(pb)
                signals.append({
                    'symbol':        symbol,
                    'sector':        sector,
                    'signal':        'DOWN_TRI',
                    'direction':     'SHORT',
                    'age':           0,
                    'pivot_date':    df.index[pb]
                                     .strftime(
                                         '%Y-%m-%d'),
                    'pivot_price':   round(
                                         pivot_px, 2),
                    'entry_est':     round(
                                         entry_est, 2),
                    'stop':          stop,
                    'atr':           round(atr, 2),
                    'regime':        regime,
                    'regime_score':  regime_score,
                    'vol_q':         vq,
                    'vol_confirm':   vc,
                    'rs_q':          rq,
                    'sec_mom':       sector_momentum
                                     .get(sector,
                                          'Neutral'),
                    'bear_bonus':    False,
                    'stock_regime':  stock_regime,
                })

    # ── BULL PROXY — ages 0-1, trend required ─────
    bp_last = -999
    for i in range(max(LB, n-20), n):
        atr = atr_v[i]
        if np.isnan(atr) or atr <= 0:
            continue
        if closes[i] < ema50v[i]:
            continue
        if (i - bp_last) <= SMC_COOLDOWN:
            continue
        if not nSZ_v[i]:
            continue
        br = highs[i] - lows[i]
        if br < 1e-6:
            continue
        cpos  = (closes[i] - lows[i]) / br
        lwick = (min(opens[i], closes[i])
                 - lows[i]) / br
        if not (cpos  >= BP_CLOSE_POS_MIN and
                lwick >= BP_LOWER_WICK_MIN and
                closes[i] > opens[i]):
            continue
        bp_last = i
        age     = last_bar - i
        if age > 1:
            continue
        stop_z = (szL_v[i] - 0.5 * atr
                  if not np.isnan(szL_v[i])
                  else lows[i] - atr)
        stop_z = round(stop_z, 2)
        if stop_z >= closes[last_bar]:
            continue
        vq, vc, rq = get_vol_rs(i)
        signals.append({
            'symbol':        symbol,
            'sector':        sector,
            'signal':        'BULL_PROXY',
            'direction':     'LONG',
            'age':           age,
            'pivot_date':    df.index[i].strftime(
                                 '%Y-%m-%d'),
            'pivot_price':   round(lows[i], 2),
            'entry_est':     round(
                                 closes[last_bar], 2),
            'stop':          stop_z,
            'atr':           round(atr, 2),
            'regime':        regime,
            'regime_score':  regime_score,
            'vol_q':         vq,
            'vol_confirm':   vc,
            'rs_q':          rq,
            'sec_mom':       sector_momentum.get(
                                 sector, 'Neutral'),
            'bear_bonus':    False,
            'stock_regime':  stock_regime,
        })

    return signals


# ── SECOND ATTEMPT DETECTION ──────────────────────────

def detect_second_attempt(df, symbol, sector,
                           regime, regime_score,
                           sector_momentum,
                           history_signals,
                           nifty_close=None):
    sa_signals = []

    if not history_signals:
        return sa_signals

    if 'atrS' not in df.columns:
        df = add_indicators(df)
        df = detect_pivots(df)

    n        = len(df)
    last_bar = n - 1
    closes   = df['Close'].values
    highs    = df['High'].values
    lows     = df['Low'].values
    atr_v    = df['atrS'].values
    LB       = PIVOT_LOOKBACK

    stock_regime = _get_stock_regime(df)
    today_str    = df.index[last_bar].strftime(
        '%Y-%m-%d')

    symbol_history = [
        h for h in history_signals
        if h.get('symbol') == symbol
    ]

    if not symbol_history:
        return sa_signals

    pending_first = [
        h for h in symbol_history
        if h.get('result') == 'PENDING'
        and h.get('attempt_number', 1) == 1
        and h.get('signal') in (
            'UP_TRI', 'DOWN_TRI')
    ]
    if pending_first:
        return sa_signals

    pending_sa = [
        h for h in symbol_history
        if h.get('result') == 'PENDING'
        and h.get('attempt_number', 1) == 2
    ]
    if pending_sa:
        return sa_signals

    eligible_parents = [
        h for h in symbol_history
        if h.get('signal') in (
            'UP_TRI', 'DOWN_TRI')
        and h.get('result') in (
            'STOPPED', 'PENDING')
        and h.get('attempt_number', 1) == 1
    ]

    if not eligible_parents:
        return sa_signals

    eligible_parents.sort(
        key=lambda x: x.get('date', ''),
        reverse=True)
    parent = eligible_parents[0]

    parent_signal = parent.get('signal')
    parent_date   = parent.get('date', '')
    parent_pivot  = float(
        parent.get('pivot_price', 0))
    parent_stop   = float(
        parent.get('stop', 0))
    parent_entry  = float(
        parent.get('entry', 0))
    parent_id     = parent.get('id', '')
    parent_result = parent.get('result', '')

    try:
        parent_dt      = pd.Timestamp(parent_date)
        parent_bar_idx = None

        for i in range(n-1, max(n-25, 0), -1):
            if df.index[i].strftime(
                    '%Y-%m-%d') == parent_date:
                parent_bar_idx = i
                break

        if parent_bar_idx is None:
            date_diffs     = abs(df.index - parent_dt)
            parent_bar_idx = date_diffs.argmin()

        bars_since_parent = last_bar - parent_bar_idx
        if bars_since_parent > 15:
            return sa_signals

    except Exception:
        return sa_signals

    current_price = closes[last_bar]
    current_atr   = atr_v[last_bar]

    if np.isnan(current_atr) or current_atr <= 0:
        return sa_signals

    # ── UP_TRI SECOND ATTEMPT ─────────────────────
    if parent_signal == 'UP_TRI':

        min_since = lows[
            parent_bar_idx:last_bar+1].min()
        if min_since < parent_pivot - current_atr:
            return sa_signals

        max_since = highs[
            parent_bar_idx:last_bar+1].max()
        pullback  = max_since - current_price
        if pullback < 0.5 * current_atr:
            return sa_signals

        dist_from_pivot = abs(
            current_price - parent_pivot)
        if dist_from_pivot > 1.5 * current_atr:
            return sa_signals

        stop = round(
            parent_pivot - STOP_MULT * current_atr,
            2)
        if stop >= current_price:
            return sa_signals

        risk = current_price - stop
        if risk <= 0:
            return sa_signals

        try:
            avg_vol = df['Volume'].iloc[
                max(0, last_bar-20):last_bar].mean()
            sig_vol = df['Volume'].iloc[last_bar]
            vr      = sig_vol / avg_vol \
                      if avg_vol > 0 else 1
            vol_q   = ('High'    if vr > 1.5 else
                       'Thin'    if vr < 0.7 else
                       'Average')
            # ── S3 FIX: cast to bool() ────────────
            vol_confirm = bool(vr >= 1.2)
        except Exception:
            vol_q       = 'Average'
            vol_confirm = False

        sa_signals.append({
            'symbol':           symbol,
            'sector':           sector,
            'signal':           'UP_TRI_SA',
            'direction':        'LONG',
            'age':              0,
            'attempt_number':   2,
            'parent_signal_id': parent_id,
            'parent_signal':    'UP_TRI',
            'parent_date':      parent_date,
            'parent_result':    parent_result,
            'pivot_date':       parent_date,
            'pivot_price':      round(
                                    parent_pivot, 2),
            'entry_est':        round(
                                    current_price, 2),
            'stop':             stop,
            'atr':              round(
                                    current_atr, 2),
            'regime':           regime,
            'regime_score':     regime_score,
            'vol_q':            vol_q,
            'vol_confirm':      vol_confirm,
            'rs_q':             'Neutral',
            'sec_mom':          sector_momentum.get(
                                    sector, 'Neutral'),
            'bear_bonus':       bool(regime == 'Bear'),
            'stock_regime':     stock_regime,
        })

    # ── DOWN_TRI SECOND ATTEMPT ───────────────────
    elif parent_signal == 'DOWN_TRI':

        max_since = highs[
            parent_bar_idx:last_bar+1].max()
        if max_since > parent_pivot + current_atr:
            return sa_signals

        min_since = lows[
            parent_bar_idx:last_bar+1].min()
        pullback  = current_price - min_since
        if pullback < 0.5 * current_atr:
            return sa_signals

        dist_from_pivot = abs(
            current_price - parent_pivot)
        if dist_from_pivot > 1.5 * current_atr:
            return sa_signals

        stop = round(
            parent_pivot + STOP_MULT * current_atr,
            2)
        if stop <= current_price:
            return sa_signals

        risk = stop - current_price
        if risk <= 0:
            return sa_signals

        try:
            avg_vol = df['Volume'].iloc[
                max(0, last_bar-20):last_bar].mean()
            sig_vol = df['Volume'].iloc[last_bar]
            vr      = sig_vol / avg_vol \
                      if avg_vol > 0 else 1
            vol_q   = ('High'    if vr > 1.5 else
                       'Thin'    if vr < 0.7 else
                       'Average')
            # ── S3 FIX: cast to bool() ────────────
            vol_confirm = bool(vr >= 1.2)
        except Exception:
            vol_q       = 'Average'
            vol_confirm = False

        sa_signals.append({
            'symbol':           symbol,
            'sector':           sector,
            'signal':           'DOWN_TRI_SA',
            'direction':        'SHORT',
            'age':              0,
            'attempt_number':   2,
            'parent_signal_id': parent_id,
            'parent_signal':    'DOWN_TRI',
            'parent_date':      parent_date,
            'parent_result':    parent_result,
            'pivot_date':       parent_date,
            'pivot_price':      round(
                                    parent_pivot, 2),
            'entry_est':        round(
                                    current_price, 2),
            'stop':             stop,
            'atr':              round(
                                    current_atr, 2),
            'regime':           regime,
            'regime_score':     regime_score,
            'vol_q':            vol_q,
            'vol_confirm':      vol_confirm,
            'rs_q':             'Neutral',
            'sec_mom':          sector_momentum.get(
                                    sector, 'Neutral'),
            'bear_bonus':       False,
            'stock_regime':     stock_regime,
        })

    return sa_signals
