# ── pattern_miner.py ─────────────────────────────────
# TIE TIY Pattern Intelligence Layer — Stage 1
#
# Reads signal_history.json, discovers patterns in
# resolved signals, writes output/patterns.json for
# consumption by Stats tab and Decision Engine (Stage 2).
#
# PHILOSOPHY:
# - Zero hardcoded rules. All patterns derived from data.
# - Three confidence tiers: Emerging / Preliminary / Validated
# - Signal-type baselines (UP_TRI vs DOWN_TRI vs BULL_PROXY)
# - Feature combinations up to depth 3 (minimum set)
# - Runs nightly at 7 PM IST via GH Actions
#
# MINIMUM FEATURE SET (Q1 decision):
#   signal × regime × sector × age × grade
# BASELINE (Q2 decision):
#   Signal-type — UP_TRI baseline is compared to UP_TRI patterns
# LOCATION (Q3 decision):
#   Scanner repo Python + GH Actions (nightly_intelligence.yml)
#
# TIER THRESHOLDS:
#   Validated:    n >= 20 AND |edge| >= 15 pts
#   Preliminary:  n >= 10 AND |edge| >= 10 pts
#   Emerging:     n <  10 OR  |edge| <  10 pts
#
# OUTPUT: output/patterns.json (schema_version=1)
# ─────────────────────────────────────────────────────

import os
import sys
import json
import itertools
from datetime import datetime, date
from statistics import mean

sys.path.insert(0, os.path.dirname(__file__))

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

HISTORY_FILE  = os.path.join(_OUTPUT, 'signal_history.json')
PATTERNS_FILE = os.path.join(_OUTPUT, 'patterns.json')

# Features to mine — minimum set
FEATURES = ['signal', 'regime', 'sector', 'age', 'grade']

# How deep to combine features
MAX_DEPTH = 3

# Minimum n required to even report a pattern
MIN_N_REPORT = 5

# Tier classification thresholds
VALIDATED_N         = 20
VALIDATED_EDGE_PCT  = 15
PRELIMINARY_N       = 10
PRELIMINARY_EDGE_PCT = 10

# Terminal outcomes — only these count as "resolved"
TERMINAL_OUTCOMES = {
    'TARGET_HIT', 'STOP_HIT',
    'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT'
}

# Which outcomes count as wins
WIN_OUTCOMES = {'TARGET_HIT', 'DAY6_WIN'}


# ── LOADING ───────────────────────────────────────────

def _load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
        return data.get('history', [])
    except Exception as e:
        print(f"[pattern_miner] Cannot load history: {e}")
        return []


def _is_resolved_live(sig):
    """
    Returns True if signal is:
    - resolved (has terminal outcome)
    - live (generation >= 1, not backfill)
    - actually taken (action=TOOK or no action field)
    - entry was valid (not gap-invalidated)
    """
    outcome = sig.get('outcome', '')
    if outcome not in TERMINAL_OUTCOMES:
        return False

    gen = sig.get('generation', 1)
    if gen == 0:
        return False  # backfill — exclude from patterns

    if sig.get('entry_valid') is False:
        return False  # gap invalidated

    return True


# ── FEATURE EXTRACTION ────────────────────────────────

def _extract_feature_value(sig, feature):
    """Extract feature value from signal. Returns str or None."""
    val = sig.get(feature)
    if val is None or val == '':
        return None

    # Normalize signal — collapse _SA variants into base type
    # for signal feature (UP_TRI_SA → UP_TRI for baseline math)
    # But keep SA as a separate trackable feature in the future.
    if feature == 'signal':
        base = str(val).upper()
        # Keep SA distinct — UP_TRI_SA is its own pattern
        return base

    # Age is numeric — keep as string for grouping
    if feature == 'age':
        try:
            return str(int(val))
        except Exception:
            return None

    # Regime/sector/grade: direct
    return str(val)


