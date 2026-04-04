// ── journal.js ───────────────────────────────────────
// Renders the Journal tab
// Called by ui.js switchTab('journal')
// Entry point: renderJournal(window.TIETIY)
//
// FIX 5 — Journal cards are now tappable
// Tap any card → opens same tap panel as signals tab
// Uses openTapPanel() from app.js via data-sig attribute
// ─────────────────────────────────────────────────────

const _BT = {
  UP_TRI:      87,
  DOWN_TRI:    87,
  UP_TRI_SA:   87,
  DOWN_TRI_SA: 87,
  BULL_PROXY:  67,
  OVERALL:     87,
};

function _resultBadge(result) {
  switch(result) {
    case 'WON':
      return `<span style="background:#0d2a0d;
        color:#00C851;border-radius:4px;
        padding:2px 7px;font-size:10px;
        font-weight:700;">✅ WIN</span>`;
    case 'STOPPED':
      return `<span style="background:#2a0a0a;
        color:#f85149;border-radius:4px;
        padding:2px 7px;font-size:10px;
        font-weight:700;">❌ STOP</span>`;
    case 'EXITED':
      return `<span style="background:#1a1a0a;
        color:#FFD700;border-radius:4px;
        padding:2px 7px;font-size:10px;
        font-weight:700;">🚪 EXIT</span>`;
    case 'PENDING':
      return `<span style="background:#0a0d1a;
        color:#58a6ff;border-radius:4px;
        padding:2px 7px;font-size:10px;
        font-weight:700;">⏳ OPEN</span>`;
    case 'REJECTED':
      return `<span style="background:#161b22;
        color:#444;border-radius:4px;
        padding:2px 7px;font-size:10px;">
        — SKIP</span>`;
    default:
      return `<span style="color:#444;
        font-size:10px;">${result || '—'}</span>`;
  }
}

function _signalColor(signal) {
  if (!signal) return '#8b949e';
  if (signal.startsWith('UP'))   return '#00C851';
  if (signal.startsWith('DOWN')) return '#f85149';
  if (signal === 'BULL_PROXY')   return '#58a6ff';
  return '#8b949e';
}

function _pnlColor(pnl) {
  if (pnl === null || pnl === undefined) return '#555';
  return parseFloat(pnl) >= 0 ? '#00C851' : '#f85149';
}

