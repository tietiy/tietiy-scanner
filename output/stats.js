// ── stats.js ─────────────────────────────────────────
// Stats — learning and system understanding screen.
//
// V1 FIXES APPLIED:
// - U1b  : sticky header at top of stats tab
// - SCAN_DAYS: dates uses tookLive (gen=1 only)
// - L1   : Win rate by regime (Bear / Bull / Choppy)
// - L2   : MAE / MFE distribution analysis
// - L3   : Timeline chart — signals per scan day
// - L8   : CSV export button in sticky header
// - L9   : Performance dashboard (expectancy, streaks,
//           best/worst trade, avg win/loss P&L)
//
// V1.1 FIXES:
// - HC6  : shadowModeActive reads tietiy.meta.shadow_mode
// - H10  : MAE outlier note shown when avg skewed
// - M9   : Failure pattern summary section
// - MC1  : WIN RATE BY REGIME explains market vs stock
// - D6-4 : Day 6 outcome breakdown section
//
// V2 FIXES:
// - SS1  : Phase 2 unlocked banner
// - SS2  : Preliminary WR shown when below threshold
// - SS3  : Score bucket Phase 2 header when unlocked
// - CSV1 : _downloadCSV field names corrected —
//          'stock' → 'symbol' (was blank for all 147 rows)
//          'entry_price' → 'entry'
//          'stop_price'  → 'stop'
//          Also fixed bestTrade/worstTrade display in
//          _renderPerfDashboard (same wrong field name).
// ─────────────────────────────────────────────────────
(function () {

const RESOLVED_TARGET = 30;
const BUCKET_MIN_N    = 5;

const OUTCOME_WIN   = new Set(['TARGET_HIT', 'DAY6_WIN']);
const OUTCOME_LOSS  = new Set(['STOP_HIT', 'DAY6_LOSS']);
const OUTCOME_DONE  = new Set([
  'TARGET_HIT', 'STOP_HIT',
  'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT']);
const OUTCOME_DAY6  = new Set([
  'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT']);

// ── HELPERS ───────────────────────────────────────────
function _pct(n, d) {
  if (!d) return 0;
  return Math.round((n / d) * 100);
}

function _isLive(s) {
  const gen = s.generation;
  if (gen === undefined || gen === null) return true;
  return gen >= 1;
}

function _isBackfill(s) { return s.generation === 0; }

function _bar(label, value, total, color) {
  const pct   = total ? Math.round((value / total) * 100) : 0;
  const width = Math.max(pct, 2);
  return `
    <div style="margin-bottom:8px;">
      <div style="display:flex;justify-content:space-between;
        font-size:11px;color:#8b949e;margin-bottom:3px;">
        <span>${label}</span>
        <span style="color:#c9d1d9;">
          ${value}
          <span style="color:#555;">&nbsp;${pct}%</span>
        </span>
      </div>
      <div style="background:#21262d;border-radius:3px;
        height:6px;overflow:hidden;">
        <div style="background:${color};height:6px;
          width:${width}%;border-radius:3px;
          transition:width 0.3s ease;"></div>
      </div>
    </div>`;
}

function _scoreBar(score, count, maxCount) {
  const width = maxCount
    ? Math.max(Math.round((count / maxCount) * 100), 2) : 2;
  const color = score >= 7 ? '#FFD700'
    : score >= 5 ? '#00C851'
    : score >= 3 ? '#8b949e'
    : '#555';
  return `
    <div style="display:flex;align-items:center;
      gap:8px;margin-bottom:6px;">
      <span style="color:${color};font-size:11px;
        font-weight:700;min-width:28px;text-align:right;">
        ${score}/10
      </span>
      <div style="flex:1;background:#21262d;
        border-radius:3px;height:8px;">
        <div style="background:${color};height:8px;
          width:${width}%;border-radius:3px;"></div>
      </div>
      <span style="color:#555;font-size:11px;min-width:20px;">
        ${count}
      </span>
    </div>`;
}

function _section(title, content) {
  return `
    <div style="background:#161b22;border:1px solid #21262d;
      border-radius:8px;padding:14px;margin-bottom:12px;">
      <div style="font-size:11px;color:#ffd700;font-weight:700;
        letter-spacing:1px;margin-bottom:12px;">
        ${title}
      </div>
      ${content}
    </div>`;
}

function _statRow(label, value, subtext, valueColor) {
  return `
    <div style="display:flex;justify-content:space-between;
      align-items:baseline;margin-bottom:6px;">
      <span style="color:#8b949e;font-size:12px;">${label}</span>
      <span>
        <span style="color:${valueColor || '#c9d1d9'};
          font-size:13px;font-weight:700;">
          ${value}
        </span>
        ${subtext
          ? `<span style="color:#555;font-size:10px;
               margin-left:4px;">${subtext}</span>`
          : ''}
      </span>
    </div>`;
}

function _lockedRow(label) {
  return `
    <div style="display:flex;justify-content:space-between;
      align-items:center;margin-bottom:6px;opacity:0.4;">
      <span style="color:#555;font-size:12px;">${label}</span>
      <span style="color:#555;font-size:11px;">🔒 collecting</span>
    </div>`;
}

function _miniStat(label, value, color) {
  return `
    <div style="flex:1;min-width:60px;background:#0d1117;
      border-radius:6px;padding:8px;text-align:center;">
      <div style="color:${color};font-size:16px;font-weight:700;">
        ${value}
      </div>
      <div style="color:#555;font-size:9px;margin-top:2px;">
        ${label}
      </div>
    </div>`;
}

function _divider() {
  return `<div style="border-top:1px solid #21262d;
    margin:8px 0;"></div>`;
}

// ── L8: CSV EXPORT ────────────────────────────────────
function _downloadCSV(raw) {
  // CSV1 FIX: field names corrected to match actual
  // signal_history.json schema. Previously used wrong
  // names causing all 147 rows to export blank stock,
  // entry, and stop columns — unusable in Colab.
  // stock → symbol  (JSON field is 'symbol')
  // entry_price → entry  (JSON field is 'entry')
  // stop_price → stop    (JSON field is 'stop')
  const cols = [
    'date', 'symbol', 'signal', 'score', 'outcome',
    'pnl_pct', 'stock_regime', 'regime', 'sector',
    'generation', 'bear_bonus', 'vol_confirm',
    'sec_leading', 'rs_strong', 'grade_A',
    'entry', 'stop', 'target_price',
    'age', 'mae_pct', 'mfe_pct', 'action', 'layer',
    'rejection_reason', 'failure_reason'
  ];
  const header = cols.join(',');
  const rows = raw.map(function (s) {
    return cols.map(function (c) {
      const v = s[c];
      if (v === undefined || v === null) return '';
      const str = String(v);
      return (str.includes(',') || str.includes('"')
              || str.includes('\n'))
        ? '"' + str.replace(/"/g, '""') + '"'
        : str;
    }).join(',');
  });
  const csv  = [header].concat(rows).join('\n');
  const uri  = 'data:text/csv;charset=utf-8,'
    + encodeURIComponent(csv);
  const link = document.createElement('a');
  link.setAttribute('href', uri);
  link.setAttribute('download',
    'tietiy_' + new Date().toISOString().slice(0, 10)
    + '.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
window._tietiyDownloadCSV = _downloadCSV;

// ── REGIME NORMALISE ──────────────────────────────────
function _normaliseRegime(s) {
  const raw = (s.stock_regime || s.regime || '')
    .toString().trim().toUpperCase();
  if (raw === 'BEAR' || raw === 'BEARISH')
    return 'Bear';
  if (raw === 'BULL' || raw === 'BULLISH')
    return 'Bull';
  if (raw === 'CHOPPY' || raw === 'RANGING'
      || raw === 'NEUTRAL')
    return 'Choppy';
  if (!raw) return null;
  return raw.charAt(0) + raw.slice(1).toLowerCase();
}

function _shortDate(iso) {
  try {
    const parts = iso.split('-');
    const mon   = parseInt(parts[1], 10);
    const day   = parseInt(parts[2], 10);
    const names = ['','Jan','Feb','Mar','Apr','May',
                   'Jun','Jul','Aug','Sep','Oct',
                   'Nov','Dec'];
    return (names[mon] || '?') + ' ' + day;
  } catch (e) { return iso; }
}

// ── DATA ANALYSIS ─────────────────────────────────────
function _analyse(raw, shadowMode) {
  const took = raw.filter(
    s => s.layer === 'MINI' && s.action === 'TOOK');
  const rej  = raw.filter(
    s => s.layer === 'ALPHA' && s.action === 'REJECTED');

  const tookLive     = took.filter(_isLive);
  const tookBackfill = took.filter(_isBackfill);
  const hasBackfill  = tookBackfill.length > 0;

  const resolvedLive = tookLive.filter(
    s => OUTCOME_DONE.has(s.outcome || ''));
  const winsLive     = resolvedLive.filter(
    s => OUTCOME_WIN.has(s.outcome));
  const lossesLive   = resolvedLive.filter(
    s => OUTCOME_LOSS.has(s.outcome));
  const openLive     = tookLive.filter(
    s => !OUTCOME_DONE.has(s.outcome || ''));

  const resolvedAll  = took.filter(
    s => OUTCOME_DONE.has(s.outcome || ''));
  const winsAll      = resolvedAll.filter(
    s => OUTCOME_WIN.has(s.outcome));
  const wrAllCombined = resolvedAll.length
    ? _pct(winsAll.length, resolvedAll.length)
    : null;

  const byType = {};
  took.forEach(function (s) {
    const t = s.signal || 'Unknown';
    byType[t] = (byType[t] || 0) + 1;
  });

  const byScore = {};
  tookLive.forEach(function (s) {
    const sc = parseInt(s.score, 10) || 0;
    byScore[sc] = (byScore[sc] || 0) + 1;
  });

  const bySector = {};
  took.forEach(function (s) {
    const sec = s.sector || 'Other';
    bySector[sec] = (bySector[sec] || 0) + 1;
  });

  const byRej = {};
  rej.forEach(function (s) {
    const r = s.rejection_reason || 'unknown';
    byRej[r] = (byRej[r] || 0) + 1;
  });

  const bearCount = tookLive.filter(
    s => s.bear_bonus === true
      || s.bear_bonus === 'true').length;

  const wrTotal = resolvedLive.length
    ? _pct(winsLive.length, resolvedLive.length)
    : null;

  const wrByType = {};
  ['UP_TRI', 'DOWN_TRI', 'BULL_PROXY'].forEach(
    function (t) {
      const res  = resolvedLive.filter(
        s => s.signal === t);
      const wins = res.filter(
        s => OUTCOME_WIN.has(s.outcome));
      if (res.length >= BUCKET_MIN_N) {
        wrByType[t] = {
          wr:    _pct(wins.length, res.length),
          n:     res.length,
          fired: byType[t] || 0,
        };
      }
    });

  const BUCKETS = [
    { label: '7–8', min: 7, max: 10 },
    { label: '5–6', min: 5, max: 6  },
    { label: '3–4', min: 3, max: 4  },
    { label: '1–2', min: 1, max: 2  },
  ];
  const bucketPerf = BUCKETS.map(function (b) {
    const inB  = resolvedLive.filter(s => {
      const sc = parseFloat(s.score) || 0;
      return sc >= b.min && sc <= b.max;
    });
    const bWins = inB.filter(
      s => OUTCOME_WIN.has(s.outcome));
    const pArr  = inB.filter(s => s.pnl_pct != null)
      .map(s => parseFloat(s.pnl_pct));
    const avgPnl = pArr.length
      ? (pArr.reduce((a, c) => a + c, 0)
         / pArr.length).toFixed(1)
      : null;
    return {
      label:   b.label,
      n:       inB.length,
      wins:    bWins.length,
      wr:      inB.length >= BUCKET_MIN_N
        ? _pct(bWins.length, inB.length) : null,
      avgPnl,
      hasData: inB.length >= BUCKET_MIN_N,
    };
  });

  const allPnl = resolvedLive
    .filter(s => s.pnl_pct != null)
    .map(s => parseFloat(s.pnl_pct));
  const avgPnl = allPnl.length
    ? (allPnl.reduce((a, b) => a + b, 0)
       / allPnl.length).toFixed(2)
    : null;

  const dates = [...new Set(
    tookLive.map(s => s.date).filter(Boolean))].sort();

  const byDate = {};
  tookLive.forEach(function (s) {
    if (s.date) byDate[s.date] =
      (byDate[s.date] || 0) + 1;
  });

  const regimeResolved = {};
  resolvedLive.forEach(function (s) {
    const r = _normaliseRegime(s);
    if (!r) return;
    if (!regimeResolved[r])
      regimeResolved[r] = { wins: 0, total: 0 };
    regimeResolved[r].total++;
    if (OUTCOME_WIN.has(s.outcome))
      regimeResolved[r].wins++;
  });
  const regimeFired = {};
  tookLive.forEach(function (s) {
    const r = _normaliseRegime(s);
    if (r) regimeFired[r] =
      (regimeFired[r] || 0) + 1;
  });

  const maeSamples = resolvedLive.filter(
    s => s.mae_pct != null && s.mae_pct !== '');
  const mfeSamples = resolvedLive.filter(
    s => s.mfe_pct != null && s.mfe_pct !== '');

  function _bands(samples, field, defs) {
    return defs.map(function (b) {
      return {
        label: b.label,
        count: samples.filter(function (s) {
          const v = Math.abs(parseFloat(s[field]));
          return b.last
            ? v >= b.min
            : (v >= b.min && v < b.max);
        }).length,
      };
    });
  }
  const MAE_DEFS = [
    { label: '0–1%', min: 0, max: 1 },
    { label: '1–2%', min: 1, max: 2 },
    { label: '2–3%', min: 2, max: 3 },
    { label: '>3%',  min: 3, last: true },
  ];
  const MFE_DEFS = [
    { label: '0–2%',  min: 0,  max: 2  },
    { label: '2–5%',  min: 2,  max: 5  },
    { label: '5–10%', min: 5,  max: 10 },
    { label: '>10%',  min: 10, last: true },
  ];
  const maeBands = _bands(maeSamples, 'mae_pct', MAE_DEFS);
  const mfeBands = _bands(mfeSamples, 'mfe_pct', MFE_DEFS);

  const maeVals = maeSamples.map(
    s => Math.abs(parseFloat(s.mae_pct)));
  const avgMAE = maeVals.length
    ? (maeVals.reduce((a, b) => a + b, 0)
       / maeVals.length).toFixed(2)
    : null;
  const avgMFE = mfeSamples.length
    ? (mfeSamples.map(
        s => Math.abs(parseFloat(s.mfe_pct)))
       .reduce((a, b) => a + b, 0)
       / mfeSamples.length).toFixed(2)
    : null;

  const maeOutlierCount = maeVals.filter(
    v => v > 10).length;
  const maeWithoutOutliers = maeVals.filter(
    v => v <= 10);
  const avgMAEAdjusted = maeWithoutOutliers.length
    ? (maeWithoutOutliers.reduce((a, b) => a + b, 0)
       / maeWithoutOutliers.length).toFixed(2)
    : null;

  const pnlRes  = resolvedLive.filter(
    s => s.pnl_pct != null);
  const pnlWArr = pnlRes.filter(
    s => OUTCOME_WIN.has(s.outcome))
    .map(s => parseFloat(s.pnl_pct));
  const pnlLArr = pnlRes.filter(
    s => OUTCOME_LOSS.has(s.outcome))
    .map(s => parseFloat(s.pnl_pct));

  const avgWinPnl = pnlWArr.length
    ? (pnlWArr.reduce((a, b) => a + b, 0)
       / pnlWArr.length).toFixed(2)
    : null;
  const avgLossPnl = pnlLArr.length
    ? (pnlLArr.reduce((a, b) => a + b, 0)
       / pnlLArr.length).toFixed(2)
    : null;

  let expectancy = null;
  if (avgWinPnl !== null
      && avgLossPnl !== null
      && wrTotal !== null) {
    const wr = wrTotal / 100;
    expectancy = (
      parseFloat(avgWinPnl)  * wr +
      parseFloat(avgLossPnl) * (1 - wr)
    ).toFixed(2);
  }

  let bestTrade = null, worstTrade = null;
  if (pnlRes.length) {
    bestTrade  = pnlRes.reduce(
      (m, s) => parseFloat(s.pnl_pct) >
        parseFloat(m.pnl_pct) ? s : m);
    worstTrade = pnlRes.reduce(
      (m, s) => parseFloat(s.pnl_pct) <
        parseFloat(m.pnl_pct) ? s : m);
  }

  let maxWinStreak = 0, maxLossStreak = 0,
      curW = 0, curL = 0;
  const sortedRes = resolvedLive.slice().sort(
    (a, b) => (a.date || '') <
              (b.date || '') ? -1 : 1);
  sortedRes.forEach(function (s) {
    if (OUTCOME_WIN.has(s.outcome)) {
      curW++; curL = 0;
      if (curW > maxWinStreak) maxWinStreak = curW;
    } else if (OUTCOME_LOSS.has(s.outcome)) {
      curL++; curW = 0;
      if (curL > maxLossStreak) maxLossStreak = curL;
    }
  });

  const shadowModeActive = shadowMode !== false;

  const failureCounts = {};
  resolvedLive.forEach(function (s) {
    const fr = s.failure_reason;
    if (!fr) return;
    failureCounts[fr] = (failureCounts[fr] || 0) + 1;
  });
  const failurePatterns = Object.entries(failureCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const day6Signals = resolvedLive.filter(
    s => OUTCOME_DAY6.has(s.outcome));
  const day6Win  = day6Signals.filter(
    s => s.outcome === 'DAY6_WIN');
  const day6Loss = day6Signals.filter(
    s => s.outcome === 'DAY6_LOSS');
  const day6Flat = day6Signals.filter(
    s => s.outcome === 'DAY6_FLAT');

  function _avgPnlArr(arr) {
    const vals = arr.filter(s => s.pnl_pct != null)
      .map(s => parseFloat(s.pnl_pct));
    return vals.length
      ? (vals.reduce((a, b) => a + b, 0)
         / vals.length).toFixed(2)
      : null;
  }

  return {
    totalLive:       tookLive.length,
    resolvedLive:    resolvedLive.length,
    openLive:        openLive.length,
    winsLive:        winsLive.length,
    lossesLive:      lossesLive.length,
    wrTotal,
    wrByType,
    avgPnl,
    bearCount,
    byScore,
    totalAll:        took.length,
    byType,
    bySector,
    byRej,
    dates,
    byDate,
    tookCount:       took.length,
    rejCount:        rej.length,
    hasBackfill,
    backfillCount:   tookBackfill.length,
    bucketPerf,
    shadowModeActive,
    regimeResolved,
    regimeFired,
    maeSamples,
    mfeSamples,
    maeBands,
    mfeBands,
    avgMAE,
    avgMFE,
    maeOutlierCount,
    avgMAEAdjusted,
    avgWinPnl,
    avgLossPnl,
    expectancy,
    bestTrade,
    worstTrade,
    maxWinStreak,
    maxLossStreak,
    failurePatterns,
    day6Signals,
    day6Win,
    day6Loss,
    day6Flat,
    day6WinAvgPnl:   _avgPnlArr(day6Win),
    day6LossAvgPnl:  _avgPnlArr(day6Loss),
    day6FlatAvgPnl:  _avgPnlArr(day6Flat),
    resolvedAll:     resolvedAll.length,
    winsAll:         winsAll.length,
    wrAllCombined,
  };
}

// ── SS1: PHASE 2 UNLOCKED BANNER ──────────────────────
function _renderPhase2Banner(d) {
  if (d.resolvedLive < RESOLVED_TARGET) return '';
  const wrColor = d.wrTotal !== null
    ? (d.wrTotal >= 60 ? '#00C851' : '#f85149')
    : '#555';
  return `
    <div style="background:#0d2a0d;
      border:1px solid #00C85166;
      border-radius:8px;padding:12px 14px;
      margin-bottom:12px;">
      <div style="color:#00C851;font-size:12px;
        font-weight:700;margin-bottom:6px;">
        🏁 PHASE 2 UNLOCKED
      </div>
      <div style="font-size:11px;color:#8b949e;
        line-height:1.7;">
        ${d.resolvedLive} live signals resolved
        (${d.resolvedLive - RESOLVED_TARGET} above
        threshold) · Win rate is now statistically
        valid · Score bucket performance and regime
        analysis active · Phase 2 mini scanner
        rules can now be evaluated.
      </div>
      <div style="display:flex;gap:12px;
        margin-top:10px;flex-wrap:wrap;
        font-size:12px;">
        <span style="color:${wrColor};font-weight:700;">
          ${d.wrTotal !== null
            ? d.wrTotal + '% WR' : '—'}
        </span>
        <span style="color:#555;">
          W:${d.winsLive} L:${d.lossesLive}
        </span>
        ${d.avgPnl !== null
          ? `<span style="color:${
               parseFloat(d.avgPnl) > 0
                 ? '#00C851' : '#f85149'};">
               avg ${parseFloat(d.avgPnl) >= 0
                 ? '+' : ''}${d.avgPnl}% / trade
             </span>`
          : ''}
      </div>
    </div>`;
}

// ── DATA QUALITY BANNER ───────────────────────────────
function _renderDataQualityBanner(d) {
  if (!d.hasBackfill) return '';
  return `
    <div style="background:#1a1a0a;border:1px solid #ffd70044;
      border-radius:8px;padding:10px 12px;
      margin-bottom:12px;font-size:11px;">
      <div style="color:#ffd700;font-weight:700;
        margin-bottom:4px;">
        ⚠️ DATA QUALITY NOTE
      </div>
      <div style="color:#8b949e;line-height:1.6;">
        ${d.backfillCount} signals are pre-live backfill data
        (generation=0, before Apr 6). These are excluded from
        win rate calculations and Phase 2 decisions. Only live
        scanner data (${d.totalLive} signals from Apr 6+) is
        used for statistical analysis.
      </div>
    </div>`;
}

// ── 1. PHASE PROGRESS ─────────────────────────────────
function _renderProgress(d) {
  const n      = d.resolvedLive;
  const target = RESOLVED_TARGET;
  const pct    = Math.min(
    Math.round((n / target) * 100), 100);
  const left   = Math.max(target - n, 0);

  const color  = n >= target ? '#00C851'
    : pct >= 50 ? '#FFD700' : '#58a6ff';

  const statusMsg = n === 0
    ? 'Collecting first live outcomes — first signals exit ~Apr 14.'
    : n >= target
      ? `30+ live resolved — win rate data is valid. Phase 2 unlocked.`
      : `${left} more live signals needed for statistical significance.`;

  return _section('📊 PHASE 1 — SIGNAL VALIDATION', `
    <div style="margin-bottom:10px;">
      <div style="display:flex;justify-content:space-between;
        font-size:12px;color:#8b949e;margin-bottom:6px;">
        <span>Live resolved signals</span>
        <span style="color:${color};font-weight:700;">
          ${n} / ${target}
          ${n >= target
            ? `<span style="font-size:10px;
                 color:#00C851;margin-left:4px;">
                 ✓ UNLOCKED
               </span>`
            : ''}
        </span>
      </div>
      <div style="background:#21262d;border-radius:4px;
        height:8px;overflow:hidden;">
        <div style="background:${color};height:8px;
          width:${pct}%;border-radius:4px;
          transition:width 0.3s ease;"></div>
      </div>
      <div style="font-size:10px;color:${
        n >= target ? '#00C851' : '#555'};
        margin-top:6px;">
        ${statusMsg}
      </div>
    </div>

    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      ${_miniStat('Live Signals', d.totalLive,    '#c9d1d9')}
      ${_miniStat('Open Now',     d.openLive,     '#FFD700')}
      ${_miniStat('Resolved',     d.resolvedLive, color)}
      ${_miniStat('Scan Days',    d.dates.length, '#8b949e')}
    </div>

    ${d.hasBackfill
      ? `<div style="font-size:10px;color:#555;margin-top:8px;
           padding-top:8px;border-top:1px solid #21262d;">
           + ${d.backfillCount} backfill signals (gen=0) tracked
           but excluded from win rate and scan day count
         </div>`
      : ''}`);
}

// ── 2. WIN RATE ───────────────────────────────────────
function _renderWinRate(d) {
  const n     = d.resolvedLive;
  const ready = n >= RESOLVED_TARGET;
  let content = '';

  if (!ready) {
    const prelimBlock = d.wrAllCombined !== null
      ? `<div style="background:#1c2128;
           border:1px solid #30363d;
           border-radius:6px;padding:8px 10px;
           margin-bottom:10px;font-size:11px;">
           <div style="color:#555;font-size:10px;
             margin-bottom:5px;letter-spacing:0.5px;">
             PRELIMINARY — NOT STATISTICALLY VALID
           </div>
           <div style="display:flex;gap:12px;
             flex-wrap:wrap;margin-bottom:4px;">
             <span style="color:${
               d.wrAllCombined >= 60
                 ? '#00C851' : '#f85149'};
               font-weight:700;font-size:14px;">
               ${d.wrAllCombined}% WR
             </span>
             <span style="color:#555;font-size:11px;">
               W:${d.winsAll}
               L:${d.resolvedAll - d.winsAll}
               · ${d.resolvedAll} resolved
             </span>
           </div>
           <div style="color:#555;font-size:10px;
             line-height:1.5;">
             Includes gen=0 backfill data.
             Statistically valid WR unlocks
             at 30 live-only (gen=1) resolved.
             Currently ${n} live resolved,
             ${RESOLVED_TARGET - n} more needed.
           </div>
         </div>`
      : '';

    content = `
      ${prelimBlock}
      <div style="text-align:center;padding:10px 0 8px;
        color:#555;">
        <div style="font-size:22px;margin-bottom:6px;">
          🔒
        </div>
        <div style="font-size:12px;">
          Live-only win rate unlocks at
          ${RESOLVED_TARGET} live resolved signals.
        </div>
        <div style="font-size:11px;color:#555;
          margin-top:4px;">
          Currently: ${n} live resolved.
          ${RESOLVED_TARGET - n} more needed.
        </div>
        ${d.hasBackfill
          ? `<div style="font-size:10px;color:#444;
               margin-top:6px;">
               ${d.backfillCount} backfill signals
               not counted toward threshold
             </div>`
          : ''}
      </div>
      <div style="border-top:1px solid #21262d;
        padding-top:10px;margin-top:4px;">
        ${_lockedRow('Live-only win rate')}
        ${_lockedRow('UP_TRI win rate')}
        ${_lockedRow('DOWN_TRI win rate')}
        ${_lockedRow('BULL_PROXY win rate')}
        ${_lockedRow('Avg P&L per trade')}
        ${_lockedRow('Avg R multiple')}
      </div>`;
  } else {
    content = `
      <div style="display:flex;gap:8px;flex-wrap:wrap;
        margin-bottom:12px;">
        ${_miniStat('Win Rate',
          d.wrTotal + '%',
          d.wrTotal >= 60 ? '#00C851' : '#f85149')}
        ${_miniStat('Wins',    d.winsLive,   '#00C851')}
        ${_miniStat('Losses',  d.lossesLive, '#f85149')}
        ${_miniStat('Avg P&L',
          d.avgPnl != null ? d.avgPnl + '%' : '—',
          parseFloat(d.avgPnl) > 0
            ? '#00C851' : '#f85149')}
      </div>
      <div style="border-top:1px solid #21262d;
        padding-top:10px;">
        <div style="font-size:11px;color:#555;
          margin-bottom:8px;">
          BY SIGNAL TYPE (min ${BUCKET_MIN_N} resolved)
        </div>
        ${['UP_TRI', 'DOWN_TRI', 'BULL_PROXY']
          .filter(t => d.wrByType[t])
          .map(t => {
            const wr  = d.wrByType[t];
            const col = wr.wr >= 60
              ? '#00C851' : '#f85149';
            return _statRow(
              t.replace(/_/g, ' '),
              wr.wr + '%',
              `${wr.n} resolved`, col);
          }).join('')}
        ${!['UP_TRI','DOWN_TRI','BULL_PROXY']
            .some(t => d.wrByType[t])
          ? `<div style="color:#555;font-size:11px;">
               Min ${BUCKET_MIN_N} resolved per type
               needed to show breakdown.
             </div>`
          : ''}
      </div>`;
  }

  return _section('🏆 WIN RATE', content);
}

// ── 3. PERFORMANCE DASHBOARD (L9) ─────────────────────
function _renderPerfDashboard(d) {
  const ready = d.resolvedLive >= RESOLVED_TARGET;

  if (!ready) {
    return _section('⚡ PERFORMANCE DASHBOARD', `
      <div style="text-align:center;padding:10px 0 6px;
        color:#555;font-size:11px;">
        Unlocks at ${RESOLVED_TARGET} resolved.
        Currently ${d.resolvedLive} live resolved.
      </div>
      <div style="border-top:1px solid #21262d;
        padding-top:10px;margin-top:8px;">
        ${_lockedRow('Avg win P&L')}
        ${_lockedRow('Avg loss P&L')}
        ${_lockedRow('Expectancy per trade')}
        ${_lockedRow('Best trade')}
        ${_lockedRow('Worst trade')}
        ${_lockedRow('Max win streak')}
        ${_lockedRow('Max loss streak')}
      </div>`);
  }

  const expColor = d.expectancy !== null
    ? (parseFloat(d.expectancy) >= 0
       ? '#00C851' : '#f85149')
    : '#555';

  const fmt = function (v, forceSign) {
    if (v == null) return '—';
    const f = parseFloat(v).toFixed(2);
    return (forceSign && parseFloat(f) > 0
      ? '+' : '') + f + '%';
  };

  // CSV1 FIX: was .stock — field is .symbol in JSON.
  // Same root cause as the CSV export blank column.
  const bestStr = d.bestTrade
    ? (d.bestTrade.symbol || '?') + '  +' +
      parseFloat(d.bestTrade.pnl_pct).toFixed(1) + '%'
    : '—';
  const worstStr = d.worstTrade
    ? (d.worstTrade.symbol || '?') + '  ' +
      parseFloat(d.worstTrade.pnl_pct).toFixed(1) + '%'
    : '—';

  return _section('⚡ PERFORMANCE DASHBOARD', `
    ${_statRow('Avg win P&L',
      fmt(d.avgWinPnl, true), '', '#00C851')}
    ${_statRow('Avg loss P&L',
      fmt(d.avgLossPnl, false), '', '#f85149')}
    ${_statRow('Expectancy / trade',
      fmt(d.expectancy, true),
      'avg expected P&L per signal', expColor)}
    ${_divider()}
    ${_statRow('Best trade',  bestStr,  '', '#00C851')}
    ${_statRow('Worst trade', worstStr, '', '#f85149')}
    ${_divider()}
    ${_statRow('Max win streak',
      d.maxWinStreak, 'consecutive wins', '#00C851')}
    ${_statRow('Max loss streak',
      d.maxLossStreak, 'consecutive losses', '#f85149')}
  `);
}

// ── 4. WIN RATE BY REGIME (L1) ────────────────────────
function _renderRegimeWR(d) {
  const REGIME_ORDER  = ['Bear', 'Bull', 'Choppy'];
  const REGIME_COLORS = {
    Bear: '#f85149', Bull: '#00C851', Choppy: '#FFD700'
  };

  const allRegimes = [...new Set(
    REGIME_ORDER.concat(
      Object.keys(d.regimeResolved),
      Object.keys(d.regimeFired)
    )
  )];

  let rows = '';
  let hasAny = false;

  allRegimes.forEach(function (r) {
    const fired = d.regimeFired[r] || 0;
    const data  = d.regimeResolved[r]
      || { wins: 0, total: 0 };
    if (!fired && !data.total) return;

    hasAny = true;
    const color = REGIME_COLORS[r] || '#8b949e';
    const wr    = data.total >= BUCKET_MIN_N
      ? _pct(data.wins, data.total) : null;
    const wrColor = wr !== null
      ? (wr >= 65 ? '#00C851'
         : wr >= 50 ? '#FFD700' : '#f85149')
      : '#555';

    rows += `
      <div style="display:flex;align-items:center;
        gap:8px;padding:7px 0;
        border-bottom:1px solid #21262d;
        font-size:11px;">
        <span style="color:${color};font-weight:700;
          min-width:55px;">${r}</span>
        <span style="color:#555;min-width:65px;">
          ${fired} signals
        </span>
        ${wr !== null
          ? `<span style="color:${wrColor};font-weight:700;
               min-width:50px;">${wr}% WR</span>
             <span style="color:#555;">
               ${data.total} resolved
             </span>`
          : `<span style="color:#555;font-style:italic;">
               🔒 ${Math.max(
                 BUCKET_MIN_N - data.total, 0)}
               more to unlock
             </span>`}
      </div>`;
  });

  return _section('🌡️ WIN RATE BY REGIME', `
    <div style="font-size:10px;color:#555;margin-bottom:8px;">
      Market regime at signal time ·
      min ${BUCKET_MIN_N} resolved per regime to unlock
    </div>
    <div style="font-size:10px;color:#444;
      background:#0d1117;border-radius:6px;
      padding:6px 8px;margin-bottom:10px;
      line-height:1.6;">
      <b style="color:#8b949e;">Market regime</b>
      = Nifty50 trend (Bull/Bear/Choppy) —
      used for scoring and this table.<br>
      <b style="color:#8b949e;">Stock regime</b>
      = individual stock trend — shown on signal cards.
      These can differ: a stock can be in Bear regime
      while market is Choppy.
    </div>
    ${hasAny
      ? rows
      : `<div style="color:#555;font-size:11px;
           text-align:center;padding:10px 0;">
           No regime data yet.
         </div>`}
    <div style="font-size:10px;color:#444;margin-top:8px;
      padding-top:8px;border-top:1px solid #21262d;">
      Bear regime UP_TRI = system's highest-conviction
      trade (backtest avg +4.85% · stop rarely hit).
    </div>`);
}

// ── 5. BY SIGNAL TYPE ─────────────────────────────────
function _renderByType(d) {
  const order  = ['UP_TRI','DOWN_TRI','BULL_PROXY',
                  'UP_TRI_SA','DOWN_TRI_SA'];
  const colors = {
    UP_TRI:     '#00C851',
    DOWN_TRI:   '#f85149',
    BULL_PROXY: '#58a6ff',
    UP_TRI_SA:  '#00C851',
    DOWN_TRI_SA:'#f85149',
  };
  const rows = order
    .filter(t => d.byType[t])
    .map(t => _bar(
      t.replace(/_/g, ' '),
      d.byType[t], d.totalAll,
      colors[t] || '#8b949e'));
  Object.keys(d.byType)
    .filter(t => !order.includes(t))
    .forEach(t => rows.push(
      _bar(t, d.byType[t], d.totalAll, '#8b949e')));

  return _section('📌 BY SIGNAL TYPE', rows.join(''));
}

// ── 6. SCORE DISTRIBUTION ─────────────────────────────
function _renderScoreDist(d) {
  const scores   = Object.keys(d.byScore).map(Number)
    .sort((a, b) => b - a);
  const maxCount = Math.max(
    ...Object.values(d.byScore), 1);
  const bars     = scores.map(s =>
    _scoreBar(s, d.byScore[s], maxCount)).join('');

  return _section('🎯 SCORE DISTRIBUTION', `
    <div style="font-size:10px;color:#555;
      margin-bottom:10px;">
      Live signals only (gen=1) ·
      higher score = stronger setup
    </div>
    ${bars || `<div style="color:#555;font-size:11px;">
      No live signals yet.</div>`}
    <div style="margin-top:8px;
      border-top:1px solid #21262d;
      padding-top:8px;
      display:flex;gap:16px;font-size:11px;">
      <span style="color:#555;">
        Bear bonus
        <b style="color:#ffd700;margin-left:4px;">
          ${d.bearCount}
        </b>
        <span style="color:#555;font-size:10px;">
          &nbsp;(${_pct(d.bearCount, d.totalLive)}%)
        </span>
      </span>
    </div>`);
}

// ── 7. SCORE BUCKET PERFORMANCE ───────────────────────
function _renderScoreBucketPerf(d) {
  const hasAnyData  = d.bucketPerf.some(b => b.hasData);
  const phase2Ready = d.resolvedLive >= RESOLVED_TARGET;

  let rows = '';
  d.bucketPerf.forEach(function (b) {
    if (b.hasData) {
      const wrColor  = b.wr >= 70 ? '#00C851' :
                       b.wr >= 55 ? '#FFD700' : '#f85149';
      const pnlColor = b.avgPnl != null
        && parseFloat(b.avgPnl) > 0
        ? '#00C851' : '#f85149';
      rows += `
        <div style="display:flex;align-items:center;
          gap:8px;padding:7px 0;
          border-bottom:1px solid #21262d;
          font-size:11px;">
          <span style="color:#ffd700;font-weight:700;
            min-width:38px;">${b.label}</span>
          <span style="color:#555;min-width:70px;">
            ${b.n} resolved
          </span>
          <span style="color:${wrColor};font-weight:700;
            min-width:50px;">${b.wr}% WR</span>
          <span style="color:${pnlColor};">
            ${b.avgPnl !== null
              ? (parseFloat(b.avgPnl) >= 0 ? '+' : '')
                + b.avgPnl + '%'
              : '—'}
          </span>
        </div>`;
    } else {
      rows += `
        <div style="display:flex;align-items:center;
          gap:8px;padding:7px 0;
          border-bottom:1px solid #21262d;
          font-size:11px;opacity:0.4;">
          <span style="color:#ffd700;font-weight:700;
            min-width:38px;">${b.label}</span>
          <span style="color:#555;min-width:70px;">
            ${b.n} resolved
          </span>
          <span style="color:#555;font-style:italic;">
            🔒 need ${BUCKET_MIN_N - b.n} more
          </span>
        </div>`;
    }
  });

  const footerNote = phase2Ready && hasAnyData
    ? `<div style="background:#0d2a0d;
         border:1px solid #00C85133;
         border-radius:6px;padding:6px 8px;
         margin-top:8px;font-size:10px;
         color:#00C851;line-height:1.6;">
         ✓ Phase 2 active — this data feeds into
         mini scanner rule evaluation. Scores with
         higher WR and avg P&L validate the scoring
         system. Use Colab to analyse full distribution.
       </div>`
    : `<div style="font-size:10px;color:#555;
         margin-top:8px;">
         Data populates as live signals resolve.
         Used in Phase 2 to validate score-based
         filtering.
       </div>`;

  const sectionTitle = phase2Ready && hasAnyData
    ? '📐 PERFORMANCE BY SCORE BUCKET — PHASE 2 ACTIVE'
    : '📐 PERFORMANCE BY SCORE BUCKET';

  return _section(sectionTitle, `
    <div style="font-size:10px;color:#555;
      margin-bottom:10px;">
      Win rate and avg P&L by score range ·
      Min ${BUCKET_MIN_N} resolved per bucket to unlock ·
      Key input for Phase 2 mini-scanner rules
    </div>
    ${rows}
    ${footerNote}`);
}

// ── 8. MAE / MFE ANALYSIS (L2) ────────────────────────
function _renderMAEMFE(d) {
  const hasMAE = d.maeSamples.length >= BUCKET_MIN_N;
  const hasMFE = d.mfeSamples.length >= BUCKET_MIN_N;

  if (!hasMAE && !hasMFE) {
    return _section('📉 MAE / MFE ANALYSIS', `
      <div style="text-align:center;padding:12px 0;
        color:#555;">
        <div style="font-size:22px;margin-bottom:6px;">
          🔒
        </div>
        <div style="font-size:11px;">
          Unlocks when ${BUCKET_MIN_N}+ resolved signals
          have MAE/MFE data.
        </div>
        <div style="font-size:10px;color:#444;
          margin-top:6px;">
          Currently: ${d.maeSamples.length} MAE
          · ${d.mfeSamples.length} MFE samples.
        </div>
      </div>`);
  }

  const maeOutlierNote = (hasMAE
    && d.maeOutlierCount > 0
    && d.avgMAEAdjusted !== null)
    ? `<div style="background:#1a0a0a;
         border:1px solid #f8514944;
         border-radius:6px;padding:6px 8px;
         margin-bottom:8px;font-size:10px;
         color:#f85149;line-height:1.6;">
         ⚠️ ${d.maeOutlierCount} outlier stop${
           d.maeOutlierCount > 1 ? 's' : ''}
         (MAE > 10%) skewing average.
         Outlier-adjusted avg MAE:
         <b>${d.avgMAEAdjusted}%</b>
         — gap-through stops are excluded
         from normal stop analysis.
       </div>`
    : '';

  const maeBlock = hasMAE ? `
    <div style="margin-bottom:12px;">
      <div style="font-size:11px;color:#8b949e;
        margin-bottom:4px;">
        MAE — Max Adverse Excursion
        <span style="color:#555;font-size:10px;
          margin-left:4px;">
          how far against you before resolve
        </span>
      </div>
      ${maeOutlierNote}
      <div style="font-size:11px;margin-bottom:8px;">
        avg MAE:
        <b style="color:#f85149;">${d.avgMAE}%</b>
        <span style="color:#555;font-size:10px;
          margin-left:6px;">
          · ${d.maeSamples.length} samples
        </span>
      </div>
      ${d.maeBands.map(b =>
        _bar(b.label, b.count,
             d.maeSamples.length,
             '#f85149')).join('')}
    </div>` : '';

  const mfeBlock = hasMFE ? `
    <div>
      <div style="font-size:11px;color:#8b949e;
        margin-bottom:4px;">
        MFE — Max Favorable Excursion
        <span style="color:#555;font-size:10px;
          margin-left:4px;">
          peak gain before resolve
        </span>
      </div>
      <div style="font-size:11px;margin-bottom:8px;">
        avg MFE:
        <b style="color:#00C851;">${d.avgMFE}%</b>
        <span style="color:#555;font-size:10px;
          margin-left:6px;">
          · ${d.mfeSamples.length} samples
        </span>
      </div>
      ${d.mfeBands.map(b =>
        _bar(b.label, b.count,
             d.mfeSamples.length,
             '#00C851')).join('')}
    </div>` : '';

  return _section('📉 MAE / MFE ANALYSIS', `
    <div style="font-size:10px;color:#555;
      margin-bottom:10px;">
      Trade excursion profile across resolved signals
    </div>
    ${maeBlock}
    ${hasMAE && hasMFE ? _divider() : ''}
    ${mfeBlock}`);
}

// ── 9. SIGNAL TIMELINE (L3) ───────────────────────────
function _renderTimeline(d) {
  if (!d.dates.length) {
    return _section('📅 SIGNAL TIMELINE', `
      <div style="color:#555;font-size:11px;
        text-align:center;padding:12px 0;">
        No scan days recorded yet.
      </div>`);
  }

  const maxCount = Math.max.apply(null,
    d.dates.map(dt => d.byDate[dt] || 0).concat([1]));

  const bars = d.dates.map(function (dt) {
    const count = d.byDate[dt] || 0;
    const width = Math.max(
      Math.round((count / maxCount) * 100), 3);
    const label = _shortDate(dt);
    const color = count >= 10 ? '#FFD700'
      : count >= 5 ? '#58a6ff' : '#30363d';
    return `
      <div style="display:flex;align-items:center;
        gap:8px;margin-bottom:5px;">
        <span style="color:#555;font-size:10px;
          min-width:38px;text-align:right;
          flex-shrink:0;">
          ${label}
        </span>
        <div style="flex:1;background:#21262d;
          border-radius:3px;height:18px;
          overflow:hidden;">
          <div style="background:${color};height:18px;
            width:${width}%;border-radius:3px;
            display:flex;align-items:center;
            padding:0 6px;box-sizing:border-box;">
            <span style="color:#07070f;font-size:10px;
              font-weight:700;white-space:nowrap;">
              ${count}
            </span>
          </div>
        </div>
      </div>`;
  });

  return _section('📅 SIGNAL TIMELINE', `
    <div style="font-size:10px;color:#555;
      margin-bottom:10px;">
      Live signals per scan day (gen=1) ·
      ${d.dates.length} scan days ·
      ${d.totalLive} total signals
    </div>
    ${bars.join('')}`);
}

// ── 10. BY SECTOR ─────────────────────────────────────
function _renderSectors(d) {
  const sorted = Object.entries(d.bySector)
    .sort((a, b) => b[1] - a[1]);
  return _section('🏭 BY SECTOR',
    sorted.map(([s, n]) =>
      _bar(s, n, d.totalAll, '#58a6ff')).join(''));
}

// ── 11. D6-4: DAY 6 EXIT BREAKDOWN ───────────────────
function _renderDay6Breakdown(d) {
  const total = d.day6Signals.length;
  if (total === 0) {
    return _section('📆 DAY 6 EXIT BREAKDOWN', `
      <div style="color:#555;font-size:11px;
        text-align:center;padding:12px 0;">
        No Day 6 exits yet — populates after first
        batch of signals complete their 6-day window.
      </div>`);
  }

  const fmtPnl = function (v) {
    if (v == null) return '—';
    const f = parseFloat(v).toFixed(1);
    return (parseFloat(f) >= 0 ? '+' : '') + f + '%';
  };

  const winPct  = _pct(d.day6Win.length,  total);
  const lossPct = _pct(d.day6Loss.length, total);
  const flatPct = _pct(d.day6Flat.length, total);

  return _section('📆 DAY 6 EXIT BREAKDOWN', `
    <div style="font-size:10px;color:#555;
      margin-bottom:10px;">
      Signals that reached Day 6 open exit ·
      ${total} total · no stop hit, no target hit
    </div>

    <div style="display:flex;gap:8px;
      flex-wrap:wrap;margin-bottom:12px;">
      ${_miniStat('Win', d.day6Win.length,  '#00C851')}
      ${_miniStat('Loss', d.day6Loss.length, '#f85149')}
      ${_miniStat('Flat', d.day6Flat.length, '#8b949e')}
    </div>

    <div style="font-size:11px;">
      <div style="display:flex;justify-content:space-between;
        padding:6px 0;border-bottom:1px solid #21262d;">
        <span style="color:#00C851;">DAY6 WIN</span>
        <span style="color:#555;">
          ${d.day6Win.length}
          <span style="color:#444;">(${winPct}%)</span>
        </span>
        <span style="color:#00C851;">
          avg ${fmtPnl(d.day6WinAvgPnl)}
        </span>
      </div>
      <div style="display:flex;justify-content:space-between;
        padding:6px 0;border-bottom:1px solid #21262d;">
        <span style="color:#f85149;">DAY6 LOSS</span>
        <span style="color:#555;">
          ${d.day6Loss.length}
          <span style="color:#444;">(${lossPct}%)</span>
        </span>
        <span style="color:#f85149;">
          avg ${fmtPnl(d.day6LossAvgPnl)}
        </span>
      </div>
      <div style="display:flex;justify-content:space-between;
        padding:6px 0;">
        <span style="color:#8b949e;">DAY6 FLAT</span>
        <span style="color:#555;">
          ${d.day6Flat.length}
          <span style="color:#444;">(${flatPct}%)</span>
        </span>
        <span style="color:#8b949e;">
          avg ${fmtPnl(d.day6FlatAvgPnl)}
        </span>
      </div>
    </div>

    <div style="font-size:10px;color:#444;margin-top:8px;
      padding-top:8px;border-top:1px solid #21262d;">
      Day 6 exit = sell at open regardless of P&L.
      Target/stop hits shown separately in win rate.
    </div>`);
}

// ── 12. M9: FAILURE PATTERN SUMMARY ──────────────────
function _renderFailurePatterns(d) {
  const resolved = d.resolvedLive;
  if (resolved < 5 || !d.failurePatterns.length) {
    return '';
  }

  const hasReasons = d.failurePatterns.some(
    ([, n]) => n > 0);
  if (!hasReasons) return '';

  const rows = d.failurePatterns.map(
    function ([reason, count]) {
      const pct = _pct(count, resolved);
      return `
        <div style="padding:5px 0;
          border-bottom:1px solid #21262d;
          font-size:11px;">
          <div style="display:flex;
            justify-content:space-between;
            margin-bottom:3px;">
            <span style="color:#c9d1d9;
              flex:1;margin-right:8px;">
              ${reason}
            </span>
            <span style="color:#555;
              white-space:nowrap;">
              ${count}
            </span>
          </div>
          <div style="background:#21262d;
            border-radius:2px;height:3px;">
            <div style="background:#8b949e;
              height:3px;width:${Math.max(pct, 2)}%;
              border-radius:2px;"></div>
          </div>
        </div>`;
    }).join('');

  return _section('🔍 FAILURE PATTERN SUMMARY', `
    <div style="font-size:10px;color:#555;
      margin-bottom:10px;">
      Most common failure reasons across
      ${resolved} resolved signals ·
      written by outcome evaluator at resolution
    </div>
    ${rows}
    <div style="font-size:10px;color:#444;
      margin-top:8px;padding-top:8px;
      border-top:1px solid #21262d;">
      Patterns with many signals = areas to
      improve via scoring weight tuning in Phase 3.
    </div>`);
}

// ── 13. SIGNAL FUNNEL ─────────────────────────────────
function _renderFunnel(d) {
  const total  = d.tookCount + d.rejCount;
  const shadow = d.shadowModeActive;

  const rejLabel   = shadow
    ? 'Shadow analysis' : 'Mini scanner rejected';
  const rejSubtext = shadow
    ? `${_pct(d.rejCount, total)}% would-be reject`
    : `${_pct(d.rejCount, total)}% reject rate`;
  const rejColor   = shadow ? '#555' : '#f85149';

  const shadowNote = shadow
    ? `<div style="background:#0d1117;
         border:1px solid #21262d;
         border-radius:6px;padding:8px 10px;
         margin-top:10px;font-size:10px;
         color:#555;line-height:1.6;">
         🔍 <b style="color:#8b949e;">
         Shadow mode active</b>
         — mini scanner is observing only.
         No signals are currently being blocked.
         Rejection reasons are logged for
         future analysis.
       </div>`
    : `<div style="background:#0d2a0d;
         border:1px solid #00C85133;
         border-radius:6px;padding:8px 10px;
         margin-top:10px;font-size:10px;
         color:#00C851;">
         ✓ Active filter mode — mini scanner
         is blocking low-conviction signals.
       </div>`;

  return _section('🔺 SIGNAL FUNNEL', `
    ${_statRow('Alpha scanner saw', total,
      'total signals')}
    ${_statRow('Mini scanner passed', d.tookCount,
      `${_pct(d.tookCount, total)}% pass rate`,
      '#00C851')}
    ${_statRow(rejLabel, d.rejCount,
      rejSubtext, rejColor)}

    ${d.rejCount > 0
      ? `<div style="margin-top:10px;
           border-top:1px solid #21262d;
           padding-top:10px;">
           <div style="font-size:11px;color:#555;
             margin-bottom:8px;letter-spacing:0.5px;">
             ${shadow
               ? 'WOULD-BE REJECTION REASONS'
               : 'REJECTION REASONS'}
           </div>
           ${Object.entries(d.byRej)
             .sort((a, b) => b[1] - a[1])
             .map(([r, n]) => _bar(
               r.replace(/_/g, ' '),
               n, d.rejCount,
               shadow ? '#444' : '#f85149'))
             .join('')}
         </div>`
      : ''}
    ${shadowNote}`);
}

// ── MAIN RENDER ───────────────────────────────────────
window.renderStats = function (tietiy) {
  const el = document.getElementById('tab-content');
  if (!el) return;

  const raw = (tietiy.history && tietiy.history.history)
    ? tietiy.history.history : [];

  if (!raw.length) {
    el.innerHTML = `
      <div style="text-align:center;
        padding:48px 16px;color:#555;
        font-size:13px;">
        No signal history yet.
      </div>`;
    return;
  }

  const shadowMode = (tietiy.meta
    && tietiy.meta.shadow_mode !== undefined)
    ? tietiy.meta.shadow_mode
    : true;

  const d = _analyse(raw, shadowMode);

  window._tietiyCSVData = raw;

  const phase2Unlocked = d.resolvedLive >= RESOLVED_TARGET;
  const headerLabel    = phase2Unlocked
    ? 'STATS — PHASE 2 ACTIVE'
    : 'STATS — PHASE 1 COLLECTION';

  el.innerHTML = `
    <div style="position:sticky;top:0;z-index:10;
      background:#07070f;
      padding:10px 16px 8px;
      border-bottom:1px solid #21262d;
      display:flex;justify-content:space-between;
      align-items:center;">
      <div style="font-size:11px;
        color:${phase2Unlocked ? '#00C851' : '#555'};
        letter-spacing:1px;font-weight:${
          phase2Unlocked ? '700' : '400'};">
        📈 ${headerLabel}
      </div>
      <button
        onclick="if(window._tietiyCSVData)
          window._tietiyDownloadCSV(
            window._tietiyCSVData);"
        style="background:#21262d;
          border:1px solid #30363d;
          color:#8b949e;font-size:10px;
          padding:4px 10px;border-radius:4px;
          cursor:pointer;
          -webkit-tap-highlight-color:transparent;">
        ⬇ CSV
      </button>
    </div>

    <div style="padding:12px 16px 80px;">
      ${_renderPhase2Banner(d)}
      ${_renderDataQualityBanner(d)}
      ${_renderProgress(d)}
      ${_renderWinRate(d)}
      ${_renderPerfDashboard(d)}
      ${_renderRegimeWR(d)}
      ${_renderByType(d)}
      ${_renderScoreDist(d)}
      ${_renderScoreBucketPerf(d)}
      ${_renderMAEMFE(d)}
      ${_renderTimeline(d)}
      ${_renderDay6Breakdown(d)}
      ${_renderFailurePatterns(d)}
      ${_renderSectors(d)}
      ${_renderFunnel(d)}
    </div>`;
};

})();
