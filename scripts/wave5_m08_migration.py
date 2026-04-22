#!/usr/bin/env python3
# ── scripts/wave5_m08_migration.py ────────────────────
# Automated migration to consolidate duplicated
# Telegram _esc helpers into a canonical import
# from telegram_bot.
#
# Kills (per doc/fix_table.md):
#   M-08 — _esc escape duplicated in 4 files
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
    'scanner/heartbeat.py',
    'scanner/gap_report.py',
    'scanner/deep_debugger.py',
    'scanner/diagnostic.py',
]

CALL_REPLACEMENTS = []

LOCAL_FUNCS_TO_DELETE = [
    '_esc',
]

CANONICAL_IMPORT = 'from telegram_bot import _esc'


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


# ── AST-BASED FUNCTION FINDER ────────────────────────

def find_function_blocks(content):
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        raise ValueError(
            'File does not parse (pre-migration): '
            + e.msg + ' at line ' + str(e.lineno)
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


# ── AST-BASED IMPORT END FINDER ──────────────────────

def find_last_import_end_line(content):
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


# ── CANONICAL-IMPORT DETECTION ───────────────────────

def _already_imports_canonical(content):
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False

    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != 'telegram_bot':
            continue
        for alias in node.names:
            if alias.name == '_esc':
                return True
    return False


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

    has_canonical = _already_imports_canonical(content)

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
    last_end_line = find_last_import_end_line(content)
    lines = content.split('\n')

    if last_end_line is None:
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
        lines.insert(last_end_line, CANONICAL_IMPORT)

    return '\n'.join(lines)


# ── VERIFY ───────────────────────────────────────────

def syntax_check(path, content):
    try:
        ast.parse(content, filename=path)
        return True, ''
    except SyntaxError as e:
        return False, e.msg + ' at line ' + str(e.lineno)
    except Exception as e:
        return False, type(e).__name__ + ': ' + str(e)


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
    lines.append('=' * 60)
    lines.append('WAVE 5.1 MIGRATION PLAN (M-08 _esc consolidation)')
    lines.append('=' * 60)

    total_changes   = 0
    files_to_modify = 0
    parse_errors    = 0
    already_done    = 0

    for p in plans:
        rel = p['file']

        if not p['exists']:
            lines.append('  [!]  ' + rel + ' - FILE NOT FOUND')
            continue

        if p.get('parse_error'):
            lines.append(
                '  [X] ' + rel + ' - PARSE ERROR: '
                + p['parse_error'])
            parse_errors += 1
            continue

        if p['has_canonical'] and not p['func_deletions']:
            lines.append(
                '  [OK] ' + rel + ' - already migrated')
            already_done += 1
            continue

        if p['total_changes'] == 0:
            lines.append('  [OK] ' + rel + ' - no changes needed')
            continue

        files_to_modify += 1
        total_changes += p['total_changes']

        lines.append('')
        lines.append('File: ' + rel)
        lines.append('   Import needed: ' + str(p['needs_import']))
        if p['func_deletions']:
            lines.append('   Local functions to delete:')
            for name, lineno, end_lineno, dec in p['func_deletions']:
                start_display = dec if dec else lineno
                lines.append(
                    '     - ' + name + '() '
                    + '[lines ' + str(start_display)
                    + '-' + str(end_lineno) + ']'
                )

    lines.append('')
    lines.append('-' * 60)
    lines.append(
        'TOTALS: ' + str(files_to_modify) + ' files to modify, '
        + str(total_changes) + ' changes, '
        + str(already_done) + ' already migrated, '
        + str(parse_errors) + ' parse errors')
    lines.append('=' * 60)

    return '\n'.join(lines)


# ── MAIN ─────────────────────────────────────────────

def run(mode='dry_run'):
    assert mode in ('dry_run', 'execute'), \
        'Unknown mode: ' + mode

    _log('[wave5] Mode: ' + mode + '  (M-08 _esc consolidation)')
    _log('[wave5] Repo root: ' + _ROOT)
    _log('[wave5] Target files: ' + str(len(TARGET_FILES)))
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
            '[wave5] ABORT - ' + str(len(parse_errors))
            + ' file(s) have pre-existing parse errors.')
        return {
            'mode':    mode,
            'success': False,
            'reason':  'pre_existing_parse_errors',
            'files_analyzed': len(plans),
            'log':     '\n'.join(_LOG_LINES),
        }

    if mode == 'dry_run':
        _log('')
        _log('[wave5] DRY RUN complete - no files modified.')
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
        _log('[wave5] No files need changes. Exiting.')
        return {
            'mode':    'execute',
            'files_analyzed': len(plans),
            'files_modified': 0,
            'success': True,
            'log':     '\n'.join(_LOG_LINES),
        }

    ts         = _ts_str()
    backup_dir = os.path.join(_ROOT, 'quarantine', 'wave5_' + ts)
    _log('')
    _log('[wave5] Backing up ' + str(len(actionable))
         + ' files -> ' + backup_dir)
    create_backup(backup_dir, actionable)

    results = []
    any_fail = False

    for rel, plan in actionable:
        abs_p = os.path.join(_ROOT, rel)
        _log('[wave5] Processing ' + rel)

        try:
            new_content = apply_changes(abs_p, plan)
        except Exception as e:
            _log('  FAIL apply_changes error: ' + str(e))
            results.append((rel, False, 'apply error: ' + str(e)))
            any_fail = True
            continue

        ok, err = syntax_check(abs_p, new_content)
        if not ok:
            _log('  FAIL syntax check: ' + err)
            results.append((rel, False, err))
            any_fail = True
            continue

        with open(abs_p, 'w', encoding='utf-8') as f:
            f.write(new_content)

        _log('  OK modified - ' + str(plan['total_changes'])
             + ' changes')
        results.append((rel, True, ''))

    if any_fail:
        _log('')
        _log('[wave5] FAIL - ONE OR MORE FILES FAILED. Rolling back.')
        restore_backup(backup_dir, actionable)
        _log('[wave5] Rollback complete. Backup preserved.')
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
    _log('[wave5] OK - ALL files modified and syntax-checked.')
    _log('[wave5] Files modified: ' + str(len(actionable)))
    _log('[wave5] Backup: ' + backup_dir)

    log_path = os.path.join(
        _ROOT, 'doc', 'wave5_m08_log_' + ts + '.md')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write('# Wave 5.1 Migration Log (M-08)\n\n')
        f.write('**Timestamp:** ' + ts + '\n\n')
        f.write('**Files modified:** ' + str(len(actionable)) + '\n\n')
        f.write('**Backup:** `'
                + os.path.relpath(backup_dir, _ROOT) + '`\n\n')
        f.write('## Plan\n\n```\n')
        f.write(report)
        f.write('\n```\n\n')
        f.write('## Execution\n\n')
        for rel, ok, err in results:
            icon = 'OK' if ok else 'FAIL'
            f.write('- [' + icon + '] `' + rel + '`')
            if err:
                f.write(' - ' + err)
            f.write('\n')

    _log('[wave5] Audit log: ' + log_path)

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
        description='Wave 5.1 - M-08 _esc consolidation')
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
