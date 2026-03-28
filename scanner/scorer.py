import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    SCORE_AGE_0, SCORE_AGE_1, SCORE_BEAR_BONUS,
    SCORE_BULL_CHOPPY, SCORE_VOL_CONFIRM,
    SCORE_SEC_LEADING, SCORE_RS_STRONG,
    SCORE_GRADE_A, EXIT_UPTRI_BEAR, EXIT_DEFAULT,
    CAPITAL, RISK_PCT_HIGH, RISK_PCT_NORMAL,
    RISK_PCT_LOW
)
from calendar_utils import (
    next_trading_day, days_until_exit, is_expiry_week
)
from datetime import date

def score_signal(sig, grade='B'):
    """
    Score signal 0-10 based on backtest-proven factors.
    Returns score and breakdown dict.
    """
    score = 0
    breakdown = []

    # Age scoring — biggest factor from backtest
    age = sig.get('age', 3)
    if age == 0:
        score += SCORE_AGE_0
        breakdown.append(f"Age 0 +{SCORE_AGE_0}")
    elif age == 1:
        score += SCORE_AGE_1
        breakdown.append(f"Age 1 +{SCORE_AGE_1}")

    # Regime scoring
    regime = sig.get('regime', 'Choppy')
    signal = sig.get('signal', '')
    if signal == 'UP_TRI' and regime == 'Bear':
        score += SCORE_BEAR_BONUS
        breakdown.append(f"Bear Bonus +{SCORE_BEAR_BONUS}")
    elif regime in ('Bull', 'Choppy'):
        score += SCORE_BULL_CHOPPY
        breakdown.append(f"Regime {regime} +{SCORE_BULL_CHOPPY}")

    # Volume confirmation
    if sig.get('vol_confirm', False):
        score += SCORE_VOL_CONFIRM
        breakdown.append(f"Vol Confirm +{SCORE_VOL_CONFIRM}")

    # Sector momentum
    if sig.get('sec_mom', 'Neutral') == 'Leading':
        score += SCORE_SEC_LEADING
        breakdown.append(f"Sector Leading +{SCORE_SEC_LEADING}")

    # RS quality
    if sig.get('rs_q', 'Neutral') == 'Strong':
        score += SCORE_RS_STRONG
        breakdown.append(f"RS Strong +{SCORE_RS_STRONG}")

    # Grade A stock
    if grade == 'A':
        score += SCORE_GRADE_A
        breakdown.append(f"Grade A +{SCORE_GRADE_A}")

    # Cap at 10
    score = min(score, 10)

    return score, breakdown

def get_action(score, signal, regime):
    """Returns action label based on score"""
    if score >= 8:
        return 'DEPLOY'
    elif score >= 5:
        return 'WATCH'
    elif score >= 3:
        return 'CAUTION'
    else:
        return 'NO_TRADE'

def get_exit_rule(signal, regime):
    """
    Returns exit strategy based on backtest findings.
    UP_TRI + Bear → Target2x
    Everything else → Day6
    """
    if signal == 'UP_TRI' and regime == 'Bear':
        return EXIT_UPTRI_BEAR
    return EXIT_DEFAULT

def calc_target(entry, stop, exit_rule, atr):
    """Calculate target price based on exit rule"""
    risk = abs(entry - stop)
    if exit_rule == 'Target2x':
        mult = 2.0
    elif exit_rule == 'Target1_5x':
        mult = 1.5
    else:
        return None  # Day6 — no fixed target
    # For longs
    if entry > stop:
        return round(entry + risk * mult, 2)
    # For shorts
    else:
        return round(entry - risk * mult, 2)

def calc_rr(entry, stop, target):
    """Calculate R:R ratio"""
    if target is None:
        return None
    risk   = abs(entry - stop)
    reward = abs(target - entry)
    if risk <= 0:
        return None
    return round(reward / risk, 2)

def calc_position_size(entry, stop, score):
    """
    Calculate position size based on conviction score.
    Returns shares and risk amount.
    """
    if score >= 8:
        risk_amt = CAPITAL * RISK_PCT_HIGH
    elif score >= 5:
        risk_amt = CAPITAL * RISK_PCT_NORMAL
    else:
        risk_amt = CAPITAL * RISK_PCT_LOW

    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return 0, 0

    shares   = int(risk_amt / stop_dist)
    actual_risk = shares * stop_dist
    return shares, round(actual_risk, 0)

def enrich_signal(sig, grade='B'):
    """
    Takes raw signal dict and adds all scored fields.
    Returns enriched signal ready for display.
    """
    score, breakdown = score_signal(sig, grade)
    action   = get_action(score, sig['signal'], sig['regime'])
    exit_rule= get_exit_rule(sig['signal'], sig['regime'])

    entry = sig.get('entry_est', 0)
    stop  = sig.get('stop', 0)

    target  = calc_target(entry, stop, exit_rule, sig.get('atr',0))
    rr      = calc_rr(entry, stop, target)
    shares, risk_amt = calc_position_size(entry, stop, score)

    # Exit date
    today    = date.today()
    exit_dt  = days_until_exit(today, 6)
    entry_dt = next_trading_day(today)

    # Expiry week warning
    expiry_warn = is_expiry_week(today)

    sig['score']       = score
    sig['breakdown']   = ' | '.join(breakdown)
    sig['action']      = action
    sig['exit_rule']   = exit_rule
    sig['target']      = target
    sig['rr']          = rr
    sig['shares']      = shares
    sig['risk_amt']    = risk_amt
    sig['entry_date']  = entry_dt.strftime('%d %b')
    sig['exit_date']   = exit_dt.strftime('%d %b')
    sig['expiry_warn'] = expiry_warn
    sig['grade']       = grade

    return sig

def filter_signals(signals, min_score=3, age0_only=False,
                   grade_a_only=False, deploy_only=False):
    """Filter signals by criteria"""
    out = []
    for s in signals:
        if s.get('score', 0) < min_score:
            continue
        if age0_only and s.get('age', 99) != 0:
            continue
        if grade_a_only and s.get('grade') != 'A':
            continue
        if deploy_only and s.get('action') != 'DEPLOY':
            continue
        out.append(s)
    # Sort by score descending
    out.sort(key=lambda x: x.get('score', 0), reverse=True)
    return out
