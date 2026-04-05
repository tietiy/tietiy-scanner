// ── stats.js ─────────────────────────────────────────
// Renders the Stats tab
// Phase 1 — Signal Validation Dashboard
//
// Reads from:
//   window.TIETIY.history  → signal_history.json
//   window.TIETIY.meta     → meta.json
//
// Outcome model (6-day window):
//   TARGET_HIT  → price hit 2R target within 6 days
//   STOP_HIT    → price hit stop within 6 days
//   DAY6_WIN    → Day 6 close > entry (no hit)
//   DAY6_LOSS   → Day 6 close < entry (no hit)
//   DAY6_FLAT   → Day 6 close ±0.5% of entry
//   OPEN        → window not yet complete
// ─────────────────────────────────────────────────────

const _SIG_THRESHOLD  = 30;  // min resolved signals
const _MIN_DISPLAY    = 3;   // min to show breakdown

const _BT_WR = {
  UP_TRI:      87,
  DOWN_TRI:    87,
  UP_TRI_SA:   87,
  DOWN_TRI_SA: 87,
  BULL_PROXY:  67,
  OVERALL:     87,
};


// ── HELPERS ───────────────────────────────────────────

function _pct(num, den) {
  if (!den || den === 0) return null;
  return Math.round(num / den * 100);
}

function _gapColor(live, baseline) {
  if (live === null || live === undefined)
    return '#555';
  const gap = live - baseline;
  if (gap >= -5)  return '#00C851';
  if (gap >= -15) return '#FFD700';
  return '#f85149';
}

function _gapLabel(live, baseline) {
  if (live === null || live === undefined)
    return '—';
  const gap  = live - baseline;
  const sign = gap >= 0 ? '+' : '';
  return sign + gap + '%';
}

function _bar(value, max, color) {
  const pct = Math.min(
    Math.round((value / max) * 100), 100);
  return `
    <div style="background:#161b22;
      border-radius:4px;height:6px;
      overflow:hidden;margin:4px 0;">
      <div style="background:${color};
        height:100%;border-radius:4px;
        width:${pct}%;"></div>
    </div>`;
}

