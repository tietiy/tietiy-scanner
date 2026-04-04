// ── stats.js ─────────────────────────────────────────
// Renders the Stats tab
// Called by ui.js switchTab('stats')
// Entry point: renderStats(window.TIETIY)
//
// Reads from:
//   window.TIETIY.history      → signal_history.json
//   window.TIETIY.scanLog      → scan_log.json
//   window.TIETIY.meta         → meta.json
//
// Phase 2: Progress bar + basic WR breakdown
// Phase 3: Full analytics (future — additive only)
//
// Minimal working version — no overengineering
// All Phase 3 additions = new functions appended below
// ─────────────────────────────────────────────────────

// ── CONSTANTS ─────────────────────────────────────────
const _SIGNIFICANCE_THRESHOLD = 20;
const _MIN_DISPLAY_THRESHOLD  = 3;

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
  if (live === null) return '#555';
  const gap = live - baseline;
  if (gap >= -5)  return '#00C851';
  if (gap >= -15) return '#FFD700';
  return '#f85149';
}

function _gapLabel(live, baseline) {
  if (live === null) return '—';
  const gap = live - baseline;
  const sign = gap >= 0 ? '+' : '';
  return sign + gap + '%';
}

function _progressBar(value, max, color) {
  const pct = Math.min(
    Math.round(value / max * 100), 100);
  return `
    <div style="background:#161b22;
      border-radius:4px;height:6px;
      overflow:hidden;margin:4px 0;">
      <div style="background:${color};
        height:100%;border-radius:4px;
        width:${pct}%;
        transition:width 0.3s ease;">
      </div>
    </div>`;
}

