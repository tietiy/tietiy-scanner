# ── push_sender.py ───────────────────────────────────
# Sends Web Push notifications to all subscribed devices
# Called from main.py after morning scan completes
# Uses VAPID keys stored in GitHub Secrets
#
# SETUP REQUIRED (one time only):
# 1. Generate VAPID keys — instructions below
# 2. Add to GitHub Secrets:
#    VAPID_PRIVATE_KEY  → private key string
#    VAPID_PUBLIC_KEY   → public key string
#    VAPID_CLAIM_EMAIL  → your email address
# 3. subscriptions.json in output/ stores device tokens
#    Written by sw.js when user grants permission
#
# HOW TO GENERATE VAPID KEYS (one time):
# pip install py-vapid
# python -c "
# from py_vapid import Vapid
# v = Vapid()
# v.generate_keys()
# print('PRIVATE:', v.private_key)
# print('PUBLIC:', v.public_key)
# "
# Copy both keys to GitHub Secrets
# ─────────────────────────────────────────────────────

import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(__file__))

# ── PATHS ─────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_ROOT    = os.path.dirname(_HERE)
_OUTPUT  = os.path.join(_ROOT, 'output')

SUBS_FILE = os.path.join(_OUTPUT, 'subscriptions.json')

# ── ENVIRONMENT ───────────────────────────────────────
VAPID_PRIVATE_KEY  = os.environ.get(
    'VAPID_PRIVATE_KEY', '')
VAPID_PUBLIC_KEY   = os.environ.get(
    'VAPID_PUBLIC_KEY', '')
VAPID_CLAIM_EMAIL  = os.environ.get(
    'VAPID_CLAIM_EMAIL', 'admin@tietiy.com')

# PIN gate — only devices that subscribed with
# correct PIN receive notifications
# Set PUSH_PIN in GitHub Secrets
# Set same PIN in app.js PUSH_PIN constant
PUSH_PIN = os.environ.get('PUSH_PIN', '')


# ── LOAD SUBSCRIPTIONS ────────────────────────────────

def _load_subscriptions():
    """
    Load device subscriptions from subscriptions.json.
    Returns empty list if file missing or corrupt.

    Each subscription looks like:
    {
      "endpoint": "https://fcm.googleapis.com/...",
      "keys": {
        "p256dh": "...",
        "auth":   "..."
      },
      "pin_verified": true,
      "subscribed_at": "2026-04-01"
    }
    """
    if not os.path.exists(SUBS_FILE):
        print("[push_sender] subscriptions.json "
              "not found — no devices subscribed yet")
        return []

    try:
        with open(SUBS_FILE, 'r') as f:
            data = json.load(f)
        subs = data.get('subscriptions', [])

        # Filter: only PIN-verified subscriptions
        if PUSH_PIN:
            verified = [
                s for s in subs
                if s.get('pin_verified', False)
            ]
            print(f"[push_sender] "
                  f"{len(verified)} verified devices "
                  f"of {len(subs)} total")
            return verified

        return subs

    except Exception as e:
        print(f"[push_sender] Load error: {e}")
        return []


def _remove_invalid_subscription(endpoint):
    """
    Remove a subscription that returned 410 Gone.
    410 = device unsubscribed or token expired.
    Keeps subscriptions.json clean.
    """
    if not os.path.exists(SUBS_FILE):
        return
    try:
        with open(SUBS_FILE, 'r') as f:
            data = json.load(f)

        subs = data.get('subscriptions', [])
        before = len(subs)
        subs = [
            s for s in subs
            if s.get('endpoint') != endpoint
        ]
        data['subscriptions'] = subs

        with open(SUBS_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"[push_sender] Removed expired "
              f"subscription. "
              f"{before} → {len(subs)} devices")
    except Exception as e:
        print(f"[push_sender] Remove sub error: {e}")


# ── BUILD NOTIFICATION PAYLOAD ────────────────────────

