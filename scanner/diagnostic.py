# scanner/diagnostic.py

# ─────────────────────────────────────────────────────

# Unified diagnostic tool for TIE TIY Scanner

# Replaces health_check.py and verify_fixes.py

# 

# Usage:

# python scanner/diagnostic.py              # Full check

# python scanner/diagnostic.py –quick      # Quick check (files + schema only)

# python scanner/diagnostic.py –telegram   # Send report to Telegram

# 

# Exit codes:

# 0 = PASS (all checks passed)

# 1 = WARNING (minor issues, system functional)

# 2 = FAIL (critical issues, needs attention)

# ─────────────────────────────────────────────────────

import os
import sys
import json
import argparse
from datetime import date, datetime, timedelta

# ── PATH SETUP ────────────────────────────────────────

_HERE   = os.path.dirname(os.path.abspath(**file**))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, ‘output’)
_DATA   = os.path.join(_ROOT, ‘data’)

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

# ── CONSTANTS ─────────────────────────────────────────

REQUIRED_FILES = [
‘signal_history.json’,
‘scan_log.json’,
‘meta.json’,
]

OPTIONAL_FILES = [
‘mini_log.json’,
‘rejected_log.json’,
‘open_prices.json’,
‘eod_prices.json’,
‘stop_alerts.json’,
‘ltp_prices.json’,
‘banned_stocks.json’,
‘nse_holidays.json’,
‘signal_archive.json’,
]

# Signal history schema (the CORRECT one)

HISTORY_REQUIRED_FIELDS = [
‘id’, ‘date’, ‘symbol’, ‘signal’, ‘direction’,
‘entry’, ‘stop’, ‘score’, ‘result’,
]

HISTORY_OPTIONAL_FIELDS = [
‘schema_version’, ‘generation’, ‘data_quality’,
‘sector’, ‘grade’, ‘age’, ‘regime’, ‘regime_score’,
‘vol_q’, ‘vol_confirm’, ‘rs_q’, ‘sec_mom’,
‘bear_bonus’, ‘stock_regime’, ‘scan_price’, ‘scan_time’,
‘pivot_price’, ‘pivot_date’, ‘atr’, ‘exit_date’,
‘target_price’, ‘actual_open’, ‘adjusted_rr’,
‘entry_valid’, ‘gap_pct’, ‘outcome’, ‘outcome_date’,
‘outcome_price’, ‘tracking_start’, ‘tracking_end’,
‘mfe_pct’, ‘mae_pct’, ‘days_to_outcome’,
‘exit_price’, ‘exit_type’, ‘exit_date_actual’,
‘pnl_pct’, ‘pnl_rs’, ‘action’, ‘attempt_number’,
‘parent_signal_id’, ‘parent_signal’, ‘parent_date’,
‘parent_result’, ‘layer’, ‘rejection_reason’,
‘scanner_version’,
]

VALID_SIGNALS = [‘UP_TRI’, ‘DOWN_TRI’, ‘BULL_PROXY’, ‘UP_TRI_SA’, ‘DOWN_TRI_SA’]
VALID_RESULTS = [‘PENDING’, ‘WON’, ‘STOPPED’, ‘EXITED’, ‘REJECTED’]
VALID_OUTCOMES = [‘OPEN’, ‘TARGET_HIT’, ‘STOP_HIT’, ‘DAY6_WIN’, ‘DAY6_LOSS’, ‘DAY6_FLAT’, None]

# ── REPORT BUILDER ────────────────────────────────────

class DiagnosticReport:
def **init**(self):
self.checks = []
self.passed = 0
self.warnings = 0
self.failed = 0
self.start_time = datetime.now()