function _sectionHead(title, sub) {
  return `
    <div style="border-left:3px solid #ffd700;
      padding-left:8px;margin:16px 0 10px;">
      <div style="color:#ffd700;font-size:11px;
        font-weight:700;letter-spacing:1px;">
        ${title}
      </div>
      ${sub
        ? `<div style="color:#444;font-size:10px;
             margin-top:2px;">${sub}</div>`
        : ''}
    </div>`;
}

function _card(label, value, sub, color) {
  return `
    <div style="background:#161b22;
      border-radius:8px;padding:10px 12px;">
      <div style="color:#555;font-size:10px;
        margin-bottom:4px;">${label}</div>
      <div style="color:${color || '#c9d1d9'};
        font-size:18px;font-weight:700;">
        ${value}
      </div>
      ${sub
        ? `<div style="color:#444;font-size:10px;
             margin-top:2px;">${sub}</div>`
        : ''}
    </div>`;
}

function _row(label, value, color) {
  return `
    <div style="display:flex;
      justify-content:space-between;
      padding:5px 0;
      border-bottom:1px solid #0c0c1a;
      font-size:11px;">
      <span style="color:#555;">${label}</span>
      <span style="color:${color || '#c9d1d9'};">
        ${value}
      </span>
    </div>`;
}


// ── DATA ENGINE ───────────────────────────────────────
// Core of Phase 1 — reads outcome fields
// written by outcome_evaluator.py

function _buildStats(records) {

  // All observed signals — exclude REJECTED
  const observed = records.filter(
    r => r.action !== 'REJECTED' &&
         r.result !== 'REJECTED');

  // Resolved = has a final outcome
  const resolved = observed.filter(r =>
    ['TARGET_HIT','STOP_HIT',
     'DAY6_WIN','DAY6_LOSS',
     'DAY6_FLAT'].includes(r.outcome));

  // Open = still in window
  const open = observed.filter(
    r => !r.outcome || r.outcome === 'OPEN');

  // Outcome breakdowns
  const targetHit  = resolved.filter(
    r => r.outcome === 'TARGET_HIT');
  const stopHit    = resolved.filter(
    r => r.outcome === 'STOP_HIT');
  const day6Win    = resolved.filter(
    r => r.outcome === 'DAY6_WIN');
  const day6Loss   = resolved.filter(
    r => r.outcome === 'DAY6_LOSS');
  const day6Flat   = resolved.filter(
    r => r.outcome === 'DAY6_FLAT');

  const n = resolved.length;

  // Win = TARGET_HIT + DAY6_WIN
  const wins   = targetHit.length + day6Win.length;
  const liveWR = _pct(wins, n);

  // MFE / MAE averages
  const mfeVals = resolved
    .map(r => parseFloat(r.mfe_pct || 0))
    .filter(v => v > 0);
  const maeVals = resolved
    .map(r => parseFloat(r.mae_pct || 0))
    .filter(v => v > 0);
  const avgMFE = mfeVals.length
    ? (mfeVals.reduce((a,b) => a+b, 0) /
       mfeVals.length).toFixed(1)
    : null;
  const avgMAE = maeVals.length
    ? (maeVals.reduce((a,b) => a+b, 0) /
       maeVals.length).toFixed(1)
    : null;
  const mfeMaeRatio = (avgMFE && avgMAE &&
    parseFloat(avgMAE) > 0)
    ? (parseFloat(avgMFE) /
       parseFloat(avgMAE)).toFixed(2)
    : null;

  // Avg days to outcome
  const daysVals = resolved
    .map(r => parseInt(r.days_to_outcome || 0))
    .filter(v => v > 0);
  const avgDays = daysVals.length
    ? Math.round(daysVals.reduce(
        (a,b) => a+b, 0) / daysVals.length)
    : null;

  // By signal type
  const byType = {};
  ['UP_TRI','DOWN_TRI','BULL_PROXY',
   'UP_TRI_SA','DOWN_TRI_SA'].forEach(sig => {
    const sigRes = resolved.filter(
      r => r.signal === sig);
    const sigTgt = sigRes.filter(
      r => r.outcome === 'TARGET_HIT');
    const sigStp = sigRes.filter(
      r => r.outcome === 'STOP_HIT');
    const sigWin = sigRes.filter(
      r => r.outcome === 'DAY6_WIN');
    const sigObs = observed.filter(
      r => r.signal === sig);
    byType[sig] = {
      resolved:   sigRes.length,
      open:       sigObs.filter(
        r => !r.outcome ||
             r.outcome === 'OPEN').length,
      targetHit:  _pct(sigTgt.length,
                    sigRes.length),
      stopHit:    _pct(sigStp.length,
                    sigRes.length),
      winRate:    _pct(
                    sigTgt.length + sigWin.length,
                    sigRes.length),
      avgMFE:     sigRes.length
        ? (sigRes
            .map(r => parseFloat(r.mfe_pct || 0))
            .reduce((a,b) => a+b, 0) /
           sigRes.length).toFixed(1)
        : null,
    };
  });

  // By regime
  const byRegime = {};
  ['Bull','Bear','Choppy'].forEach(reg => {
    const regRes = resolved.filter(
      r => r.regime === reg);
    const regTgt = regRes.filter(
      r => r.outcome === 'TARGET_HIT');
    const regWin = regRes.filter(
      r => r.outcome === 'DAY6_WIN');
    if (regRes.length > 0) {
      byRegime[reg] = {
        resolved: regRes.length,
        targetHit: _pct(regTgt.length,
                     regRes.length),
        winRate:   _pct(
                     regTgt.length +
                     regWin.length,
                     regRes.length),
      };
    }
  });

  // By score bucket
  const byScore = {
    high: { label:'8-10', resolved:0,
            target:0, stop:0, win:0 },
    mid:  { label:'5-7',  resolved:0,
            target:0, stop:0, win:0 },
    low:  { label:'0-4',  resolved:0,
            target:0, stop:0, win:0 },
  };
  resolved.forEach(r => {
    const s    = r.score || 0;
    const tier = s >= 8 ? 'high' :
                 s >= 5 ? 'mid'  : 'low';
    byScore[tier].resolved++;
    if (r.outcome === 'TARGET_HIT')
      byScore[tier].target++;
    if (r.outcome === 'STOP_HIT')
      byScore[tier].stop++;
    if (r.outcome === 'DAY6_WIN')
      byScore[tier].win++;
  });
  Object.keys(byScore).forEach(k => {
    const b = byScore[k];
    b.targetHitPct = _pct(b.target, b.resolved);
    b.stopHitPct   = _pct(b.stop,   b.resolved);
    b.winRate      = _pct(
      b.target + b.win, b.resolved);
  });

  return {
    observed:    observed.length,
    resolved:    n,
    open:        open.length,
    wins,
    liveWR,
    targetHitPct: _pct(targetHit.length, n),
    stopHitPct:   _pct(stopHit.length,   n),
    day6WinPct:   _pct(day6Win.length,   n),
    day6LossPct:  _pct(day6Loss.length,  n),
    day6FlatPct:  _pct(day6Flat.length,  n),
    avgMFE,
    avgMAE,
    mfeMaeRatio,
    avgDays,
    byType,
    byRegime,
    byScore,
    needed: Math.max(0,
      _SIG_THRESHOLD - n),
  };
}


// ── SECTION: OVERVIEW ─────────────────────────────────

function _buildOverview(d) {
  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;
      margin-bottom:4px;">

      <!-- Progress bar -->
      <div style="display:flex;
        justify-content:space-between;
        align-items:center;margin-bottom:6px;">
        <div style="color:#c9d1d9;
          font-size:12px;font-weight:700;">
          Signal Validation Progress
        </div>
        <div style="color:#555;font-size:10px;">
          ${d.resolved} / ${_SIG_THRESHOLD}
          resolved
        </div>
      </div>
      ${_bar(d.resolved, _SIG_THRESHOLD, '#ffd700')}

      <!-- Count grid -->
      <div style="display:grid;
        grid-template-columns:repeat(3,1fr);
        gap:8px;margin-top:12px;">
        ${_card('Observed',
          d.observed, 'total signals',
          '#c9d1d9')}
        ${_card('Resolved',
          d.resolved, 'outcomes known',
          '#8b949e')}
        ${_card('Open',
          d.open, 'in window',
          '#58a6ff')}
      </div>

      <!-- Significance note -->
      <div style="font-size:11px;
        text-align:center;margin-top:10px;
        color:${d.needed > 0
          ? '#444' : '#00C851'};">
        ${d.needed > 0
          ? `${d.needed} more resolutions needed
             for statistical significance`
          : '✅ Statistically significant'}
      </div>
    </div>`;
}


