# ── meta_writer.py ───────────────────────────────────
# Writes meta.json and nse_holidays.json to output/
# MUST be called last in main.py after all other writes
# Owns these two files exclusively
#
# ADDED: active_signals_count — total PENDING signals
#        separate from signals_found (new today only)
#        Frontend status bar reads this for display.
#
# SESSION 3 ADDITION (Apr 19 2026):
#   SM1 — sector_momentum kwarg.
#         Accepts dict of {sector_name: "Leading"/"Neutral"/"Lagging"}
#         from main.py's get_sector_momentum() function.
#         Exposed in meta.json so PWA can render all 8
#         sectors (Bank Nifty, IT, Pharma, Auto, Metal,
#         Energy, FMCG, Infra) as status row.
#         schema_version bumped 4 → 5 so PWA can detect
#         the new field's presence.
# ─────────────────────────────────────────────────────

import json
import os
from datetime import datetime, timezone

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
    active_signals_count,
    is_trading_day,
    scanner_version,
    app_version,
    fetch_failed=None,
    insufficient_data=None,
    corporate_action_skip=None,
    history_record_count=0,
    sector_momentum=None,
):
    """
    Writes meta.json to output_dir.
    Called last in main.py after all other writes.

    Parameters:
        output_dir            : str  path to output/
        market_date           : str  'YYYY-MM-DD'
        regime                : str  'Bull'/'Bear'/'Neutral'
        universe_size         : int  total stocks scanned
        signals_found         : int  NEW signals today
        active_signals_count  : int  total PENDING signals
        is_trading_day        : bool
        scanner_version       : str  e.g. 'v2.0'
        app_version           : str  e.g. '2.0'
        fetch_failed          : list symbols that failed
        insufficient_data     : list symbols with <60 bars
        corporate_action_skip : list symbols skipped for CA
        history_record_count  : int  total records in history
        sector_momentum       : dict {sector: status} where
                                status is "Leading"/"Neutral"/"Lagging"
                                (SM1 — Session 3 addition)
    """

    fetch_failed          = fetch_failed or []
    insufficient_data     = insufficient_data or []
    corporate_action_skip = corporate_action_skip or []
    sector_momentum       = sector_momentum or {}

    now_utc = datetime.now(timezone.utc)

    meta = {
        "last_scan":             now_utc.strftime(
                                     '%Y-%m-%dT%H:%M:%SZ'),
        "deployed_at":           None,
        "market_date":           market_date,
        "regime":                regime,
        "universe_size":         universe_size,

        # signals_found = new signals detected today
        # active_signals_count = total PENDING signals
        # Status bar should show active_signals_count
        "signals_found":         signals_found,
        "active_signals_count":  active_signals_count,

        "is_trading_day":        is_trading_day,
        "scanner_version":       scanner_version,
        "app_version":           app_version,
        "schema_version":        5,
        "holidays_valid_until":  "2026-12-31",
        "fetch_failed":          fetch_failed,
        "insufficient_data":     insufficient_data,
        "corporate_action_skip": corporate_action_skip,
        "history_record_count":  history_record_count,

        # SM1: Session 3 — all 8 sectors status
        # Keys: Bank, IT, Pharma, Auto, Metal, Energy, FMCG, Infra
        # Values: "Leading" / "Neutral" / "Lagging"
        "sector_momentum":       sector_momentum,
    }

    meta_path = os.path.join(
        output_dir, 'meta.json')
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
        "valid_until": "2026-12-31",
        "holidays":    NSE_HOLIDAYS_2026,
    }

    path = os.path.join(
        output_dir, 'nse_holidays.json')
    with open(path, 'w') as f:
        json.dump(holidays, f, indent=2)

    print(f"nse_holidays.json written → {path}")