```
def add(self, name, status, detail=None):
    """Add a check result. status: PASS, WARN, FAIL"""
    self.checks.append({
        'name': name,
        'status': status,
        'detail': detail,
    })
    if status == 'PASS':
        self.passed += 1
    elif status == 'WARN':
        self.warnings += 1
    else:
        self.failed += 1

def exit_code(self):
    if self.failed > 0:
        return 2
    if self.warnings > 0:
        return 1
    return 0

def summary_line(self):
    total = self.passed + self.warnings + self.failed
    if self.failed > 0:
        return f"❌ FAIL — {self.failed} critical, {self.warnings} warnings, {self.passed} passed"
    if self.warnings > 0:
        return f"⚠️ WARNING — {self.warnings} warnings, {self.passed} passed"
    return f"✅ PASS — {total} checks passed"

def to_console(self):
    lines = []
    lines.append("=" * 50)
    lines.append("TIE TIY DIAGNOSTIC REPORT")
    lines.append(f"Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 50)
    lines.append("")

    for check in self.checks:
        icon = '✅' if check['status'] == 'PASS' else '⚠️' if check['status'] == 'WARN' else '❌'
        line = f"{icon} {check['name']}"
        if check['detail']:
            line += f" — {check['detail']}"
        lines.append(line)

    lines.append("")
    lines.append("-" * 50)
    lines.append(self.summary_line())
    lines.append("-" * 50)

    return "\n".join(lines)

def to_telegram(self):
    """Compact Telegram format"""
    lines = []
    lines.append(f"🔧 *DIAGNOSTIC REPORT*")
    lines.append(f"{date.today().isoformat()}")
    lines.append("")

    # Group by status
    fails = [c for c in self.checks if c['status'] == 'FAIL']
    warns = [c for c in self.checks if c['status'] == 'WARN']

    if fails:
        lines.append("❌ *CRITICAL:*")
        for c in fails[:5]:  # Max 5
            detail = f" — {c['detail']}" if c['detail'] else ""
            lines.append(f"  • {c['name']}{detail}")
        if len(fails) > 5:
            lines.append(f"  + {len(fails) - 5} more")
        lines.append("")

    if warns:
        lines.append("⚠️ *WARNINGS:*")
        for c in warns[:5]:  # Max 5
            detail = f" — {c['detail']}" if c['detail'] else ""
            lines.append(f"  • {c['name']}{detail}")
        if len(warns) > 5:
            lines.append(f"  + {len(warns) - 5} more")
        lines.append("")

    lines.append(self.summary_line())

    # Escape for MarkdownV2
    text = "\n".join(lines)
    for ch in r'_[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text
```

# ── LOAD HELPERS ──────────────────────────────────────

def _load_json(filename):
“”“Load JSON file from output directory”””
path = os.path.join(_OUTPUT, filename)
if not os.path.exists(path):
return None, f”File not found: {filename}”
try:
with open(path, ‘r’) as f:
data = json.load(f)
return data, None
except json.JSONDecodeError as e:
return None, f”Invalid JSON: {e}”
except Exception as e:
return None, f”Read error: {e}”

def _is_today_trading_day():
“”“Check if today is a trading day”””
if CALENDAR_AVAILABLE:
try:
return is_trading_day(date.today())
except Exception:
pass
# Fallback: weekday check only
return date.today().weekday() < 5

def _parse_date(date_str):
“”“Parse date string to date object”””
if not date_str:
return None
try:
return datetime.strptime(date_str[:10], ‘%Y-%m-%d’).date()
except Exception:
return None

# ── CHECK FUNCTIONS ───────────────────────────────────

def check_files(report):
“”“F1-F4: Check required and optional files exist”””
for filename in REQUIRED_FILES:
path = os.path.join(_OUTPUT, filename)
if os.path.exists(path):
size = os.path.getsize(path)
if size < 10:
report.add(f”F: {filename}”, “WARN”, f”File too small ({size} bytes)”)
else:
report.add(f”F: {filename}”, “PASS”)
else:
report.add(f”F: {filename}”, “FAIL”, “Missing required file”)

```
# Optional files - just note if missing
missing_optional = []
for filename in OPTIONAL_FILES:
    path = os.path.join(_OUTPUT, filename)
    if not os.path.exists(path):
        missing_optional.append(filename)

if missing_optional:
    report.add("F: Optional files", "WARN", f"{len(missing_optional)} missing")
```