// ── SECTION: OUTCOME BREAKDOWN ────────────────────────

function _buildOutcomeBreakdown(d) {
  if (d.resolved < _MIN_DISPLAY) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        Need ${_MIN_DISPLAY} resolved signals
        to show outcome breakdown.
        <br>${d.resolved} resolved so far.
      </div>`;
  }

  const bt  = _BT_WR.OVERALL;
  const gc  = _gapColor(d.liveWR, bt);

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      <!-- WR vs backtest -->
      <div style="display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:8px;margin-bottom:14px;">
        ${_card('Live WR',
          d.liveWR !== null
            ? d.liveWR + '%' : '—',
          'TARGET_HIT + DAY6_WIN', gc)}
        ${_card('Backtest WR',
          bt + '%', 'V3 baseline', '#555')}
        ${_card('Gap',
          _gapLabel(d.liveWR, bt),
          d.liveWR !== null && d.liveWR >= bt-5
            ? 'On track ✅'
            : d.liveWR !== null &&
              d.liveWR >= bt-15
            ? 'Monitor ⚠️'
            : 'Review 🔴',
          gc)}
      </div>

      <!-- Outcome bars -->
      <div style="margin-bottom:4px;
        font-size:10px;color:#555;
        letter-spacing:1px;">
        OUTCOME BREAKDOWN
      </div>

      ${_outcomeBar('TARGET_HIT',
        d.targetHitPct, d.resolved,
        '#00C851',
        'Hit 2R target within 6 days')}
      ${_outcomeBar('STOP_HIT',
        d.stopHitPct, d.resolved,
        '#f85149',
        'Stop hit within 6 days')}
      ${_outcomeBar('DAY6_WIN',
        d.day6WinPct, d.resolved,
        '#58a6ff',
        'Day 6 exit — profitable')}
      ${_outcomeBar('DAY6_LOSS',
        d.day6LossPct, d.resolved,
        '#f8514966',
        'Day 6 exit — at loss')}
      ${_outcomeBar('DAY6_FLAT',
        d.day6FlatPct, d.resolved,
        '#444',
        'Day 6 exit — flat ±0.5%')}
    </div>`;
}

