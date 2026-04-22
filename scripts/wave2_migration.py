#!/usr/bin/env python3
# ── scripts/wave2_migration.py (v3 — AST import fix) ─
# Automated migration from per-file local IST helpers
# to the canonical calendar_utils helpers shipped in
# Wave 1.
#
# Kills (per doc/fix_table.md):
#   H-03 — _is_trading_day duplicated in 4 files
#   H-09 — date.today() UTC drift across 5+ files
#   M-06 — IST helpers duplicated in 5 files
#
# v3 CHANGE (Apr 23 2026):
#   _inject_import() now uses ast.parse() to find
#   the TRUE end line of the last import statement,
#   including multi-line parenthesized imports like:
#
#     from outcome_evaluator import (
#         _load_holidays,
#         _is_trading_day,
#         FLAT_PCT,
#     )
#
#   v2 matched only the OPENING line of such imports
#   and injected the canonical import at line+1 —
#   landing INSIDE the paren list and breaking syntax.
#   3 of 11 files failed in v2 for exactly this reason
#   (outcome_evaluator L75, open_validator L35,
#   recover_stuck_signals L64).
#
# v2 CHANGE (kept):
#   Function deletion uses ast.parse() for exact
#   FunctionDef boundaries (lineno / end_lineno).
#
# Does NOT touch:
#   - telegram_bot.py (user skip decision)
#   - M-11 recover_stuck_signals TELEGRAM_TOKEN rename
#   - Any local helpers not in LOCAL_FUNCS_TO_DELETE
#
# Usage:
#   python scripts/wave2_migration.py --dry-run
#   python scripts/wave2_migration.py --execute
#
# Safety rails:
#   1. Backup every file to quarantine/wave2_<ts>/
#   2. Syntax check every modified file via ast.parse
#   3. If ANY file fails syntax → revert ALL files
#   4. Full audit log in doc/wave2_migration_log_*.md
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

CALL_REPLACEMENTS = [
    (r'\bdate\.today\(\)',   'ist_today()',   'date.today() UTC → ist_today() IST'),
    (r'\b_ist_today\(\)',    'ist_today()',   '_ist_today() → ist_today()'),
    (r'\b_today_ist\(\)',    'ist_today()',   '_today_ist() → ist_today()'),
    (r'\b_now_ist_date\(\)', 'ist_today()',   '_now_ist_date() → ist_today()'),
    (r'\b_ist_now\(\)',      'ist_now()',     '_ist_now() → ist_now()'),
    (r'\b_now_ist\(\)',      'ist_now()',     '_now_ist() → ist_now()'),
    (r'\b_ist_now_str\(\)',  'ist_now_str()', '_ist_now_str() → ist_now_str()'),
    (r'\b_now_ist_str\(\)',  'ist_now_str()', '_now_ist_str() → ist_now_str()'),
    (r'\b_is_trading_day\(', 'is_trading_day(', '_is_trading_day( → is_trading_day('),
]

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

CANONICAL_IMPORT = (
    'from calendar_utils import '
    'ist_today, ist_now, ist_now_str, is_trading_day'
)


# ── PATHS ────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _ts_str():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(tz=ist).strftime('%Y%m%d_%H%M%S')


_LOG_LINES = []


def _log(msg, also_print=True):
    _LOG_LINES.append(msg)
    if also_print:
        print(msg)


# ── AST-BASED FUNCTION FINDER (v2) ───────────────────

