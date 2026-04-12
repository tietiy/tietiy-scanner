# scanner/colab_sync.py
# Exports signal_history.json as Colab-ready JSON
# New file — V1 Fix R9
#
# Writes output/colab_export.json
# Served via GitHub Pages at:
#   tietiy.github.io/tietiy-scanner/colab_export.json
#
# Colab reads it with:
#   import requests
#   data = requests.get(EXPORT_URL).json()
#   signals = data['signals']
#
# Export adds derived boolean fields so Colab cells
# don't need to reimplement outcome/generation logic.
# ─────────────────────────────────────────────────────

import os
import sys
import json
from datetime import date, datetime

_HERE   = os.path.dirname(os.path.abspath(__file__))
_ROOT   = os.path.dirname(_HERE)
_OUTPUT = os.path.join(_ROOT, 'output')

sys.path.insert(0, _HERE)

HISTORY_FILE = os.path.join(_OUTPUT, 'signal_history.json')
EXPORT_FILE  = os.path.join(_OUTPUT, 'colab_export.json')

EXPORT_URL   = ('https://tietiy.github.io/'
                'tietiy-scanner/colab_export.json')

# ── OUTCOME SETS ──────────────────────────────────────
OUTCOME_WIN  = {'TARGET_HIT', 'DAY6_WIN'}
OUTCOME_LOSS = {'STOP_HIT',   'DAY6_LOSS'}
OUTCOME_FLAT = {'DAY6_FLAT'}
OUTCOME_DONE = OUTCOME_WIN | OUTCOME_LOSS | OUTCOME_FLAT

LIVE_START_DATE = '2026-04-06'


# ── LOAD ──────────────────────────────────────────────
def _load_history():
    if not os.path.exists(HISTORY_FILE):
        print('[colab_sync] signal_history.json not found')
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            data = json.load(f)
        return data.get('history', [])
    except Exception as e:
        print(f'[colab_sync] Load error: {e}')
        return []


# ── ENRICH SIGNAL ─────────────────────────────────────
def _enrich(sig):
    """
    Add derived boolean fields to a signal dict.
    These are computed — not stored — fields that
    Colab analysis cells commonly need.
    """
    outcome    = (sig.get('outcome') or '').upper()
    result     = (sig.get('result')  or '').upper()
    action     = (sig.get('action')  or '').upper()
    generation = sig.get('generation', 1) or 1
    sig_date   = sig.get('date', '')

    is_took     = action == 'TOOK'
    is_rejected = result == 'REJECTED'
    is_live     = generation >= 1
    is_backfill = generation == 0
    is_resolved = outcome in OUTCOME_DONE
    is_win      = outcome in OUTCOME_WIN
    is_loss     = outcome in OUTCOME_LOSS
    is_flat     = outcome in OUTCOME_FLAT
    is_open     = is_took and not is_resolved
    is_sa       = bool(sig.get('is_sa', False)) or \
                  (sig.get('signal') or '').endswith('_SA')

    # R:R derived
    entry  = float(sig.get('entry')        or 0)
    stop   = float(sig.get('stop')         or 0)
    target = float(sig.get('target_price') or 0)
    rr     = None
    if entry > 0 and stop > 0 and target > 0:
        risk   = abs(entry - stop)
        reward = abs(target - entry)
        if risk > 0:
            rr = round(reward / risk, 2)

    # Bear regime flag (normalised)
    bear_bonus = (
        sig.get('bear_bonus') is True or
        str(sig.get('bear_bonus')).lower() == 'true')

    # Quality composite
    vol_confirm  = (
        sig.get('vol_confirm') is True or
        str(sig.get('vol_confirm')).lower() == 'true')
    rs_strong    = (
        sig.get('rs_strong') is True or
        sig.get('rs_q') == 'Strong')
    sec_leading  = (
        sig.get('sec_leading') is True or
        sig.get('sec_mom') == 'Leading')
    grade_A      = (
        sig.get('grade_A') is True or
        sig.get('grade') == 'A')
    quality_score = sum([
        vol_confirm, rs_strong, sec_leading, grade_A])

    # Normalise regime
    regime_raw = (
        sig.get('stock_regime') or
        sig.get('regime') or '').strip()
    regime_norm = (
        'Bear'   if regime_raw.upper() in
                    ('BEAR', 'BEARISH') else
        'Bull'   if regime_raw.upper() in
                    ('BULL', 'BULLISH') else
        'Choppy' if regime_raw.upper() in
                    ('CHOPPY', 'RANGING',
                     'NEUTRAL', 'CHOPPY') else
        regime_raw or None)

    enriched = dict(sig)
    enriched.update({
        # derived booleans
        'is_took':      is_took,
        'is_rejected':  is_rejected,
        'is_live':      is_live,
        'is_backfill':  is_backfill,
        'is_resolved':  is_resolved,
        'is_win':       is_win,
        'is_loss':      is_loss,
        'is_flat':      is_flat,
        'is_open':      is_open,
        'is_sa':        is_sa,
        # derived numerics
        'rr_calc':      rr,
        'quality_score': quality_score,
        # normalised fields
        'bear_bonus':   bear_bonus,
        'vol_confirm':  vol_confirm,
        'rs_strong':    rs_strong,
        'sec_leading':  sec_leading,
        'grade_A':      grade_A,
        'regime_norm':  regime_norm,
    })
    return enriched