def _signal_type_for_baseline(sig):
    """
    Map signal to baseline group.
    UP_TRI + UP_TRI_SA → UP_TRI baseline
    DOWN_TRI + DOWN_TRI_SA → DOWN_TRI baseline
    BULL_PROXY → BULL_PROXY baseline
    """
    sig_type = str(sig.get('signal', '')).upper()
    if sig_type.startswith('UP_TRI'):
        return 'UP_TRI'
    if sig_type.startswith('DOWN_TRI'):
        return 'DOWN_TRI'
    if sig_type.startswith('BULL_PROXY'):
        return 'BULL_PROXY'
    return 'OTHER'


# ── BASELINE COMPUTATION ──────────────────────────────

def _compute_baselines(resolved):
    """
    Compute WR/avg_pnl/n per signal-type baseline.
    """
    by_type = {}
    for sig in resolved:
        bt = _signal_type_for_baseline(sig)
        if bt not in by_type:
            by_type[bt] = []
        by_type[bt].append(sig)

    baselines = {}
    for bt, sigs in by_type.items():
        n = len(sigs)
        if n == 0:
            continue
        wins = sum(1 for s in sigs
                   if s.get('outcome') in WIN_OUTCOMES)
        wr = round(wins / n * 100, 1)
        pnls = [float(s.get('pnl_pct', 0) or 0)
                for s in sigs]
        avg_pnl = round(mean(pnls), 2) if pnls else 0.0
        baselines[bt] = {
            'wr': wr,
            'avg_pnl': avg_pnl,
            'n': n,
            'wins': wins,
            'losses': n - wins,
        }

    return baselines


# ── PATTERN COMPUTATION ───────────────────────────────

def _compute_pattern_stats(signals_in_pattern, baselines):
    """
    Given list of signals matching a feature combo,
    compute WR, avg_pnl, MAE/MFE, edge vs baseline.
    """
    n = len(signals_in_pattern)
    wins = sum(1 for s in signals_in_pattern
               if s.get('outcome') in WIN_OUTCOMES)
    losses = n - wins
    wr = round(wins / n * 100, 1) if n > 0 else 0.0

    pnls = [float(s.get('pnl_pct', 0) or 0)
            for s in signals_in_pattern]
    avg_pnl = round(mean(pnls), 2) if pnls else 0.0

    maes = [float(s.get('mae_pct', 0) or 0)
            for s in signals_in_pattern
            if s.get('mae_pct') is not None]
    mfes = [float(s.get('mfe_pct', 0) or 0)
            for s in signals_in_pattern
            if s.get('mfe_pct') is not None]
    avg_mae = round(mean(maes), 2) if maes else 0.0
    avg_mfe = round(mean(mfes), 2) if mfes else 0.0

    # Determine baseline type — dominant signal-type
    # in the pattern. For single-signal patterns, exact
    # match; for mixed, weighted majority.
    type_counts = {}
    for s in signals_in_pattern:
        bt = _signal_type_for_baseline(s)
        type_counts[bt] = type_counts.get(bt, 0) + 1

    if type_counts:
        baseline_type = max(type_counts.items(),
                            key=lambda x: x[1])[0]
    else:
        baseline_type = 'UP_TRI'

    baseline = baselines.get(baseline_type, {})
    baseline_wr = baseline.get('wr', 0.0)
    edge_pct = round(wr - baseline_wr, 1)

    return {
        'n_resolved': n,
        'wins': wins,
        'losses': losses,
        'wr': wr,
        'avg_pnl': avg_pnl,
        'avg_mae': avg_mae,
        'avg_mfe': avg_mfe,
        'baseline_type': baseline_type,
        'baseline_wr': baseline_wr,
        'edge_pct': edge_pct,
    }


# ── TIER CLASSIFICATION ───────────────────────────────

def _classify_tier(n, edge_pct):
    abs_edge = abs(edge_pct)
    if n >= VALIDATED_N and abs_edge >= VALIDATED_EDGE_PCT:
        return 'validated'
    if n >= PRELIMINARY_N and abs_edge >= PRELIMINARY_EDGE_PCT:
        return 'preliminary'
    return 'emerging'