def _build_payload(signals, regime,
                   universe_size, scan_time):
    """
    Build the notification payload.
    Kept short — push notifications have size limits.

    Returns dict with title, body, data fields.
    """
    count = len(signals)

    if count == 0:
        title = "TIE TIY Scanner 📊"
        body  = (f"No signals today · "
                 f"{regime} regime · "
                 f"{universe_size} stocks scanned")
    elif count == 1:
        sig   = signals[0]
        sym   = sig.get('symbol', '').replace(
            '.NS', '')
        stype = sig.get('signal', '')
        title = f"TIE TIY — 1 Signal 📊"
        body  = (f"{sym} · {stype} · "
                 f"{regime} · {scan_time} IST")
    else:
        # Get top 3 symbols
        top_syms = [
            s.get('symbol', '').replace('.NS', '')
            for s in signals[:3]
        ]
        sym_str  = ', '.join(top_syms)
        more     = (f" +{count - 3} more"
                    if count > 3 else '')
        title    = f"TIE TIY — {count} Signals 📊"
        body     = (f"{sym_str}{more} · "
                    f"{regime} · {scan_time} IST")

    return {
        "title":   title,
        "body":    body,
        "icon":    "/icon-192.png",
        "badge":   "/badge-72.png",
        "url":     "https://tietiy.github.io"
                   "/tietiy-scanner/",
        "tag":     "tietiy-daily-scan",
        "renotify": True,
        "data": {
            "signal_count": count,
            "regime":       regime,
            "scan_date":    date.today().isoformat(),
        }
    }


# ── SEND NOTIFICATION ─────────────────────────────────

def _send_one(subscription, payload_json,
              vapid_claims):
    """
    Send push notification to one subscription.
    Uses pywebpush library.

    Returns:
        True  — sent successfully
        False — failed
        None  — subscription expired (410)
    """
    try:
        from pywebpush import webpush, WebPushException

        webpush(
            subscription_info = subscription,
            data              = payload_json,
            vapid_private_key = VAPID_PRIVATE_KEY,
            vapid_claims      = vapid_claims,
        )
        return True

    except Exception as e:
        err_str = str(e)

        # 410 Gone = subscription expired
        if '410' in err_str:
            endpoint = subscription.get(
                'endpoint', '')
            print(f"[push_sender] 410 Gone — "
                  f"removing expired subscription")
            _remove_invalid_subscription(endpoint)
            return None

        # 401 = VAPID key issue
        if '401' in err_str:
            print(f"[push_sender] 401 Unauthorized — "
                  f"check VAPID keys in GitHub Secrets")
            return False

        # 400 = malformed subscription
        if '400' in err_str:
            print(f"[push_sender] 400 Bad Request — "
                  f"malformed subscription")
            return False

        print(f"[push_sender] Send error: {e}")
        return False


# ── MAIN FUNCTION ─────────────────────────────────────

def send_notifications(signals, regime,
                       universe_size):
    """
    Main entry point. Called from main.py.

    Parameters:
        signals       : list of signal dicts
        regime        : str 'Bull'/'Bear'/'Neutral'
        universe_size : int total stocks scanned
    """

    # Check VAPID keys configured
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        print("[push_sender] VAPID keys not configured "
              "— skipping push notifications")
        print("[push_sender] Add VAPID_PRIVATE_KEY and "
              "VAPID_PUBLIC_KEY to GitHub Secrets")
        return

    # Load subscriptions
    subscriptions = _load_subscriptions()

    if not subscriptions:
        print("[push_sender] No subscriptions — "
              "nothing to send")
        return

    # Build payload
    scan_time = datetime.utcnow().strftime('%H:%M')
    ist_hour  = (datetime.utcnow().hour + 5) % 24
    ist_min   = (datetime.utcnow().minute + 30) % 60
    if datetime.utcnow().minute + 30 >= 60:
        ist_hour = (ist_hour + 1) % 24
    scan_time_ist = f"{ist_hour:02d}:{ist_min:02d}"

    payload      = _build_payload(
        signals, regime, universe_size, scan_time_ist)
    payload_json = json.dumps(payload)

    vapid_claims = {
        "sub": f"mailto:{VAPID_CLAIM_EMAIL}"
    }

    # Send to all subscriptions
    sent    = 0
    failed  = 0
    expired = 0

    print(f"[push_sender] Sending to "
          f"{len(subscriptions)} devices...")

    for sub in subscriptions:
        result = _send_one(
            sub, payload_json, vapid_claims)

        if result is True:
            sent += 1
        elif result is None:
            expired += 1
        else:
            failed += 1

    print(f"[push_sender] Done → "
          f"Sent:{sent} "
          f"Failed:{failed} "
          f"Expired:{expired}")


# ── DEPENDENCY CHECK ──────────────────────────────────

def check_dependencies():
    """
    Check pywebpush is installed.
    Called at top of main.py before scan starts.
    """
    try:
        import pywebpush
        return True
    except ImportError:
        print("[push_sender] pywebpush not installed")
        print("[push_sender] Add to requirements.txt: "
              "pywebpush>=1.14.0")
        return False


# ── ENTRY POINT ───────────────────────────────────────

if __name__ == '__main__':
    print("[push_sender] Test mode")
    test_signals = [{
        'symbol':  'TEST.NS',
        'signal':  'UP_TRI',
        'score':   8,
    }]
    send_notifications(
        test_signals, 'Bear', 187)
