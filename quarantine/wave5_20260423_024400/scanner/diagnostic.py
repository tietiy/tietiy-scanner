# scanner/diagnostic.py
# Unified diagnostic tool for TIE TIY Scanner
# Replaces health_check.py and verify_fixes.py
#
# Usage:
#   python scanner/diagnostic.py              # Full check
#   python scanner/diagnostic.py --quick      # Quick check
#   python scanner/diagnostic.py --telegram   # Send report
#   python scanner/diagnostic.py --heal       # Check + heal
#   python scanner/diagnostic.py --heal --telegram
#
# Exit codes:
#   0 = PASS, 1 = WARNING, 2 = FAIL
#
# V1 FIXES APPLIED:
# - M8  : check_staleness() — per-file mtime + content
#         date freshness checks with specific thresholds
# - M13 : attempt_self_heal() — safe auto-fixes:
#         schema V5 migration, generation backfill,
#         target price backfill. --heal CLI flag.
# BUG FIX: to_telegram() strips divider lines that
#          contain raw dashes breaking MarkdownV2
# ─────────────────────────────────────────────────────

import os
import sys
import json
import argparse
from datetime import date, datetime, timedelta

# ── PATH SETUP ────────────────────────────────────────
_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')
_DATA   = os.path.join(_ROOT, 'data')

sys.path.insert(0, _HERE)

# ── OPTIONAL IMPORTS ──────────────────────────────────
try:
    from telegram_bot import send_message
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    from calendar_utils import is_trading_day
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

try:
    import journal as _journal
    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False


# ── CONSTANTS ─────────────────────────────────────────
REQUIRED_FILES = [
    'signal_history.json',
    'scan_log.json',
    'meta.json',
]

OPTIONAL_FILES = [
    'mini_log.json',
    'rejected_log.json',
    'open_prices.json',
    'eod_prices.json',
    'stop_alerts.json',
    'ltp_prices.json',
    'banned_stocks.json',
    'nse_holidays.json',
    'signal_archive.json',
]

HISTORY_REQUIRED_FIELDS = [
    'id', 'date', 'symbol', 'signal', 'direction',
    'entry', 'stop', 'score', 'result',
]

VALID_SIGNALS  = [
    'UP_TRI', 'DOWN_TRI', 'BULL_PROXY',
    'UP_TRI_SA', 'DOWN_TRI_SA',
]
VALID_RESULTS  = [
    'PENDING', 'WON', 'STOPPED',
    'EXITED', 'REJECTED',
]
SCHEMA_VERSION = 5

# ── M8: STALENESS THRESHOLDS ──────────────────────────
_STALENESS_RULES = [
    ('meta.json',             8,   True),
    ('scan_log.json',         8,   True),
    ('signal_history.json',   48,  False),
    ('ltp_prices.json',       2,   True),
    ('open_prices.json',      8,   True),
    ('eod_prices.json',       8,   True),
    ('stop_alerts.json',      6,   True),
]

_MARKET_OPEN_UTC_H  = 3
_MARKET_CLOSE_UTC_H = 10


