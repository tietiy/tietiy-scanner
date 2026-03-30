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


def prepare(symbol, period='1y'):
    try:
        df = yf.download(symbol, period=period,
                         progress=False,
                         auto_adjust=True)
        if df is None or df.empty:
            return None
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
        if len(df) < 100:
            return None
        return df
    except Exception as e:
        print(f"Download failed {symbol}: {e}")
        return None


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
    df['atr']   = tr.ewm(
        span=ATR_PERIOD, adjust=False).mean()
    df['atrS']  = df['atr'].clip(lower=1e-6)
    df['vavg20']= df['Volume'].rolling(20).mean()
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

    # UP TRIANGLE — ages 0-3, no EMA50 filter
    for pb in range(max(0, n-15), n-1):
        if not pl_v[pb]:
            continue
        atr = atr_v[pb]
        if np.isnan(atr) or atr <= 0:
            continue
        age = last_bar - pb - 1
        if age > 3:
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

    # DOWN TRIANGLE — age 0 only, all regimes
    for pb in range(max(0, n-15), n-1):
        if not ph_v[pb]:
            continue
        atr = atr_v[pb]
        if np.isnan(atr) or atr <= 0:
            continue
        age = last_bar - pb - 1
        if age != 0:
            continue
        pivot_px  = highs[pb]
        entry_est = closes[last_bar]
        stop      = round(pivot_px + STOP_MULT * atr, 2)
        if stop <= entry_est:
            continue
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

    # BULL PROXY — ages 0-1, trend filter required
    bp_last = -999
    for i in range(max(0, n-15), n):
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