def check_signal_history_schema(report):
“”“S1-S4: Check signal_history.json schema”””
data, err = _load_json(‘signal_history.json’)
if err:
report.add(“S: signal_history load”, “FAIL”, err)
return None

```
# Check root structure
if 'history' not in data:
    report.add("S: history key", "FAIL", "Missing 'history' array (found 'signals'?)")
    return None
report.add("S: history key", "PASS")

# Check schema_version
if data.get('schema_version') != 4:
    report.add("S: schema_version", "WARN", f"Expected 4, got {data.get('schema_version')}")
else:
    report.add("S: schema_version", "PASS")

history = data.get('history', [])
if not history:
    report.add("S: history array", "WARN", "Empty history")
    return data

report.add("S: history array", "PASS", f"{len(history)} signals")
return data
```

def check_signal_fields(report, history_data):
“”“D1-D5: Check individual signal fields”””
if not history_data:
return

```
history = history_data.get('history', [])
if not history:
    return

# Sample check - first 20 + last 10
sample = history[:20] + history[-10:] if len(history) > 30 else history

missing_required = 0
invalid_signal_type = 0
invalid_result = 0
vol_confirm_not_bool = 0
invalid_generation = 0

for sig in sample:
    # Required fields
    for field in HISTORY_REQUIRED_FIELDS:
        if sig.get(field) is None:
            missing_required += 1
            break

    # Signal type
    if sig.get('signal') not in VALID_SIGNALS:
        invalid_signal_type += 1

    # Result
    if sig.get('result') not in VALID_RESULTS:
        invalid_result += 1

    # vol_confirm should be boolean
    vc = sig.get('vol_confirm')
    if vc is not None and not isinstance(vc, bool):
        vol_confirm_not_bool += 1

    # generation should be 0 or 1
    gen = sig.get('generation')
    if gen is not None and gen not in [0, 1]:
        invalid_generation += 1

# Report
if missing_required > 0:
    report.add("D: Required fields", "FAIL", f"{missing_required} signals missing fields")
else:
    report.add("D: Required fields", "PASS")

if invalid_signal_type > 0:
    report.add("D: Signal types", "WARN", f"{invalid_signal_type} invalid")
else:
    report.add("D: Signal types", "PASS")

if invalid_result > 0:
    report.add("D: Result values", "WARN", f"{invalid_result} invalid")
else:
    report.add("D: Result values", "PASS")

if vol_confirm_not_bool > 0:
    report.add("D: vol_confirm type", "WARN", f"{vol_confirm_not_bool} not boolean")
else:
    report.add("D: vol_confirm type", "PASS")

if invalid_generation > 0:
    report.add("D: generation values", "WARN", f"{invalid_generation} invalid")
else:
    report.add("D: generation values", "PASS")
```

def check_scan_log(report):
“”“L1-L3: Check scan_log.json”””
data, err = _load_json(‘scan_log.json’)
if err:
report.add(“L: scan_log load”, “FAIL”, err)
return None

```
# Check required fields
required = ['date', 'regime', 'signals']
missing = [f for f in required if f not in data]
if missing:
    report.add("L: scan_log fields", "FAIL", f"Missing: {missing}")
    return data

report.add("L: scan_log fields", "PASS")

# Check date
scan_date = _parse_date(data.get('date') or data.get('scan_date'))
today = date.today()
is_trading = _is_today_trading_day()

if is_trading:
    if scan_date == today:
        report.add("L: scan_log date", "PASS", "Today's scan")
    elif scan_date and (today - scan_date).days == 1:
        report.add("L: scan_log date", "WARN", "Yesterday's data")
    else:
        report.add("L: scan_log date", "FAIL", f"Stale data: {scan_date}")
else:
    report.add("L: scan_log date", "PASS", "Non-trading day")

return data
```

def check_meta(report, history_data):
“”“M1-M3: Check meta.json consistency”””
data, err = _load_json(‘meta.json’)
if err:
report.add(“M: meta load”, “FAIL”, err)
return