def find_function_blocks(content):
    """
    Use ast.parse() to locate exact function boundaries.
    Returns list of dicts with name, lineno, end_lineno,
    and optional decorator_lineno.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        raise ValueError(
            f'File does not parse (pre-migration): '
            f'{e.msg} at line {e.lineno}'
        )

    blocks = []
    for node in tree.body:
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        if node.name not in LOCAL_FUNCS_TO_DELETE:
            continue

        dec_lineno = None
        if node.decorator_list:
            dec_lineno = min(
                d.lineno for d in node.decorator_list
            )

        blocks.append({
            'name':             node.name,
            'lineno':           node.lineno,
            'end_lineno':       node.end_lineno,
            'decorator_lineno': dec_lineno,
        })

    return blocks


# ── AST-BASED IMPORT END FINDER (v3 NEW) ─────────────

def find_last_import_end_line(content):
    """
    v3 FIX: Use ast.parse() to find the end line of the
    LAST module-level import statement. Handles multi-line
    parenthesized imports like:

      from outcome_evaluator import (
          _load_holidays,
          FLAT_PCT,
      )

    ast gives us node.end_lineno which points to the
    closing paren line. This is the ONLY reliable way
    to know where an import statement ends.

    Returns:
      int — 1-indexed line number of the last line of
            the final import statement, OR
      None — if no imports exist at module level.
    """
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None

    last_end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end = getattr(node, 'end_lineno', node.lineno)
            if end > last_end:
                last_end = end

    return last_end if last_end > 0 else None


# ── ANALYSIS ─────────────────────────────────────────

def analyze_file(abs_path):
    rel = os.path.relpath(abs_path, _ROOT)

    if not os.path.exists(abs_path):
        return {
            'file':              rel,
            'exists':            False,
            'needs_import':      False,
            'call_replacements': [],
            'func_deletions':    [],
            'total_changes':     0,
            'parse_error':       None,
        }

    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = []
    for pattern, replacement, desc in CALL_REPLACEMENTS:
        matches = re.findall(pattern, content)
        if matches:
            replacements.append((desc, len(matches)))

    parse_error = None
    func_deletions = []
    try:
        blocks = find_function_blocks(content)
        for b in blocks:
            func_deletions.append((
                b['name'],
                b['lineno'],
                b['end_lineno'],
                b['decorator_lineno'],
            ))
    except ValueError as e:
        parse_error = str(e)

    has_canonical = CANONICAL_IMPORT in content
    has_any_cu_import = bool(
        re.search(r'^from\s+calendar_utils\s+import\s+',
                  content, re.MULTILINE)
    )

    needs_import = (
        bool(replacements) or bool(func_deletions)
    ) and not has_canonical

    total = (
        sum(c for _, c in replacements)
        + len(func_deletions)
    )
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
        'parse_error':       parse_error,
    }


# ── APPLY ────────────────────────────────────────────

def apply_changes(abs_path, plan):
    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    def _del_start(entry):
        _name, lineno, _end, dec = entry
        return dec if dec is not None else lineno

    deletions = sorted(
        plan['func_deletions'],
        key=_del_start,
        reverse=True,
    )

    for name, lineno, end_lineno, dec_lineno in deletions:
        start_idx = (dec_lineno if dec_lineno else lineno) - 1
        end_idx   = end_lineno

        scoop_start = start_idx
        j = start_idx - 1
        while j >= 0:
            stripped = lines[j].strip()
            if not stripped:
                break
            if stripped.startswith('#'):
                scoop_start = j
                j -= 1
                continue
            break

        del lines[scoop_start:end_idx]

    content = '\n'.join(lines)

    for pattern, replacement, _desc in CALL_REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    if plan['needs_import']:
        content = _inject_import(content)

    return content


def _inject_import(content):
    """
    v3 FIX: Use AST to find TRUE end line of last
    import. Handles multi-line parenthesized imports
    that v2 broke on.

    Inserts CANONICAL_IMPORT on the line AFTER the
    last import statement ends. Falls back to top-of-
    file placement if no imports exist.
    """
    last_end_line = find_last_import_end_line(content)
    lines = content.split('\n')

    if last_end_line is None:
        # No imports found. Find first non-comment,
        # non-blank, non-docstring line and insert there.
        i = 0
        in_docstring = False
        docstring_q  = None
        while i < len(lines):
            s = lines[i].strip()
            if not in_docstring:
                for q in ('"""', "'''"):
                    if s.startswith(q):
                        if (len(s) > 3 and s.endswith(q)):
                            break
                        in_docstring = True
                        docstring_q = q
                        break
                if in_docstring:
                    i += 1
                    continue
                if s and not s.startswith('#'):
                    break
            else:
                if docstring_q and docstring_q in s:
                    in_docstring = False
                    docstring_q = None
                i += 1
                continue
            i += 1
        lines.insert(i, CANONICAL_IMPORT)
        lines.insert(i + 1, '')
    else:
        # Insert AFTER the line where last import ends.
        # last_end_line is 1-indexed, list is 0-indexed,
        # so insert at index last_end_line.
        lines.insert(last_end_line, CANONICAL_IMPORT)

    return '\n'.join(lines)


# ── VERIFY ───────────────────────────────────────────

def syntax_check(path, content):
    try:
        ast.parse(content, filename=path)
        return True, ''
    except SyntaxError as e:
        return False, f'{e.msg} at line {e.lineno}'
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


# ── BACKUP ───────────────────────────────────────────

