# scanner/heartbeat.py
# Simple daily heartbeat — runs at 8:30 AM IST
# ─────────────────────────────────────────────────────

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from telegram_bot import send_heartbeat

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

META_FILE = os.path.join(_OUTPUT, 'meta.json')


def run_heartbeat():
    print("[heartbeat] Starting...")
    
    # Load meta.json
    meta = {}
    try:
        with open(META_FILE, 'r') as f:
            meta = json.load(f)
        print(f"[heartbeat] Meta loaded: {meta.get('market_date', '?')}")
    except Exception as e:
        print(f"[heartbeat] Meta load error: {e}")
    
    # Send heartbeat
    try:
        send_heartbeat(meta)
        print("[heartbeat] Telegram sent")
    except Exception as e:
        print(f"[heartbeat] Telegram error: {e}")
    
    print("[heartbeat] Done")


if __name__ == '__main__':
    run_heartbeat()