function _sectionHeader(title, subtitle) {
  return `
    <div style="border-left:3px solid #ffd700;
      padding-left:8px;margin:16px 0 10px;">
      <div style="color:#ffd700;font-size:11px;
        font-weight:700;letter-spacing:1px;">
        ${title}
      </div>
      ${subtitle
        ? `<div style="color:#444;font-size:10px;
             margin-top:2px;">${subtitle}</div>`
        : ''}
    </div>`;
}

function _statCard(label, value, sub, color) {
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

// ── DATA PREPARATION ──────────────────────────────────

function _prepareData(records) {
  // Only TOOK signals — exclude REJECTED
  const took = records.filter(
    r => r.action === 'TOOK' &&
    r.result !== 'REJECTED');

  const closed = took.filter(r =>
    ['WON','STOPPED','EXITED']
    .includes(r.result));

  const pending = took.filter(
    r => r.result === 'PENDING');

  const wins = closed.filter(
    r => r.result === 'WON');

  const overallWR = _pct(wins.length,
    closed.length);

  // By signal type
  const byType = {};
  Object.keys(_BT_WR).forEach(sig => {
    const sigAll    = took.filter(
      r => r.signal === sig);
    const sigClosed = sigAll.filter(r =>
      ['WON','STOPPED','EXITED']
      .includes(r.result));
    const sigWins   = sigClosed.filter(
      r => r.result === 'WON');
    byType[sig] = {
      total:   sigAll.length,
      closed:  sigClosed.length,
      wins:    sigWins.length,
      pending: sigAll.filter(
        r => r.result === 'PENDING').length,
      wr:      _pct(sigWins.length,
                 sigClosed.length),
    };
  });

  // By grade
  const byGrade = {};
  ['A','B','C'].forEach(g => {
    const gAll    = took.filter(
      r => r.grade === g);
    const gClosed = gAll.filter(r =>
      ['WON','STOPPED','EXITED']
      .includes(r.result));
    const gWins   = gClosed.filter(
      r => r.result === 'WON');
    byGrade[g] = {
      total:  gAll.length,
      closed: gClosed.length,
      wins:   gWins.length,
      wr:     _pct(gWins.length, gClosed.length),
    };
  });

  // By score tier
  const byScore = {
    high:   { label:'8-10', closed:0, wins:0 },
    mid:    { label:'5-7',  closed:0, wins:0 },
    low:    { label:'0-4',  closed:0, wins:0 },
  };
  closed.forEach(r => {
    const s = r.score || 0;
    const tier = s >= 8 ? 'high' :
                 s >= 5 ? 'mid'  : 'low';
    byScore[tier].closed++;
    if (r.result === 'WON')
      byScore[tier].wins++;
  });
  Object.keys(byScore).forEach(k => {
    byScore[k].wr = _pct(
      byScore[k].wins,
      byScore[k].closed);
  });

  // By regime
  const byRegime = {};
  ['Bull','Bear','Choppy'].forEach(reg => {
    const rClosed = closed.filter(
      r => r.regime === reg);
    const rWins   = rClosed.filter(
      r => r.result === 'WON');
    if (rClosed.length > 0) {
      byRegime[reg] = {
        closed: rClosed.length,
        wins:   rWins.length,
        wr:     _pct(rWins.length, rClosed.length),
      };
    }
  });

  // Recent streak
  const recentClosed = [...closed].sort(
    (a,b) => (b.date||'')
             .localeCompare(a.date||''))
    .slice(0,5);
  const recentWins = recentClosed.filter(
    r => r.result === 'WON').length;
  const recentWR   = _pct(
    recentWins, recentClosed.length);

  return {
    total:      took.length,
    closed:     closed.length,
    pending:    pending.length,
    wins:       wins.length,
    overallWR,
    byType,
    byGrade,
    byScore,
    byRegime,
    recentWR,
    recentCount: recentClosed.length,
    needed: Math.max(0,
      _SIGNIFICANCE_THRESHOLD - closed.length),
  };
}

// ── SHADOW FILTER ANALYSIS ────────────────────────────
// Shows what mini scanner WOULD have filtered
// in shadow mode — for future rule validation

function _buildShadowAnalysis(records) {
  const rejected = records.filter(
    r => r.result === 'REJECTED' &&
    r.rejection_reason);

  if (!rejected.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:12px 14px;
        font-size:11px;color:#444;">
        No shadow rejections yet.
        Shadow data builds as scanner runs daily.
      </div>`;
  }

  // Count by filter
  const byFilter = {};
  rejected.forEach(r => {
    const f = r.rejection_filter || 'unknown';
    if (!byFilter[f]) byFilter[f] = {
      count: 0, signals: [] };
    byFilter[f].count++;
    byFilter[f].signals.push(r.signal);
  });

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:12px 14px;">

      <div style="font-size:11px;color:#555;
        margin-bottom:10px;">
        ${rejected.length} signals evaluated
        in shadow mode.
        Filters inactive — all passed through.
        Data collected for future validation.
      </div>

      ${Object.entries(byFilter).map(
        ([filter, d]) => `
          <div style="display:flex;
            justify-content:space-between;
            font-size:11px;padding:4px 0;
            border-bottom:1px solid #0c0c1a;">
            <span style="color:#8b949e;">
              ${filter}
            </span>
            <span style="color:#555;">
              ${d.count} would be filtered
            </span>
          </div>`
      ).join('')}

      <div style="font-size:10px;color:#333;
        margin-top:8px;">
        Activate filters in
        data/mini_scanner_rules.json
        only after backtest validation
      </div>
    </div>`;
}

// ── PROGRESS SECTION ──────────────────────────────────

function _buildProgressSection(d) {
  const pct = Math.min(
    Math.round(d.closed /
      _SIGNIFICANCE_THRESHOLD * 100), 100);

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;
      margin-bottom:4px;">

      <div style="display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:8px;">
        <div style="color:#c9d1d9;font-size:13px;
          font-weight:700;">
          Track Record
        </div>
        <div style="color:#555;font-size:11px;">
          ${d.closed} / ${_SIGNIFICANCE_THRESHOLD}
          trades
        </div>
      </div>

      ${_progressBar(d.closed,
        _SIGNIFICANCE_THRESHOLD, '#ffd700')}

      <div style="display:grid;
        grid-template-columns:repeat(3,1fr);
        gap:8px;margin-top:10px;">
        ${_statCard('Total Signals',
          d.total, 'recorded', '#c9d1d9')}
        ${_statCard('Closed',
          d.closed, 'completed', '#8b949e')}
        ${_statCard('Open',
          d.pending, 'pending', '#58a6ff')}
      </div>

      ${d.needed > 0
        ? `<div style="font-size:11px;
             color:#444;margin-top:10px;
             text-align:center;">
             ${d.needed} more closed trades needed
             for 95% confidence significance
           </div>`
        : `<div style="font-size:11px;
             color:#00C851;margin-top:10px;
             text-align:center;">
             ✅ Statistically significant
           </div>`}
    </div>`;
}