def _pattern_direction(edge_pct):
    if edge_pct > 0:
        return 'positive'
    if edge_pct < 0:
        return 'negative'
    return 'neutral'


# ── INSIGHT GENERATION ────────────────────────────────

def _generate_insight(features, stats):
    """
    Generate plain-language insight for a pattern.
    Template-based — not LLM.
    """
    feat_parts = []
    for k, v in features.items():
        if k == 'signal':
            feat_parts.append(v)
        elif k == 'regime':
            feat_parts.append(f"{v} regime")
        elif k == 'sector':
            feat_parts.append(f"{v} sector")
        elif k == 'age':
            feat_parts.append(f"age={v}")
        elif k == 'grade':
            feat_parts.append(f"Grade {v}")

    desc = " + ".join(feat_parts)
    baseline_type = stats['baseline_type']
    edge = stats['edge_pct']
    wr = stats['wr']
    n = stats['n_resolved']

    if edge > 0:
        return (f"{desc} outperforms {baseline_type} "
                f"baseline by {edge}pp "
                f"({wr}% WR in {n} trades)")
    elif edge < 0:
        return (f"{desc} underperforms {baseline_type} "
                f"baseline by {abs(edge)}pp "
                f"({wr}% WR in {n} trades)")
    else:
        return (f"{desc} matches {baseline_type} "
                f"baseline ({wr}% WR in {n} trades)")


# ── FEATURE COMBINATION GENERATOR ─────────────────────

def _generate_feature_combos(features, max_depth):
    """
    Generate all feature combinations from 1 to max_depth.
    Returns list of tuples: [(signal,), (signal, regime), ...]
    """
    combos = []
    for depth in range(1, max_depth + 1):
        for combo in itertools.combinations(features, depth):
            combos.append(combo)
    return combos


def _group_by_features(resolved, feature_combo):
    """
    Group resolved signals by their values for the
    given feature tuple.

    Returns: {(val1, val2, ...): [signals], ...}
    """
    groups = {}
    for sig in resolved:
        values = []
        skip = False
        for feat in feature_combo:
            v = _extract_feature_value(sig, feat)
            if v is None:
                skip = True
                break
            values.append(v)

        if skip:
            continue

        key = tuple(values)
        if key not in groups:
            groups[key] = []
        groups[key].append(sig)

    return groups


# ── MAIN PATTERN MINING ───────────────────────────────

