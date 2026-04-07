# scanner/scorer.py
# Scoring, enrichment, position sizing, action labels
#
# BUG 1 FIX: enrich_signal() now writes:
#   sig['scan_price']   — used by Telegram _resolve_price
#   sig['entry']        — used by Telegram _resolve_price
#   sig['target_price'] — used by Telegram _resolve_price
# These three fields were missing, causing 0.00 in all Telegram alerts.

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

# Age scoring
SCORE_AGE_0 = 3
SCORE_AGE_1 = 2

# Regime scoring — UP_TRI
# Bear = highest conviction per backtest (avg trade 4.85%)
SCORE_UPTRI_BEAR   = 3
SCORE_UPTRI_BULL   = 2
SCORE_UPTRI_CHOPPY = 1

# Regime scoring — DOWN_TRI (no regime filter per backtest)
SCORE_DOWN_ALL = 2

# Regime scoring — BULL_PROXY (trend filter active)
SCORE_BULLPROXY_VALID = 1

# Quality bonuses
SCORE_VOL_CONFIRM = 1
SCORE_SEC_LEADING = 1
SCORE_RS_STRONG   = 1
SCORE_GRADE_A     = 1


def score_signal(sig, grade='B'):
    score     = 0
    breakdown = []
    age       = sig.get('age', 3)
    signal    = sig.get('signal', '')
    regime    = sig.get('regime', 'Choppy')

    # --- Age layer ---
    if age == 0:
        score += SCORE_AGE_0
        breakdown.append(f"Age0+{SCORE_AGE_0}")
    elif age == 1:
        score += SCORE_AGE_1
        breakdown.append(f"Age1+{SCORE_AGE_1}")

    # --- Regime layer ---
    if signal == 'UP_TRI':
        if regime == 'Bear':
            score += SCORE_UPTRI_BEAR
            breakdown.append(f"Bear+{SCORE_UPTRI_BEAR}")
        elif regime == 'Bull':
            score += SCORE_UPTRI_BULL
            breakdown.append(f"Bull+{SCORE_UPTRI_BULL}")
        else:
            score += SCORE_UPTRI_CHOPPY
            breakdown.append(f"Choppy+{SCORE_UPTRI_CHOPPY}")

    elif signal == 'DOWN_TRI':
        score += SCORE_DOWN_ALL
        breakdown.append(f"DownAll+{SCORE_DOWN_ALL}")

    elif signal == 'BULL_PROXY':
        if regime in ('Bull', 'Choppy'):
            score += SCORE_BULLPROXY_VALID
            breakdown.append(f"{regime}+{SCORE_BULLPROXY_VALID}")

    # --- Quality layer ---
    vc = sig.get('vol_confirm', False)
    if vc is True or vc == 'True' or vc == 'true':
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
    try:
        entry = float(entry or 0)
        stop  = float(stop  or 0)
        if entry <= 0 or stop <= 0:
            return None
        risk = abs(entry - stop)
        if risk <= 0:
            return None
        if exit_rule == 'Target2x':
            mult = 2.0
        elif exit_rule == 'Target1_5x':
            mult = 1.5
        else:
            return None
        if entry > stop:
            return round(entry + risk * mult, 2)
        else:
            return round(entry - risk * mult, 2)
    except Exception:
        return None


def calc_rr(entry, stop, target):
    try:
        if target is None:
            return None
        entry  = float(entry  or 0)
        stop   = float(stop   or 0)
        target = float(target or 0)
        risk   = abs(entry - stop)
        reward = abs(target - entry)
        return round(reward / risk, 2) if risk > 0 else None
    except Exception:
        return None


def calc_position_size(entry, stop, score):
    try:
        entry = float(entry or 0)
        stop  = float(stop  or 0)
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
    except Exception:
        return 0, 0


def enrich_signal(sig, grade='B'):
    score, breakdown = score_signal(sig, grade)
    action    = get_action(score)
    exit_rule = get_exit_rule(
        sig.get('signal', ''), sig.get('regime', ''))

    entry  = sig.get('entry_est', 0) or 0
    stop   = sig.get('stop', 0)      or 0
    target = calc_target(entry, stop, exit_rule)
    rr     = calc_rr(entry, stop, target)

    shares, risk_amt = calc_position_size(entry, stop, score)
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
    sig['expiry_warn'] = False
    sig['grade']      = grade

    # ── BUG 1 FIX ─────────────────────────────────────
    # Telegram's _resolve_price() checks these fields in
    # order: actual_open → scan_price → entry → entry_est
    # Without these, all Telegram prices show 0.00.
    if entry and float(entry) > 0:
        sig['scan_price']   = round(float(entry), 2)
        sig['entry']        = round(float(entry), 2)
    if target is not None:
        sig['target_price'] = round(float(target), 2)
    # ──────────────────────────────────────────────────

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
    out.sort(
        key=lambda x: x.get('score', 0),
        reverse=True)
    return out