// ── WR OVERVIEW ───────────────────────────────────────

function _buildWROverview(d) {
  if (d.closed < _MIN_DISPLAY_THRESHOLD) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        text-align:center;font-size:12px;
        color:#444;">
        Need ${_MIN_DISPLAY_THRESHOLD} closed
        trades to show WR breakdown.
        <br>
        <span style="color:#333;">
          ${d.closed} closed so far.
        </span>
      </div>`;
  }

  const wr = d.overallWR;
  const bt = _BT_WR.OVERALL;
  const gc = _gapColor(wr, bt);

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      <!-- Overall WR -->
      <div style="display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:8px;margin-bottom:12px;">
        ${_statCard('Live WR',
          wr !== null ? wr + '%' : '—',
          `${d.wins}W / ${d.closed-d.wins}L`,
          gc)}
        ${_statCard('Backtest WR',
          bt + '%',
          'V3 baseline', '#555')}
        ${_statCard('Gap',
          _gapLabel(wr, bt),
          wr !== null && wr >= bt - 5
            ? 'On track ✅'
            : wr !== null && wr >= bt - 15
            ? 'Monitor ⚠️'
            : 'Review 🔴',
          gc)}
      </div>

      <!-- Recent 5 -->
      ${d.recentCount >= 3
        ? `<div style="border-top:1px solid #21262d;
             padding-top:10px;font-size:11px;
             display:flex;
             justify-content:space-between;">
             <span style="color:#555;">
               Last ${d.recentCount} trades WR
             </span>
             <span style="color:${
               _gapColor(d.recentWR, bt)};">
               ${d.recentWR !== null
                 ? d.recentWR + '%' : '—'}
             </span>
           </div>`
        : ''}
    </div>`;
}

// ── BY SIGNAL TYPE ────────────────────────────────────

