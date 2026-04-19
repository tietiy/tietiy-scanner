# ── mini_scanner.py ──────────────────────────────────
# Conviction filter layer between scorer.py and output
# Sits between Alpha Scanner and final signal output
#
# CURRENT MODE: SHADOW MODE
# All signals pass through — nothing is blocked
# Every signal is evaluated against rules silently
# Rejection reasons logged for future analysis
# Rules activate one by one as live data validates them
#
# KILL PATTERNS (NEW — Session 3, Apr 19 2026):
# Hard-block patterns that bypass shadow_mode
# When a signal matches a kill_pattern (signal+sector combo)
# it is REJECTED regardless of shadow_mode
# Also triggers contra_tracker to record inverted shadow
#
# HOW TO ACTIVATE A RULE:
# Edit data/mini_scanner_rules.json only
# Set the rule's "active" field to true
# Zero Python changes needed
#
# HOW TO ADD A KILL PATTERN:
# Add entry to kill_patterns array in mini_scanner_rules.json
# OR approve a rule_proposer proposal via Telegram /approve_rule
#
# NEVER hardcode thresholds in this file
# ALL thresholds live in mini_scanner_rules.json
# ─────────────────────────────────────────────────────

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# ── PATHS ─────────────────────────────────────────────
_HERE      = os.path.dirname(os.path.abspath(__file__))
_ROOT      = os.path.dirname(_HERE)
_RULES     = os.path.join(_ROOT, 'data',
                 'mini_scanner_rules.json')
_OUTPUT    = os.path.join(_ROOT, 'output')


# ── DEFAULT RULES ─────────────────────────────────────
# Used if mini_scanner_rules.json is missing or corrupt
# All rules inactive — everything passes
# This is the safe fallback state
DEFAULT_RULES = {
    "shadow_mode": True,
    "rules": {
        "min_score": {
            "active":      False,
            "threshold":   7,
            "sa_threshold": 5,
            "description": "Minimum score to pass"
        },
        "min_rr": {
            "active":      False,
            "threshold":   2.0,
            "description": "Minimum R:R ratio"
        },
        "regime_alignment": {
            "active":      False,
            "description": (
                "UP_TRI only Bull/Neutral, "
                "DOWN_TRI only Bear/Neutral"
            )
        },
        "require_volume": {
            "active":      False,
            "description": "Require vol_confirm = True"
        },
        "grade_gate": {
            "active":      False,
            "allowed":     ["A", "B", "C"],
            "description": "Only allowed grades pass"
        },
        "clean_air": {
            "active":      False,
            "description": "Clean air above/below required"
        },
        "delivery_volume": {
            "active":      False,
            "description": (
                "Delivery volume filter — Phase 3"
            )
        }
    },
    "kill_patterns": [],
    "warn_patterns": [],
    "boost_patterns": []
}


# ── LOAD RULES ────────────────────────────────────────

def _load_rules():
    """
    Load rules from mini_scanner_rules.json.
    Returns DEFAULT_RULES if file missing or corrupt.
    """
    if not os.path.exists(_RULES):
        print("[mini_scanner] Rules file not found "
              "— using defaults (shadow mode)")
        return DEFAULT_RULES

    try:
        with open(_RULES, 'r') as f:
            rules = json.load(f)
        return rules
    except Exception as e:
        print(f"[mini_scanner] Rules load error: {e} "
              "— using defaults")
        return DEFAULT_RULES


# ── R:R CALCULATION ───────────────────────────────────

def _calculate_rr(sig):
    """
    Calculate R:R ratio from signal dict.
    Returns float or None if cannot calculate.
    """
    try:
        entry     = float(sig.get('entry_est', 0) or 0)
        stop      = float(sig.get('stop', 0) or 0)
        direction = sig.get('direction', 'LONG')

        if entry <= 0 or stop <= 0:
            return None

        if direction == 'LONG':
            risk   = entry - stop
            # Target = entry + 2x risk (standard)
            target = entry + 2.0 * risk
            if risk <= 0:
                return None
            return round(
                (target - entry) / risk, 2)

        elif direction == 'SHORT':
            risk   = stop - entry
            target = entry - 2.0 * risk
            if risk <= 0:
                return None
            return round(
                (entry - target) / risk, 2)

        return None
    except Exception:
        return None


