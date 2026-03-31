# ── meta_writer.py ───────────────────────────────────
# Writes meta.json and nse_holidays.json to output/
# MUST be called last in main.py after all other writes
# Owns these two files exclusively — nothing else writes them
# ─────────────────────────────────────────────────────

import json
import os
from datetime import datetime, timezone

# ── STEP 1 CHANGE 1 ──────────────────────────────────
# NSE holidays 2026
# ⚠️ UPDATE EVERY DECEMBER FOR NEXT YEAR
# Source: nseindia.com/regulations/holiday-master
NSE_HOLIDAYS_2026 = [
    "2026-01-26",  # Republic Day
    "2026-03-31",  # Eid ul-Fitr
    "2026-04-02",  # Ram Navami
    "2026-04-06",  # Mahavir Jayanti
    "2026-04-10",  # Good Friday
    "2026-04-14",  # Dr. Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-08-15",  # Independence Day
    "2026-08-27",  # Ganesh Chaturthi
    "2026-10-02",  # Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-04",  # Diwali Laxmi Puja
    "2026-11-05",  # Diwali Balipratipada
    "2026-11-25",  # Gurunanak Jayanti
    "2026-12-25",  # Christmas
]


def write_meta(
    output_dir,
    market_date,
    regime,
    universe_size,
    signals_found,
    is_trading_day,
    scanner_version,
    app_version,
    fetch_failed=None,
    insufficient_data=None,
    corporate_action_skip=None,
    history_record_count=0,
):
    """
    Writes meta.json to output_dir.
    Called last in main.py after all other writes.

    Parameters:
        output_dir          : str  path to output/
        market_date         : str  'YYYY-MM-DD'
        regime              : str  'Bull'/'Bear'/'Neutral'
        universe_size       : int  total stocks scanned
        signals_found       : int  deploy signals count
        is_trading_day      : bool
        scanner_version     : str  e.g. 'v2.0'
        app_version         : str  e.g. '2.0'
        fetch_failed        : list symbols that failed fetch
        insufficient_data   : list symbols with <60 bars
        corporate_action_skip: list symbols skipped for CA
        history_record_count: int  total records in history
    """

    fetch_failed          = fetch_failed or []
    insufficient_data     = insufficient_data or []
    corporate_action_skip = corporate_action_skip or []

    now_utc = datetime.now(timezone.utc)

    meta = {
        "last_scan":              now_utc.strftime(
                                      '%Y-%m-%dT%H:%M:%SZ'),
        "deployed_at":            None,
        "market_date":            market_date,
        "regime":                 regime,
        "universe_size":          universe_size,
        "signals_found":          signals_found,
        "is_trading_day":         is_trading_day,
        "scanner_version":        scanner_version,
        "app_version":            app_version,
        "schema_version":         4,
        "holidays_valid_until":   "2026-12-31",
        "fetch_failed":           fetch_failed,
        "insufficient_data":      insufficient_data,
        "corporate_action_skip":  corporate_action_skip,
        "history_record_count":   history_record_count,
    }

    meta_path = os.path.join(output_dir, 'meta.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)

    print(f"meta.json written → {meta_path}")


def write_holidays(output_dir):
    """
    Writes nse_holidays.json to output_dir.
    Called once per scan from main.py.
    JS reads this for Day X/6 counter calculations.
    """

    holidays = {
        "valid_until":  "2026-12-31",
        "holidays":     NSE_HOLIDAYS_2026,
    }

    path = os.path.join(output_dir, 'nse_holidays.json')
    with open(path, 'w') as f:
        json.dump(holidays, f, indent=2)

    print(f"nse_holidays.json written → {path}")
