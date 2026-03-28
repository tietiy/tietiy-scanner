import numpy as np
import pandas as pd
import yfinance as yf
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    PIVOT_LOOKBACK, ATR_PERIOD, EMA_FAST, EMA_MID,
    EMA_SLOW, ZONE_ATR, SMC_COOLDOWN, STOP_MULT,
    BP_CLOSE_POS_MIN, BP_LOWER_WICK_MIN, EXIT_BARS
)

# ── DATA DOWNLOAD ─────────────────────────────────
def download_stock(symbol, period='1y'):
    try:
        df = yf.download(symbol, period=period,
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        for col in ['Open','High','Low','Close','Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.index = pd.to_datetime(df.index, errors='coerce')
        df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
        df = df[df.index.notna()]
        df.dropna(subset=['Close'], inplace=True)
        if len(df) < 100:
            return None
        return df
    except Exception as e:
        print(f"Download failed {symbol}: {e}")
        return None

# ── SCANNER-EXACT INDICATORS ──────────────────────
def add_indicators(df):
    df = df.copy()
    df["ema20"]  = df["Close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema50"]  = df["Close"].ewm(span=EMA_MID,  adjust=False).mean()
    df["ema200"] = df["Close"].ewm(span=EMA_SLOW, adjust=False).mean()
    pc = df["Close"].shift(1)
    tr = pd.concat([
        df["High"]-df["Low"],
        (df["High"]-pc).abs(),
        (df["Low"]-pc).abs()
    ], axis=1).max(axis=1)
    df["atr"]      = tr.ewm(span=ATR_PERIOD, adjust=False).mean()
    df["atrS"]     = df["atr"].clip(lower=1e-6)
    df["vavg20"]   = df["Volume"].rolling(20).mean()
    df["vol_ratio"]= df["Volume"] / df["vavg20"].replace(0, np.nan)
    df["bar_range"]= (df["High"]-df["Low"]).clip(lower=1e-6)
    df["close_pos"]= (df["Close"]-df["Low"]) / df["bar_range"]
    df["body_size"]= (df["Close"]-df["Open"]).abs()
    df["lo20p"]    = df["Low"].shift(1).rolling(20).min()
    df["hi20p"]    = df["High"].shift(1).rolling(20).max()
    s20  = (df["ema20"]-df["ema20"].shift(5))/df["ema20"].shift(5)*100
    e20r = s20 > 0.15
    e20f = s20 < -0.15
    conds = [
        (df["Close"]>df["ema20"])&(df["ema20"]>df["ema50"])&
        (df["ema50"]>df["ema200"])&e20r,
        (df["Close"]>df["ema50"])&(df["ema50"]>df["ema200"]),
        (df["Close"]<df["ema20"])&(df["ema20"]<df["ema50"])&
        (df["ema50"]<df["ema200"])&e20f,
        (df["Close"]<df["ema50"])&(df["ema50"]<df["ema200"]),
    ]
    df["trend"]  = np.select(conds,
        ["Strong Bull","Bull","Strong Bear","Bear"],
        default="Neutral")
    df["isBull"] = df["trend"].isin(["Strong Bull","Bull"])
    df["isBear"] = df["trend"].isin(["Strong Bear","Bear"])
    return df

# ── SCANNER-EXACT PIVOT DETECTION ─────────────────
def detect_pivots(df):
    n  = len(df)
    pl = np.zeros(n, dtype=bool)
    ph = np.zeros(n, dtype=bool)
    lo = df["Low"].values
    hi = df["High"].values
    lb = PIVOT_LOOKBACK
    for i in range(lb, n-lb):
        if (all(lo[i]<=lo[i-j] for j in range(1,lb+1)) and
                all(lo[i]<=lo[i+j] for j in range(1,lb+1))):
            pl[i] = True
        if (all(hi[i]>=hi[i-j] for j in range(1,lb+1)) and
                all(hi[i]>=hi[i+j] for j in range(1,lb+1))):
            ph[i] = True
    df["pivotLow"]  = pl
    df["pivotHigh"] = ph
    return df

# ── SCANNER-EXACT ZONE BUILDER ────────────────────
def build_zones(df):
    n    = len(df)
    szH  = np.full(n, np.nan)
    szL  = np.full(n, np.nan)
    rzH  = np.full(n, np.nan)
    rzL  = np.full(n, np.nan)
    sbrk = np.zeros(n, dtype=bool)
    lo   = df["Low"].values
    hi   = df["High"].values
    cl   = df["Close"].values
    av   = df["atrS"].values
    pl   = df["pivotLow"].values
    ph   = df["pivotHigh"].values
    ib   = df["isBear"].values
    sp   = np.nan; rp = np.nan; rb_ = -999
    for i in range(n):
        if pl[i]: sp = lo[i]
        if ph[i]:
            np_ = hi[i]
            if np.isnan(rp) or (i-rb_)>120:
                rp=np_; rb_=i
            elif ib[i] and np_>rp:
                rp=np_; rb_=i
            elif not ib[i] and np_<rp:
                rp=np_; rb_=i
        if not np.isnan(sp):
            szH[i]=sp+0.5*av[i]
            szL[i]=sp-0.1*av[i]
        if not np.isnan(rp):
            rzH[i]=rp+0.1*av[i]
            rzL[i]=rp-0.5*av[i]
        if not np.isnan(szH[i]):
            sbrk[i]=(cl[i]-szH[i])/av[i]<-0.5
    df["szH"]=szH; df["szL"]=szL
    df["rzH"]=rzH; df["rzL"]=rzL
    df["sBroken"]=sbrk
    return df

# ── SCANNER-EXACT PROXIMITY ───────────────────────
def add_proximity(df):
    a = df["atrS"]
    df["nearSZ"] = (
        ~df["sBroken"] & ~df["isBear"] & (
            ((df["Low"]<=df["szH"]) & (df["High"]>=df["szL"])) |
            ((df["Low"]-df["szH"]).abs() <= a*ZONE_ATR)
        )
    )
    return df

# ── PREPARE STOCK DATA ────────────────────────────
def prepare(symbol, period='1y'):
    df = download_stock(symbol, period)
    if df is None:
        return None
    df = add_indicators(df)
    df = detect_pivots(df)
    df = build_zones(df)
    df = add_proximity(df)
    return df

# ── SIGNAL DETECTION ──────────────────────────────
def detect_signals(df, symbol, sector, regime,
                   regime_score, sector_momentum,
                   nifty_close):
    signals = []
    if df is None or len(df) < 50:
        return signals

    n       = len(df)
    opens   = df['Open'].values
    closes  = df['Close'].values
    highs   = df['High'].values
    lows    = df['Low'].values
    atr_v   = df['atrS'].values
    ema50v  = df['ema50'].values
    pl_v    = df['pivotLow'].values
    ph_v    = df['pivotHigh'].values
    szL_v   = df['szL'].values
    nSZ_v   = df['nearSZ'].values

    last_bar = n - 1

    # ── UP TRI ────────────────────────────────────
    for pb in range(max(0, n-30), n-1):
        if not pl_v[pb]:
            continue
        atr = atr_v[pb]
        if np.isnan(atr) or atr <= 0:
            continue
        age = last_bar - pb - 1
        if age < 0 or age > 3:
            continue
        pivot_px = lows[pb]
        entry_est = closes[last_bar]
        stop      = pivot_px - STOP_MULT * atr

        # Volume quality
        avg_vol = df['Volume'].iloc[max(0,pb-20):pb].mean()
        sig_vol = df['Volume'].iloc[pb]
        vr      = sig_vol/avg_vol if avg_vol>0 else 1
        vol_q   = 'High' if vr>1.5 else ('Thin' if vr<0.7 else 'Average')
        vol_confirm = vr >= 1.2

        # RS vs Nifty
        rs_q = 'Neutral'
        if pb >= 20 and nifty_close is not None:
            try:
                nifty_idx = nifty_close.index.get_loc(
                    df.index[pb], method='nearest')
                if nifty_idx >= 20:
                    s_r = closes[pb]/closes[max(0,pb-20)] - 1
                    n_r = (nifty_close.iloc[nifty_idx] /
                           nifty_close.iloc[nifty_idx-20] - 1)
                    d   = (s_r - n_r) * 100
                    rs_q = ('Strong' if d>3
                            else 'Weak' if d<-3
                            else 'Neutral')
            except:
                pass

        signals.append({
            'symbol':       symbol,
            'sector':       sector,
            'signal':       'UP_TRI',
            'age':          age,
            'pivot_bar':    pb,
            'pivot_date':   df.index[pb].strftime('%Y-%m-%d'),
            'pivot_price':  round(pivot_px, 2),
            'entry_est':    round(entry_est, 2),
            'stop':         round(stop, 2),
            'atr':          round(atr, 2),
            'regime':       regime,
            'regime_score': regime_score,
            'vol_q':        vol_q,
            'vol_confirm':  vol_confirm,
            'rs_q':         rs_q,
            'sec_mom':      sector_momentum.get(sector,'Neutral'),
            'bear_bonus':   (regime == 'Bear'),
        })

    # ── DOWN TRI (age 0 only) ─────────────────────
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
        stop      = pivot_px + STOP_MULT * atr

        avg_vol = df['Volume'].iloc[max(0,pb-20):pb].mean()
        sig_vol = df['Volume'].iloc[pb]
        vr      = sig_vol/avg_vol if avg_vol>0 else 1
        vol_q   = 'High' if vr>1.5 else ('Thin' if vr<0.7 else 'Average')
        vol_confirm = vr >= 1.2

        rs_q = 'Neutral'
        if pb >= 20 and nifty_close is not None:
            try:
                nifty_idx = nifty_close.index.get_loc(
                    df.index[pb], method='nearest')
                if nifty_idx >= 20:
                    s_r = closes[pb]/closes[max(0,pb-20)] - 1
                    n_r = (nifty_close.iloc[nifty_idx] /
                           nifty_close.iloc[nifty_idx-20] - 1)
                    d   = (s_r - n_r) * 100
                    rs_q = ('Strong' if d>3
                            else 'Weak' if d<-3
                            else 'Neutral')
            except:
                pass

        signals.append({
            'symbol':       symbol,
            'sector':       sector,
            'signal':       'DOWN_TRI',
            'age':          0,
            'pivot_bar':    pb,
            'pivot_date':   df.index[pb].strftime('%Y-%m-%d'),
            'pivot_price':  round(pivot_px, 2),
            'entry_est':    round(entry_est, 2),
            'stop':         round(stop, 2),
            'atr':          round(atr, 2),
            'regime':       regime,
            'regime_score': regime_score,
            'vol_q':        vol_q,
            'vol_confirm':  vol_confirm,
            'rs_q':         rs_q,
            'sec_mom':      sector_momentum.get(sector,'Neutral'),
            'bear_bonus':   False,
        })

    # ── BULL PROXY ────────────────────────────────
    bp_last = -999
    for i in range(max(0, n-15), n):
        atr = atr_v[i]
        if np.isnan(atr) or atr <= 0:
            continue
        if np.isnan(ema50v[i]) or closes[i] < ema50v[i]:
            continue
        if (i - bp_last) <= SMC_COOLDOWN:
            continue
        if not nSZ_v[i]:
            continue
        br = highs[i] - lows[i]
        if br < 1e-6:
            continue
        close_pos   = (closes[i]-lows[i]) / br
        lower_wick  = (min(opens[i],closes[i])-lows[i]) / br
        if not (close_pos >= BP_CLOSE_POS_MIN and
                lower_wick >= BP_LOWER_WICK_MIN and
                closes[i] > opens[i]):
            continue
        bp_last = i
        age = last_bar - i
        if age > 1:
            continue

        stop_zone = (szL_v[i] - 0.5*atr
                     if not np.isnan(szL_v[i])
                     else lows[i] - atr)

        avg_vol = df['Volume'].iloc[max(0,i-20):i].mean()
        sig_vol = df['Volume'].iloc[i]
        vr      = sig_vol/avg_vol if avg_vol>0 else 1
        vol_q   = 'High' if vr>1.5 else ('Thin' if vr<0.7 else 'Average')
        vol_confirm = vr >= 1.2

        rs_q = 'Neutral'
        if i >= 20 and nifty_close is not None:
            try:
                nifty_idx = nifty_close.index.get_loc(
                    df.index[i], method='nearest')
                if nifty_idx >= 20:
                    s_r = closes[i]/closes[max(0,i-20)] - 1
                    n_r = (nifty_close.iloc[nifty_idx] /
                           nifty_close.iloc[nifty_idx-20] - 1)
                    d   = (s_r - n_r) * 100
                    rs_q = ('Strong' if d>3
                            else 'Weak' if d<-3
                            else 'Neutral')
            except:
                pass

        signals.append({
            'symbol':       symbol,
            'sector':       sector,
            'signal':       'BULL_PROXY',
            'age':          age,
            'pivot_bar':    i,
            'pivot_date':   df.index[i].strftime('%Y-%m-%d'),
            'pivot_price':  round(lows[i], 2),
            'entry_est':    round(closes[last_bar], 2),
            'stop':         round(stop_zone, 2),
            'atr':          round(atr, 2),
            'wick_ratio':   round(lower_wick, 3),
            'regime':       regime,
            'regime_score': regime_score,
            'vol_q':        vol_q,
            'vol_confirm':  vol_confirm,
            'rs_q':         rs_q,
            'sec_mom':      sector_momentum.get(sector,'Neutral'),
            'bear_bonus':   False,
        })

    return signals
