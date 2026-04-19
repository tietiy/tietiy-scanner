"""
contra_tracker.py — Contra Shadow Tracker

Purpose:
  When mini_scanner kills a DOWN_TRI+Bank signal (or any pattern in kill_patterns),
  this tracker records the INVERTED version as a shadow LONG trade.

  Based on brainstorm analysis Apr 19 2026:
  - DOWN_TRI+Bank: 0/11 WR live (all 11 shorts stopped out)
  - If INVERTED to LONG at same entry: would have been 11/11 WR, +130% total
  - This tracker validates whether that hypothesis holds going forward

Key rules:
  - is_tradeable: false (never shows in Telegram or PWA as actionable)
  - is_shadow: true (clearly marked as research, not real signal)
  - Resolves via outcome_evaluator same as real signals
  - Unlocks for review after n=30 (per stats.js gate)

Schema:
  Each record in output/contra_shadow.json matches structure below.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

CONTRA_SHADOW_PATH = "output/contra_shadow.json"
SCHEMA_VERSION = 1


def _load_contra_shadow():
    """Load existing contra_shadow.json or return fresh structure."""
    if not os.path.exists(CONTRA_SHADOW_PATH):
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": None,
            "description": "Shadow tracker for INVERTED versions of kill_switch rejected signals. Research only, never actionable.",
            "total_tracked": 0,
            "resolved_count": 0,
            "pending_count": 0,
            "shadows": []
        }

    try:
        with open(CONTRA_SHADOW_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        print(f"[contra_tracker] Warning: {CONTRA_SHADOW_PATH} corrupt, reinitializing")
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": None,
            "description": "Shadow tracker for INVERTED versions of kill_switch rejected signals. Research only, never actionable.",
            "total_tracked": 0,
            "resolved_count": 0,
            "pending_count": 0,
            "shadows": []
        }


def _save_contra_shadow(data):
    """Save contra_shadow.json atomically."""
    data["generated_at"] = datetime.utcnow().isoformat() + "Z"

    tmp_path = CONTRA_SHADOW_PATH + ".tmp"
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2)

    os.replace(tmp_path, CONTRA_SHADOW_PATH)


def _calculate_inverted_trade(rejected_signal):
    """
    Build the inverted shadow trade from a rejected DOWN_TRI signal.

    Original DOWN_TRI SHORT:
      - Entry: scan_price (expects price to go DOWN from here)
      - Stop: pivot_high + 1 ATR (stopped out if price goes UP)
      - Target: scan_price - 2R (profits if price falls)

    Inverted LONG (what we're tracking):
      - Entry: scan_price (expects price to go UP from here — data suggests it does)
      - Stop: pivot_high + 0.5 ATR (tighter than original stop for better R:R)
      - Target: entry + 1.5R (conservative profit target)
    """
    entry = rejected_signal.get('entry') or rejected_signal.get('scan_price')
    if entry is None:
        return None

    # Stop: where the inverted LONG is invalidated
    # Use the original DOWN_TRI stop (which was ABOVE entry) minus a bit tighter
    pivot_price = rejected_signal.get('pivot_price')
    atr = rejected_signal.get('atr') or 0

    if pivot_price and atr:
        # Stop below pivot high, tighter than original DOWN_TRI stop
        # Original DOWN_TRI stop was pivot_high + 1*ATR (above entry)
        # Inverted LONG stop should be below entry — use entry - 1*ATR
        stop = entry - atr
    else:
        # Fallback: 5% below entry
        stop = entry * 0.95

    # Risk per share
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return None

    # Target: 1.5R above entry (conservative)
    target = entry + (1.5 * risk_per_share)

    return {
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk_per_share": round(risk_per_share, 2),
        "rr_ratio": 1.5
    }


def record_contra_shadow(rejected_signal, kill_rule_id=None):
    """
    Record an inverted shadow trade when kill_switch rejects a signal.

    Args:
      rejected_signal: dict, the original signal that was rejected
      kill_rule_id: str, the ID of the kill rule that triggered (e.g., "kill_001")

    Returns:
      dict: the shadow record created, or None if skipped
    """
    # Only track signals that pass the inversion criteria
    # For now: only DOWN_TRI (inverting SHORT to LONG makes sense)
    # Could expand later to handle other signal types
    original_signal = rejected_signal.get('signal', '')
    if not original_signal.startswith('DOWN_TRI'):
        return None

    # Build inverted trade parameters
    inverted = _calculate_inverted_trade(rejected_signal)
    if inverted is None:
        return None

    # Build shadow record
    symbol = rejected_signal.get('symbol', '')
    date = rejected_signal.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    sector = rejected_signal.get('sector', 'Unknown')

    shadow_id = f"contra_{date}-{symbol.replace('.NS', '')}-{original_signal}"

    shadow_record = {
        "id": shadow_id,
        "origin_signal_id": rejected_signal.get('id', ''),
        "origin_signal_type": original_signal,
        "origin_signal_direction": rejected_signal.get('direction', 'SHORT'),
        "kill_rule_id": kill_rule_id,

        # Trade details (INVERTED)
        "symbol": symbol,
        "sector": sector,
        "date": date,
        "direction": "LONG",  # INVERTED
        "entry": inverted["entry"],
        "stop": inverted["stop"],
        "target": inverted["target"],
        "risk_per_share": inverted["risk_per_share"],
        "rr_ratio": inverted["rr_ratio"],

        # Context from original signal
        "original_score": rejected_signal.get('score'),
        "original_stop": rejected_signal.get('stop'),
        "regime": rejected_signal.get('regime'),
        "age": rejected_signal.get('age'),
        "grade": rejected_signal.get('grade'),
        "atr": rejected_signal.get('atr'),

        # Tracking windows (same as real signals)
        "exit_date": rejected_signal.get('exit_date'),
        "effective_exit_date": None,
        "tracking_start": None,
        "tracking_end": None,

        # Outcome fields (populated by outcome_evaluator)
        "outcome": None,
        "outcome_date": None,
        "outcome_price": None,
        "pnl_pct": None,
        "mfe_pct": None,
        "mae_pct": None,
        "day6_open": None,

        # Shadow flags
        "is_shadow": True,
        "is_tradeable": False,
        "hypothesis": "DOWN_TRI+Bank consistently fails live (0/11 WR). Data suggests INVERTED LONG may succeed. Tracking for n=30 samples before any activation decision.",
        "shadow_version": "v1",

        # Metadata
        "recorded_at": datetime.utcnow().isoformat() + "Z",
        "schema_version": SCHEMA_VERSION
    }

    # Save to contra_shadow.json
    data = _load_contra_shadow()

    # Check for duplicates (same symbol + date combo)
    existing_ids = {s.get('id') for s in data.get('shadows', [])}
    if shadow_id in existing_ids:
        print(f"[contra_tracker] Shadow already exists: {shadow_id}")
        return None

    data['shadows'].append(shadow_record)
    data['total_tracked'] = len(data['shadows'])
    data['resolved_count'] = sum(
        1 for s in data['shadows'] if s.get('outcome') is not None
    )
    data['pending_count'] = data['total_tracked'] - data['resolved_count']

    _save_contra_shadow(data)

    print(f"[contra_tracker] Recorded shadow: {shadow_id}")
    print(f"  Direction: {original_signal} (SHORT) → INVERTED to LONG")
    print(f"  Entry: {inverted['entry']} | Stop: {inverted['stop']} | Target: {inverted['target']}")
    print(f"  Total tracked: {data['total_tracked']} (resolved: {data['resolved_count']}, pending: {data['pending_count']})")

    return shadow_record


def get_active_shadows():
    """
    Return list of shadow trades still needing resolution.
    Used by outcome_evaluator to know which shadows to resolve.
    """
    data = _load_contra_shadow()
    return [s for s in data.get('shadows', []) if s.get('outcome') is None]


def update_shadow_outcome(shadow_id, outcome_data):
    """
    Update a shadow record with its resolved outcome.
    Called by outcome_evaluator after running Day 6 logic on shadows.

    Args:
      shadow_id: str, the shadow's id field
      outcome_data: dict with outcome, outcome_price, pnl_pct, mfe_pct, mae_pct, etc.
    """
    data = _load_contra_shadow()

    updated = False
    for shadow in data.get('shadows', []):
        if shadow.get('id') == shadow_id:
            shadow.update(outcome_data)
            shadow['resolved_at'] = datetime.utcnow().isoformat() + "Z"
            updated = True
            break

    if updated:
        data['resolved_count'] = sum(
            1 for s in data['shadows'] if s.get('outcome') is not None
        )
        data['pending_count'] = data['total_tracked'] - data['resolved_count']
        _save_contra_shadow(data)
        print(f"[contra_tracker] Resolved shadow: {shadow_id}")
        return True
    else:
        print(f"[contra_tracker] Shadow not found: {shadow_id}")
        return False


def get_summary_stats():
    """
    Compute summary statistics for stats.js to display.
    Returns dict with WR, n, avg_pnl, etc.
    """
    data = _load_contra_shadow()
    shadows = data.get('shadows', [])

    resolved = [s for s in shadows if s.get('outcome') is not None]
    n = len(resolved)

    if n == 0:
        return {
            "total_tracked": len(shadows),
            "resolved": 0,
            "pending": len(shadows),
            "wr": None,
            "avg_pnl": None,
            "unlocked": False,
            "unlock_threshold": 30,
            "message": "Insufficient data. Need n=30 resolved shadows."
        }

    wins = sum(1 for s in resolved if (s.get('pnl_pct') or 0) > 0)
    wr = (wins / n) * 100
    avg_pnl = sum((s.get('pnl_pct') or 0) for s in resolved) / n

    return {
        "total_tracked": len(shadows),
        "resolved": n,
        "pending": len(shadows) - n,
        "wr": round(wr, 1),
        "avg_pnl": round(avg_pnl, 2),
        "unlocked": n >= 30,
        "unlock_threshold": 30,
        "message": f"n={n}/30 resolved" + (" — UNLOCKED" if n >= 30 else " — locked")
    }


if __name__ == "__main__":
    # Standalone test
    print("[contra_tracker] Standalone test mode")
    print("Current stats:")
    print(json.dumps(get_summary_stats(), indent=2))
    print("\nActive shadows:")
    active = get_active_shadows()
    for s in active[:5]:
        print(f"  {s['id']}: {s['symbol']} LONG @ {s['entry']}")