# ── REPORT BUILDER ────────────────────────────────────
class DiagnosticReport:
    def __init__(self):
        self.checks     = []
        self.passed     = 0
        self.warnings   = 0
        self.failed     = 0
        self.heals      = []
        self.start_time = datetime.now()

    def add(self, name, status, detail=None):
        self.checks.append({
            'name':   name,
            'status': status,
            'detail': detail,
        })
        if status == 'PASS':
            self.passed   += 1
        elif status == 'WARN':
            self.warnings += 1
        else:
            self.failed   += 1

    def add_heal(self, action, success, detail=None):
        self.heals.append({
            'action':  action,
            'success': success,
            'detail':  detail,
        })

    def exit_code(self):
        if self.failed > 0:
            return 2
        if self.warnings > 0:
            return 1
        return 0

    def summary_line(self):
        total = self.passed + self.warnings + self.failed
        if self.failed > 0:
            return (f"FAIL: {self.failed} critical, "
                    f"{self.warnings} warnings, "
                    f"{self.passed} passed")
        if self.warnings > 0:
            return (f"WARNING: {self.warnings} warnings, "
                    f"{self.passed} passed")
        return f"PASS: {total} checks passed"

    def to_console(self):
        lines = []
        lines.append("=" * 50)
        lines.append("TIE TIY DIAGNOSTIC REPORT")
        lines.append(
            f"Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 50)
        lines.append("")

        for check in self.checks:
            icon = (
                'OK'   if check['status'] == 'PASS' else
                'WARN' if check['status'] == 'WARN' else
                'FAIL'
            )
            line = f"[{icon}] {check['name']}"
            if check['detail']:
                line += f" - {check['detail']}"
            lines.append(line)

        if self.heals:
            lines.append("")
            lines.append("── SELF-HEAL RESULTS ──")
            for h in self.heals:
                icon = 'HEALED' if h['success'] else 'FAILED'
                line = f"[{icon}] {h['action']}"
                if h['detail']:
                    line += f" - {h['detail']}"
                lines.append(line)

        lines.append("")
        lines.append("-" * 50)
        lines.append(self.summary_line())
        lines.append("-" * 50)

        return "\n".join(lines)
        
    def to_telegram(self):
        lines = []
        lines.append('🔧 *DIAGNOSTIC REPORT*')
        lines.append(_esc(date.today().isoformat()))
        lines.append('')


        fails = [c for c in self.checks
                 if c['status'] == 'FAIL']
        warns = [c for c in self.checks
                 if c['status'] == 'WARN']

        if fails:
            lines.append('❌ *CRITICAL:*')
            for c in fails[:5]:
                detail = (f" \\- {_esc(c['detail'])}"
                          if c['detail'] else "")
                lines.append(
                    f"  • {_esc(c['name'])}{detail}")
            if len(fails) > 5:
                lines.append(
                    f"  \\+ {len(fails) - 5} more")
            lines.append('')

        if warns:
            lines.append('⚠️ *WARNINGS:*')
            for c in warns[:5]:
                detail = (f" \\- {_esc(c['detail'])}"
                          if c['detail'] else "")
                lines.append(
                    f"  • {_esc(c['name'])}{detail}")
            if len(warns) > 5:
                lines.append(
                    f"  \\+ {len(warns) - 5} more")
            lines.append('')

        if self.heals:
            healed_ok  = [h for h in self.heals
                          if h['success']]
            healed_bad = [h for h in self.heals
                          if not h['success']]
            lines.append('🔧 *AUTO\\-HEAL:*')
            for h in healed_ok:
                detail = (f" \\- {_esc(h['detail'])}"
                          if h['detail'] else "")
                lines.append(
                    f"  ✓ {_esc(h['action'])}{detail}")
            for h in healed_bad:
                detail = (f" \\- {_esc(h['detail'])}"
                          if h['detail'] else "")
                lines.append(
                    f"  ✕ {_esc(h['action'])}{detail}")
            lines.append('')

        if self.failed > 0:
            lines.append(
                f'❌ {_esc(self.summary_line())}')
        elif self.warnings > 0:
            lines.append(
                f'⚠️ {_esc(self.summary_line())}')
        else:
            lines.append(
                f'✅ {_esc(self.summary_line())}')

        # BUG FIX: strip raw divider lines that contain
        # unescaped dashes — breaks MarkdownV2 parser.
        # to_console() uses these for formatting but
        # to_telegram() must not emit them raw.
        cleaned = [
            l for l in lines
            if not (l.strip().startswith('──') or
                    l.strip().startswith('--') or
                    l.strip().startswith('=='))
        ]
        return '\n'.join(cleaned)


def _esc(text):
    if text is None:
        return ''
    text = str(text)
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text


# ── LOAD HELPERS ──────────────────────────────────────
def _load_json(filename):
    path = os.path.join(_OUTPUT, filename)
    if not os.path.exists(path):
        return None, f"File not found: {filename}"
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"
    except Exception as e:
        return None, f"Read error: {e}"


def _file_age_hours(filename):
    path = os.path.join(_OUTPUT, filename)
    if not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
        age_s = (datetime.now().timestamp() - mtime)
        return age_s / 3600.0
    except Exception:
        return None


def _is_today_trading_day():
    if CALENDAR_AVAILABLE:
        try:
            return is_trading_day(date.today())
        except Exception:
            pass
    return date.today().weekday() < 5


def _is_market_hours_now():
    now_utc_h = datetime.utcnow().hour
    return _MARKET_OPEN_UTC_H <= now_utc_h <= _MARKET_CLOSE_UTC_H


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(
            date_str[:10], '%Y-%m-%d').date()
    except Exception:
        return None


# ── CHECK FUNCTIONS ───────────────────────────────────

def check_files(report):
    for filename in REQUIRED_FILES:
        path = os.path.join(_OUTPUT, filename)
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size < 10:
                report.add(f"F: {filename}", "WARN",
                           f"File too small ({size} bytes)")
            else:
                report.add(f"F: {filename}", "PASS")
        else:
            report.add(f"F: {filename}", "FAIL",
                       "Missing required file")

    missing_optional = [
        f for f in OPTIONAL_FILES
        if not os.path.exists(os.path.join(_OUTPUT, f))
    ]
    if missing_optional:
        report.add("F: Optional files", "WARN",
                   f"{len(missing_optional)} missing")


def check_staleness(report):
    is_trading  = _is_today_trading_day()
    in_market   = _is_market_hours_now()
    today_str   = date.today().isoformat()

    for filename, max_age_h, trading_only in _STALENESS_RULES:
        path = os.path.join(_OUTPUT, filename)

        if not os.path.exists(path):
            continue

        if trading_only and not is_trading:
            continue

        age_h = _file_age_hours(filename)
        if age_h is None:
            report.add(f"ST: {filename}", "WARN",
                       "Cannot read mtime")
            continue

        if filename == 'ltp_prices.json' and not in_market:
            continue

        if age_h > max_age_h:
            hrs = f"{age_h:.1f}h"
            report.add(
                f"ST: {filename}", "WARN",
                f"Stale — {hrs} old (max {max_age_h}h)")
        else:
            report.add(f"ST: {filename}", "PASS",
                       f"{age_h:.1f}h old")

    if is_trading:
        meta, err = _load_json('meta.json')
        if meta and not err:
            meta_date = meta.get('market_date', '')
            if meta_date and meta_date < today_str:
                days_old = (
                    date.today() -
                    _parse_date(meta_date)
                ).days if _parse_date(meta_date) else '?'
                report.add(
                    "ST: meta content date",
                    "FAIL" if days_old != 1 else "WARN",
                    f"market_date={meta_date} "
                    f"({days_old}d old)")
            elif meta_date == today_str:
                report.add("ST: meta content date",
                           "PASS", "Today's data")

        scan, err = _load_json('scan_log.json')
        if scan and not err:
            scan_date = scan.get('date') or \
                        scan.get('scan_date', '')
            if scan_date and scan_date < today_str:
                report.add("ST: scan_log content date",
                           "WARN",
                           f"scan_date={scan_date}")
            elif scan_date == today_str:
                report.add("ST: scan_log content date",
                           "PASS")

        ltp, err = _load_json('ltp_prices.json')
        if ltp and not err and in_market:
            ltp_ts = (ltp.get('updated_at') or
                      ltp.get('ltp_updated_at') or '')
            if ltp_ts:
                try:
                    ltp_dt = datetime.fromisoformat(
                        ltp_ts.replace('Z', '+00:00'))
                    age_min = int(
                        (datetime.now().astimezone() -
                         ltp_dt).total_seconds() / 60)
                    if age_min > 15:
                        report.add(
                            "ST: ltp content age",
                            "WARN",
                            f"{age_min}m since last LTP")
                    else:
                        report.add(
                            "ST: ltp content age",
                            "PASS",
                            f"{age_min}m ago")
                except Exception:
                    pass


def check_signal_history_schema(report):
    data, err = _load_json('signal_history.json')
    if err:
        report.add("S: signal_history load", "FAIL", err)
        return None

    if 'history' not in data:
        report.add("S: history key", "FAIL",
                   "Missing 'history' array")
        return None
    report.add("S: history key", "PASS")

    sv = data.get('schema_version')
    if sv != SCHEMA_VERSION:
        report.add("S: schema_version", "WARN",
                   f"Expected {SCHEMA_VERSION}, got {sv}")
    else:
        report.add("S: schema_version", "PASS")

    history = data.get('history', [])
    if not history:
        report.add("S: history array", "WARN",
                   "Empty history")
        return data

    report.add("S: history array", "PASS",
               f"{len(history)} signals")
    return data


def check_signal_fields(report, history_data):
    if not history_data:
        return

    history = history_data.get('history', [])
    if not history:
        return

    sample = (history[:20] + history[-10:]
              if len(history) > 30 else history)

    missing_required     = 0
    invalid_signal_type  = 0
    invalid_result       = 0
    vol_confirm_not_bool = 0
    invalid_generation   = 0
    missing_v5_fields    = 0

    V5_FIELDS = [
        'user_action', 'is_sa',
        'sa_parent_id', 'rs_strong',
        'grade_A', 'sec_leading',
    ]

    for sig in sample:
        for field in HISTORY_REQUIRED_FIELDS:
            if sig.get(field) is None:
                missing_required += 1
                break

        if sig.get('signal') not in VALID_SIGNALS:
            invalid_signal_type += 1

        if sig.get('result') not in VALID_RESULTS:
            invalid_result += 1

        vc = sig.get('vol_confirm')
        if vc is not None and not isinstance(vc, bool):
            vol_confirm_not_bool += 1

        gen = sig.get('generation')
        if gen is not None and gen not in [0, 1]:
            invalid_generation += 1

        missing = [f for f in V5_FIELDS if f not in sig]
        if missing:
            missing_v5_fields += 1

    if missing_required > 0:
        report.add("D: Required fields", "FAIL",
                   f"{missing_required} signals missing fields")
    else:
        report.add("D: Required fields", "PASS")

    if invalid_signal_type > 0:
        report.add("D: Signal types", "WARN",
                   f"{invalid_signal_type} invalid")
    else:
        report.add("D: Signal types", "PASS")

    if invalid_result > 0:
        report.add("D: Result values", "WARN",
                   f"{invalid_result} invalid")
    else:
        report.add("D: Result values", "PASS")

    if vol_confirm_not_bool > 0:
        report.add("D: vol_confirm type", "WARN",
                   f"{vol_confirm_not_bool} not boolean")
    else:
        report.add("D: vol_confirm type", "PASS")

    if invalid_generation > 0:
        report.add("D: generation values", "WARN",
                   f"{invalid_generation} invalid")
    else:
        report.add("D: generation values", "PASS")

    if missing_v5_fields > 0:
        report.add("D: V5 fields", "WARN",
                   f"{missing_v5_fields} records missing "
                   f"V5 fields — run --heal")
    else:
        report.add("D: V5 fields", "PASS")


def check_scan_log(report):
    data, err = _load_json('scan_log.json')
    if err:
        report.add("L: scan_log load", "FAIL", err)
        return None

    required = ['date', 'regime', 'signals']
    missing  = [f for f in required if f not in data]
    if missing:
        report.add("L: scan_log fields", "FAIL",
                   f"Missing: {missing}")
        return data

    report.add("L: scan_log fields", "PASS")

    scan_date  = _parse_date(
        data.get('date') or data.get('scan_date'))
    today      = date.today()
    is_trading = _is_today_trading_day()

    if is_trading:
        if scan_date == today:
            report.add("L: scan_log date", "PASS",
                       "Today's scan")
        elif scan_date and (today - scan_date).days == 1:
            report.add("L: scan_log date", "WARN",
                       "Yesterday's data")
        else:
            report.add("L: scan_log date", "FAIL",
                       f"Stale data: {scan_date}")
    else:
        report.add("L: scan_log date", "PASS",
                   "Non-trading day")

    return data


def check_meta(report, history_data):
    data, err = _load_json('meta.json')
    if err:
        report.add("M: meta load", "FAIL", err)
        return

    required = ['market_date', 'regime', 'scanner_version']
    missing  = [f for f in required if f not in data]
    if missing:
        report.add("M: meta fields", "WARN",
                   f"Missing: {missing}")
    else:
        report.add("M: meta fields", "PASS")

    if history_data:
        history = history_data.get('history', [])
        actual_pending = len([
            s for s in history
            if s.get('result') == 'PENDING'
            and s.get('action') == 'TOOK'
        ])
        meta_count = data.get('active_signals_count', 0)

        if actual_pending == meta_count:
            report.add("M: active count", "PASS",
                       f"{actual_pending} active")
        else:
            report.add("M: active count", "WARN",
                       f"meta says {meta_count}, "
                       f"actual {actual_pending}")


def check_trading_logic(report, history_data):
    if not history_data:
        return

    history = history_data.get('history', [])
    today   = date.today()

    overdue = 0
    for sig in history:
        if sig.get('result') != 'PENDING':
            continue
        if sig.get('action') != 'TOOK':
            continue
        exit_date = _parse_date(sig.get('exit_date'))
        if exit_date and exit_date < today:
            overdue += 1

    if overdue > 0:
        report.add("T: Overdue signals", "WARN",
                   f"{overdue} past exit_date but PENDING")
    else:
        report.add("T: Overdue signals", "PASS")

    gen0 = len([s for s in history
                if s.get('generation') == 0])
    gen1 = len([s for s in history
                if s.get('generation') == 1])
    report.add("T: Generation split", "PASS",
               f"gen0={gen0}, gen1={gen1}")

    missing_target = len([
        s for s in history
        if s.get('result') == 'PENDING'
        and s.get('target_price') is None
    ])
    if missing_target > 0:
        report.add("T: Missing targets", "WARN",
                   f"{missing_target} signals without "
                   f"target_price")
    else:
        report.add("T: Missing targets", "PASS")

    bad_rejected = len([
        s for s in history
        if s.get('result') == 'REJECTED'
        and s.get('outcome') == 'OPEN'
    ])
    if bad_rejected > 0:
        report.add("T: Rejected outcome", "WARN",
                   f"{bad_rejected} REJECTED with "
                   f"outcome=OPEN — run --heal")
    else:
        report.add("T: Rejected outcome", "PASS")

    bad_vc = len([
        s for s in history
        if isinstance(s.get('vol_confirm'), str)
    ])
    if bad_vc > 0:
        report.add("T: vol_confirm strings", "WARN",
                   f"{bad_vc} not boolean — run --heal")
    else:
        report.add("T: vol_confirm strings", "PASS")


def check_data_dir(report):
    universe_path = os.path.join(_DATA, 'fno_universe.csv')
    if os.path.exists(universe_path):
        with open(universe_path, 'r') as f:
            lines = len(f.readlines())
        report.add("C: fno_universe.csv", "PASS",
                   f"{lines} lines")
    else:
        report.add("C: fno_universe.csv", "FAIL",
                   "Missing universe file")

    rules_path = os.path.join(
        _DATA, 'mini_scanner_rules.json')
    if os.path.exists(rules_path):
        try:
            with open(rules_path, 'r') as f:
                rules = json.load(f)
            shadow = rules.get('shadow_mode', 'unknown')
            report.add("C: mini_scanner_rules", "PASS",
                       f"shadow_mode={shadow}")
        except Exception as e:
            report.add("C: mini_scanner_rules", "WARN",
                       f"Parse error: {e}")
    else:
        report.add("C: mini_scanner_rules", "WARN",
                   "Missing rules file")


# ── M13: SELF-HEAL ────────────────────────────────────
def attempt_self_heal(report):
    if not JOURNAL_AVAILABLE:
        report.add_heal(
            "Journal import",
            False,
            "journal.py not importable — skipping all heals")
        return

    print("[diagnostic] Running self-heal pass...")

    try:
        _journal.backfill_schema_v5()
        report.add_heal(
            "Schema V5 migration", True,
            "backfill_schema_v5() completed")
    except Exception as e:
        report.add_heal(
            "Schema V5 migration", False, str(e))

    try:
        _journal.backfill_generation_flags()
        report.add_heal(
            "Generation + vol_confirm backfill", True,
            "backfill_generation_flags() completed")
    except Exception as e:
        report.add_heal(
            "Generation + vol_confirm backfill",
            False, str(e))

    try:
        _journal.backfill_target_prices()
        report.add_heal(
            "Target price backfill", True,
            "backfill_target_prices() completed")
    except Exception as e:
        report.add_heal(
            "Target price backfill", False, str(e))

    stale_fails = [
        c for c in report.checks
        if c['status'] == 'FAIL'
        and c['name'].startswith('ST:')
    ]
    if stale_fails:
        for sf in stale_fails:
            report.add_heal(
                f"Stale file: {sf['name']}", False,
                "Cannot auto-heal — requires scanner rerun. "
                "Trigger morning_scan workflow manually.")

    overdue_warn = next(
        (c for c in report.checks
         if 'Overdue' in c['name']
         and c['status'] == 'WARN'), None)
    if overdue_warn:
        report.add_heal(
            "Overdue signals", False,
            "Cannot auto-heal — requires outcome_evaluator "
            "rerun. Trigger eod_update workflow manually.")

    print(f"[diagnostic] Self-heal complete: "
          f"{sum(1 for h in report.heals if h['success'])} "
          f"succeeded, "
          f"{sum(1 for h in report.heals if not h['success'])} "
          f"skipped/failed")


# ── MAIN RUNNER ───────────────────────────────────────
def run_diagnostic(quick=False,
                   send_telegram=False,
                   heal=False):
    report = DiagnosticReport()

    print("[diagnostic] Starting system check...")

    check_files(report)
    history_data = check_signal_history_schema(report)

    if not quick:
        check_staleness(report)
        check_signal_fields(report, history_data)
        check_scan_log(report)
        check_meta(report, history_data)
        check_trading_logic(report, history_data)
        check_data_dir(report)

    if heal or (not quick and report.failed > 0):
        attempt_self_heal(report)

    print(report.to_console())

    if send_telegram and TELEGRAM_AVAILABLE:
        try:
            send_message(report.to_telegram())
            print("[diagnostic] Telegram report sent")
        except Exception as e:
            print(f"[diagnostic] Telegram failed: {e}")

    return report.exit_code()


# ── CLI ───────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='TIE TIY Scanner Diagnostic Tool')
    parser.add_argument(
        '--quick', action='store_true',
        help='Quick check (files + schema only)')
    parser.add_argument(
        '--telegram', action='store_true',
        help='Send report to Telegram')
    parser.add_argument(
        '--heal', action='store_true',
        help='Attempt safe auto-fixes after check')

    args = parser.parse_args()

    exit_code = run_diagnostic(
        quick         = args.quick,
        send_telegram = args.telegram,
        heal          = args.heal,
    )

    sys.exit(exit_code)
