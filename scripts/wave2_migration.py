#!/usr/bin/env python3
# ── scripts/wave2_migration.py ───────────────────────
# Automated migration from per-file local IST helpers
# to the canonical calendar_utils helpers shipped in
# Wave 1.
#
# Kills (per doc/fix_table.md):
#   H-03 — _is_trading_day duplicated in 4 files
#   H-09 — date.today() UTC drift across 5+ files
#   M-06 — IST helpers duplicated in 5 files
#
# Does NOT touch:
#   - telegram_bot.py (user skip decision)
#   - M-11 recover_stuck_signals TELEGRAM_TOKEN rename
#     (handled separately in Wave 3)
#   - Any local helpers that aren't in REPLACE_MAP
#
# Usage:
#   python scripts/wave2_migration.py --dry-run   # Plan only
#   python scripts/wave2_migration.py --execute   # Apply
#
# Triggered via .github/workflows/wave2.yml with a
# mode selector (dry_run / execute).
#
# Safety rails:
#   1. Backup every file to quarantine/wave2_<ts>/
#   2. Syntax check every modified file via ast.parse
#   3. If ANY file fails syntax → revert ALL files
#   4. Full audit log written to doc/wave2_migration_log.md
#   5. No commits — workflow handles git commit step
# ─────────────────────────────────────────────────────

import argparse
import ast
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta


# ── CONFIG ───────────────────────────────────────────

# Target files relative to repo root
TARGET_FILES = [
    'scanner/outcome_evaluator.py',
    'scanner/open_validator.py',
    'scanner/ltp_writer.py',
    'scanner/heartbeat.py',
    'scanner/stop_alert_writer.py',
    'scanner/journal.py',
    'scanner/main.py',
    'scanner/weekend_summary.py',
    'scanner/recover_stuck_signals.py',
    'scanner/eod_prices_writer.py',
    'scanner/chain_validator.py',
]

# Call site replacements — ordered, regex-safe.
# (pattern, replacement, description)
# Patterns use word boundaries so partial matches don't hit.
CALL_REPLACEMENTS = [
    # date.today() → ist_today() — H-09 core
    (r'\bdate\.today\(\)',   'ist_today()',   'date.today() UTC → ist_today() IST'),

    # Local IST date helpers → ist_today()
    (r'\b_ist_today\(\)',    'ist_today()',   '_ist_today() → ist_today()'),
    (r'\b_today_ist\(\)',    'ist_today()',   '_today_ist() → ist_today()'),
    (r'\b_now_ist_date\(\)', 'ist_today()',   '_now_ist_date() → ist_today()'),

    # Local datetime helpers → ist_now()
    (r'\b_ist_now\(\)',      'ist_now()',     '_ist_now() → ist_now()'),
    (r'\b_now_ist\(\)',      'ist_now()',     '_now_ist() → ist_now()'),

    # Formatted string helpers → ist_now_str()
    (r'\b_ist_now_str\(\)',  'ist_now_str()', '_ist_now_str() → ist_now_str()'),
    (r'\b_now_ist_str\(\)',  'ist_now_str()', '_now_ist_str() → ist_now_str()'),

    # Trading day helpers → is_trading_day()
    # Note: calendar_utils.is_trading_day(d=None, holidays=None)
    # accepts both 0-arg and 2-arg signatures so any existing
    # call pattern continues to work after name swap.
    (r'\b_is_trading_day\(', 'is_trading_day(', '_is_trading_day( → is_trading_day('),
]

# Local function definitions to DELETE from target files.
# Each entry is a function name. Script finds `def <n>(`
# at column 0, deletes entire block until next column-0 `def`
# or blank-line boundary. Order matters: more specific first.
LOCAL_FUNCS_TO_DELETE = [
    '_ist_today',
    '_today_ist',
    '_now_ist_date',
    '_ist_now',
    '_now_ist',
    '_ist_now_str',
    '_now_ist_str',
    '_is_trading_day',
]

# The canonical import line added to each file.
# Placed after the last existing `from` or `import` line.
CANONICAL_IMPORT = (
    'from calendar_utils import '
    'ist_today, ist_now, ist_now_str, is_trading_day'
)

# ── PATHS ────────────────────────────────────────────

_HERE  = os.path.dirname(os.path.abspath(__file__))
_ROOT  = os.path.dirname(_HERE)


