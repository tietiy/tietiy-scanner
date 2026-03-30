import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from datetime import date
from calendar_utils import next_trading_day, days_until_exit

CAPITAL         = 100_000
RISK_PCT_HIGH   = 0.05
RISK_PCT_NORMAL = 0.03
RISK_PCT_LOW    = 0.01

EXIT_UPTRI_BEAR = 'Target2x'
EXIT_DEFAULT    = 'Day6'

SCORE_AGE_0       = 3
SCORE_AGE_1       = 2
SCORE_BEAR_BONUS  = 3
SCORE_DOWN_ALL    = 2
SCORE_BULL_CHOPPY = 1
SCORE_BEAR_BASE   = 1
SCORE_VOL_CONFIRM = 1
SCORE_SEC_LEADING = 1
SCORE_RS_STRONG   = 1
SCORE_GRADE_A     = 1


def score_signal(sig, grade='B'):
    score     = 0
    breakdown = []
    age       = sig.get('age', 3)
    if age == 0:
        score += SCORE_AGE_0
        breakdown.append(f"Age0+{SCORE_AGE_0}")
    elif age == 1:
        score += SCORE_AGE_1
        breakdown.append(f"Age1+{SCORE_AGE_1}")

    regime = sig.get('regime', 'Choppy')
    signal = sig.get('signal', '')
    if signal == 'UP_TRI' and regime == 'Bear':
        score += SCORE_BEAR_BONUS
        breakdown.append(f"BearBonus+{SCORE_BEAR_BONUS}")
    elif signal == 'DOWN_TRI':
        score += SCORE_DOWN_ALL
        breakdown.append(f"DownAll+{SCORE_DOWN_ALL}")
    elif regime in ('Bull', 'Choppy'):
        score += SCORE_BULL_CHOPPY
        breakdown.append(f"{regime}+{SCORE_BULL_CHOPPY}")
    elif regime == 'Bear':
        score += SCORE_BEAR_BASE
        breakdown.append(f"Bear+{SCORE_BEAR_BASE}")

    if sig.get('vol_confirm', False):
        score += SCORE_VOL_CONFIRM
        breakdown.append(f"Vol+{SCORE_VOL_CONFIRM}")
    if sig.get('sec_mom', 'Neutral') == 'Leading':
        score += SCORE_SEC_LEADING
        breakdown.append(f"SecLead+{SCORE_SEC_LEADING}")
    if sig.get('rs_q', 'Neutral') == 'Strong':
        score += SCORE_RS_STRONG
        breakdown.append(f"RS+{SCORE_RS_STRONG}")
    if grade == 'A':
        score += SCORE_GRADE_A
        breakdown.append(f"GradeA+{SCORE_GRADE_A}")

    return min(score, 10), breakdown


def get_action(score):
    if score >= 6:  return 'DEPLOY'
    if score >= 3:  return 'WATCH'
    if score >= 2:  return 'CAUTION'
    return 'NO_TRADE'


def get_exit_rule(signal, regime):
    if signal == 'UP_TRI' and regime == 'Bear':
        return EXIT_UPTRI_BEAR
    return EXIT_DEFAULT


def calc_target(entry, stop, exit_rule):
    risk = abs(entry - stop)
    if exit_rule == 'Target2x':
        mult = 2.0
    elif exit_rule == 'Target1_5x':
        mult = 1.5
    else:
        return None
    return round(entry + risk * mult, 2) \
           if entry > stop \
           else round(entry - risk * mult, 2)


def calc_rr(entry, stop, target):
    if target is None:
        return None
    risk   = abs(entry - stop)
    reward = abs(target - entry)
    return round(reward / risk, 2) if risk > 0 else None


def calc_position_size(entry, stop, score):
    if score >= 6:
        risk_amt = CAPITAL * RISK_PCT_HIGH
    elif score >= 3:
        risk_amt = CAPITAL * RISK_PCT_NORMAL
    else:
        risk_amt = CAPITAL * RISK_PCT_LOW
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return 0, 0
    shares = int(risk_amt / stop_dist)
    return shares, round(shares * stop_dist, 0)


def enrich_signal(sig, grade='B'):
    score, breakdown = score_signal(sig, grade)
    action    = get_action(score)
    exit_rule = get_exit_rule(
        sig['signal'], sig.get('regime', ''))
    entry  = sig.get('entry_est', 0)
    stop   = sig.get('stop', 0)
    target = calc_target(entry, stop, exit_rule)
    rr     = calc_rr(entry, stop, target)
    shares, risk_amt = calc_position_size(
        entry, stop, score)
    today   = date.today()
    exit_dt = days_until_exit(today, 6)

    sig['score']      = score
    sig['breakdown']  = ' | '.join(breakdown)
    sig['action']     = action
    sig['exit_rule']  = exit_rule
    sig['target']     = target
    sig['rr']         = rr
    sig['shares']     = shares
    sig['risk_amt']   = risk_amt
    sig['entry_date'] = next_trading_day(
        today).strftime('%d %b')
    sig['exit_date']  = exit_dt.strftime('%d %b')
    sig['expiry_warn']= False
    sig['grade']      = grade
    return sig


def filter_signals(signals, min_score=2,
                   age0_only=False,
                   grade_a_only=False,
                   deploy_only=False):
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
    out.sort(key=lambda x: x.get('score', 0),
             reverse=True)
    return out
