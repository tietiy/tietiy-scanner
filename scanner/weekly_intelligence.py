"""
weekly_intelligence.py — Sunday Weekly Intelligence Report

Purpose:
  Runs every Sunday evening. Composes a comprehensive AI-driven intelligence report
  and sends to Telegram.
  
  This is DIFFERENT from weekend_summary.py:
  - weekend_summary.py (Saturday) = trader's recap — "how did I do this week"
  - weekly_intelligence.py (Sunday) = system's analysis — "what should change"
  
  Contents:
  - Pattern Miner findings (validated, new, shifted)
  - Pending rule proposals needing /approve_rule
  - Regime distribution over the week
  - Contra shadow progress
  - System health snapshot
  - Active kill rules status
  - Suggestions for the coming week

Integration:
  - Triggered by .github/workflows/weekly_intelligence.yml (Sunday 8 PM IST)
  - Uses telegram_bot.send_weekly_intelligence() for delivery (added in telegram_bot.py update)
  - Also writes output/weekly_intelligence_latest.json for PWA/audit

Design principle:
  - One long Telegram message. Scannable with emojis and sections.
  - Markdown formatting (Telegram Markdown)
  - Under Telegram's 4096-char limit (may split if needed)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, os.path.dirname(__file__))

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

SIGNAL_HISTORY_PATH = os.path.join(_OUTPUT, 'signal_history.json')
PATTERNS_PATH = os.path.join(_OUTPUT, 'patterns.json')
PROPOSED_RULES_PATH = os.path.join(_OUTPUT, 'proposed_rules.json')
CONTRA_SHADOW_PATH = os.path.join(_OUTPUT, 'contra_shadow.json')
REGIME_DEBUG_PATH = os.path.join(_OUTPUT, 'regime_debug.json')
SYSTEM_HEALTH_PATH = os.path.join(_OUTPUT, 'system_health.json')
MINI_RULES_PATH = os.path.join(_ROOT, 'data', 'mini_scanner_rules.json')
WEEKLY_INTEL_OUTPUT = os.path.join(_OUTPUT, 'weekly_intelligence_latest.json')

MAX_TELEGRAM_LEN = 4000  # buffer under 4096


def _load_json(path, default=None):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default


def _save_json(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def _get_week_range():
    """Return (start, end) as YYYY-MM-DD strings for the past 7 days."""
    end = datetime.utcnow().date()
    start = end - timedelta(days=7)
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


def _analyze_patterns():
    """Summarize current pattern_miner findings."""
    patterns_data = _load_json(PATTERNS_PATH, default={'patterns': []})
    patterns = patterns_data.get('patterns', [])

    validated = [p for p in patterns if p.get('tier') == 'validated']
    preliminary = [p for p in patterns if p.get('tier') == 'preliminary']
    emerging = [p for p in patterns if p.get('tier') == 'emerging']

    # Top validated by absolute edge magnitude
    top_validated = sorted(
        validated,
        key=lambda p: abs(p.get('edge_pct', 0) or 0),
        reverse=True
    )[:3]

    # Baselines
    baselines = patterns_data.get('baselines', {})

    return {
        'total': len(patterns),
        'validated_count': len(validated),
        'preliminary_count': len(preliminary),
        'emerging_count': len(emerging),
        'total_resolved_signals': patterns_data.get('total_resolved_signals', 0),
        'baselines': baselines,
        'top_validated': [
            {
                'id': p.get('id'),
                'wr': p.get('wr'),
                'n': p.get('n_resolved'),
                'edge': p.get('edge_pct'),
                'direction': p.get('direction'),
                'insight': p.get('insight', '')[:100]
            }
            for p in top_validated
        ]
    }


def _analyze_proposals():
    """Summarize pending proposals."""
    data = _load_json(PROPOSED_RULES_PATH, default={'proposals': []})
    proposals = data.get('proposals', [])

    pending = [p for p in proposals if p.get('status') == 'pending']
    approved = [p for p in proposals if p.get('status') == 'approved']
    active = [p for p in proposals if p.get('status') == 'already_active']
    rejected = [p for p in proposals if p.get('status') == 'rejected']

    return {
        'total': len(proposals),
        'pending_count': len(pending),
        'approved_count': len(approved),
        'already_active_count': len(active),
        'rejected_count': len(rejected),
        'pending_items': [
            {
                'id': p.get('id'),
                'action': p.get('action'),
                'target_signal': p.get('target_signal'),
                'target_sector': p.get('target_sector'),
                'wr': p.get('evidence', {}).get('wr', 0),
                'n': p.get('evidence', {}).get('n', 0),
                'edge': p.get('evidence', {}).get('edge_pp', 0)
            }
            for p in pending[:5]
        ]
    }


def _analyze_contra_shadow():
    """Summarize contra shadow tracker progress."""
    data = _load_json(CONTRA_SHADOW_PATH, default={'shadows': []})
    shadows = data.get('shadows', [])

    resolved = [s for s in shadows if s.get('outcome') is not None]
    wins = sum(1 for s in resolved if (s.get('pnl_pct') or 0) > 0)

    avg_pnl = round(
        sum((s.get('pnl_pct') or 0) for s in resolved) / len(resolved), 2
    ) if resolved else 0

    return {
        'total': len(shadows),
        'resolved': len(resolved),
        'pending': len(shadows) - len(resolved),
        'wr': round(wins / len(resolved) * 100, 1) if resolved else 0,
        'avg_pnl': avg_pnl,
        'unlocked': len(resolved) >= 30,
        'unlock_threshold': 30,
        'recent_3': [
            {
                'symbol': s.get('symbol', '').replace('.NS', ''),
                'outcome': s.get('outcome'),
                'pnl': s.get('pnl_pct', 0)
            }
            for s in resolved[-3:]
        ]
    }


def _analyze_regime():
    """Summarize regime distribution over the week."""
    data = _load_json(REGIME_DEBUG_PATH, default={'logs': []})
    logs = data.get('logs', [])

    start_str, end_str = _get_week_range()
    week_logs = [l for l in logs
                 if start_str <= l.get('date', '') <= end_str]

    if not week_logs:
        return None

    regimes = Counter(l.get('classified_as') for l in week_logs)
    latest = week_logs[-1] if week_logs else None

    # Compute average slope over week
    slopes = [l.get('last_slope', 0) or 0 for l in week_logs if l.get('last_slope') is not None]
    avg_slope = sum(slopes) / len(slopes) if slopes else 0

    ret20s = [l.get('ret20_pct', 0) or 0 for l in week_logs if l.get('ret20_pct') is not None]
    avg_ret20 = sum(ret20s) / len(ret20s) if ret20s else 0

    return {
        'days_logged': len(week_logs),
        'regime_distribution': dict(regimes),
        'avg_slope': round(avg_slope, 5),
        'avg_ret20': round(avg_ret20, 2),
        'latest': {
            'date': latest.get('date'),
            'regime': latest.get('classified_as'),
            'slope': latest.get('last_slope'),
            'ret20': latest.get('ret20_pct'),
            'above_ema50': latest.get('last_above_ema50')
        } if latest else None
    }


def _analyze_system_health():
    """Get last system_health.json overall status."""
    data = _load_json(SYSTEM_HEALTH_PATH, default={})
    return {
        'overall': data.get('overall', 'unknown'),
        'last_validated': data.get('generated_at', 'never'),
        'checks_passed': sum(
            1 for c in data.get('checks', {}).values()
            if c.get('status') == 'ok'
        ),
        'checks_failed': sum(
            1 for c in data.get('checks', {}).values()
            if c.get('status') in ('error', 'warn')
        )
    }


def _analyze_kill_rules():
    """List currently active kill rules."""
    data = _load_json(MINI_RULES_PATH, default={})
    kills = data.get('kill_patterns', [])
    return {
        'count': len(kills),
        'rules': [
            {
                'id': k.get('id'),
                'signal': k.get('signal'),
                'sector': k.get('sector'),
                'reason': k.get('reason', '')[:60]
            }
            for k in kills
        ]
    }


def _generate_suggestions(patterns, proposals, contra, regime):
    """AI-generated suggestions based on current state."""
    suggestions = []

    # Pending proposals suggestion
    if proposals['pending_count'] > 0:
        suggestions.append(
            f"📝 {proposals['pending_count']} rule proposal(s) awaiting your review. "
            f"Use /approve_rule <id> to apply."
        )

    # Contra shadow progress
    if contra['total'] > 0 and not contra['unlocked']:
        needed = contra['unlock_threshold'] - contra['resolved']
        suggestions.append(
            f"👁 Contra shadow at {contra['resolved']}/{contra['unlock_threshold']} resolved. "
            f"{needed} more before activation decision."
        )

    # Pattern validation momentum
    if patterns['validated_count'] > 0:
        suggestions.append(
            f"🔬 {patterns['validated_count']} validated patterns found. "
            f"Review top items above."
        )

    # Regime consistency check
    if regime and regime.get('regime_distribution'):
        regime_counts = regime['regime_distribution']
        if len(regime_counts) == 1:
            dominant = list(regime_counts.keys())[0]
            suggestions.append(
                f"🌡 Market classified {dominant} every day this week. "
                f"If signal WR diverges from this, classifier may need recalibration."
            )

    # Default if all good
    if not suggestions:
        suggestions.append(
            "✅ All systems operating normally. No action needed."
        )

    return suggestions


def _format_telegram_message(summary):
    """Compose the Telegram message."""
    start, end = _get_week_range()

    lines = []
    lines.append(f"🧠 *TIE TIY Weekly Intelligence*")
    lines.append(f"_{start} to {end}_")
    lines.append("")

    # Signal baseline status
    patterns = summary['patterns']
    if patterns['baselines']:
        lines.append(f"📊 *Live Signal Baselines* (n={patterns['total_resolved_signals']})")
        for sig_type, data in patterns['baselines'].items():
            lines.append(f"  {sig_type}: {data.get('wr', 0)}% WR (n={data.get('n', 0)})")
        lines.append("")

    # Patterns
    lines.append(f"🔬 *Pattern Mining*")
    lines.append(f"Total: {patterns['total']} | Validated: {patterns['validated_count']} | Preliminary: {patterns['preliminary_count']}")
    if patterns['top_validated']:
        lines.append("\nTop validated:")
        for p in patterns['top_validated']:
            direction_emoji = '🟢' if p['direction'] == 'positive' else '🔴'
            lines.append(f"  {direction_emoji} {p['wr']}% WR n={p['n']} edge {p['edge']:+.0f}pp")
            lines.append(f"     _{p['insight']}_")
    lines.append("")

    # Kill rules active
    kills = summary['kill_rules']
    if kills['count'] > 0:
        lines.append(f"🛑 *Active Kill Rules: {kills['count']}*")
        for k in kills['rules']:
            target = k['signal']
            if k['sector']:
                target += f"+{k['sector']}"
            lines.append(f"  `{k['id']}`: {target}")
        lines.append("")

    # Proposals
    proposals = summary['proposals']
    if proposals['pending_count'] > 0:
        lines.append(f"⚡ *Pending Proposals: {proposals['pending_count']}*")
        for p in proposals['pending_items']:
            target = p['target_signal'] or ''
            if p['target_sector']:
                target += f"+{p['target_sector']}"
            lines.append(f"  `/approve_rule {p['id']}`")
            lines.append(f"     {p['action'].upper()} {target} — {p['wr']}% WR n={p['n']}")
        lines.append("")
    else:
        lines.append(f"⚡ *Rules Status*")
        lines.append(f"  Active: {proposals['already_active_count']}")
        lines.append(f"  Approved history: {proposals['approved_count']}")
        lines.append(f"  No new proposals pending.")
        lines.append("")

    # Contra shadow
    contra = summary['contra']
    if contra['total'] > 0:
        lines.append(f"👁 *Contra Shadow Research*")
        lines.append(f"Tracking: {contra['total']} | Resolved: {contra['resolved']} | Pending: {contra['pending']}")
        if contra['resolved'] > 0:
            unlock_status = "UNLOCKED ✓" if contra['unlocked'] else f"{contra['resolved']}/{contra['unlock_threshold']}"
            lines.append(f"WR: {contra['wr']}% | Avg P&L: {contra['avg_pnl']:+.2f}% | {unlock_status}")
        if contra.get('recent_3'):
            lines.append("Recent outcomes:")
            for r in contra['recent_3']:
                pnl_str = f"{r['pnl']:+.2f}%" if r['pnl'] is not None else "?"
                lines.append(f"  {r['symbol']}: {r['outcome']} {pnl_str}")
        lines.append("")

    # Regime
    regime = summary['regime']
    if regime and regime['days_logged'] > 0:
        lines.append(f"🌡 *Regime Audit ({regime['days_logged']} days)*")
        for r, count in regime['regime_distribution'].items():
            lines.append(f"  {r}: {count}d")
        if regime['latest']:
            above = "↑EMA50" if regime['latest'].get('above_ema50') else "↓EMA50"
            lines.append(f"Latest: {regime['latest']['regime']} ({above})")
            lines.append(f"  slope: {regime['latest']['slope']:+.4f}, ret20: {regime['latest']['ret20']:+.2f}%")
        lines.append("")

    # Health
    health = summary['health']
    health_emoji = '✅' if health['overall'] in ('ok', 'green') else '⚠️'
    lines.append(f"{health_emoji} *System Health: {health['overall'].upper()}*")
    lines.append(f"  Checks: {health['checks_passed']} passed, {health['checks_failed']} failed")
    lines.append("")

    # Suggestions
    lines.append(f"💡 *This Week's Focus*")
    for s in summary['suggestions']:
        lines.append(f"  {s}")
    lines.append("")

    lines.append("_Tap any /approve_rule link to apply proposal. Reply STOP to pause weekly intel._")

    message = "\n".join(lines)

    # Truncate if needed
    if len(message) > MAX_TELEGRAM_LEN:
        message = message[:MAX_TELEGRAM_LEN - 100] + "\n\n_... truncated. See weekly_intelligence_latest.json for full report._"

    return message


def generate_weekly_intelligence():
    """
    Main entry point. Generates intelligence report, saves JSON, returns Telegram message.
    """
    print("[weekly_intelligence] Generating weekly intelligence report...")

    # Analyze all sections
    patterns = _analyze_patterns()
    proposals = _analyze_proposals()
    contra = _analyze_contra_shadow()
    regime = _analyze_regime()
    health = _analyze_system_health()
    kill_rules = _analyze_kill_rules()

    suggestions = _generate_suggestions(patterns, proposals, contra, regime)

    summary = {
        'schema_version': 1,
        'generated_at': datetime.utcnow().isoformat() + "Z",
        'week_range': _get_week_range(),
        'patterns': patterns,
        'proposals': proposals,
        'contra': contra,
        'regime': regime,
        'health': health,
        'kill_rules': kill_rules,
        'suggestions': suggestions
    }

    # Save JSON (for PWA/audit)
    _save_json(WEEKLY_INTEL_OUTPUT, summary)
    print(f"[weekly_intelligence] Saved: {WEEKLY_INTEL_OUTPUT}")

    # Format Telegram message
    message = _format_telegram_message(summary)
    print(f"[weekly_intelligence] Message length: {len(message)} chars")

    return summary, message


def send_weekly_intelligence():
    """
    Generate and send via Telegram.
    Uses new send_weekly_intelligence() function in telegram_bot (added this session).
    """
    summary, message = generate_weekly_intelligence()

    try:
        from telegram_bot import send_weekly_intelligence as _send
        success = _send(message)
        if success:
            print("[weekly_intelligence] ✅ Telegram sent successfully")
        else:
            print("[weekly_intelligence] ❌ Telegram send failed")
        return success
    except ImportError as e:
        print(f"[weekly_intelligence] ❌ Could not import telegram_bot.send_weekly_intelligence: {e}")
        print("[weekly_intelligence] Message would have been:")
        print(message)
        return False
    except Exception as e:
        print(f"[weekly_intelligence] ❌ Error sending: {e}")
        return False


if __name__ == "__main__":
    # Standalone execution
    if len(sys.argv) > 1 and sys.argv[1] == '--send':
        success = send_weekly_intelligence()
        sys.exit(0 if success else 1)
    else:
        # Generate only, don't send
        summary, message = generate_weekly_intelligence()
        print("\n" + "=" * 60)
        print("WEEKLY INTELLIGENCE (dry-run)")
        print("=" * 60)
        print(message)
        print("=" * 60)