# ── KILL PATTERNS CHECK (NEW — Session 3) ─────────────
# Runs BEFORE rule evaluation. Hard-blocks matched signals
# regardless of shadow_mode. Triggers contra_tracker for
# DOWN_TRI+Bank pattern (can extend to more later).

def _check_kill_patterns(sig, rules):
    """
    Check if signal matches any active kill_pattern.
    Returns (matched: bool, kill_rule: dict or None)
    """
    kill_patterns = rules.get('kill_patterns', [])
    if not kill_patterns:
        return False, None

    sig_type   = sig.get('signal', '')
    sig_sector = sig.get('sector', '')

    for kill_rule in kill_patterns:
        # Skip inactive kill rules
        if not kill_rule.get('active', True):
            continue

        rule_signal = kill_rule.get('signal')
        rule_sector = kill_rule.get('sector')

        # Match logic: signal+sector combo
        signal_match = (rule_signal is None or
                        rule_signal == sig_type)
        sector_match = (rule_sector is None or
                        rule_sector == sig_sector)

        if signal_match and sector_match:
            return True, kill_rule

    return False, None


def _trigger_contra_shadow(sig, kill_rule):
    """
    Record inverted shadow trade via contra_tracker.
    Only for kill_patterns flagged with contra_shadow_tracked.
    Gracefully handles import failure.
    """
    if not kill_rule.get('contra_shadow_tracked', False):
        return

    try:
        from contra_tracker import record_contra_shadow
        shadow = record_contra_shadow(
            sig,
            kill_rule_id=kill_rule.get('id')
        )
        if shadow:
            print(f"[mini_scanner] Contra shadow recorded: "
                  f"{shadow.get('id')}")
    except ImportError as e:
        print(f"[mini_scanner] contra_tracker not available: {e}")
    except Exception as e:
        # Never let contra tracking break the scanner
        print(f"[mini_scanner] Contra tracker error: {e}")


def get_active_kill_patterns():
    """
    Public helper for telegram_bot /status command.
    Returns list of currently active kill patterns.
    """
    rules = _load_rules()
    kills = rules.get('kill_patterns', [])
    return [k for k in kills if k.get('active', True)]


# ── EVALUATE SINGLE SIGNAL ────────────────────────────

