# scanner/alert_failure.py
# Called by workflows on failure
# ─────────────────────────────────────────────────────

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from telegram_bot import send_workflow_failure


def main():
    workflow = os.environ.get('WORKFLOW_NAME', 'Unknown')
    run_url  = os.environ.get('RUN_URL', '')
    
    print(f"[alert_failure] Workflow: {workflow}")
    print(f"[alert_failure] Run URL: {run_url}")
    
    try:
        send_workflow_failure(workflow, run_url)
        print("[alert_failure] Telegram sent")
    except Exception as e:
        print(f"[alert_failure] Telegram error: {e}")


if __name__ == '__main__':
    main()
