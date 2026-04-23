/* ────────────────────────────────────────────────────────────
   overview.js — AN-02 Overview tab plugins (6 questions)
   
   The 30-second health check. Opens by default.
   
   1. scoreboard     — total resolved, W/L/Flat, WR, avg P&L, avg R
   2. whats_open     — TRADING-DAY aware, color-coded exit urgency
   3. todays_action  — signals logged today
   4. last_7_days    — bar chart: signals per day
   5. month_vs_month — this month vs last month side-by-side
   6. edge_trend     — rolling-20 WR and P&L trend
   
   UPDATE 2026-04-24 (3 AM fix):
     whats_open rewritten as custom render — trading-day math,
     summary bar (exit today / exit tomorrow / active / new),
     color-coded Day column. Replaces calendar-day julianday
     that looked alarming at 3 AM ("Day 7!") when signals were
     actually on-schedule.
──────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  var AN  = window.AN;
  var REG = window.AN_PLUGINS.overview;
  var TODAY = AN.today;
  var WR  = AN.wrFragment;
  var PNL = AN.avgPnlFragment;

  // ── Trading-day SQL fragment ──────────────────────────
  // Given a `date` column (detection date) and TODAY constant,
  // returns the number of trading days elapsed (ignoring Sat/Sun).
  // NOTE: does NOT account for NSE public holidays. For a 0–6 day
  // window, holiday drift is tolerable and never misleading by more
  // than 1 day. If holiday-accurate math is needed later, extend
  // this with a lookup against data/nse_holidays.json.
  //
  // Math: calendar_days - weekend_days_in_range.
  // Validated against all 7 entry weekdays × 10 target offsets.
  var TRADING_DAYS_EXPR =
    "(" +
      "CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) " +
      "- (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) / 7) * 2 " +
      "- CASE " +
        "WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) = 0 THEN 0 " +
        "ELSE " +
          "CASE CAST(strftime('%w', date) AS INTEGER) " +
            "WHEN 0 THEN (CASE WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 6 THEN 1 ELSE 0 END) " +
            "WHEN 1 THEN (CASE WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 6 THEN 2 " +
                             "WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 5 THEN 1 ELSE 0 END) " +
            "WHEN 2 THEN (CASE WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 5 THEN 2 " +
                             "WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 4 THEN 1 ELSE 0 END) " +
            "WHEN 3 THEN (CASE WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 4 THEN 2 " +
                             "WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 3 THEN 1 ELSE 0 END) " +
            "WHEN 4 THEN (CASE WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 3 THEN 2 " +
                             "WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 2 THEN 1 ELSE 0 END) " +
            "WHEN 5 THEN (CASE WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 2 THEN 2 " +
                             "WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 1 THEN 1 ELSE 0 END) " +
            "WHEN 6 THEN (CASE WHEN (CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) % 7) >= 1 THEN 1 ELSE 0 END) " +
          "END " +
      "END " +
    ")";

  // Day-to-status mapping
  function statusForDay(d) {
    if (d >= 7)  return { label: 'OVERDUE',    color: '#f85149', bg: 'rgba(248,81,73,0.15)',  border: '#f85149' };
    if (d === 6) return { label: 'EXIT TODAY', color: '#f0883e', bg: 'rgba(240,136,62,0.15)', border: '#d97706' };
    if (d === 5) return { label: 'EXIT TMRW',  color: '#d29922', bg: 'rgba(210,153,34,0.10)', border: '#bb8009' };
    if (d >= 1)  return { label: 'ACTIVE',     color: '#3fb950', bg: 'transparent',           border: 'transparent' };
    return            { label: 'NEW',          color: '#8b949e', bg: 'transparent',           border: 'transparent' };
  }

  // ── 1. System scoreboard ────────────────────────────────
  REG.push({
    id: 'scoreboard',
    tab: 'overview',
    order: 1,
    title: '📊 System scoreboard',
    subtitle: 'The 30-second health check',
    render: 'number_cards',
    sql: function (w) {
      return "SELECT " +
        "COUNT(*) AS total, " + WR + ", " + PNL + ", " +
        "ROUND(AVG(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS') " +
        "              THEN r_multiple END), 2) AS avg_r " +
        "FROM signals " + w;
    },
    countFn: function (r) {
      if (!r.values.length) return 0;
      var idx = r.columns.indexOf('resolved');
      return idx >= 0 ? r.values[0][idx] : r.values[0][0];
    }
  });

  // ── 2. What's open right now ────────────────────────────
  //    TRADING-DAY aware. Summary bar + color-coded Day column.
  REG.push({
    id: 'whats_open',
    tab: 'overview',
    order: 2,
    title: '🎯 What\'s open right now',
    subtitle: 'Day = trading day of holding (0 = new, 6 = exits at open today)',
    render: 'custom',
    minSampleSize: 0,
    emptyMessage: 'No open positions.',
    sql: function (w) {
      return "SELECT " +
        "symbol, signal, date AS detected, " +
        TRADING_DAYS_EXPR + " AS day_n, " +
        "regime, sector, grade, " +
        "ROUND(entry, 2) AS entry, ROUND(stop, 2) AS stop, " +
        "ROUND(target, 2) AS target, score " +
        "FROM signals " + w +
        " AND (outcome IS NULL OR outcome='OPEN') " +
        "ORDER BY day_n DESC, date ASC, score DESC";
    },
    customRender: function (result, body) {
      if (!result.values.length) {
        var empty = document.createElement('div');
        empty.className = 'empty-state';
        empty.textContent = 'No open positions.';
        body.appendChild(empty);
        return;
      }

      var cols = result.columns;
      var dayIdx = cols.indexOf('day_n');

      // ── Build summary counts ──
      var counts = { overdue: 0, today: 0, tomorrow: 0, active: 0, newly: 0, total: result.values.length };
      for (var i = 0; i < result.values.length; i++) {
        var d = result.values[i][dayIdx];
        if (d === null || d === undefined) continue;
        if (d >= 7)      counts.overdue++;
        else if (d === 6) counts.today++;
        else if (d === 5) counts.tomorrow++;
        else if (d >= 1)  counts.active++;
        else              counts.newly++;
      }

      // ── Summary bar ──
      var summary = document.createElement('div');
      summary.style.cssText =
        'display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));' +
        'gap:8px;margin-bottom:14px;';

      function card(label, count, color) {
        return '<div style="padding:10px;background:#161b22;border:1px solid #21262d;' +
               'border-radius:6px;border-left:3px solid ' + color + ';">' +
               '<div style="font-size:20px;font-weight:600;color:' + color + ';' +
               'font-variant-numeric:tabular-nums;">' + count + '</div>' +
               '<div style="font-size:11px;color:#8b949e;margin-top:2px;' +
               'text-transform:uppercase;letter-spacing:0.5px;">' + label + '</div>' +
               '</div>';
      }

      var summaryHtml = '';
      summaryHtml += card('Open total', counts.total, '#c9d1d9');
      if (counts.overdue > 0) summaryHtml += card('⚠ Overdue', counts.overdue, '#f85149');
      summaryHtml += card('Exit today', counts.today, '#f0883e');
      summaryHtml += card('Exit tomorrow', counts.tomorrow, '#d29922');
      summaryHtml += card('Active', counts.active, '#3fb950');
      if (counts.newly > 0) summaryHtml += card('Just detected', counts.newly, '#58a6ff');

      summary.innerHTML = summaryHtml;
      body.appendChild(summary);

      // ── Table with colored day_n column ──
      var wrap = document.createElement('div');
      wrap.className = 'table-wrap';
      var tbl = document.createElement('table');

      // Header
      var thead = document.createElement('thead');
      var htr = document.createElement('tr');
      var headerLabels = {
        symbol: 'Symbol', signal: 'Signal', detected: 'Detected',
        day_n: 'Day', regime: 'Regime', sector: 'Sector', grade: 'Grade',
        entry: 'Entry', stop: 'Stop', target: 'Target', score: 'Score'
      };
      for (var h = 0; h < cols.length; h++) {
        var th = document.createElement('th');
        th.textContent = headerLabels[cols[h]] || cols[h];
        htr.appendChild(th);
      }
      thead.appendChild(htr);
      tbl.appendChild(thead);

      // Body rows
      var tbody = document.createElement('tbody');
      for (var r = 0; r < result.values.length; r++) {
        var row = result.values[r];
        var tr = document.createElement('tr');
        for (var c = 0; c < row.length; c++) {
          var v = row[c];
          var col = cols[c];
          var td = document.createElement('td');

          if (col === 'day_n' && typeof v === 'number') {
            // Color-coded Day cell
            var st = statusForDay(v);
            td.className = 'num';
            td.style.cssText =
              'background:' + st.bg + ';' +
              'color:' + st.color + ';' +
              'font-weight:600;' +
              (st.border !== 'transparent' ? 'border-left:3px solid ' + st.border + ';' : '') +
              'text-align:center;';
            td.innerHTML =
              String(v) +
              '<span style="display:block;font-size:9px;font-weight:400;opacity:0.85;' +
              'text-transform:uppercase;letter-spacing:0.3px;margin-top:1px;">' +
              st.label + '</span>';
          } else if (v === null || v === undefined) {
            td.className = 'null';
            td.textContent = '—';
          } else if (typeof v === 'number') {
            td.className = 'num';
            td.textContent = AN.fmtNum(v);
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
    }
  });

  // ── 3. Today's action ───────────────────────────────────
  REG.push({
    id: 'todays_action',
    tab: 'overview',
    order: 3,
    title: '⚡ Today\'s action',
    subtitle: 'Signals detected today + positions exiting today (D6)',
    render: 'custom',
    minSampleSize: 0,
    sql: function (w) {
      return "SELECT symbol, signal, score, regime, sector " +
             "FROM signals " + w + " AND date = '" + TODAY + "' " +
             "ORDER BY score DESC";
    },
    customRender: function (result, body) {
      var h1 = document.createElement('div');
      h1.style.cssText = 'font-size:12px;color:#8b949e;margin-bottom:6px;font-weight:600;';
      h1.textContent = '📝 New signals today (' + (result.values.length) + ')';
      body.appendChild(h1);

      if (result.values.length === 0) {
        var e1 = document.createElement('div');
        e1.className = 'empty-state';
        e1.textContent = 'No new signals today yet.';
        body.appendChild(e1);
      } else {
        var pseudoPlugin = { id: 'todays_new', render: 'table' };
        (window.AN_RENDER_TABLE || defaultRenderTable)(result, pseudoPlugin, body);
      }

      var h2 = document.createElement('div');
      h2.style.cssText = 'font-size:12px;color:#8b949e;margin:14px 0 6px;font-weight:600;';
      body.appendChild(h2);

      try {
        var exitsSql =
          AN.filterWhere(getCurrentFilter()) + " AND (outcome IS NULL OR outcome='OPEN') " +
          "AND " + TRADING_DAYS_EXPR + " >= 6";
        var exitsResult = AN.query(
          "SELECT symbol, signal, date AS detected, " +
          TRADING_DAYS_EXPR + " AS day_n, " +
          "ROUND(entry, 2) AS entry, ROUND(stop, 2) AS stop, ROUND(target, 2) AS target " +
          "FROM signals " + exitsSql + " ORDER BY date ASC");

        h2.textContent = '🚪 Exits due today at open (' + exitsResult.values.length + ')';

        if (exitsResult.values.length === 0) {
          var e2 = document.createElement('div');
          e2.className = 'empty-state';
          e2.textContent = 'No exits due today.';
          body.appendChild(e2);
        } else {
          var pseudo2 = { id: 'todays_exits', render: 'table' };
          (window.AN_RENDER_TABLE || defaultRenderTable)(exitsResult, pseudo2, body);
        }
      } catch (e) {
        console.error('[overview] exits query failed', e);
      }
    }
  });

  // ── 4. Last 7 scan days ─────────────────────────────────
  REG.push({
    id: 'last_7_days',
    tab: 'overview',
    order: 4,
    title: '📅 Last 7 scan days',
    subtitle: 'Signals detected per day, stacked by signal type',
    render: 'bar_chart',
    sql: function (w) {
      return "SELECT date, signal, COUNT(*) AS n " +
        "FROM signals " + w +
        " AND date >= date('" + TODAY + "', '-7 days') " +
        "GROUP BY date, signal ORDER BY date ASC";
    },
    config: {
      xField: 'date',
      yField: 'n',
      seriesField: 'signal',
      stacked: true,
      yTitle: 'Signals',
      xTitle: null
    },
    minSampleSize: 0
  });

  // ── 5. This month vs last month ─────────────────────────
  REG.push({
    id: 'month_vs_month',
    tab: 'overview',
    order: 5,
    title: '📆 This month vs last month',
    subtitle: 'Resolved-trades comparison — is the edge trending up or down?',
    render: 'table',
    sql: function (w) {
      return "SELECT " +
        "CASE " +
        "  WHEN strftime('%Y-%m', date) = strftime('%Y-%m', '" + TODAY + "') THEN 'This month' " +
        "  WHEN strftime('%Y-%m', date) = strftime('%Y-%m', date('" + TODAY + "', '-1 month')) THEN 'Last month' " +
        "  ELSE 'Older' " +
        "END AS period, " +
        "COUNT(*) AS n, " + WR + ", " + PNL + ", " +
        "ROUND(MAX(pnl_pct), 2) AS best, " +
        "ROUND(MIN(pnl_pct), 2) AS worst " +
        "FROM signals " + w +
        " AND date >= date('" + TODAY + "', '-2 months') " +
        "GROUP BY period ORDER BY " +
        "CASE period WHEN 'This month' THEN 1 WHEN 'Last month' THEN 2 ELSE 3 END";
    },
    minSampleSize: 0
  });

  // ── 6. Edge trend — rolling 20 ──────────────────────────
  REG.push({
    id: 'edge_trend',
    tab: 'overview',
    order: 6,
    title: '📈 Edge trend (rolling 20)',
    subtitle: 'Rolling-20-trade WR% and avg P&L% over time — edge decay check',
    render: 'line_chart',
    sql: function (w) {
      return "WITH resolved AS ( " +
        "  SELECT date, outcome, pnl_pct, " +
        "         ROW_NUMBER() OVER (ORDER BY outcome_date, id) AS rn " +
        "  FROM signals " + w +
        "   AND outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS') " +
        ") " +
        "SELECT r1.rn AS trade_num, r1.date, " +
        "  ROUND(AVG(CASE WHEN r2.outcome IN ('TARGET_HIT','DAY6_WIN') " +
        "                 THEN 100.0 ELSE 0.0 END), 1) AS rolling_wr, " +
        "  ROUND(AVG(r2.pnl_pct), 2) AS rolling_pnl " +
        "FROM resolved r1 " +
        "JOIN resolved r2 ON r2.rn BETWEEN MAX(1, r1.rn - 19) AND r1.rn " +
        "GROUP BY r1.rn, r1.date ORDER BY r1.rn";
    },
    config: {
      xField: 'trade_num',
      yField: 'rolling_wr',
      xTitle: 'Resolved trade #',
      yTitle: 'Rolling 20 WR %',
      beginAtZero: false
    },
    minSampleSize: 0
  });

  // ── Local helpers ──────────────────────────────────────
  function getCurrentFilter() {
    var active = document.querySelector('.filter-group button.active');
    return active ? active.getAttribute('data-filter') : 'live';
  }

  function defaultRenderTable(result, plugin, body) {
    var pre = document.createElement('pre');
    pre.style.fontSize = '11px';
    pre.textContent = JSON.stringify(result, null, 2);
    body.appendChild(pre);
  }

  console.log('[AN] overview.js registered ' + REG.length + ' plugins');
})();