def create_backup(backup_dir, targets_with_plans):
    os.makedirs(backup_dir, exist_ok=True)
    for rel_path, _plan in targets_with_plans:
        abs_path = os.path.join(_ROOT, rel_path)
        if not os.path.exists(abs_path):
            continue
        dest = os.path.join(backup_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(abs_path, dest)


def restore_backup(backup_dir, targets_with_plans):
    for rel_path, _plan in targets_with_plans:
        src = os.path.join(backup_dir, rel_path)
        dst = os.path.join(_ROOT, rel_path)
        if os.path.exists(src):
            shutil.copy2(src, dst)


# ── REPORT ───────────────────────────────────────────

def format_plan_report(plans):
    lines = []
    lines.append('═' * 60)
    lines.append('WAVE 2 MIGRATION PLAN (v3 — AST imports + funcs)')
    lines.append('═' * 60)

    total_changes = 0
    files_to_modify = 0
    parse_errors = 0

    for p in plans:
        rel = p['file']

        if not p['exists']:
            lines.append(f'  ⚠️  {rel} — FILE NOT FOUND, skipping')
            continue

        if p.get('parse_error'):
            lines.append(
                f'  ❌ {rel} — PARSE ERROR: {p["parse_error"]}')
            parse_errors += 1
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
            for name, lineno, end_lineno, dec in p['func_deletions']:
                start_display = dec if dec else lineno
                lines.append(
                    f'     • {name}() '
                    f'[lines {start_display}-{end_lineno}]'
                )

    lines.append('')
    lines.append('─' * 60)
    lines.append(
        f'TOTALS: {files_to_modify} files to modify, '
        f'{total_changes} changes planned, '
        f'{parse_errors} parse errors')
    lines.append('═' * 60)

    return '\n'.join(lines)


# ── MAIN ─────────────────────────────────────────────

def run(mode='dry_run'):
    assert mode in ('dry_run', 'execute'), \
        f'Unknown mode: {mode}'

    _log(f'[wave2] Mode: {mode}  (v3 AST-based)')
    _log(f'[wave2] Repo root: {_ROOT}')
    _log(f'[wave2] Target files: {len(TARGET_FILES)}')
    _log('')

    plans = []
    for rel in TARGET_FILES:
        abs_p = os.path.join(_ROOT, rel)
        plans.append(analyze_file(abs_p))

    report = format_plan_report(plans)
    _log(report)

    parse_errors = [
        p for p in plans
        if p['exists'] and p.get('parse_error')
    ]
    if parse_errors:
        _log('')
        _log(
            f'[wave2] ❌ ABORT — {len(parse_errors)} file(s) '
            f'have pre-existing parse errors.')
        return {
            'mode':    mode,
            'success': False,
            'reason':  'pre_existing_parse_errors',
            'files_analyzed': len(plans),
            'log':     '\n'.join(_LOG_LINES),
        }

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

    actionable = [
        (p['file'], p) for p in plans
        if p['exists'] and p['total_changes'] > 0
    ]

    if not actionable:
        _log('')
        _log('[wave2] No files need changes. Exiting.')
        return {
            'mode':    'execute',
            'files_analyzed': len(plans),
            'files_modified': 0,
            'success': True,
            'log':     '\n'.join(_LOG_LINES),
        }

    ts         = _ts_str()
    backup_dir = os.path.join(_ROOT, 'quarantine', f'wave2_{ts}')
    _log('')
    _log(f'[wave2] Backing up {len(actionable)} files → {backup_dir}')
    create_backup(backup_dir, actionable)

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

    _log('')
    _log('[wave2] ✅ ALL files modified and syntax-checked.')
    _log(f'[wave2] Files modified: {len(actionable)}')
    _log(f'[wave2] Backup: {backup_dir}')

    log_path = os.path.join(
        _ROOT, 'doc', f'wave2_migration_log_{ts}.md')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('# Wave 2 Migration Log (v3)\n\n')
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
        description='Wave 2 IST migration script (v3)')
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run', action='store_true')
    g.add_argument('--execute', action='store_true')
    parser.add_argument('--json', action='store_true')

    args = parser.parse_args()
    mode = 'dry_run' if args.dry_run else 'execute'

    result = run(mode)

    if args.json:
        summary = {k: v for k, v in result.items() if k != 'log'}
        print('\n=== JSON_RESULT ===')
        print(json.dumps(summary, indent=2, default=str))

    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    _cli()
