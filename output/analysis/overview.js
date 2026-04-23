/* ────────────────────────────────────────────────────────────
   overview.js — AN-02 Overview tab plugins (6 questions)
   
   The 30-second health check. Opens by default.
   
   1. scoreboard     — total resolved, W/L/Flat, WR, avg P&L, avg R
   2. whats_open     — table of current open positions
   3. todays_action  — signals logged today
   4. last_7_days    — bar chart: signals per day
   5. month_vs_month — this month vs last month side-by-side
   6. edge_trend     — rolling-20 WR and P&L trend
   
   Each plugin reads window.AN.filterWhere() + window.AN.wrFragment
   so global filter changes propagate automatically.
──────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  var AN  = window.AN;
  var REG = window.AN_PLUGINS.overview;
  var TODAY = AN.today;
  var WR  = AN.wrFragment;
  var PNL = AN.avgPnlFragment;

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
  REG.push({
    id: 'whats_open',
    tab: 'overview',
    order: 2,
    title: '🎯 What\'s open right now',
    subtitle: 'Active positions sorted by entry date (oldest first — closest to D6 exit)',
    render: 'table',
    emptyMessage: 'No open positions right now.',
    sql: function (w) {
      return "SELECT " +
        "symbol, signal, date AS entry_date, " +
        "CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) AS day_n, " +
        "regime, sector, grade, " +
        "ROUND(entry, 2) AS entry, ROUND(stop, 2) AS stop, " +
        "ROUND(target, 2) AS target, score " +
        "FROM signals " + w + " AND (outcome IS NULL OR outcome='OPEN') " +
        "ORDER BY date ASC";
    },
    // Small-n warning doesn't apply here — it's a list, not a stat.
    minSampleSize: 0
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
    // We need two tables — one for today's signals, one for today's exits.
    // Use a custom renderer that fires two queries.
    sql: function (w) {
      // Dummy — real work is in customRender. Still defined so the
      // engine can run it and the footer shows something sensible.
      return "SELECT symbol, signal, score, regime, sector " +
             "FROM signals " + w + " AND date = '" + TODAY + "' " +
             "ORDER BY score DESC";
    },
    customRender: function (result, body) {
      // Section 1: today's new signals (from the default SQL)
      var h1 = document.createElement('div');
      h1.style.cssText = 'font-size:12px;color:#8b949e;margin-bottom:6px;font-weight:600;';
      h1.textContent = '📝 New signals today (' + (result.values.length) + ')';
      body.appendChild(h1);

      if (result.values.length === 0) {
        var e1 = document.createElement('div');
        e1.className = 'empty-state';
        e1.textContent = 'No new signals today.';
        body.appendChild(e1);
      } else {
        var pseudoPlugin = { id: 'todays_new', render: 'table' };
        (window.AN_RENDER_TABLE || defaultRenderTable)(result, pseudoPlugin, body);
      }

      // Section 2: exits due today (separate query)
      var h2 = document.createElement('div');
      h2.style.cssText = 'font-size:12px;color:#8b949e;margin:14px 0 6px;font-weight:600;';
      body.appendChild(h2);

      try {
        var exitsSql =
          AN.filterWhere(getCurrentFilter()) + " AND (outcome IS NULL OR outcome='OPEN') " +
          "AND CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) >= 5";
        var exitsResult = AN.query(
          "SELECT symbol, signal, date AS entry_date, " +
          "CAST(julianday('" + TODAY + "') - julianday(date) AS INTEGER) AS day_n, " +
          "ROUND(entry, 2) AS entry, ROUND(stop, 2) AS stop, ROUND(target, 2) AS target " +
          "FROM signals " + exitsSql + " ORDER BY date ASC");

        h2.textContent = '🚪 Exits due today/soon (' + exitsResult.values.length + ')';

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
      // Use a CTE + window function for cleaner SQL.
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
    // n here is trade count, not a bucket — ignore small-n banner
    minSampleSize: 0
  });

  // ── Local helpers — needed because customRender runs outside
  //    the standard engine flow but still needs access to the
  //    table renderer. We re-expose it lazily via a noop fallback.
  function getCurrentFilter() {
    var active = document.querySelector('.filter-group button.active');
    return active ? active.getAttribute('data-filter') : 'live';
  }

  function defaultRenderTable(result, plugin, body) {
    // Minimal fallback — should never be reached if engine loaded properly.
    var pre = document.createElement('pre');
    pre.style.fontSize = '11px';
    pre.textContent = JSON.stringify(result, null, 2);
    body.appendChild(pre);
  }

  console.log('[AN] overview.js registered ' + REG.length + ' plugins');
})();