```
# Check required fields
required = ['market_date', 'regime', 'scanner_version']
missing = [f for f in required if f not in data]
if missing:
    report.add("M: meta fields", "WARN", f"Missing: {missing}")
else:
    report.add("M: meta fields", "PASS")

# Check active count matches reality
if history_data:
    history = history_data.get('history', [])
    actual_pending = len([
        s for s in history
        if s.get('result') == 'PENDING'
        and s.get('action') == 'TOOK'
    ])
    meta_count = data.get('active_signals_count', 0)

    if actual_pending == meta_count:
        report.add("M: active count", "PASS", f"{actual_pending} active")
    else:
        report.add("M: active count", "WARN",
                   f"meta says {meta_count}, actual {actual_pending}")
```

def check_trading_logic(report, history_data):
“”“T1-T3: Check trading logic consistency”””
if not history_data:
return

```
history = history_data.get('history', [])
today = date.today()

# Check for overdue signals (past exit_date but still PENDING)
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
    report.add("T: Overdue signals", "WARN", f"{overdue} past exit_date but PENDING")
else:
    report.add("T: Overdue signals", "PASS")

# Check generation counts
gen0 = len([s for s in history if s.get('generation') == 0])
gen1 = len([s for s in history if s.get('generation') == 1])
report.add("T: Generation split", "PASS", f"gen0={gen0}, gen1={gen1}")

# Check for signals missing target_price
missing_target = len([
    s for s in history
    if s.get('result') == 'PENDING'
    and s.get('target_price') is None
])
if missing_target > 0:
    report.add("T: Missing targets", "WARN", f"{missing_target} signals without target_price")
else:
    report.add("T: Missing targets", "PASS")
```

def check_data_dir(report):
“”“C1: Check data directory”””
universe_path = os.path.join(_DATA, ‘fno_universe.csv’)
if os.path.exists(universe_path):
with open(universe_path, ‘r’) as f:
lines = len(f.readlines())
report.add(“C: fno_universe.csv”, “PASS”, f”{lines} lines”)
else:
report.add(“C: fno_universe.csv”, “FAIL”, “Missing universe file”)

```
rules_path = os.path.join(_DATA, 'mini_scanner_rules.json')
if os.path.exists(rules_path):
    try:
        with open(rules_path, 'r') as f:
            rules = json.load(f)
        shadow = rules.get('shadow_mode', 'unknown')
        report.add("C: mini_scanner_rules", "PASS", f"shadow_mode={shadow}")
    except Exception as e:
        report.add("C: mini_scanner_rules", "WARN", f"Parse error: {e}")
else:
    report.add("C: mini_scanner_rules", "WARN", "Missing rules file")
```

# ── MAIN RUNNER ───────────────────────────────────────

def run_diagnostic(quick=False, send_telegram=False):
“”“Run full diagnostic check”””
report = DiagnosticReport()

```
print("[diagnostic] Starting system check...")

# Layer 1: Files
check_files(report)

# Layer 2: Signal history schema
history_data = check_signal_history_schema(report)

if not quick:
    # Layer 3: Signal fields
    check_signal_fields(report, history_data)

    # Layer 4: Scan log
    check_scan_log(report)

    # Layer 5: Meta consistency
    check_meta(report, history_data)

    # Layer 6: Trading logic
    check_trading_logic(report, history_data)

    # Layer 7: Data directory
    check_data_dir(report)

# Output
print(report.to_console())

# Telegram if requested
if send_telegram and TELEGRAM_AVAILABLE:
    try:
        send_message(report.to_telegram())
        print("[diagnostic] Telegram report sent")
    except Exception as e:
        print(f"[diagnostic] Telegram failed: {e}")

return report.exit_code()
```

# ── CLI ───────────────────────────────────────────────

if **name** == ‘**main**’:
parser = argparse.ArgumentParser(
description=‘TIE TIY Scanner Diagnostic Tool’)
parser.add_argument(’–quick’, action=‘store_true’,
help=‘Quick check (files + schema only)’)
parser.add_argument(’–telegram’, action=‘store_true’,
help=‘Send report to Telegram’)

```
args = parser.parse_args()

exit_code = run_diagnostic(
    quick=args.quick,
    send_telegram=args.telegram
)

sys.exit(exit_code)
```