function _buildByType(d) {
  const rows = Object.entries(d.byType)
    .filter(([, v]) =>
      v.closed >= _MIN_DISPLAY_THRESHOLD)
    .map(([sig, v]) => {
      const bt = _BT_WR[sig] || _BT_WR.OVERALL;
      const gc = _gapColor(v.wr, bt);
      const sigColor =
        sig.startsWith('UP')   ? '#00C851' :
        sig.startsWith('DOWN') ? '#f85149' :
        '#58a6ff';
      return `
        <div style="padding:8px 0;
          border-bottom:1px solid #0c0c1a;">
          <div style="display:flex;
            justify-content:space-between;
            margin-bottom:4px;font-size:11px;">
            <span style="color:${sigColor};
              font-weight:700;">${sig}</span>
            <span style="color:${gc};
              font-weight:700;">
              ${v.wr !== null
                ? v.wr + '%' : '—'}
              <span style="color:#333;
                font-size:10px;">
                vs ${bt}%
              </span>
            </span>
          </div>
          ${_progressBar(v.wins,
            v.closed, sigColor)}
          <div style="display:flex;
            justify-content:space-between;
            font-size:10px;color:#444;
            margin-top:2px;">
            <span>
              ${v.wins}W /
              ${v.closed - v.wins}L ·
              ${v.pending} open
            </span>
            <span>${_gapLabel(v.wr, bt)}</span>
          </div>
        </div>`;
    });

  if (!rows.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        Need ${_MIN_DISPLAY_THRESHOLD}+ closed
        trades per signal type to show breakdown.
      </div>`;
  }

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">
      ${rows.join('')}
    </div>`;
}

// ── BY SCORE TIER ─────────────────────────────────────

function _buildByScore(d) {
  const tiers = Object.entries(d.byScore)
    .filter(([, v]) => v.closed > 0);

  if (!tiers.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        No closed trades yet for score analysis.
      </div>`;
  }

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      <div style="font-size:10px;color:#444;
        margin-bottom:8px;">
        Validates whether higher scores
        actually produce better outcomes
      </div>

      ${tiers.map(([, v]) => {
        const wr = v.wr;
        const gc = wr !== null && wr >= 70
          ? '#00C851'
          : wr !== null && wr >= 50
          ? '#FFD700'
          : '#f85149';
        return `
          <div style="display:flex;
            justify-content:space-between;
            align-items:center;
            padding:6px 0;
            border-bottom:1px solid #0c0c1a;
            font-size:11px;">
            <span style="color:#8b949e;">
              Score ${v.label}
            </span>
            <span style="color:#555;">
              ${v.wins}W / ${v.closed}T
            </span>
            <span style="color:${gc};
              font-weight:700;">
              ${wr !== null ? wr + '%' : '—'}
            </span>
          </div>`;
      }).join('')}

      <div style="font-size:10px;color:#333;
        margin-top:8px;">
        Higher scores should show higher WR.
        If not, scoring weights need review.
      </div>
    </div>`;
}

// ── BY GRADE ──────────────────────────────────────────

function _buildByGrade(d) {
  const grades = Object.entries(d.byGrade)
    .filter(([, v]) => v.closed > 0);

  if (!grades.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        No closed trades yet for grade analysis.
      </div>`;
  }

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">

      <div style="font-size:10px;color:#444;
        margin-bottom:8px;">
        Grade A = backtest validated ·
        B = limited history ·
        C = unvalidated
      </div>

      ${grades.map(([grade, v]) => {
        const gc = v.wr !== null && v.wr >= 70
          ? '#00C851'
          : v.wr !== null && v.wr >= 50
          ? '#FFD700'
          : '#f85149';
        return `
          <div style="display:flex;
            justify-content:space-between;
            align-items:center;padding:6px 0;
            border-bottom:1px solid #0c0c1a;
            font-size:11px;">
            <span style="color:#ffd700;
              font-weight:700;">
              Grade ${grade}
            </span>
            <span style="color:#555;">
              ${v.wins}W / ${v.closed}T
            </span>
            <span style="color:${gc};
              font-weight:700;">
              ${v.wr !== null
                ? v.wr + '%' : '—'}
            </span>
          </div>`;
      }).join('')}
    </div>`;
}

// ── BY REGIME ─────────────────────────────────────────

function _buildByRegime(d) {
  const regimes = Object.entries(d.byRegime);

  if (!regimes.length) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        font-size:11px;color:#444;
        text-align:center;">
        No closed trades yet for regime analysis.
      </div>`;
  }

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:14px;">
      ${regimes.map(([regime, v]) => {
        const rc =
          regime === 'Bear'   ? '#f85149' :
          regime === 'Bull'   ? '#00C851' :
          '#FFD700';
        const gc = v.wr !== null && v.wr >= 70
          ? '#00C851'
          : v.wr !== null && v.wr >= 50
          ? '#FFD700'
          : '#f85149';
        return `
          <div style="display:flex;
            justify-content:space-between;
            align-items:center;
            padding:6px 0;
            border-bottom:1px solid #0c0c1a;
            font-size:11px;">
            <span style="color:${rc};
              font-weight:700;">
              ${regime}
            </span>
            <span style="color:#555;">
              ${v.wins}W / ${v.closed}T
            </span>
            <span style="color:${gc};
              font-weight:700;">
              ${v.wr !== null
                ? v.wr + '%' : '—'}
            </span>
          </div>`;
      }).join('')}
      <div style="font-size:10px;color:#333;
        margin-top:8px;">
        Bear regime UP_TRI = highest conviction
        by backtest evidence
      </div>
    </div>`;
}

// ── SYSTEM INFO ───────────────────────────────────────

function _buildSystemInfo(meta) {
  if (!meta) return '';
  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:12px 14px;
      font-size:11px;">
      ${_detailRow('Scanner version',
        meta.scanner_version || '—')}
      ${_detailRow('Schema version',
        meta.schema_version  || '—')}
      ${_detailRow('Universe size',
        (meta.universe_size || '—') +
        ' stocks')}
      ${_detailRow('Last scan',
        meta.last_scan
          ? fmtTime(meta.last_scan) : '—')}
      ${_detailRow('Deployed at',
        meta.deployed_at
          ? fmtTime(meta.deployed_at) : '—')}
      ${_detailRow('Holidays valid until',
        meta.holidays_valid_until || '—')}
      ${_detailRow('History records',
        meta.history_record_count || '—')}
      ${meta.fetch_failed &&
        meta.fetch_failed.length > 0
        ? _detailRow('Fetch failed',
            meta.fetch_failed.join(', '))
        : ''}
      ${meta.corporate_action_skip &&
        meta.corporate_action_skip.length > 0
        ? _detailRow('CA skipped',
            meta.corporate_action_skip
            .join(', '))
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

  // ── EMPTY STATE ───────────────────────────────
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
            color:#444;line-height:1.6;">
            Stats build automatically as
            signals are recorded.<br><br>
            What you will see here:<br>
            <span style="color:#333;">
              • Live WR vs backtest 87%<br>
              • Performance by signal type<br>
              • Score tier accuracy<br>
              • Grade A vs B vs C breakdown<br>
              • Regime performance analysis<br>
              • Mini scanner shadow analysis
            </span>
          </div>
        </div>
        ${_sectionHeader('SYSTEM INFO',
          'Scanner configuration')}
        ${_buildSystemInfo(meta)}
      </div>`;
    _renderNav('stats');
    return;
  }

  // ── PREPARE DATA ──────────────────────────────
  const d = _prepareData(records);

  // ── RENDER ────────────────────────────────────
  content.innerHTML = `
    <div style="padding:14px;">

      <!-- TRACK RECORD PROGRESS -->
      ${_sectionHeader('TRACK RECORD',
        'Building toward statistical significance')}
      ${_buildProgressSection(d)}

      <!-- WR OVERVIEW -->
      ${_sectionHeader('WIN RATE',
        'Live performance vs backtest baseline')}
      ${_buildWROverview(d)}

      <!-- BY SIGNAL TYPE -->
      ${_sectionHeader('BY SIGNAL TYPE',
        'Minimum ' + _MIN_DISPLAY_THRESHOLD +
        ' closed trades per type to show')}
      ${_buildByType(d)}

      <!-- BY SCORE TIER -->
      ${_sectionHeader('BY SCORE TIER',
        'Validates scoring model discrimination')}
      ${_buildByScore(d)}

      <!-- BY GRADE -->
      ${_sectionHeader('BY GRADE',
        'A = validated · B = limited · ' +
        'C = unvalidated')}
      ${_buildByGrade(d)}

      <!-- BY REGIME -->
      ${_sectionHeader('BY REGIME',
        'Bear regime UP_TRI = highest conviction')}
      ${_buildByRegime(d)}

      <!-- MINI SCANNER SHADOW -->
      ${_sectionHeader('MINI SCANNER SHADOW',
        'Filter impact analysis — ' +
        'all rules currently inactive')}
      ${_buildShadowAnalysis(records)}

      <!-- SYSTEM INFO -->
      ${_sectionHeader('SYSTEM INFO',
        'Scanner configuration and metadata')}
      ${_buildSystemInfo(meta)}

      <!-- PHASE 3 PLACEHOLDER -->
      <div style="background:#0a0d1a;
        border:1px solid #21262d;
        border-radius:8px;padding:14px;
        margin-top:8px;text-align:center;
        font-size:11px;color:#333;">
        📊 Phase 3 analytics coming soon<br>
        <span style="font-size:10px;color:#222;">
          Walk-forward validation ·
          Delivery volume filter ·
          Sector rotation heatmap ·
          Score weight optimisation
        </span>
      </div>

    </div>`;

  _renderNav('stats');
}