# ── BUILD SUMMARY STATS ───────────────────────────────
def _build_summary(signals):
    """
    Top-level summary stats written into the export.
    Lets Colab display a quick status without iterating.
    """
    live   = [s for s in signals if s['is_live']
              and s['is_took']]
    res    = [s for s in live    if s['is_resolved']]
    wins   = [s for s in res     if s['is_win']]
    losses = [s for s in res     if s['is_loss']]
    open_s = [s for s in live    if s['is_open']]

    wr = None
    if len(res) >= 5:
        wr = round(len(wins) / len(res) * 100, 1)

    # avg P&L
    pnl_arr = [float(s['pnl_pct'])
               for s in res
               if s.get('pnl_pct') is not None]
    avg_pnl = (round(sum(pnl_arr) / len(pnl_arr), 2)
               if pnl_arr else None)

    # score bucket WR
    buckets = {}
    for s in res:
        sc   = float(s.get('score') or 0)
        buck = ('7-10' if sc >= 7 else
                '5-6'  if sc >= 5 else
                '3-4'  if sc >= 3 else '1-2')
        if buck not in buckets:
            buckets[buck] = {'wins': 0, 'total': 0}
        buckets[buck]['total'] += 1
        if s['is_win']:
            buckets[buck]['wins'] += 1

    bucket_wr = {}
    for buck, data in buckets.items():
        if data['total'] >= 5:
            bucket_wr[buck] = round(
                data['wins'] / data['total'] * 100, 1)

    # regime WR
    regime_stats = {}
    for s in res:
        r = s.get('regime_norm') or 'Unknown'
        if r not in regime_stats:
            regime_stats[r] = {'wins': 0, 'total': 0}
        regime_stats[r]['total'] += 1
        if s['is_win']:
            regime_stats[r]['wins'] += 1

    regime_wr = {}
    for r, data in regime_stats.items():
        if data['total'] >= 5:
            regime_wr[r] = round(
                data['wins'] / data['total'] * 100, 1)

    return {
        'total_signals':    len(signals),
        'live_took':        len(live),
        'live_resolved':    len(res),
        'live_open':        len(open_s),
        'wins':             len(wins),
        'losses':           len(losses),
        'win_rate':         wr,
        'avg_pnl':          avg_pnl,
        'phase2_unlocked':  len(res) >= 30,
        'bucket_wr':        bucket_wr,
        'regime_wr':        regime_wr,
        'export_date':      date.today().isoformat(),
        'export_url':       EXPORT_URL,
    }


# ── MAIN ──────────────────────────────────────────────
def run_colab_sync():
    print('[colab_sync] Starting...')

    history = _load_history()
    if not history:
        print('[colab_sync] Empty history — aborting')
        return False

    # Enrich all signals
    enriched = [_enrich(s) for s in history]

    # Build summary
    summary = _build_summary(enriched)

    # Assemble export
    export = {
        'export_version':  1,
        'export_date':     date.today().isoformat(),
        'export_url':      EXPORT_URL,
        'generated_at':    datetime.utcnow()
                           .strftime('%Y-%m-%dT%H:%M:%SZ'),
        'live_start_date': LIVE_START_DATE,
        'summary':         summary,
        'signals':         enriched,
        # Colab usage hint
        '_usage': {
            'load': (
                'import requests\n'
                'data = requests.get(export_url).json()\n'
                'signals = data["signals"]\n'
                'live = [s for s in signals '
                'if s["is_live"] and s["is_took"]]'
            ),
            'filter_examples': [
                'resolved = [s for s in live '
                'if s["is_resolved"]]',
                'wins = [s for s in resolved '
                'if s["is_win"]]',
                'bear_uptri = [s for s in live '
                'if s["signal"]=="UP_TRI" '
                'and s["bear_bonus"]]',
            ],
        },
    }

    # Write
    os.makedirs(_OUTPUT, exist_ok=True)
    tmp = EXPORT_FILE + '.tmp'
    try:
        with open(tmp, 'w') as f:
            json.dump(export, f, indent=2,
                      default=str)
        # Validate
        with open(tmp, 'r') as f:
            json.load(f)
        os.replace(tmp, EXPORT_FILE)
    except Exception as e:
        print(f'[colab_sync] Write failed: {e}')
        if os.path.exists(tmp):
            os.remove(tmp)
        return False

    size_kb = os.path.getsize(EXPORT_FILE) / 1024
    print(f'[colab_sync] ✓ Written: colab_export.json '
          f'({size_kb:.1f} KB · '
          f'{len(enriched)} signals)')
    print(f'[colab_sync] Summary: '
          f'live={summary["live_took"]} '
          f'resolved={summary["live_resolved"]} '
          f'WR={summary["win_rate"]}% '
          f'phase2={summary["phase2_unlocked"]}')
    print(f'[colab_sync] URL: {EXPORT_URL}')
    return True


if __name__ == '__main__':
    run_colab_sync()