def _ts_str():
    """IST timestamp for backup folder naming."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(tz=ist).strftime('%Y%m%d_%H%M%S')


def _log(msg, also_print=True):
    """Log to list + optionally stdout."""
    _LOG_LINES.append(msg)
    if also_print:
        print(msg)


_LOG_LINES = []


# ── ANALYSIS ─────────────────────────────────────────

def analyze_file(abs_path):
    """
    Read a file and return planned changes without writing.
    Returns dict:
      {
        'file': rel_path,
        'exists': bool,
        'needs_import': bool,
        'call_replacements': [(pattern_desc, count)],
        'func_deletions': [(func_name, start_line, end_line)],
        'total_changes': int,
        'before_bytes': int,
      }
    """
    rel = os.path.relpath(abs_path, _ROOT)

    if not os.path.exists(abs_path):
        return {
            'file':              rel,
            'exists':            False,
            'needs_import':      False,
            'call_replacements': [],
            'func_deletions':    [],
            'total_changes':     0,
            'before_bytes':      0,
        }

    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Count call replacements (dry scan — no write)
    replacements = []
    for pattern, replacement, desc in CALL_REPLACEMENTS:
        matches = re.findall(pattern, content)
        if matches:
            replacements.append((desc, len(matches)))

    # Find local function definitions to delete
    func_deletions = []
    lines = content.split('\n')
    for fn_name in LOCAL_FUNCS_TO_DELETE:
        for i, line in enumerate(lines):
            # Match column-0 `def <n>(` only
            if re.match(
                rf'^def\s+{re.escape(fn_name)}\s*\(',
                line
            ):
                end_line = _find_block_end(lines, i)
                func_deletions.append((fn_name, i, end_line))
                break  # Only first occurrence; duplicates are a bug

    # Check if canonical import already present
    has_canonical = CANONICAL_IMPORT in content

    # Check if any calendar_utils import exists at all
    has_any_cu_import = bool(
        re.search(r'^from\s+calendar_utils\s+import\s+',
                  content, re.MULTILINE)
    )

    needs_import = (
        bool(replacements) or bool(func_deletions)
    ) and not has_canonical

    total = sum(c for _, c in replacements) + len(func_deletions)
    if needs_import:
        total += 1

    return {
        'file':              rel,
        'exists':            True,
        'needs_import':      needs_import,
        'has_any_cu_import': has_any_cu_import,
        'has_canonical':     has_canonical,
        'call_replacements': replacements,
        'func_deletions':    func_deletions,
        'total_changes':     total,
        'before_bytes':      len(content),
    }


def _find_block_end(lines, start_idx):
    """
    Find the end line (exclusive) of a function block
    starting at start_idx (the `def` line).
    Block ends at:
      - Next column-0 `def ` or `class ` line
      - End of file
    Returns the line index where the block ends (exclusive).
    """
    n = len(lines)
    i = start_idx + 1
    while i < n:
        line = lines[i]
        # Another top-level def/class = boundary
        if re.match(r'^(def|class)\s+', line):
            return i
        # Top-level non-blank non-comment line NOT indented
        # = boundary (handles edge case of function followed
        # by module-level code).
        stripped = line.lstrip()
        if stripped and not line.startswith((' ', '\t')):
            # A top-level statement — function block ended
            # at previous line. Walk back past trailing blank
            # lines.
            j = i - 1
            while j > start_idx and not lines[j].strip():
                j -= 1
            return j + 1
        i += 1
    # End of file
    return n


# ── APPLY ────────────────────────────────────────────

def apply_changes(abs_path, plan):
    """
    Apply the migration changes to a file.
    Returns new content string (does not write).
    """
    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Delete local function definitions (from bottom up
    #    so line indices stay valid).
    lines = content.split('\n')
    deletions = sorted(
        plan['func_deletions'],
        key=lambda t: t[1],
        reverse=True
    )
    for fn_name, start, end in deletions:
        # Also scoop up any immediately preceding comment
        # block (contiguous '# ...' lines with no blank).
        scoop_start = start
        j = start - 1
        while j >= 0 and lines[j].strip().startswith('#'):
            scoop_start = j
            j -= 1
        del lines[scoop_start:end]

    content = '\n'.join(lines)

    # 2. Apply call replacements
    for pattern, replacement, _desc in CALL_REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    # 3. Add canonical import if needed
    if plan['needs_import']:
        content = _inject_import(content)

    return content


def _inject_import(content):
    """
    Add CANONICAL_IMPORT after the last existing
    `from` or `import` statement. Preserves original
    formatting.
    """
    lines = content.split('\n')
    last_import_idx = -1

    in_docstring = False
    docstring_quote = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track triple-quoted docstrings so we don't
        # accidentally treat `from X import Y` inside
        # a docstring as a real import.
        if not in_docstring:
            for q in ('"""', "'''"):
                if stripped.startswith(q):
                    # Inline docstring (both open and close
                    # on same line)?
                    if len(stripped) > 3 and stripped.endswith(q):
                        continue
                    in_docstring  = True
                    docstring_quote = q
                    break
        else:
            if docstring_quote and docstring_quote in stripped:
                in_docstring    = False
                docstring_quote = None
            continue

        if in_docstring:
            continue

        if (stripped.startswith('import ')
                or stripped.startswith('from ')):
            last_import_idx = i

    if last_import_idx == -1:
        # No imports — inject at top of file after any header
        # comment / docstring.
        # Find first non-comment, non-blank, non-docstring line.
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if (s and not s.startswith('#')
                    and not s.startswith('"""')
                    and not s.startswith("'''")):
                break
            i += 1
        lines.insert(i, CANONICAL_IMPORT)
        lines.insert(i + 1, '')
    else:
        lines.insert(last_import_idx + 1, CANONICAL_IMPORT)

    return '\n'.join(lines)