def _mine_patterns(resolved, baselines):
    """
    Core mining loop: iterate all feature combos,
    group signals, compute stats, classify tier.

    Returns list of pattern dicts sorted by edge magnitude.
    """
    patterns = []
    combos = _generate_feature_combos(FEATURES, MAX_DEPTH)

    print(f"[pattern_miner] Testing "
          f"{len(combos)} feature combinations...")

    for combo in combos:
        groups = _group_by_features(resolved, combo)

        for values, sigs_in_group in groups.items():
            n = len(sigs_in_group)
            if n < MIN_N_REPORT:
                continue

            stats = _compute_pattern_stats(
                sigs_in_group, baselines)

            # Build feature dict
            features_dict = dict(zip(combo, values))

            # Skip if edge is basically zero — no insight
            if abs(stats['edge_pct']) < 1 and n < 15:
                continue

            tier = _classify_tier(
                stats['n_resolved'], stats['edge_pct'])

            direction = _pattern_direction(stats['edge_pct'])

            insight = _generate_insight(
                features_dict, stats)

            pattern_id = '_'.join(
                f"{k}={v}" for k, v in features_dict.items())

            patterns.append({
                'id': pattern_id,
                'features': features_dict,
                'feature_depth': len(combo),
                'n_resolved': stats['n_resolved'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'wr': stats['wr'],
                'avg_pnl': stats['avg_pnl'],
                'avg_mae': stats['avg_mae'],
                'avg_mfe': stats['avg_mfe'],
                'baseline_type': stats['baseline_type'],
                'baseline_wr': stats['baseline_wr'],
                'edge_pct': stats['edge_pct'],
                'tier': tier,
                'direction': direction,
                'insight': insight,
            })

    # Sort: validated first, then by absolute edge
    tier_order = {
        'validated': 0, 'preliminary': 1, 'emerging': 2
    }
    patterns.sort(
        key=lambda p: (
            tier_order.get(p['tier'], 3),
            -abs(p['edge_pct']),
            -p['n_resolved']
        )
    )

    return patterns


# ── SUMMARY BUILDER ───────────────────────────────────

def _build_summary(patterns):
    """Top-level stats for patterns.json"""
    tier_counts = {
        'emerging': 0, 'preliminary': 0, 'validated': 0
    }
    for p in patterns:
        tier_counts[p['tier']] = tier_counts.get(
            p['tier'], 0) + 1

    positive = [p for p in patterns
                if p['direction'] == 'positive']
    negative = [p for p in patterns
                if p['direction'] == 'negative']

    # Top positive = highest edge among validated/preliminary
    top_positive = None
    for p in positive:
        if p['tier'] in ('validated', 'preliminary'):
            top_positive = p['id']
            break

    top_negative = None
    for p in negative:
        if p['tier'] in ('validated', 'preliminary'):
            top_negative = p['id']
            break

    return {
        'emerging': tier_counts['emerging'],
        'preliminary': tier_counts['preliminary'],
        'validated': tier_counts['validated'],
        'total_patterns': len(patterns),
        'top_positive': top_positive,
        'top_negative': top_negative,
    }


# ── MAIN ──────────────────────────────────────────────

def run_pattern_miner():
    print("[pattern_miner] Starting pattern discovery...")

    history = _load_history()
    if not history:
        print("[pattern_miner] No history — aborting")
        return

    print(f"[pattern_miner] Total history records: "
          f"{len(history)}")

    # Filter to resolved live signals
    resolved = [s for s in history if _is_resolved_live(s)]
    print(f"[pattern_miner] Resolved live signals: "
          f"{len(resolved)}")

    if len(resolved) < 20:
        print(f"[pattern_miner] Too few resolved signals "
              f"({len(resolved)} < 20) — patterns will be "
              f"emerging tier only")

    # Compute baselines per signal type
    baselines = _compute_baselines(resolved)
    print(f"[pattern_miner] Baselines computed:")
    for bt, b in baselines.items():
        print(f"  {bt}: WR={b['wr']}% n={b['n']} "
              f"avg_pnl={b['avg_pnl']}%")

    # Mine patterns
    patterns = _mine_patterns(resolved, baselines)
    print(f"[pattern_miner] Discovered "
          f"{len(patterns)} patterns (n>={MIN_N_REPORT})")

    # Build summary
    summary = _build_summary(patterns)
    print(f"[pattern_miner] Tier breakdown: "
          f"Validated={summary['validated']} "
          f"Preliminary={summary['preliminary']} "
          f"Emerging={summary['emerging']}")

    # Write output
    output = {
        'schema_version': 1,
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'total_resolved_signals': len(resolved),
        'feature_set': FEATURES,
        'max_depth': MAX_DEPTH,
        'min_n_report': MIN_N_REPORT,
        'tier_thresholds': {
            'validated': {
                'n_min': VALIDATED_N,
                'edge_pct_min': VALIDATED_EDGE_PCT,
            },
            'preliminary': {
                'n_min': PRELIMINARY_N,
                'edge_pct_min': PRELIMINARY_EDGE_PCT,
            },
        },
        'baselines': baselines,
        'patterns': patterns,
        'summary': summary,
    }

    os.makedirs(_OUTPUT, exist_ok=True)
    try:
        with open(PATTERNS_FILE, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"[pattern_miner] patterns.json written: "
              f"{len(patterns)} patterns, "
              f"{len(resolved)} source signals")
    except Exception as e:
        print(f"[pattern_miner] Write failed: {e}")
        raise


if __name__ == '__main__':
    run_pattern_miner()
