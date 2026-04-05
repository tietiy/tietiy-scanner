# ── ban_fetcher.py ───────────────────────────────────
# Fetches NSE F&O ban list daily
# Called from main.py morning scan
# Writes output/banned_stocks.json
#
# Ban list = stocks in F&O ban period
# These stocks cannot have new F&O positions
# Signal still fires — card shows ⛔ BAN warning
# Trader decides — system informs only
#
# Source: NSE archives daily CSV
# Falls back to empty list if fetch fails
# Never crashes morning scan
# ─────────────────────────────────────────────────────

import os
import sys
import json
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import OUTPUT_DIR

# ── NSE BAN LIST URL ──────────────────────────────────
# NSE publishes this daily before market open
# URL stable since 2019 — fallback if it changes
NSE_BAN_URL = (
    'https://nsearchives.nseindia.com'
    '/content/fo/fo_secban.csv'
)

# NSE requires browser-like headers + session cookies
NSE_HOME    = 'https://www.nseindia.com'
NSE_HEADERS = {
    'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36',
    'Accept':
        'text/html,application/xhtml+xml,'
        'application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer':         'https://www.nseindia.com',
    'Connection':      'keep-alive',
}

BANNED_FILE = os.path.join(
    OUTPUT_DIR, 'banned_stocks.json')


# ── FETCH ─────────────────────────────────────────────

def _fetch_ban_csv():
    """
    Fetches the F&O ban CSV from NSE.
    Returns list of banned symbols (without .NS suffix).
    Returns empty list on any failure — never raises.
    """
    try:
        session = requests.Session()

        # Hit NSE home first to get session cookies
        # NSE blocks direct CSV requests without cookies
        session.get(
            NSE_HOME,
            headers = NSE_HEADERS,
            timeout = 15,
        )

        # Now fetch the ban CSV
        r = session.get(
            NSE_BAN_URL,
            headers = NSE_HEADERS,
            timeout = 15,
        )

        if r.status_code != 200:
            print(f"[ban] NSE returned "
                  f"{r.status_code}")
            return []

        # Parse CSV
        # Format: Symbol,Series,Date,...
        # First line is header
        lines   = r.text.strip().split('\n')
        banned  = []

        for line in lines[1:]:  # skip header
            parts = line.strip().split(',')
            if not parts:
                continue
            sym = parts[0].strip()
            if sym:
                banned.append(sym)

        print(f"[ban] Fetched {len(banned)} "
              f"banned stocks from NSE")
        return banned

    except requests.exceptions.Timeout:
        print("[ban] NSE request timed out")
        return []
    except Exception as e:
        print(f"[ban] Fetch error: {e}")
        return []


# ── WRITE ─────────────────────────────────────────────

def write_ban_list():
    """
    Fetches ban list and writes to
    output/banned_stocks.json

    Called from main.py run_morning_scan()
    before signal detection so cards can
    show ban warnings immediately.

    Returns list of banned symbols for
    use in morning scan if needed.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    banned = _fetch_ban_csv()
    today  = datetime.now().strftime('%Y-%m-%d')

    data = {
        'date':    today,
        'count':   len(banned),
        'banned':  banned,
        'note':    'Stocks in F&O ban period. '
                   'New positions not allowed.',
    }

    try:
        with open(BANNED_FILE, 'w') as f:
            json.dump(data, f,
                      indent=2, default=str)
        print(f"[ban] banned_stocks.json written "
              f"→ {len(banned)} stocks")
    except Exception as e:
        print(f"[ban] Write error: {e}")

    return banned


# ── QUERY ─────────────────────────────────────────────

def is_banned(symbol):
    """
    Returns True if symbol is currently banned.
    symbol can be with or without .NS suffix.
    """
    try:
        if not os.path.exists(BANNED_FILE):
            return False
        with open(BANNED_FILE, 'r') as f:
            data = json.load(f)
        sym_clean = symbol.replace('.NS', '')
        return sym_clean in data.get('banned', [])
    except Exception:
        return False


# ── ENTRY POINT ───────────────────────────────────────
if __name__ == '__main__':
    write_ban_list()