function _outcomeBar(label, pct, total,
                     color, desc) {
  const count = pct !== null
    ? Math.round(pct / 100 * total) : 0;
  return `
    <div style="margin-bottom:8px;">
      <div style="display:flex;
        justify-content:space-between;
        font-size:11px;margin-bottom:2px;">
        <span style="color:${color};
          font-weight:700;">${label}</span>
        <span style="color:#555;">
          ${pct !== null
            ? pct + '% (' + count + ')' : '—'}
        </span>
      </div>
      ${_bar(pct || 0, 100, color)}
      <div style="font-size:10px;color:#333;">
        ${desc}
      </div>
    </div>`;
}


// ── SECTION: MFE / MAE ────────────────────────────────

function _buildMFEMAE(d) {
  if (!d.avgMFE && !d.avgMAE) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        MFE/MAE data builds as signals resolve.
      </div>`;
  }

  const ratioColor = d.mfeMaeRatio !== null
    ? parseFloat(d.mfeMaeRatio) >= 1.5
      ? '#00C851'
      : parseFloat(d.mfeMaeRatio) >= 1.0
      ? '#FFD700'
      : '#f85149'
    : '#555';

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      <div style="display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:8px;margin-bottom:10px;">
        ${_card('Avg MFE',
          d.avgMFE !== null
            ? d.avgMFE + '%' : '—',
          'best move for you',
          '#00C851')}
        ${_card('Avg MAE',
          d.avgMAE !== null
            ? d.avgMAE + '%' : '—',
          'worst move against',
          '#f85149')}
        ${_card('MFE:MAE',
          d.mfeMaeRatio !== null
            ? d.mfeMaeRatio + 'x' : '—',
          'ratio > 1.5 = good',
          ratioColor)}
      </div>

      ${d.avgDays !== null
        ? `<div style="font-size:11px;
             color:#555;text-align:center;
             padding-top:8px;
             border-top:1px solid #21262d;">
             Avg ${d.avgDays} trading days
             to outcome resolution
           </div>`
        : ''}

      <div style="font-size:10px;color:#333;
        margin-top:8px;line-height:1.5;">
        MFE:MAE > 1.5 = signals move more in
        right direction than wrong.<br>
        < 1.0 = signals have directional problem.
      </div>
    </div>`;
}


// ── SECTION: BY SIGNAL TYPE ───────────────────────────

