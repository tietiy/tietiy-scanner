// ── stats.js ─────────────────────────────────────────
// Step 22 — Stats Dashboard (Phase 1)
//
// Phase 1 goal: collect 30 resolved signals
// Until then: show inventory, funnel, score dist, sectors
// Win rate section renders automatically once data exists
// ─────────────────────────────────────────────────────

(function () {

  // ── CONSTANTS ────────────────────────────────────────

  const RESOLVED_TARGET = 30;

  const OUTCOME_WIN = new Set([
    'TARGET_HIT', 'DAY6_WIN']);
  const OUTCOME_LOSS = new Set([
    'STOP_HIT', 'DAY6_LOSS']);
  const OUTCOME_DONE = new Set([
    'TARGET_HIT', 'STOP_HIT',
    'DAY6_WIN', 'DAY6_LOSS', 'DAY6_FLAT']);


  // ── HELPERS ──────────────────────────────────────────

  function _sym(s) {
    return (s || '').replace('.NS', '');
  }

  function _pct(n, d) {
    if (!d) return 0;
    return Math.round((n / d) * 100);
  }

  // Simple CSS bar — no external lib
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
            transition:width 0.3s ease;">
          </div>
        </div>
      </div>`;
  }

  function _scoreBar(score, count, maxCount) {
    const width = maxCount
      ? Math.max(Math.round((count / maxCount) * 100), 2) : 2;
    const color = score >= 8 ? '#ffd700'
                : score >= 6 ? '#00C851'
                : score >= 4 ? '#58a6ff'
                : '#555';
    return `
      <div style="display:flex;align-items:center;
        gap:8px;margin-bottom:6px;">
        <span style="color:${color};font-size:11px;
          font-weight:700;min-width:28px;
          text-align:right;">${score}/10</span>
        <div style="flex:1;background:#21262d;
          border-radius:3px;height:8px;">
          <div style="background:${color};height:8px;
            width:${width}%;border-radius:3px;">
          </div>
        </div>
        <span style="color:#555;font-size:11px;
          min-width:20px;">${count}</span>
      </div>`;
  }

  function _section(title, content) {
    return `
      <div style="background:#161b22;
        border:1px solid #21262d;border-radius:8px;
        padding:14px;margin-bottom:12px;">
        <div style="font-size:11px;color:#ffd700;
          font-weight:700;letter-spacing:1px;
          margin-bottom:12px;">
          ${title}
        </div>
        ${content}
      </div>`;
  }

  function _statRow(label, value, subtext, valueColor) {
    return `
      <div style="display:flex;justify-content:space-between;
        align-items:baseline;margin-bottom:6px;">
        <span style="color:#8b949e;font-size:12px;">
          ${label}
        </span>
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
        <span style="color:#555;font-size:12px;">
          ${label}
        </span>
        <span style="color:#555;font-size:11px;">
          🔒 collecting
        </span>
      </div>`;
  }


  // ── DATA ANALYSIS ────────────────────────────────────

  function _analyse(raw) {
    // Only analyse TOOK entries (MINI layer)
    // REJECTED entries used separately for funnel
    const took = raw.filter(
      s => s.layer === 'MINI' && s.action === 'TOOK');
    const rej  = raw.filter(
      s => s.layer === 'ALPHA' && s.action === 'REJECTED');

    // Resolved = outcome in DONE set
    const resolved = took.filter(
      s => OUTCOME_DONE.has(s.outcome || ''));
    const wins   = resolved.filter(
      s => OUTCOME_WIN.has(s.outcome));
    const losses = resolved.filter(
      s => OUTCOME_LOSS.has(s.outcome));
    const open   = took.filter(
      s => !OUTCOME_DONE.has(s.outcome || ''));

    // Signal type breakdown — TOOK only
    const byType = {};
    took.forEach(function (s) {
      const t = s.signal || 'Unknown';
      byType[t] = (byType[t] || 0) + 1;
    });

    // Score distribution — TOOK only
    const byScore = {};
    took.forEach(function (s) {
      const sc = parseInt(s.score) || 0;
      byScore[sc] = (byScore[sc] || 0) + 1;
    });

    // Sector breakdown — TOOK only
    const bySector = {};
    took.forEach(function (s) {
      const sec = s.sector || 'Other';
      bySector[sec] = (bySector[sec] || 0) + 1;
    });

    // Rejection reasons — ALPHA layer
    const byRej = {};
    rej.forEach(function (s) {
      const r = s.rejection_reason || 'unknown';
      byRej[r] = (byRej[r] || 0) + 1;
    });

    // Bear bonus rate
    const bearCount = took.filter(
      s => s.bear_bonus === true
        || s.bear_bonus === 'true').length;

    // Win rates (only when enough data)
    const wrTotal = resolved.length
      ? _pct(wins.length, resolved.length) : null;

    // By signal type WR
    const wrByType = {};
    ['UP_TRI', 'DOWN_TRI', 'BULL_PROXY'].forEach(
      function (t) {
        const typeResolved = resolved.filter(
          s => s.signal === t);
        const typeWins = typeResolved.filter(
          s => OUTCOME_WIN.has(s.outcome));
        if (typeResolved.length >= 5) {
          wrByType[t] = {
            wr:    _pct(typeWins.length,
                        typeResolved.length),
            n:     typeResolved.length,
            fired: byType[t] || 0,
          };
        }
      });

    // Avg P&L on resolved
    const pnlArr = resolved
      .filter(s => s.pnl_pct != null)
      .map(s => parseFloat(s.pnl_pct));
    const avgPnl = pnlArr.length
      ? (pnlArr.reduce((a, b) => a + b, 0)
         / pnlArr.length).toFixed(2)
      : null;

    // Dates seen
    const dates = [...new Set(
      took.map(s => s.date).filter(Boolean))];

    return {
      total:      took.length,
      resolved:   resolved.length,
      open:       open.length,
      wins:       wins.length,
      losses:     losses.length,
      byType,
      byScore,
      bySector,
      byRej,
      bearCount,
      wrTotal,
      wrByType,
      avgPnl,
      dates,
      tookCount:  took.length,
      rejCount:   rej.length,
    };
  }


  // ── SECTION RENDERERS ────────────────────────────────

  function _renderProgress(d) {
    const n      = d.resolved;
    const target = RESOLVED_TARGET;
    const pct    = Math.min(Math.round(
      (n / target) * 100), 100);
    const left   = Math.max(target - n, 0);
    const color  = pct >= 100 ? '#00C851'
                 : pct >= 50  ? '#FFD700'
                 : '#58a6ff';

    return _section('📊 PHASE 1 — SIGNAL VALIDATION', `
      <div style="margin-bottom:10px;">
        <div style="display:flex;
          justify-content:space-between;
          font-size:12px;color:#8b949e;
          margin-bottom:6px;">
          <span>Resolved signals</span>
          <span style="color:${color};font-weight:700;">
            ${n} / ${target}
          </span>
        </div>
        <div style="background:#21262d;border-radius:4px;
          height:8px;overflow:hidden;">
          <div style="background:${color};height:8px;
            width:${pct}%;border-radius:4px;
            transition:width 0.3s ease;">
          </div>
        </div>
        <div style="font-size:10px;color:#555;
          margin-top:6px;">
          ${n === 0
            ? 'Collecting first outcomes — first signals exit Apr 14.'
            : left > 0
              ? `${left} more needed for statistical significance.`
              : '30+ resolved — win rate data is now valid.'}
        </div>
      </div>

      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        ${_miniStat('Signals Fired', d.total, '#c9d1d9')}
        ${_miniStat('Open Now',      d.open,  '#FFD700')}
        ${_miniStat('Resolved',      d.resolved, color)}
        ${_miniStat('Scan Days',     d.dates.length, '#8b949e')}
      </div>`);
  }

  function _miniStat(label, value, color) {
    return `
      <div style="flex:1;min-width:60px;
        background:#0d1117;border-radius:6px;
        padding:8px;text-align:center;">
        <div style="color:${color};font-size:16px;
          font-weight:700;">${value}</div>
        <div style="color:#555;font-size:9px;
          margin-top:2px;">${label}</div>
      </div>`;
  }

  function _renderFunnel(d) {
    const total = d.tookCount + d.rejCount;
    return _section('🔺 SIGNAL FUNNEL', `
      ${_statRow('Alpha scanner saw',
        total, 'total signals')}
      ${_statRow('Mini scanner passed',
        d.tookCount,
        `${_pct(d.tookCount, total)}% pass rate`,
        '#00C851')}
      ${_statRow('Mini scanner rejected',
        d.rejCount,
        `${_pct(d.rejCount, total)}% reject rate`,
        '#f85149')}
      <div style="margin-top:10px;
        border-top:1px solid #21262d;padding-top:10px;">
        <div style="font-size:11px;color:#555;
          margin-bottom:8px;letter-spacing:0.5px;">
          REJECTION REASONS
        </div>
        ${Object.entries(d.byRej)
          .sort((a, b) => b[1] - a[1])
          .map(([r, n]) => _bar(
            r.replace(/_/g, ' '),
            n, d.rejCount, '#f85149'))
          .join('')}
      </div>`);
  }

  function _renderByType(d) {
    const order  = ['UP_TRI', 'DOWN_TRI',
                    'BULL_PROXY', 'UP_TRI_SA',
                    'DOWN_TRI_SA'];
    const colors = {
      UP_TRI:      '#00C851',
      DOWN_TRI:    '#f85149',
      BULL_PROXY:  '#58a6ff',
      UP_TRI_SA:   '#00C851',
      DOWN_TRI_SA: '#f85149',
    };

    const rows = order
      .filter(t => d.byType[t])
      .map(t => _bar(
        t.replace(/_/g, ' '),
        d.byType[t], d.total,
        colors[t] || '#8b949e'));

    // Unknown types
    Object.keys(d.byType)
      .filter(t => !order.includes(t))
      .forEach(t => rows.push(
        _bar(t, d.byType[t], d.total, '#8b949e')));

    return _section('📌 BY SIGNAL TYPE', rows.join(''));
  }

  function _renderScoreDist(d) {
    const scores = Object.keys(d.byScore)
      .map(Number)
      .sort((a, b) => b - a);
    const maxCount = Math.max(
      ...Object.values(d.byScore), 1);

    const bars = scores.map(s =>
      _scoreBar(s, d.byScore[s], maxCount)).join('');

    return _section('🎯 SCORE DISTRIBUTION', `
      <div style="font-size:10px;color:#555;
        margin-bottom:10px;">
        TOOK signals only · higher score = stronger setup
      </div>
      ${bars}
      <div style="margin-top:8px;
        border-top:1px solid #21262d;padding-top:8px;
        display:flex;gap:16px;font-size:11px;">
        <span style="color:#555;">
          Bear bonus
          <b style="color:#ffd700;margin-left:4px;">
            ${d.bearCount}
          </b>
          <span style="color:#555;font-size:10px;">
            &nbsp;(${_pct(d.bearCount, d.total)}%)
          </span>
        </span>
      </div>`);
  }

  function _renderSectors(d) {
    const sorted = Object.entries(d.bySector)
      .sort((a, b) => b[1] - a[1]);

    return _section('🏭 BY SECTOR', sorted
      .map(([s, n]) =>
        _bar(s, n, d.total, '#58a6ff'))
      .join(''));
  }

  function _renderWinRate(d) {
    const n      = d.resolved;
    const target = RESOLVED_TARGET;
    const ready  = n >= target;

    // Header with overall WR if enough data
    let content = '';

    if (!ready) {
      content += `
        <div style="text-align:center;
          padding:16px 0;color:#555;">
          <div style="font-size:28px;margin-bottom:6px;">
            🔒
          </div>
          <div style="font-size:12px;">
            Win rate unlocks at ${target} resolved signals.
          </div>
          <div style="font-size:11px;color:#555;
            margin-top:4px;">
            Currently: ${n} resolved.
            ${target - n} more needed.
          </div>
        </div>

        <div style="border-top:1px solid #21262d;
          padding-top:10px;margin-top:4px;">
          ${_lockedRow('Overall win rate')}
          ${_lockedRow('UP_TRI win rate')}
          ${_lockedRow('DOWN_TRI win rate')}
          ${_lockedRow('BULL_PROXY win rate')}
          ${_lockedRow('Avg P&L per trade')}
          ${_lockedRow('Avg R multiple')}
        </div>`;
    } else {
      // Enough data — show it
      content += `
        <div style="display:flex;gap:8px;
          flex-wrap:wrap;margin-bottom:12px;">
          ${_miniStat('Win Rate',
            d.wrTotal + '%',
            d.wrTotal >= 60 ? '#00C851' : '#f85149')}
          ${_miniStat('Wins',   d.wins,   '#00C851')}
          ${_miniStat('Losses', d.losses, '#f85149')}
          ${_miniStat('Avg P&L',
            d.avgPnl != null ? d.avgPnl + '%' : '—',
            parseFloat(d.avgPnl) > 0 ? '#00C851' : '#f85149')}
        </div>

        <div style="border-top:1px solid #21262d;
          padding-top:10px;">
          <div style="font-size:11px;color:#555;
            margin-bottom:8px;">
            BY SIGNAL TYPE (min 5 resolved)
          </div>
          ${['UP_TRI', 'DOWN_TRI', 'BULL_PROXY']
            .filter(t => d.wrByType[t])
            .map(t => {
              const wr   = d.wrByType[t];
              const col  = wr.wr >= 60
                ? '#00C851' : '#f85149';
              return _statRow(
                t.replace(/_/g, ' '),
                wr.wr + '%',
                `${wr.n} resolved`,
                col);
            }).join('')}
        </div>`;
    }

    return _section('🏆 WIN RATE', content);
  }


  // ── MAIN RENDER ──────────────────────────────────────

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

    const d = _analyse(raw);

    el.innerHTML = `
      <div style="padding:12px 16px 80px;">

        <div style="font-size:11px;color:#555;
          letter-spacing:1px;margin-bottom:12px;">
          📈 STATS — PHASE 1 COLLECTION
        </div>

        ${_renderProgress(d)}
        ${_renderWinRate(d)}
        ${_renderByType(d)}
        ${_renderScoreDist(d)}
        ${_renderSectors(d)}
        ${_renderFunnel(d)}

      </div>`;
  };

})();
