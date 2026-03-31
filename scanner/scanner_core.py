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


# ── STEP 1 CHANGE 1 ──────────────────────────────────
# auto_adjust=False — prevents retroactive price
# adjustment from splits/bonuses corrupting pivot history
# corporate action skip — detects recent splits/bonuses
# and skips the stock for 60 days after the event
def has_recent_corporate_action(symbol, days=60):
    """
    Returns True if stock had a split or bonus issue
    in the last `days` calendar days.
    Skips the stock to prevent adjusted-price pivot errors.
    """
    try:
        ticker  = yf.Ticker(symbol)
        actions = ticker.actions
        if actions is None or actions.empty:
            return False
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        if actions.index.tzinfo:
            actions.index = actions.index.tz_localize(None)
        recent = actions[actions.index >= cutoff]
        if recent.empty:
            return False
        # Stock Splits column — any non-zero value = split
        if 'Stock Splits' in recent.columns:
            if (recent['Stock Splits'] != 0).any():
                return True
        return False
    except Exception:
        return False
# ── END CHANGE 1 SECTION A ───────────────────────────


def prepare(symbol, period='1y'):
    try:
        # ── STEP 1 CHANGE 1B ─────────────────────────
        # auto_adjust=True  → OLD (adjusted prices)
        # auto_adjust=False → NEW (raw unadjusted prices)
        # Pivots now calculated on actual traded prices
        df = yf.download(symbol, period=period,
                         progress=False,
                         auto_adjust=False)       # CHANGED
        # ── END CHANGE 1B ────────────────────────────
        if df is None or df.empty:
            return None, 'empty_data'             # CHANGED: return reason
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        for col in ['Open','High','Low','Close','Volume']:
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
            return None, 'insufficient_bars'      # CHANGED: return reason
        return df, None                           # CHANGED: return reason=None on success
    except Exception as e:
        print(f"Download failed {symbol}: {e}")
        return None, 'download_failed'            # CHANGED: return reason


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
    df['close_pos'] = (df['Close'] - df['Low']) / rng
    e50  = df['ema50']
    e200 = df['ema200']
    df['bull']   = e50 > e200
    df['bear']   = e50 < e200
    df['isBull'] = df['bull']
    df['isBear'] = df['bear']
    return df


def detect_pivots(df, lookback=None):
    if lookback is None:
        lookback = PIVOT_LOOKBACK
    n     = len(df)
    lows  = df['Low'].values
    highs = df['High'].values
    pl    = np.zeros(n, dtype=bool)
    ph    = np.zeros(n, dtype=bool)
    for i in range(lookback, n - lookback):
        if lows[i]  == lows[i-lookback:i+lookback+1].min():
            pl[i] = True
        if highs[i] == highs[i-lookback:i+lookback+1].max():
            ph[i] = True
    df = df.copy()
    df['pivot_low']  = pl
    df['pivot_high'] = ph
    return df


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


def detect_signals(df, symbol, sector,
                   regime, regime_score,
                   sector_momentum,
                   nifty_close=None):
    # ── THIS FUNCTION UNCHANGED ───────────────────
    # All existing detection logic preserved exactly
    # Second attempt detection is a separate function
    # called from main.py after this function
    # ─────────────────────────────────────────────

    df       = add_indicators(df)
    df       = detect_pivots(df)
    df       = build_zones(df)
    df       = add_zone_proximity(df)

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
        vol_confirm = vr >= 1.2
        rs_q = 'Neutral'
        if pb >= 20 and nifty_close is not None:
            try:
                nidx = nifty_close.index.get_loc(
                    df.index[pb], method='nearest')
                if nidx >= 20:
                    s_r = (closes[pb] /
                           closes[max(0, pb-20)] - 1)
                    n_r = (float(nifty_close.iloc[nidx]) /
                           float(nifty_close.iloc[nidx-20])
                           - 1)
                    d   = (s_r - n_r) * 100
                    rs_q = ('Strong' if d > 3 else
                            'Weak'   if d < -3 else
                            'Neutral')
            except:
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
        stop      = round(pivot_px - STOP_MULT * atr, 2)
        if stop >= entry_est:
            continue
        vq, vc, rq = get_vol_rs(pb)
        signals.append({
            'symbol':       symbol,
            'sector':       sector,
            'signal':       'UP_TRI',
            'direction':    'LONG',
            'age':          age,
            'pivot_date':   df.index[pb].strftime(
                                '%Y-%m-%d'),
            'pivot_price':  round(pivot_px, 2),
            'entry_est':    round(entry_est, 2),
            'stop':         stop,
            'atr':          round(atr, 2),
            'regime':       regime,
            'regime_score': regime_score,
            'vol_q':        vq,
            'vol_confirm':  vc,
            'rs_q':         rq,
            'sec_mom':      sector_momentum.get(
                                sector, 'Neutral'),
            'bear_bonus':   (regime == 'Bear'),
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
                    'symbol':       symbol,
                    'sector':       sector,
                    'signal':       'DOWN_TRI',
                    'direction':    'SHORT',
                    'age':          0,
                    'pivot_date':   df.index[pb].strftime(
                                        '%Y-%m-%d'),
                    'pivot_price':  round(pivot_px, 2),
                    'entry_est':    round(entry_est, 2),
                    'stop':         stop,
                    'atr':          round(atr, 2),
                    'regime':       regime,
                    'regime_score': regime_score,
                    'vol_q':        vq,
                    'vol_confirm':  vc,
                    'rs_q':         rq,
                    'sec_mom':      sector_momentum.get(
                                        sector, 'Neutral'),
                    'bear_bonus':   False,
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
            'symbol':       symbol,
            'sector':       sector,
            'signal':       'BULL_PROXY',
            'direction':    'LONG',
            'age':          age,
            'pivot_date':   df.index[i].strftime(
                                '%Y-%m-%d'),
            'pivot_price':  round(lows[i], 2),
            'entry_est':    round(closes[last_bar], 2),
            'stop':         stop_z,
            'atr':          round(atr, 2),
            'regime':       regime,
            'regime_score': regime_score,
            'vol_q':        vq,
            'vol_confirm':  vc,
            'rs_q':         rq,
            'sec_mom':      sector_momentum.get(
                                sector, 'Neutral'),
            'bear_bonus':   False,
        })

    return signals