function _buildByType(d) {
  const rows = Object.entries(d.byType)
    .filter(([, v]) =>
      v.resolved >= _MIN_DISPLAY)
    .map(([sig, v]) => {
      const bt = _BT_WR[sig] || _BT_WR.OVERALL;
      const gc = _gapColor(v.winRate, bt);
      const sc =
        sig.startsWith('UP')   ? '#00C851' :
        sig.startsWith('DOWN') ? '#f85149' :
        '#58a6ff';
      return `
        <div style="padding:8px 0;
          border-bottom:1px solid #0c0c1a;">
          <div style="display:flex;
            justify-content:space-between;
            margin-bottom:4px;font-size:11px;">
            <span style="color:${sc};
              font-weight:700;">${sig}</span>
            <span style="color:${gc};
              font-weight:700;">
              WR ${v.winRate !== null
                ? v.winRate + '%' : '—'}
              <span style="color:#333;
                font-size:10px;">
                vs ${bt}%
              </span>
            </span>
          </div>
          <div style="display:flex;
            justify-content:space-between;
            font-size:10px;color:#444;">
            <span>
              🎯 ${v.targetHit !== null
                ? v.targetHit + '%' : '—'}
              target ·
              ❌ ${v.stopHit !== null
                ? v.stopHit + '%' : '—'}
              stop
            </span>
            <span>
              ${v.resolved} resolved ·
              ${v.open} open
            </span>
          </div>
          ${v.avgMFE !== null
            ? `<div style="font-size:10px;
                 color:#333;margin-top:2px;">
                 Avg MFE ${v.avgMFE}%
               </div>`
            : ''}
        </div>`;
    });

  if (!rows.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        Need ${_MIN_DISPLAY}+ resolved signals
        per type to show breakdown.
      </div>`;
  }

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">
      ${rows.join('')}
    </div>`;
}


// ── SECTION: BY REGIME ────────────────────────────────

function _buildByRegime(d) {
  const entries = Object.entries(d.byRegime);

  if (!entries.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        No resolved signals yet for
        regime breakdown.
      </div>`;
  }

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      ${entries.map(([regime, v]) => {
        const rc =
          regime === 'Bear'   ? '#f85149' :
          regime === 'Bull'   ? '#00C851' :
          '#FFD700';
        const gc = _gapColor(
          v.winRate, _BT_WR.OVERALL);
        return `
          <div style="padding:6px 0;
            border-bottom:1px solid #0c0c1a;
            font-size:11px;">
            <div style="display:flex;
              justify-content:space-between;
              margin-bottom:2px;">
              <span style="color:${rc};
                font-weight:700;">
                ${regime}
              </span>
              <span style="color:${gc};
                font-weight:700;">
                WR ${v.winRate !== null
                  ? v.winRate + '%' : '—'}
              </span>
            </div>
            <div style="font-size:10px;
              color:#444;">
              🎯 ${v.targetHit !== null
                ? v.targetHit + '%' : '—'}
              target hit ·
              ${v.resolved} resolved
            </div>
          </div>`;
      }).join('')}

      <div style="font-size:10px;color:#333;
        margin-top:8px;">
        Bear regime UP_TRI = highest conviction
        by backtest. Live data validates this.
      </div>
    </div>`;
}


// ── SECTION: BY SCORE TIER ────────────────────────────

function _buildByScore(d) {
  const tiers = Object.entries(d.byScore)
    .filter(([, v]) => v.resolved > 0);

  if (!tiers.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        No resolved signals yet for
        score tier analysis.
      </div>`;
  }

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      <div style="font-size:10px;color:#444;
        margin-bottom:8px;">
        Higher scores should produce higher
        TARGET_HIT %. If not — scoring
        model needs revision.
      </div>

      ${tiers.map(([, v]) => {
        const gc = v.winRate !== null &&
                   v.winRate >= 70
          ? '#00C851'
          : v.winRate !== null &&
            v.winRate >= 50
          ? '#FFD700'
          : '#f85149';
        return `
          <div style="padding:6px 0;
            border-bottom:1px solid #0c0c1a;
            font-size:11px;">
            <div style="display:flex;
              justify-content:space-between;
              margin-bottom:2px;">
              <span style="color:#8b949e;
                font-weight:700;">
                Score ${v.label}
              </span>
              <span style="color:${gc};
                font-weight:700;">
                WR ${v.winRate !== null
                  ? v.winRate + '%' : '—'}
              </span>
            </div>
            <div style="font-size:10px;
              color:#444;">
              🎯 ${v.targetHitPct !== null
                ? v.targetHitPct + '%' : '—'}
              target ·
              ❌ ${v.stopHitPct !== null
                ? v.stopHitPct + '%' : '—'}
              stop ·
              ${v.resolved} resolved
            </div>
          </div>`;
      }).join('')}
    </div>`;
}


// ── SECTION: MINI SCANNER SHADOW ──────────────────────

function _buildShadow(records) {
  const rejected = records.filter(
    r => r.result === 'REJECTED' &&
         r.rejection_reason);

  if (!rejected.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;">
        No shadow rejections yet.
        Shadow data builds as scanner runs.
        <br><br>
        <span style="color:#333;">
          Once data builds: rejected signal
          outcomes will be compared against
          accepted signal outcomes to validate
          whether each filter actually improves
          signal quality before activation.
        </span>
      </div>`;
  }

  // Compare accepted vs rejected outcomes
  const accepted = records.filter(
    r => r.action === 'TOOK' &&
         ['TARGET_HIT','STOP_HIT',
          'DAY6_WIN','DAY6_LOSS',
          'DAY6_FLAT'].includes(r.outcome));
  const rejResolved = rejected.filter(r =>
    ['TARGET_HIT','STOP_HIT',
     'DAY6_WIN','DAY6_LOSS',
     'DAY6_FLAT'].includes(r.outcome));

  const accTgt = accepted.filter(
    r => r.outcome === 'TARGET_HIT');
  const rejTgt = rejResolved.filter(
    r => r.outcome === 'TARGET_HIT');

  const accWR = _pct(
    accTgt.length + accepted.filter(
      r => r.outcome === 'DAY6_WIN').length,
    accepted.length);
  const rejWR = _pct(
    rejTgt.length + rejResolved.filter(
      r => r.outcome === 'DAY6_WIN').length,
    rejResolved.length);

  // By filter
  const byFilter = {};
  rejected.forEach(r => {
    const f = r.rejection_filter || 'unknown';
    if (!byFilter[f])
      byFilter[f] = { count: 0 };
    byFilter[f].count++;
  });

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      <div style="font-size:11px;color:#555;
        margin-bottom:10px;">
        ${rejected.length} signals in shadow mode
        · All passed through (rules inactive)
      </div>

      <!-- Accepted vs Rejected comparison -->
      ${accepted.length >= _MIN_DISPLAY &&
        rejResolved.length >= _MIN_DISPLAY
        ? `<div style="background:#161b22;
             border-radius:6px;
             padding:10px;margin-bottom:10px;">
             <div style="font-size:10px;
               color:#444;margin-bottom:6px;
               letter-spacing:1px;">
               ACCEPTED vs SHADOW-REJECTED
             </div>
             ${_row('Accepted WR',
               accWR !== null
                 ? accWR + '%' : '—',
               '#00C851')}
             ${_row('Shadow-Rejected WR',
               rejWR !== null
                 ? rejWR + '%' : '—',
               '#555')}
             ${_row('Gap',
               accWR !== null &&
               rejWR !== null
                 ? (accWR > rejWR
                   ? '+' + (accWR-rejWR) +
                     '% (filter helps ✅)'
                   : (accWR-rejWR) +
                     '% (filter hurts ❌)')
                 : 'Need more data',
               accWR !== null &&
               rejWR !== null &&
               accWR > rejWR
                 ? '#00C851' : '#f85149')}
           </div>`
        : `<div style="font-size:11px;
             color:#333;margin-bottom:10px;">
             Need ${_MIN_DISPLAY}+ resolved
             signals on each side for
             comparison.
           </div>`}

      <!-- By filter -->
      ${Object.entries(byFilter).map(
        ([f, v]) => `
          <div style="display:flex;
            justify-content:space-between;
            font-size:11px;padding:4px 0;
            border-bottom:1px solid #0c0c1a;">
            <span style="color:#8b949e;">
              ${f}
            </span>
            <span style="color:#555;">
              ${v.count} would filter
            </span>
          </div>`
      ).join('')}

      <div style="font-size:10px;color:#333;
        margin-top:8px;">
        Activate filters in
        mini_scanner_rules.json
        only when accepted WR > rejected WR
        by 5%+ with 20+ signals each side.
      </div>
    </div>`;
}


// ── SECTION: SYSTEM INFO ──────────────────────────────

function _buildSysInfo(meta) {
  if (!meta) return '';
  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:12px 14px;
      font-size:11px;">
      ${_row('Scanner version',
        meta.scanner_version || '—')}
      ${_row('Universe size',
        (meta.universe_size || '—') +
        ' stocks')}
      ${_row('Last scan',
        meta.last_scan
          ? fmtTime(meta.last_scan) : '—')}
      ${_row('History records',
        meta.history_record_count || '—')}
      ${_row('Regime',
        meta.regime || '—')}
      ${meta.fetch_failed &&
        meta.fetch_failed.length > 0
        ? _row('Fetch failed',
            meta.fetch_failed.join(', '),
            '#FFD700')
        : ''}
      ${meta.corporate_action_skip &&
        meta.corporate_action_skip.length > 0
        ? _row('CA skipped',
            meta.corporate_action_skip
              .join(', '),
            '#555')
        : ''}
    </div>`;
}


// ── MAIN RENDER ───────────────────────────────────────

function renderStats(data) {
  const content = document.getElementById(
    'tab-content');
  if (!content) return;

  const histData = data.history;
  const records  = (histData && histData.history)
    ? histData.history : [];
  const meta     = data.meta || {};

  // Empty state
  if (!records.length) {
    content.innerHTML = `
      <div style="padding:14px;">
        <div style="text-align:center;
          padding:40px 20px;
          color:#555;font-size:13px;">
          <div style="font-size:32px;
            margin-bottom:12px;">📈</div>
          <div style="color:#8b949e;
            font-size:15px;font-weight:700;
            margin-bottom:8px;">
            No data yet
          </div>
          <div style="font-size:12px;
            color:#444;line-height:1.8;">
            What fills here automatically:<br>
            <span style="color:#333;">
              • Outcome breakdown
                (TARGET_HIT / STOP_HIT / DAY6)<br>
              • Live WR vs backtest 87%<br>
              • MFE / MAE per signal<br>
              • By signal type, regime, score<br>
              • Mini scanner shadow analysis
            </span>
          </div>
        </div>
        ${_sectionHead('SYSTEM INFO',
          'Scanner configuration')}
        ${_buildSysInfo(meta)}
      </div>`;
    _renderNav('stats');
    return;
  }

  const d = _buildStats(records);

  content.innerHTML = `
    <div style="padding:14px;">

      ${_sectionHead('SIGNAL VALIDATION',
        'Phase 1 — 6-day outcome tracking')}
      ${_buildOverview(d)}

      ${_sectionHead('OUTCOME BREAKDOWN',
        'All ' + d.resolved +
        ' resolved signals')}
      ${_buildOutcomeBreakdown(d)}

      ${_sectionHead('MFE / MAE',
        'Signal movement quality')}
      ${_buildMFEMAE(d)}

      ${_sectionHead('BY SIGNAL TYPE',
        'Min ' + _MIN_DISPLAY +
        ' resolved per type')}
      ${_buildByType(d)}

      ${_sectionHead('BY REGIME',
        'Does regime improve signal quality?')}
      ${_buildByRegime(d)}

      ${_sectionHead('BY SCORE TIER',
        'Does scoring discriminate correctly?')}
      ${_buildByScore(d)}

      ${_sectionHead('MINI SCANNER SHADOW',
        'All rules inactive — data collecting')}
      ${_buildShadow(records)}

      ${_sectionHead('SYSTEM INFO', null)}
      ${_buildSysInfo(meta)}

    </div>`;

  _renderNav('stats');
}