def _evaluate(sig, rules):
    """
    Evaluates one signal against all active rules.

    Returns:
        passes          : bool
        rejection_reason: str or None
        rejection_filter: str or None
        threshold       : value or None
        shadow_hits     : list of rules that WOULD
                          have rejected in shadow mode
    """
    active_rules = rules.get('rules', {})
    shadow_mode  = rules.get('shadow_mode', True)
    is_sa        = sig.get('attempt_number', 1) == 2
    score        = sig.get('score', 0)
    regime       = sig.get('regime', 'Neutral')
    direction    = sig.get('direction', 'LONG')
    vol_confirm  = sig.get('vol_confirm', False)
    grade        = sig.get('grade', 'C')
    rr           = _calculate_rr(sig)

    shadow_hits = []  # rules that would reject
                      # but are inactive

    # ── RULE 1: min_score ─────────────────────────
    r = active_rules.get('min_score', {})
    if r:
        threshold = (
            r.get('sa_threshold', 5) if is_sa
            else r.get('threshold', 7)
        )
        if score < threshold:
            hit = {
                'filter':    'min_score',
                'reason':    'score_below_threshold',
                'threshold': threshold,
                'value':     score,
            }
            if r.get('active', False):
                return (False,
                        'score_below_threshold',
                        'min_score',
                        threshold,
                        shadow_hits)
            else:
                shadow_hits.append(hit)

    # ── RULE 2: min_rr ────────────────────────────
    r = active_rules.get('min_rr', {})
    if r and rr is not None:
        threshold = r.get('threshold', 2.0)
        if rr < threshold:
            hit = {
                'filter':    'min_rr',
                'reason':    'rr_below_minimum',
                'threshold': threshold,
                'value':     rr,
            }
            if r.get('active', False):
                return (False,
                        'rr_below_minimum',
                        'min_rr',
                        threshold,
                        shadow_hits)
            else:
                shadow_hits.append(hit)

    # ── RULE 3: regime_alignment ──────────────────
    r = active_rules.get('regime_alignment', {})
    if r:
        fails_alignment = False
        if (direction == 'LONG' and
                regime == 'Bear'):
            fails_alignment = True
        if (direction == 'SHORT' and
                regime == 'Bull'):
            fails_alignment = True

        if fails_alignment:
            hit = {
                'filter':    'regime_alignment',
                'reason':    'regime_not_aligned',
                'threshold': direction,
                'value':     regime,
            }
            if r.get('active', False):
                return (False,
                        'regime_not_aligned',
                        'regime_alignment',
                        direction,
                        shadow_hits)
            else:
                shadow_hits.append(hit)

    # ── RULE 4: require_volume ────────────────────
    r = active_rules.get('require_volume', {})
    if r:
        if not vol_confirm:
            hit = {
                'filter':    'require_volume',
                'reason':    'volume_not_confirmed',
                'threshold': True,
                'value':     vol_confirm,
            }
            if r.get('active', False):
                return (False,
                        'volume_not_confirmed',
                        'require_volume',
                        True,
                        shadow_hits)
            else:
                shadow_hits.append(hit)

    # ── RULE 5: grade_gate ────────────────────────
    r = active_rules.get('grade_gate', {})
    if r:
        allowed = r.get('allowed', ['A', 'B', 'C'])
        if grade not in allowed:
            hit = {
                'filter':    'grade_gate',
                'reason':    'grade_not_allowed',
                'threshold': allowed,
                'value':     grade,
            }
            if r.get('active', False):
                return (False,
                        'grade_not_allowed',
                        'grade_gate',
                        str(allowed),
                        shadow_hits)
            else:
                shadow_hits.append(hit)

    # ── RULE 6: delivery_volume ───────────────────
    # Phase 3 placeholder
    # Rule exists in config but never activates
    # until delivery_volume field exists in signal dict
    r = active_rules.get('delivery_volume', {})
    if r and r.get('active', False):
        delivery = sig.get('delivery_pct', None)
        if delivery is None:
            # Data not available — pass silently
            pass

    # All checks passed (or shadow mode)
    return (True, None, None, None, shadow_hits)


# ── MAIN PUBLIC FUNCTION ──────────────────────────────

