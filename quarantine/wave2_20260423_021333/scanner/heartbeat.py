# scanner/heartbeat.py
# Simple daily heartbeat — runs at 8:30 AM IST
# Shows system status + recent workflow results
# S2: Skips on weekends and NSE holidays
# M6: Reminds to update holidays in December
# ─────────────────────────────────────────────────────

import os
import sys
import json
import requests
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from telegram_bot import send_heartbeat, send_message, _esc

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
            return json.load(f)
    except Exception:
        return {'holidays': [], 'valid_until': ''}


def _is_trading_day():
    """Returns True if today is a trading day."""
    today = date.today()
    
    # Weekend check
    if today.weekday() >= 5:
        return False
    
    # Holiday check
    holidays_data = _load_holidays()
    holidays = holidays_data.get('holidays', [])
    if today.strftime('%Y-%m-%d') in holidays:
        return False
    
    return True


def _check_holiday_reminder():
    """
    M6: Check if holidays need updating.
    Sends reminder in December if holidays expire this year.
    """
    today = date.today()
    
    # Only remind in December
    if today.month != 12:
        return
    
    # Only remind once (on Dec 1st)
    if today.day != 1:
        return
    
    holidays_data = _load_holidays()
    valid_until = holidays_data.get('valid_until', '')
    
    # Check if holidays expire this year
    if valid_until and valid_until.startswith(str(today.year)):
        try:
            lines = []
            lines.append('📅 *HOLIDAY UPDATE REMINDER*')
            lines.append('')
            lines.append(f'NSE holidays valid until: {_esc(valid_until)}')
            lines.append('')
            lines.append('Please update holidays for next year:')
            lines.append('1\\. Check nseindia\\.com for 2027 holidays')
            lines.append('2\\. Update scanner/meta\\_writer\\.py')
            lines.append('3\\. Commit and push')
            
            send_message('\n'.join(lines))
            print("[heartbeat] Holiday reminder sent")
        except Exception as e:
            print(f"[heartbeat] Holiday reminder error: {e}")


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

    # ── M6: Holiday reminder in December ──────────────
    _check_holiday_reminder()

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