function _fmtPnl(pnl) {
  if (pnl === null || pnl === undefined || pnl === '')
    return '—';
  const v = parseFloat(pnl);
  return (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
}

function _fmtR(record) {
  try {
    const entry = parseFloat(record.entry || 0);
    const stop  = parseFloat(record.stop  || 0);
    const exit  = parseFloat(record.exit_price || 0);
    if (!entry || !stop || !exit) return null;
    const risk = Math.abs(entry - stop);
    if (risk <= 0) return null;
    const direction = record.direction === 'LONG' ? 1 : -1;
    const rMult = direction * (exit - entry) / risk;
    return rMult.toFixed(2);
  } catch(e) { return null; }
}

// ── STATISTICS ENGINE ─────────────────────────────────

function _calcStats(records) {
  const took = records.filter(
    r => r.action === 'TOOK' &&
    r.result !== 'REJECTED');

  const closed = took.filter(r =>
    ['WON','STOPPED','EXITED'].includes(r.result));
  const pending = took.filter(
    r => r.result === 'PENDING');
  const wins = closed.filter(
    r => r.result === 'WON');

  const wr = closed.length > 0
    ? Math.round(wins.length / closed.length * 100)
    : null;

  const byType = {};
  ['UP_TRI','DOWN_TRI','BULL_PROXY',
   'UP_TRI_SA','DOWN_TRI_SA'].forEach(sig => {
    const sigClosed = closed.filter(
      r => r.signal === sig);
    const sigWins = sigClosed.filter(
      r => r.result === 'WON');
    if (sigClosed.length > 0) {
      byType[sig] = {
        total: sigClosed.length,
        wins:  sigWins.length,
        wr:    Math.round(
          sigWins.length / sigClosed.length * 100),
      };
    }
  });

  let ciLow = null, ciHigh = null;
  if (closed.length >= 5 && wr !== null) {
    const n = closed.length;
    const p = wins.length / n;
    const z = 1.96;
    const denom  = 1 + z*z/n;
    const centre = p + z*z/(2*n);
    const spread = z * Math.sqrt(
      p*(1-p)/n + z*z/(4*n*n));
    ciLow  = Math.round((centre - spread) / denom * 100);
    ciHigh = Math.round((centre + spread) / denom * 100);
  }

  return {
    total:   took.length,
    closed:  closed.length,
    pending: pending.length,
    wins:    wins.length,
    wr,
    ciLow,
    ciHigh,
    byType,
  };
}

// ── WR COMPARISON BANNER ──────────────────────────────

function _buildWRBanner(stats) {
  const needed = Math.max(0, 20 - stats.closed);

  if (stats.closed < 5) {
    return `
      <div style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;padding:12px 14px;
        margin-bottom:12px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:6px;">
          📊 Building Track Record
        </div>
        <div style="background:#161b22;
          border-radius:6px;height:6px;
          margin-bottom:6px;overflow:hidden;">
          <div style="background:#ffd700;
            height:100%;border-radius:6px;
            width:${Math.round(
              stats.closed/20*100)}%;">
          </div>
        </div>
        <div style="font-size:11px;color:#555;">
          ${stats.closed} of 20 trades completed ·
          ${needed} more needed for significance
        </div>
        <div style="font-size:11px;color:#444;
          margin-top:8px;line-height:1.5;">
          What you will see at 20 trades:<br>
          • Live WR vs backtest ${_BT.OVERALL}%
            comparison<br>
          • Performance by signal type<br>
          • Score tier accuracy<br>
          • Grade A vs B vs C breakdown
        </div>
      </div>`;
  }

  const wr       = stats.wr;
  const btWr     = _BT.OVERALL;
  const gap      = wr - btWr;
  const gapColor = gap >= -5  ? '#00C851' :
                   gap >= -15 ? '#FFD700' : '#f85149';
  const gapIcon  = gap >= -5  ? '✅' :
                   gap >= -15 ? '⚠️' : '🔴';
  const ci       = (stats.ciLow !== null)
    ? ` (${stats.ciLow}%–${stats.ciHigh}% CI)`
    : '';

  return `
    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:12px 14px;
      margin-bottom:12px;">

      <div style="color:#ffd700;font-size:12px;
        font-weight:700;margin-bottom:10px;">
        📊 Performance — ${stats.closed} trades
      </div>

      <div style="display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:8px;margin-bottom:10px;">
        ${_statBox('Live WR',
          wr + '%' + ci, gapColor)}
        ${_statBox('Backtest WR',
          btWr + '%', '#555')}
        ${_statBox('Gap',
          (gap >= 0 ? '+' : '') + gap + '%',
          gapColor)}
      </div>

      <div style="font-size:11px;color:${gapColor};">
        ${gapIcon} ${
          gap >= -5
            ? 'Tracking backtest expectations'
          : gap >= -15
            ? 'Slightly below backtest — monitor'
          : 'Significantly below backtest — review signals'
        }
      </div>

      ${stats.closed < 20
        ? `<div style="font-size:10px;color:#444;
             margin-top:6px;">
             ${needed} more trades for statistical
             significance at 95% confidence
           </div>`
        : ''}

      ${Object.keys(stats.byType).length > 0
        ? `<div style="margin-top:10px;
             border-top:1px solid #21262d;
             padding-top:8px;">
             ${Object.entries(stats.byType)
               .map(([sig, d]) => {
                 const bt  = _BT[sig] || _BT.OVERALL;
                 const g   = d.wr - bt;
                 const gc  = g >= -5 ? '#00C851' :
                             g >= -15 ? '#FFD700' :
                             '#f85149';
                 return `
                   <div style="display:flex;
                     justify-content:space-between;
                     font-size:11px;padding:3px 0;
                     border-bottom:1px solid #0c0c1a;">
                     <span style="color:${
                       _signalColor(sig)};">
                       ${sig}
                     </span>
                     <span style="color:#555;">
                       ${d.wins}/${d.total}
                     </span>
                     <span style="color:${gc};">
                       ${d.wr}%
                       <span style="color:#444;
                         font-size:10px;">
                         vs ${bt}%
                       </span>
                     </span>
                   </div>`;
               }).join('')}
           </div>`
        : ''}
    </div>`;
}

function _statBox(label, value, color) {
  return `
    <div style="background:#161b22;
      border-radius:6px;padding:8px;">
      <div style="color:#555;font-size:10px;
        margin-bottom:2px;">${label}</div>
      <div style="color:${color};font-size:14px;
        font-weight:700;">${value}</div>
    </div>`;
}

// ── GROUP SIGNALS ─────────────────────────────────────

function _groupSignals(records) {
  const groups  = [];
  const saMap   = {};
  const parents = [];

  records.forEach(r => {
    if (r.attempt_number === 2 &&
        r.parent_signal_id) {
      saMap[r.parent_signal_id] = r;
    } else {
      parents.push(r);
    }
  });

  parents.forEach(p => {
    groups.push({
      primary:  p,
      attempt2: saMap[p.id] || null,
    });
  });

  records.forEach(r => {
    if (r.attempt_number === 2 &&
        r.parent_signal_id) {
      const hasParent = parents.find(
        p => p.id === r.parent_signal_id);
      if (!hasParent) {
        groups.push({
          primary:  r,
          attempt2: null,
        });
      }
    }
  });

  return groups;
}

// ── SINGLE TRADE ROW ──────────────────────────────────
// FIX 5 — cards are now tappable
// onclick calls openTapPanel() from app.js
// data-sig contains full signal record

function _buildTradeRow(record, isChild) {
  const sym    = (record.symbol || '')
                 .replace('.NS','');
  const signal = record.signal  || '';
  const result = record.result  || '';
  const date   = record.date    || '';
  const entry  = record.entry
    ? '₹' + fmt(record.entry) : '—';
  const stop   = record.stop
    ? '₹' + fmt(record.stop)  : '—';
  const exitPx = record.exit_price
    ? '₹' + fmt(record.exit_price) : '—';
  const exitDt = record.exit_date
    ? fmtDate(record.exit_date) : '—';
  const pnl    = _fmtPnl(record.pnl_pct);
  const rMult  = _fmtR(record);
  const score  = record.score || 0;
  const grade  = record.grade || '—';
  const sigColor = _signalColor(signal);
  const indent   = isChild
    ? 'border-left:3px solid #21262d;' +
      'margin-left:16px;' : '';

  // Day counter for PENDING
  let dayInfo = '';
  if (result === 'PENDING' && date) {
    try {
      const dayNum   = getDayNumber(date);
      const dayColor = dayNum >= 5 ? '#f85149' :
                       dayNum >= 4 ? '#FFD700' : '#555';
      dayInfo = `<span style="color:${dayColor};
        font-size:10px;margin-left:6px;">
        Day ${dayNum}/6
      </span>`;
    } catch(e) {}
  }

  // Open price note
  let openNote = '';
  if (result === 'PENDING' &&
      record.actual_open &&
      record.entry_valid === false) {
    openNote = `<div style="font-size:10px;
      color:#f85149;margin-top:2px;">
      ❌ Gap too large at open — skip signal
    </div>`;
  } else if (result === 'PENDING' &&
             record.actual_open) {
    openNote = `<div style="font-size:10px;
      color:#555;margin-top:2px;">
      Open: ₹${fmt(record.actual_open)}
      ${record.adjusted_rr
        ? '· R:R ' + record.adjusted_rr + 'x'
        : ''}
    </div>`;
  }

  // FIX 5 — encode full record for tap panel
  const sigData = encodeURIComponent(
    JSON.stringify(record));

  // Signal border color
  const borderColor = signal.startsWith('UP')
    ? '#00C851'
    : signal.startsWith('DOWN')
    ? '#f85149'
    : '#58a6ff';

  return `
    <div
      onclick="openTapPanel(this)"
      data-sig="${sigData}"
      style="background:#0d1117;
        border:1px solid #21262d;
        border-left:4px solid ${borderColor};
        border-radius:8px;
        padding:10px 12px;
        margin-bottom:8px;
        cursor:pointer;
        transition:opacity 0.2s;
        ${indent}"
      ontouchstart="this.style.opacity='0.7'"
      ontouchend="this.style.opacity='1'">

      <!-- Row 1: Symbol + result -->
      <div style="display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:6px;">
        <div>
          <span style="font-weight:700;
            color:#fff;font-size:15px;">
            ${sym}
          </span>
          ${isChild
            ? `<span style="font-size:10px;
                 color:#555;margin-left:6px;">
                 ↳ 2nd attempt
               </span>`
            : ''}
          <span style="color:${sigColor};
            font-size:10px;margin-left:6px;
            font-weight:700;">
            ${signal}
          </span>
          ${dayInfo}
        </div>
        ${_resultBadge(result)}
      </div>

      <!-- Row 2: Date + score + grade -->
      <div style="font-size:10px;color:#444;
        margin-bottom:6px;">
        ${fmtDate(date)} ·
        Score ${score}/10 ·
        Grade ${grade} ·
        ${record.regime || '—'}
      </div>

      <!-- Row 3: Price grid -->
      <div style="display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:4px;font-size:11px;">
        <div>
          <div style="color:#444;
            font-size:9px;">ENTRY</div>
          <div style="color:#58a6ff;">
            ${entry}
          </div>
        </div>
        <div>
          <div style="color:#444;
            font-size:9px;">STOP</div>
          <div style="color:#f85149;">
            ${stop}
          </div>
        </div>
        <div>
          <div style="color:#444;
            font-size:9px;">EXIT</div>
          <div style="color:#c9d1d9;">
            ${result === 'PENDING'
              ? exitDt : exitPx}
          </div>
        </div>
        <div>
          <div style="color:#444;
            font-size:9px;">
            ${result === 'PENDING'
              ? 'DUE' : 'P&L'}
          </div>
          <div style="color:${
            result === 'PENDING'
              ? '#555'
              : _pnlColor(record.pnl_pct)};">
            ${result === 'PENDING'
              ? exitDt
              : pnl + (rMult
                  ? ' · ' + rMult + 'R'
                  : '')}
          </div>
        </div>
      </div>

      ${openNote}

      <!-- Tap hint -->
      <div style="font-size:9px;color:#333;
        margin-top:6px;text-align:right;">
        Tap for details →
      </div>

    </div>`;
}

// ── CSV DOWNLOAD ───────────────────────────────────────

function downloadCSV(records) {
  const cols = [
    'Date','Symbol','Signal','Grade',
    'Score','Regime','Age',
    'Entry','Stop','Exit Date',
    'Exit Price','Result','PnL %','R Multiple',
    'Attempt','Parent Signal ID',
  ];

  const took = records.filter(
    r => r.action === 'TOOK' &&
    r.result !== 'REJECTED');

  const rows = took.map(r => [
    r.date             || '',
    (r.symbol || '').replace('.NS',''),
    r.signal           || '',
    r.grade            || '',
    r.score            || '',
    r.regime           || '',
    r.age              || '',
    r.entry            || '',
    r.stop             || '',
    r.exit_date        || '',
    r.exit_price       || '',
    r.result           || '',
    r.pnl_pct          || '',
    _fmtR(r)           || '',
    r.attempt_number   || 1,
    r.parent_signal_id || '',
  ]);

  const stats  = _calcStats(records);
  const sumRow = [
    '--- SUMMARY ---',
    `Total: ${stats.total}`,
    `Closed: ${stats.closed}`,
    '', '', '', '', '', '', '', '',
    `WR: ${stats.wr !== null
      ? stats.wr + '%' : 'N/A'}`,
    '', '', '', '',
  ];

  const csvContent = [
    cols.join(','),
    ...rows.map(r =>
      r.map(v => `"${String(v)
        .replace(/"/g,'""')}"`).join(',')),
    sumRow.join(','),
  ].join('\n');

  const blob  = new Blob([csvContent],
    { type: 'text/csv;charset=utf-8;' });
  const url   = URL.createObjectURL(blob);
  const link  = document.createElement('a');
  const today = new Date()
    .toISOString().slice(0,10)
    .replace(/-/g,'');

  link.href     = url;
  link.download = `tietiy_journal_${today}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// ── MAIN RENDER ───────────────────────────────────────

function renderJournal(data) {
  const content = document.getElementById(
    'tab-content');
  if (!content) return;

  const histData = data.history;
  const records  = (histData && histData.history)
    ? histData.history : [];

  const journalRecords = records.filter(
    r => r.result !== 'REJECTED');

  const sorted = [...journalRecords].sort(
    (a, b) => (b.date || '')
              .localeCompare(a.date || ''));

  const stats = _calcStats(records);

  if (!sorted.length) {
    content.innerHTML = `
      <div style="padding:14px;">
        <div style="text-align:center;
          padding:40px 20px;
          color:#555;font-size:13px;">
          <div style="font-size:32px;
            margin-bottom:12px;">📓</div>
          <div style="color:#8b949e;
            font-size:15px;font-weight:700;
            margin-bottom:8px;">
            No trades yet
          </div>
          <div style="font-size:12px;
            color:#444;line-height:1.6;">
            Signals found by the scanner are
            automatically recorded here.<br><br>
            Check back after the next market
            scan at 8:45 AM IST.
          </div>
        </div>
      </div>`;
    _renderNav('journal');
    return;
  }

  const recent  = sorted.slice(0, 30);
  const groups  = _groupSignals(recent);

  const pendingGroups = groups.filter(
    g => g.primary.result === 'PENDING');
  const closedGroups  = groups.filter(
    g => g.primary.result !== 'PENDING');

  content.innerHTML = `
    <div style="padding:14px;">

      ${_buildWRBanner(stats)}

      <div style="text-align:right;
        margin-bottom:12px;">
        <button onclick="downloadCSV(
          window.TIETIY.history.history || [])"
          style="background:#161b22;
            border:1px solid #30363d;
            color:#8b949e;border-radius:6px;
            padding:6px 14px;font-size:11px;
            cursor:pointer;">
          ⬇ Download CSV
        </button>
      </div>

      ${pendingGroups.length > 0 ? `
        <div style="color:#8b949e;font-size:11px;
          font-weight:700;letter-spacing:1px;
          border-left:3px solid #58a6ff;
          padding-left:8px;margin-bottom:10px;">
          OPEN POSITIONS
          <span style="color:#555;font-weight:400;">
            (${pendingGroups.length})
          </span>
        </div>
        ${pendingGroups.map(g => `
          ${_buildTradeRow(g.primary, false)}
          ${g.attempt2
            ? _buildTradeRow(g.attempt2, true)
            : ''}
        `).join('')}
      ` : ''}

      ${closedGroups.length > 0 ? `
        <div style="color:#8b949e;font-size:11px;
          font-weight:700;letter-spacing:1px;
          border-left:3px solid #ffd700;
          padding-left:8px;
          margin:16px 0 10px;">
          CLOSED TRADES
          <span style="color:#555;font-weight:400;">
            (${closedGroups.length})
          </span>
        </div>
        ${closedGroups.map(g => `
          ${_buildTradeRow(g.primary, false)}
          ${g.attempt2
            ? _buildTradeRow(g.attempt2, true)
            : ''}
        `).join('')}
      ` : ''}

      <div style="text-align:center;
        font-size:11px;color:#333;
        padding:12px 0;">
        Showing last ${Math.min(
          sorted.length, 30)} of
        ${sorted.length} total records ·
        Tap any card for full details
      </div>

    </div>`;

  _renderNav('journal');
}
