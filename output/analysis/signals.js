/* ────────────────────────────────────────────────────────────
   signals.js — AN-02 Signals tab plugins (10 questions)
   
   Per-signal-type deep dives. Tests the backtest assumptions
   against live data:
   
     7.  uptri_scoreboard        — UP_TRI totals + MFE/MAE
     8.  uptri_by_age            — tests "ages 0–3 valid"
     9.  uptri_by_regime         — tests "Bear = highest conviction"
     10. downtri_scoreboard      — DOWN_TRI totals
     11. downtri_by_age          — tests "Age 0 only" rule
     12. downtri_mystery         — INV-01: backtest 87% vs live 18%
     13. bullproxy_scoreboard    — BULL_PROXY totals
     14. bullproxy_by_sector     — BP-01: the NBFC/Bank drag
     15. sa_performance          — second-attempt join with parent
     16. signal_comparison       — side-by-side bar chart
──────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  var AN  = window.AN;
  var REG = window.AN_PLUGINS.signals;
  var WR  = AN.wrFragment;
  var PNL = AN.avgPnlFragment;

  // ── ENGINE BRIDGE: expose the table renderer to plugins that
  //    use customRender and need to draw sub-tables. Pulled out
  //    of the closed-over engine via a lazy getter on window.
  //    This is the fix promised in the overview.js paste.
  if (!window.AN_RENDER_TABLE) {
    window.AN_RENDER_TABLE = function (result, plugin, body) {
      var wrap = document.createElement('div');
      wrap.className = 'table-wrap';
      var tbl = document.createElement('table');

      var thead = document.createElement('thead');
      var htr = document.createElement('tr');
      for (var i = 0; i < result.columns.length; i++) {
        var th = document.createElement('th');
        th.setAttribute('data-idx', i);
        th.textContent = prettify(result.columns[i]);
        htr.appendChild(th);
      }
      thead.appendChild(htr);
      tbl.appendChild(thead);

      var tbody = document.createElement('tbody');
      for (var r = 0; r < result.values.length; r++) {
        var row = result.values[r];
        var tr = document.createElement('tr');
        for (var c = 0; c < row.length; c++) {
          var v = row[c];
          var td = document.createElement('td');
          var col = String(result.columns[c]).toLowerCase();
          if (v === null || v === undefined) {
            td.className = 'null';
            td.textContent = '—';
          } else if (typeof v === 'number') {
            td.className = 'num';
            var tone = toneForCell(col, v);
            if (tone) td.className += ' ' + tone;
            td.textContent = formatForCol(col, v);
          } else {
            td.textContent = String(v);
          }
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }
      tbl.appendChild(tbody);
      wrap.appendChild(tbl);
      body.appendChild(wrap);
    };
  }

  function prettify(raw) {
    var map = {
      n: 'n', total: 'Total', wins: 'Wins', losses: 'Losses',
      flats: 'Flats', resolved: 'Resolved', wr_pct: 'WR %',
      avg_pnl: 'Avg P&L %', avg_r: 'Avg R',
      symbol: 'Symbol', signal: 'Signal', sector: 'Sector',
      regime: 'Regime', grade: 'Grade', age: 'Age', date: 'Date',
      entry_date: 'Entry date', day_n: 'Day',
      entry: 'Entry', stop: 'Stop', target: 'Target', score: 'Score',
      outcome: 'Outcome', pnl: 'P&L %', mae: 'MAE %', mfe: 'MFE %',
      parent_outcome: 'Parent outcome', sa_outcome: 'SA outcome',
      worst_trade: 'Worst trade %',
      avg_mfe: 'Avg MFE %', avg_mae: 'Avg MAE %'
    };
    if (map[raw]) return map[raw];
    return String(raw).replace(/_/g, ' ').replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
  }

  function formatForCol(col, v) {
    if (col === 'wr_pct') return v + '%';
    if (col === 'avg_pnl' || col === 'pnl' || col === 'pnl_pct' ||
        col === 'mae' || col === 'mfe' || col === 'avg_mfe' ||
        col === 'avg_mae' || col === 'worst_trade') {
      return (v >= 0 ? '+' : '') + v + '%';
    }
    return AN.fmtNum(v);
  }

  function toneForCell(col, v) {
    if (col === 'wr_pct') {
      if (v >= 60) return 'good';
      if (v < 40) return 'bad';
    }
    if (col === 'pnl' || col === 'pnl_pct' || col === 'avg_pnl' ||
        col === 'worst_trade') {
      if (v > 0) return 'good';
      if (v < 0) return 'bad';
    }
    return '';
  }

  // ── Shared helper: generic signal scoreboard ────────────
  function scoreboardSql(signalType) {
    return function (w) {
      return "SELECT COUNT(*) AS total, " + WR + ", " + PNL + ", " +
        "ROUND(AVG(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS') " +
        "              THEN mfe_pct END), 2) AS avg_mfe, " +
        "ROUND(AVG(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS') " +
        "              THEN mae_pct END), 2) AS avg_mae " +
        "FROM signals " + w + " AND signal = '" + signalType + "'";
    };
  }

  // ── 7. UP_TRI scoreboard ────────────────────────────────
  REG.push({
    id: 'uptri_scoreboard',
    tab: 'signals',
    order: 7,
    title: '🟢 UP_TRI scoreboard',
    subtitle: 'Your highest-edge signal — backtest says 87–88% WR',
    render: 'number_cards',
    sql: scoreboardSql('UP_TRI'),
    countFn: function (r) {
      var idx = r.columns.indexOf('resolved');
      return r.values.length && idx >= 0 ? r.values[0][idx] : 0;
    }
  });

  // ── 8. UP_TRI by age ────────────────────────────────────
  REG.push({
    id: 'uptri_by_age',
    tab: 'signals',
    order: 8,
    title: 'UP_TRI by age',
    subtitle: 'Backtest says ages 0–3 all valid. Does live data agree?',
    render: 'table',
    sql: function (w) {
      return "SELECT age, COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " AND signal = 'UP_TRI' AND age IS NOT NULL " +
        "GROUP BY age ORDER BY age";
    }
  });

  // ── 9. UP_TRI by regime ─────────────────────────────────
  REG.push({
    id: 'uptri_by_regime',
    tab: 'signals',
    order: 9,
    title: 'UP_TRI by regime',
    subtitle: 'Backtest says Bear = highest avg P&L. Still true live?',
    render: 'table',
    sql: function (w) {
      return "SELECT regime, COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " AND signal = 'UP_TRI' " +
        "AND regime IS NOT NULL AND regime != '' " +
        "GROUP BY regime ORDER BY n DESC";
    }
  });

  // ── 10. DOWN_TRI scoreboard ─────────────────────────────
  REG.push({
    id: 'downtri_scoreboard',
    tab: 'signals',
    order: 10,
    title: '🔴 DOWN_TRI scoreboard',
    subtitle: 'Backtest says 87–89% WR — live is running very different',
    render: 'number_cards',
    sql: scoreboardSql('DOWN_TRI'),
    countFn: function (r) {
      var idx = r.columns.indexOf('resolved');
      return r.values.length && idx >= 0 ? r.values[0][idx] : 0;
    }
  });

  // ── 11. DOWN_TRI by age ─────────────────────────────────
  REG.push({
    id: 'downtri_by_age',
    tab: 'signals',
    order: 11,
    title: 'DOWN_TRI by age',
    subtitle: 'Backtest says age 0 ONLY. Is the age filter correct live?',
    render: 'table',
    sql: function (w) {
      return "SELECT age, COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " AND signal = 'DOWN_TRI' AND age IS NOT NULL " +
        "GROUP BY age ORDER BY age";
    }
  });

  // ── 12. DOWN_TRI mystery (INV-01) ───────────────────────
  REG.push({
    id: 'downtri_mystery',
    tab: 'signals',
    order: 12,
    title: '🔍 DOWN_TRI backtest vs live (INV-01)',
    subtitle: 'Backtest 87% · Live 18% — every DOWN_TRI trade, ordered by date',
    render: 'table',
    sql: function (w) {
      return "SELECT " +
        "symbol, date, regime, sector, age, outcome, " +
        "ROUND(pnl_pct, 2) AS pnl, " +
        "ROUND(mae_pct, 2) AS mae " +
        "FROM signals " + w + " AND signal = 'DOWN_TRI' " +
        "ORDER BY date DESC";
    },
    minSampleSize: 0
  });

  // ── 13. BULL_PROXY scoreboard ───────────────────────────
  REG.push({
    id: 'bullproxy_scoreboard',
    tab: 'signals',
    order: 13,
    title: '🟡 BULL_PROXY scoreboard',
    subtitle: 'Support-rejection setups — ages 0–1 only per backtest',
    render: 'number_cards',
    sql: scoreboardSql('BULL_PROXY'),
    countFn: function (r) {
      var idx = r.columns.indexOf('resolved');
      return r.values.length && idx >= 0 ? r.values[0][idx] : 0;
    }
  });

  // ── 14. BULL_PROXY by sector (BP-01) ────────────────────
  REG.push({
    id: 'bullproxy_by_sector',
    tab: 'signals',
    order: 14,
    title: '🔍 BULL_PROXY by sector (BP-01)',
    subtitle: 'Is Bank/NBFC dragging BULL_PROXY down the same way it killed DOWN_TRI?',
    render: 'table',
    sql: function (w) {
      return "SELECT sector, COUNT(*) AS n, " + WR + ", " + PNL + ", " +
        "ROUND(MIN(pnl_pct), 2) AS worst_trade " +
        "FROM signals " + w + " AND signal = 'BULL_PROXY' " +
        "AND sector IS NOT NULL AND sector != '' " +
        "GROUP BY sector ORDER BY wr_pct ASC, n DESC";
    }
  });

  // ── 15. SA performance ──────────────────────────────────
  REG.push({
    id: 'sa_performance',
    tab: 'signals',
    order: 15,
    title: '🔁 Second-attempt (SA) performance',
    subtitle: 'Does SA after a losing parent outperform SA after a winning one?',
    render: 'table',
    emptyMessage: 'No second-attempt signals yet.',
    sql: function (w) {
      // SA has its own is_sa filter — don't apply the generic filter
      // (SA records may belong to different eras than the filter window).
      // We still exclude REJECTED and require TOOK.
      return "SELECT " +
        "COALESCE(parent.outcome, '(parent not found)') AS parent_outcome, " +
        "sa.outcome AS sa_outcome, " +
        "COUNT(*) AS n, " +
        "ROUND(AVG(sa.pnl_pct), 2) AS avg_pnl " +
        "FROM signals sa " +
        "LEFT JOIN signals parent ON parent.id = sa.sa_parent_id " +
        "WHERE sa.is_sa = 1 " +
        "  AND sa.action = 'TOOK' " +
        "  AND (sa.result IS NULL OR sa.result != 'REJECTED') " +
        "GROUP BY parent_outcome, sa_outcome " +
        "ORDER BY n DESC";
    }
  });

  // ── 16. Signal type comparison ──────────────────────────
  REG.push({
    id: 'signal_comparison',
    tab: 'signals',
    order: 16,
    title: '📊 Signal type comparison',
    subtitle: 'WR% side-by-side across UP_TRI / DOWN_TRI / BULL_PROXY',
    render: 'bar_chart',
    sql: function (w) {
      return "SELECT signal, COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " AND signal IS NOT NULL " +
        "GROUP BY signal ORDER BY signal";
    },
    config: {
      xField: 'signal',
      yField: 'wr_pct',
      yTitle: 'WR %',
      beginAtZero: true
    }
  });

  console.log('[AN] signals.js registered ' + REG.length + ' plugins');
})();