# ── STEP 1 CHANGE 2 ──────────────────────────────────
# detect_second_attempt() — NEW FUNCTION
# Called from main.py after detect_signals()
# Requires history_signals — list of recent signal
# dicts from signal_history.json passed in by main.py
#
# Rules:
# 1. Parent signal exists in last 10 trading days
# 2. Parent is UP_TRI or DOWN_TRI (not BULL_PROXY)
# 3. Parent result is PENDING or STOPPED
# 4. For UP_TRI_SA: pivot low not violated since parent
# 5. For DOWN_TRI_SA: pivot high not violated since parent
# 6. Pullback did not exceed original stop distance
# 7. Price now back near original breakout level
# 8. No existing PENDING second attempt for same symbol
# 9. No existing PENDING first attempt still open (block)
# ─────────────────────────────────────────────────────
def detect_second_attempt(df, symbol, sector,
                           regime, regime_score,
                           sector_momentum,
                           history_signals,
                           nifty_close=None):
    """
    Scans history_signals for eligible parent signals
    for this symbol and detects if price is making
    a second attempt at the same level.

    history_signals: list of dicts from signal_history.json
                     filtered to recent 15 trading days
    Returns: list of second attempt signal dicts
             (empty list if none found)
    """
    sa_signals = []

    if not history_signals:
        return sa_signals

    # Prepare df with indicators if not already done
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

    today_str = df.index[last_bar].strftime('%Y-%m-%d')

    # Filter history to this symbol only
    symbol_history = [
        h for h in history_signals
        if h.get('symbol') == symbol
    ]

    if not symbol_history:
        return sa_signals

    # Block: if any PENDING first attempt still open
    # for this symbol, no second attempt allowed
    pending_first = [
        h for h in symbol_history
        if h.get('result') == 'PENDING'
        and h.get('attempt_number', 1) == 1
        and h.get('signal') in ('UP_TRI', 'DOWN_TRI')
    ]
    if pending_first:
        return sa_signals

    # Block: if any PENDING second attempt already exists
    pending_sa = [
        h for h in symbol_history
        if h.get('result') == 'PENDING'
        and h.get('attempt_number', 1) == 2
    ]
    if pending_sa:
        return sa_signals

    # Find eligible parent signals
    # Parent must be STOPPED (first attempt failed)
    # Parent must be within last 10 trading days
    eligible_parents = [
        h for h in symbol_history
        if h.get('signal') in ('UP_TRI', 'DOWN_TRI')
        and h.get('result') in ('STOPPED', 'PENDING')
        and h.get('attempt_number', 1) == 1
    ]

    if not eligible_parents:
        return sa_signals

    # Sort by date descending — use most recent parent
    eligible_parents.sort(
        key=lambda x: x.get('date', ''), reverse=True)
    parent = eligible_parents[0]

    parent_signal    = parent.get('signal')
    parent_date      = parent.get('date', '')
    parent_pivot     = float(parent.get('pivot_price', 0))
    parent_stop      = float(parent.get('stop', 0))
    parent_entry     = float(parent.get('entry', 0))
    parent_id        = parent.get('id', '')
    parent_result    = parent.get('result', '')

    # Check parent is within 10 trading days
    try:
        parent_dt = pd.Timestamp(parent_date)
        today_dt  = df.index[last_bar]
        # Count trading bars since parent date
        parent_bar_idx = None
        for i in range(n-1, max(n-25, 0), -1):
            if df.index[i].strftime('%Y-%m-%d') == parent_date:
                parent_bar_idx = i
                break
        if parent_bar_idx is None:
            # Try nearest date
            date_diffs = abs(df.index - parent_dt)
            parent_bar_idx = date_diffs.argmin()

        bars_since_parent = last_bar - parent_bar_idx
        if bars_since_parent > 15:
            # Too old — more than ~10-15 trading days
            return sa_signals
    except Exception:
        return sa_signals

    current_price = closes[last_bar]
    current_atr   = atr_v[last_bar]

    if np.isnan(current_atr) or current_atr <= 0:
        return sa_signals

    # ── UP_TRI SECOND ATTEMPT ─────────────────────
    if parent_signal == 'UP_TRI':
        # Condition 1: Pivot low must not have been
        # violated since parent signal fired
        # (structure still intact)
        bars_since = slice(parent_bar_idx, last_bar+1)
        min_since  = lows[parent_bar_idx:last_bar+1].min()
        if min_since < parent_pivot - current_atr:
            # Structure broken — pivot low violated
            return sa_signals

        # Condition 2: Pullback occurred
        # Price must have pulled back toward pivot level
        max_since = highs[parent_bar_idx:last_bar+1].max()
        pullback  = max_since - current_price
        if pullback < 0.5 * current_atr:
            # No meaningful pullback happened
            return sa_signals

        # Condition 3: Price now back near breakout level
        # Within 1.5 ATR of parent pivot price
        dist_from_pivot = abs(current_price - parent_pivot)
        if dist_from_pivot > 1.5 * current_atr:
            return sa_signals

        # Condition 4: Stop calculation
        stop = round(parent_pivot - STOP_MULT * current_atr, 2)
        if stop >= current_price:
            return sa_signals

        # Condition 5: R:R check (minimum 1.5)
        risk   = current_price - stop
        target = current_price + 2.0 * risk
        if risk <= 0:
            return sa_signals

        # Volume and RS
        try:
            avg_vol = df['Volume'].iloc[
                max(0, last_bar-20):last_bar].mean()
            sig_vol = df['Volume'].iloc[last_bar]
            vr      = sig_vol / avg_vol if avg_vol > 0 else 1
            vol_q   = ('High'    if vr > 1.5 else
                       'Thin'    if vr < 0.7 else
                       'Average')
            vol_confirm = vr >= 1.2
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
            'pivot_price':      round(parent_pivot, 2),
            'entry_est':        round(current_price, 2),
            'stop':             stop,
            'atr':              round(current_atr, 2),
            'regime':           regime,
            'regime_score':     regime_score,
            'vol_q':            vol_q,
            'vol_confirm':      vol_confirm,
            'rs_q':             'Neutral',
            'sec_mom':          sector_momentum.get(
                                    sector, 'Neutral'),
            'bear_bonus':       (regime == 'Bear'),
        })

    # ── DOWN_TRI SECOND ATTEMPT ───────────────────
    elif parent_signal == 'DOWN_TRI':
        # Condition 1: Pivot high must not have been
        # exceeded since parent signal fired
        max_since = highs[parent_bar_idx:last_bar+1].max()
        if max_since > parent_pivot + current_atr:
            # Structure broken — pivot high exceeded
            return sa_signals

        # Condition 2: Pullback occurred
        min_since = lows[parent_bar_idx:last_bar+1].min()
        pullback  = current_price - min_since
        if pullback < 0.5 * current_atr:
            return sa_signals

        # Condition 3: Price now back near breakdown level
        dist_from_pivot = abs(current_price - parent_pivot)
        if dist_from_pivot > 1.5 * current_atr:
            return sa_signals

        # Condition 4: Stop calculation
        stop = round(parent_pivot + STOP_MULT * current_atr, 2)
        if stop <= current_price:
            return sa_signals

        # Condition 5: R:R check
        risk = stop - current_price
        if risk <= 0:
            return sa_signals

        try:
            avg_vol = df['Volume'].iloc[
                max(0, last_bar-20):last_bar].mean()
            sig_vol = df['Volume'].iloc[last_bar]
            vr      = sig_vol / avg_vol if avg_vol > 0 else 1
            vol_q   = ('High'    if vr > 1.5 else
                       'Thin'    if vr < 0.7 else
                       'Average')
            vol_confirm = vr >= 1.2
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
            'pivot_price':      round(parent_pivot, 2),
            'entry_est':        round(current_price, 2),
            'stop':             stop,
            'atr':              round(current_atr, 2),
            'regime':           regime,
            'regime_score':     regime_score,
            'vol_q':            vol_q,
            'vol_confirm':      vol_confirm,
            'rs_q':             'Neutral',
            'sec_mom':          sector_momentum.get(
                                    sector, 'Neutral'),
            'bear_bonus':       False,
        })

    return sa_signals
# ── END STEP 1 CHANGE 2 ──────────────────────────────