def filter_signals(signals):
    """
    Main entry point. Called from main.py.

    Takes list of scored signal dicts from scorer.py.
    Returns three lists:
        mini_signals    : passed conviction filter
        alpha_signals   : all signals (same as input)
        rejection_log   : what was rejected and why
                          includes shadow hits + kill hits

    In shadow mode most signals appear in mini_signals.
    Exception: kill_patterns hard-block regardless of
    shadow_mode.

    Parameters:
        signals : list of signal dicts from scorer.py

    Returns:
        mini_signals  : list — conviction approved
        alpha_signals : list — all signals
        rejection_log : list — rejection detail dicts
    """
    rules         = _load_rules()
    shadow_mode   = rules.get('shadow_mode', True)

    mini_signals  = []
    alpha_signals = list(signals)  # full copy
    rejection_log = []

    # ── Count kill hits separately for logging ────
    kill_count = 0

    for sig in signals:
        # ── NEW (Session 3): Kill patterns check FIRST
        # Bypasses shadow_mode — hard block
        killed, kill_rule = _check_kill_patterns(
            sig, rules)

        if killed:
            kill_count += 1
            # Trigger contra shadow tracking if flagged
            _trigger_contra_shadow(sig, kill_rule)

            # Log as rejection (NOT shadow — actual block)
            rejection_log.append({
                'date':              _today(),
                'symbol':            sig.get(
                                         'symbol', ''),
                'signal':            sig.get(
                                         'signal', ''),
                'alpha_score':       sig.get(
                                         'score', 0),
                'regime':            sig.get(
                                         'regime', ''),
                'grade':             sig.get(
                                         'grade', 'C'),
                'passed':            False,
                'shadow_only':       False,
                'rejection_reason':  'kill_switch',
                'rejection_filter':  'kill_patterns',
                'threshold':         kill_rule.get('id'),
                'actual_value':      (
                    f"{sig.get('signal', '')}+"
                    f"{sig.get('sector', '')}"
                ),
                'kill_rule_id':      kill_rule.get('id'),
                'kill_reason':       kill_rule.get(
                                         'reason', ''),
                'contra_tracked':    kill_rule.get(
                                 'contra_shadow_tracked',
                                 False),
                'scanner_version':   sig.get(
                                 'scanner_version', 'v2.0'),
            })
            # Skip rule evaluation — signal is killed
            continue

        # ── Regular rule evaluation ───────────────
        passes, reason, filt, threshold, shadows = \
            _evaluate(sig, rules)

        if passes or shadow_mode:
            # Signal passes — add to mini
            mini_signals.append(sig)

            # Log any shadow hits for analysis
            for sh in shadows:
                rejection_log.append({
                    'date':              _today(),
                    'symbol':            sig.get(
                                             'symbol', ''),
                    'signal':            sig.get(
                                             'signal', ''),
                    'alpha_score':       sig.get(
                                             'score', 0),
                    'regime':            sig.get(
                                             'regime', ''),
                    'grade':             sig.get(
                                             'grade', 'C'),
                    'passed':            True,
                    'shadow_only':       True,
                    'rejection_reason':  sh['reason'],
                    'rejection_filter':  sh['filter'],
                    'threshold':         sh['threshold'],
                    'actual_value':      sh['value'],
                    'scanner_version':   sig.get(
                                 'scanner_version', 'v2.0'),
                })
        else:
            # Signal blocked by active rule
            rejection_log.append({
                'date':              _today(),
                'symbol':            sig.get(
                                         'symbol', ''),
                'signal':            sig.get(
                                         'signal', ''),
                'alpha_score':       sig.get(
                                         'score', 0),
                'regime':            sig.get(
                                         'regime', ''),
                'grade':             sig.get(
                                         'grade', 'C'),
                'passed':            False,
                'shadow_only':       False,
                'rejection_reason':  reason,
                'rejection_filter':  filt,
                'threshold':         threshold,
                'actual_value':      None,
                'scanner_version':   sig.get(
                                 'scanner_version', 'v2.0'),
            })

    mode_str = "SHADOW" if shadow_mode else "ACTIVE"
    print(f"[mini_scanner] Mode: {mode_str} | "
          f"In: {len(signals)} | "
          f"Mini: {len(mini_signals)} | "
          f"Killed: {kill_count} | "
          f"Shadow hits: {len(rejection_log) - kill_count}")

    return mini_signals, alpha_signals, rejection_log


def _today():
    from datetime import date
    return date.today().isoformat()


# ── WRITE OUTPUTS ─────────────────────────────────────

def write_mini_log(mini_signals, output_dir=None):
    """
    Writes mini_log.json to output/
    Called from main.py after filter_signals()
    """
    import json
    from datetime import date

    if output_dir is None:
        output_dir = _OUTPUT

    os.makedirs(output_dir, exist_ok=True)

    data = {
        "date":    date.today().isoformat(),
        "count":   len(mini_signals),
        "signals": mini_signals,
    }

    path = os.path.join(output_dir, 'mini_log.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"[mini_scanner] mini_log.json written "
          f"→ {len(mini_signals)} signals")


def write_rejected_log(rejection_log, output_dir=None):
    """
    Writes rejected_log.json to output/
    Called from main.py after filter_signals()
    Includes both hard rejections and shadow hits
    """
    import json
    from datetime import date

    if output_dir is None:
        output_dir = _OUTPUT

    os.makedirs(output_dir, exist_ok=True)

    data = {
        "date":       date.today().isoformat(),
        "count":      len(rejection_log),
        "rejections": rejection_log,
    }

    path = os.path.join(output_dir, 'rejected_log.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"[mini_scanner] rejected_log.json written "
          f"→ {len(rejection_log)} entries")