# ── VERIFY ───────────────────────────────────────────

def syntax_check(path, content):
    """
    Parse content as Python via ast. Returns
    (ok: bool, error_message: str)
    """
    try:
        ast.parse(content, filename=path)
        return True, ''
    except SyntaxError as e:
        return False, f'{e.msg} at line {e.lineno}'
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


# ── BACKUP ───────────────────────────────────────────

def create_backup(backup_dir, targets_with_plans):
    """Copy every target file to backup_dir preserving structure."""
    os.makedirs(backup_dir, exist_ok=True)

    for rel_path, _plan in targets_with_plans:
        abs_path = os.path.join(_ROOT, rel_path)
        if not os.path.exists(abs_path):
            continue

        dest = os.path.join(backup_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(abs_path, dest)


def restore_backup(backup_dir, targets_with_plans):
    """Copy files from backup_dir back to original locations."""
    for rel_path, _plan in targets_with_plans:
        src = os.path.join(backup_dir, rel_path)
        dst = os.path.join(_ROOT, rel_path)
        if os.path.exists(src):
            shutil.copy2(src, dst)


# ── REPORT ───────────────────────────────────────────

def format_plan_report(plans):
    """Human-readable multi-file migration plan."""
    lines = []
    lines.append('═' * 60)
    lines.append('WAVE 2 MIGRATION PLAN')
    lines.append('═' * 60)

    total_changes = 0
    files_to_modify = 0

    for p in plans:
        rel = p['file']

        if not p['exists']:
            lines.append(f'  ⚠️  {rel} — FILE NOT FOUND, skipping')
            continue

        if p['total_changes'] == 0:
            lines.append(f'  ✅ {rel} — already migrated, 0 changes')
            continue

        files_to_modify += 1
        total_changes += p['total_changes']

        lines.append('')
        lines.append(f'📝 {rel}')
        lines.append(f'   Import needed: {p["needs_import"]}')
        if p['call_replacements']:
            lines.append('   Call-site replacements:')
            for desc, n in p['call_replacements']:
                lines.append(f'     • {n}× {desc}')
        if p['func_deletions']:
            lines.append('   Local functions to delete:')
            for fn, start, end in p['func_deletions']:
                lines.append(
                    f'     • {fn}() '
                    f'[lines {start+1}-{end}]'
                )

    lines.append('')
    lines.append('─' * 60)
    lines.append(
        f'TOTALS: {files_to_modify} files to modify, '
        f'{total_changes} changes planned')
    lines.append('═' * 60)

    return '\n'.join(lines)


# ── MAIN ─────────────────────────────────────────────

def run(mode='dry_run'):
    """
    Main entrypoint.
    mode: 'dry_run' or 'execute'
    """
    assert mode in ('dry_run', 'execute'), \
        f'Unknown mode: {mode}'

    _log(f'[wave2] Mode: {mode}')
    _log(f'[wave2] Repo root: {_ROOT}')
    _log(f'[wave2] Target files: {len(TARGET_FILES)}')
    _log('')

    # Phase 1: Analyze every file
    plans = []
    for rel in TARGET_FILES:
        abs_p = os.path.join(_ROOT, rel)
        plans.append(analyze_file(abs_p))

    # Print plan
    report = format_plan_report(plans)
    _log(report)

    if mode == 'dry_run':
        _log('')
        _log('[wave2] DRY RUN complete — no files modified.')
        return {
            'mode':            'dry_run',
            'files_analyzed':  len(plans),
            'files_to_modify': sum(
                1 for p in plans
                if p['exists'] and p['total_changes'] > 0),
            'total_changes':   sum(
                p['total_changes']
                for p in plans if p['exists']),
            'success':         True,
            'log':             '\n'.join(_LOG_LINES),
        }

    # ─── EXECUTE MODE ────────────────────────────────

    # Filter to files that actually need changes
    actionable = [
        (p['file'], p) for p in plans
        if p['exists'] and p['total_changes'] > 0
    ]

    if not actionable:
        _log('')
        _log('[wave2] No files need changes. Exiting.')
        return {
            'mode':            'execute',
            'files_analyzed':  len(plans),
            'files_modified':  0,
            'success':         True,
            'log':             '\n'.join(_LOG_LINES),
        }

    # Phase 2: Backup
    ts          = _ts_str()
    backup_dir  = os.path.join(_ROOT, 'quarantine', f'wave2_{ts}')
    _log('')
    _log(f'[wave2] Backing up {len(actionable)} files → {backup_dir}')
    create_backup(backup_dir, actionable)

    # Phase 3: Apply + syntax check each
    results = []
    any_fail = False

    for rel, plan in actionable:
        abs_p = os.path.join(_ROOT, rel)
        _log(f'[wave2] Processing {rel}')

        try:
            new_content = apply_changes(abs_p, plan)
        except Exception as e:
            _log(f'  ❌ apply_changes error: {e}')
            results.append((rel, False, f'apply error: {e}'))
            any_fail = True
            continue

        ok, err = syntax_check(abs_p, new_content)
        if not ok:
            _log(f'  ❌ syntax check failed: {err}')
            results.append((rel, False, err))
            any_fail = True
            continue

        with open(abs_p, 'w', encoding='utf-8') as f:
            f.write(new_content)

        _log(f'  ✅ modified — {plan["total_changes"]} changes')
        results.append((rel, True, ''))

    # Phase 4: Rollback on any failure
    if any_fail:
        _log('')
        _log('[wave2] ❌ ONE OR MORE FILES FAILED. Rolling back ALL changes.')
        restore_backup(backup_dir, actionable)
        _log('[wave2] Rollback complete. Backup preserved for forensics.')
        return {
            'mode':           'execute',
            'files_analyzed': len(plans),
            'files_modified': 0,
            'success':        False,
            'backup_dir':     backup_dir,
            'results':        results,
            'log':            '\n'.join(_LOG_LINES),
        }

    # Phase 5: Write audit log
    _log('')
    _log('[wave2] ✅ ALL files modified and syntax-checked.')
    _log(f'[wave2] Files modified: {len(actionable)}')
    _log(f'[wave2] Backup: {backup_dir}')

    log_path = os.path.join(
        _ROOT, 'doc', f'wave2_migration_log_{ts}.md')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('# Wave 2 Migration Log\n\n')
        f.write(f'**Timestamp:** {ts}\n\n')
        f.write(f'**Files modified:** {len(actionable)}\n\n')
        f.write(f'**Backup:** `{os.path.relpath(backup_dir, _ROOT)}`\n\n')
        f.write('## Plan\n\n```\n')
        f.write(report)
        f.write('\n```\n\n')
        f.write('## Execution\n\n')
        for rel, ok, err in results:
            icon = '✅' if ok else '❌'
            f.write(f'- {icon} `{rel}`')
            if err:
                f.write(f' — {err}')
            f.write('\n')

    _log(f'[wave2] Audit log: {log_path}')

    return {
        'mode':           'execute',
        'files_analyzed': len(plans),
        'files_modified': len(actionable),
        'success':        True,
        'backup_dir':     backup_dir,
        'log_path':       log_path,
        'results':        results,
        'log':            '\n'.join(_LOG_LINES),
    }


# ── CLI ──────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(
        description='Wave 2 IST migration script')
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument(
        '--dry-run',
        action='store_true',
        help='Analyze + print plan, no file writes')
    g.add_argument(
        '--execute',
        action='store_true',
        help='Apply migration with backup + syntax checks')
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit result as JSON at end (for workflow)')

    args = parser.parse_args()
    mode = 'dry_run' if args.dry_run else 'execute'

    result = run(mode)

    if args.json:
        # Strip log from JSON (too big for GITHUB_OUTPUT)
        summary = {
            k: v for k, v in result.items() if k != 'log'
        }
        print('\n=== JSON_RESULT ===')
        print(json.dumps(summary, indent=2))

    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    _cli()
