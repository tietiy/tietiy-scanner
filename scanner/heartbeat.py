# scanner/heartbeat.py
# Simple daily heartbeat — runs at 8:30 AM IST
# Shows system status + recent workflow results
# S2: Skips on weekends and NSE holidays
# ─────────────────────────────────────────────────────

import os
import sys
import json
import requests
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from telegram_bot import send_heartbeat

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

META_FILE     = os.path.join(_OUTPUT, 'meta.json')
HOLIDAYS_FILE = os.path.join(_OUTPUT, 'nse_holidays.json')

GH_TOKEN = os.environ.get('GH_TOKEN', '')
GH_REPO  = os.environ.get('GH_REPO', 'tietiy/tietiy-scanner')


def _load_holidays():
    """Load NSE holidays list."""
    try:
        with open(HOLIDAYS_FILE, 'r') as f:
            return json.load(f).get('holidays', [])
    except Exception:
        return []


def _is_trading_day():
    """Returns True if today is a trading day."""
    today = date.today()
    
    # Weekend check
    if today.weekday() >= 5:
        return False
    
    # Holiday check
    holidays = _load_holidays()
    if today.strftime('%Y-%m-%d') in holidays:
        return False
    
    return True


def _get_workflow_status():
    """
    Fetch last 5 workflow runs from GitHub API.
    Returns string like "✅✅✅❌✅" or None if error.
    """
    if not GH_TOKEN:
        print("[heartbeat] No GH_TOKEN — skipping workflow status")
        return None

    url = f"https://api.github.com/repos/{GH_REPO}/actions/runs"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {
        "per_page": 5,
        "status": "completed",
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        runs = data.get("workflow_runs", [])
        if not runs:
            return None

        icons = []
        for run in runs[:5]:
            conclusion = run.get("conclusion", "")
            if conclusion == "success":
                icons.append("✅")
            elif conclusion == "failure":
                icons.append("❌")
            elif conclusion == "cancelled":
                icons.append("⏹️")
            else:
                icons.append("⚪")

        return "".join(icons)

    except Exception as e:
        print(f"[heartbeat] GitHub API error: {e}")
        return None


def run_heartbeat():
    print("[heartbeat] Starting...")

    # ── S2: Skip on non-trading days ──────────────────
    if not _is_trading_day():
        print(f"[heartbeat] Non-trading day ({date.today()}) — skipping")
        return

    # Load meta.json
    meta = {}
    try:
        with open(META_FILE, 'r') as f:
            meta = json.load(f)
        print(f"[heartbeat] Meta loaded: {meta.get('market_date', '?')}")
    except Exception as e:
        print(f"[heartbeat] Meta load error: {e}")

    # Get workflow status
    workflow_status = _get_workflow_status()
    if workflow_status:
        meta['workflow_status'] = workflow_status
        print(f"[heartbeat] Workflow status: {workflow_status}")

    # Mark as trading day for message
    meta['is_trading_day'] = True

    # Send heartbeat
    try:
        send_heartbeat(meta)
        print("[heartbeat] Telegram sent")
    except Exception as e:
        print(f"[heartbeat] Telegram error: {e}")

    print("[heartbeat] Done")


if __name__ == '__main__':
    run_heartbeat()
