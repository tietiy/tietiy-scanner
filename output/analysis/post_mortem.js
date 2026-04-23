/* ────────────────────────────────────────────────────────────
   post_mortem.js — AN-02 Post-mortem tab plugins (8 questions)

   Why things died + data health:

     29. all_stopouts           — every STOPPED trade with context
     30. stops_by_day           — Day 1 stops vs Day 6 stops (timing)
     31. mae_distribution       — how deep do losers go?
     32. mfe_distribution       — how much gain did we see? (gave-back check)
     33. failures_by_reason     — grouped failure_reason strings
     34. gap_invalidated        — entry_valid=false signals
     35. sector_stop_clusters   — which sectors are bleeding?
     36. data_quality_audit     — the DQ-01 reconciliation view
──────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  var AN  = window.AN;
  var REG = window.AN_PLUGINS.post_mortem;
  var TODAY = AN.today;

  // ── 29. All stop-outs ───────────────────────────────────
  REG.push({
    id: 'all_stopouts',
    tab: 'post_mortem',
    order: 29,
    title: '🛑 All stop-outs',
    subtitle: 'Every STOPPED trade with entry, stop, exit, MAE, and failure reason',
    render: 'table',
    emptyMessage: 'No stop-outs in the current filter. Clean slate.',
    sql: function (w) {
      return "SELECT " +
        "date, symbol, signal, sector, regime, " +
        "ROUND(entry, 2) AS entry, " +
        "ROUND(stop, 2) AS stop, " +
        "ROUND(outcome_price, 2) AS exit_price, " +
        "ROUND(pnl_pct, 2) AS pnl, " +
        "ROUND(mae_pct, 2) AS mae, " +
        "failure_reason " +
        "FROM signals " + w + " AND outcome = 'STOP_HIT' " +
        "ORDER BY date DESC";
    },
    minSampleSize: 0
  });

  // ── 30. Stops by exit day ───────────────────────────────
  REG.push({
    id: 'stops_by_day',
    tab: 'post_mortem',
    order: 30,
    title: '📅 Stops by exit day',
    subtitle: 'Day 1 stops = signal-timing issue. Day 5–6 stops = pattern failed slowly.',
    render: 'bar_chart',
    sql: function (w) {
      return "SELECT " +
        "CAST(julianday(outcome_date) - julianday(date) AS INTEGER) AS days_to_stop, " +
        "COUNT(*) AS n " +
        "FROM signals " + w +
        " AND outcome = 'STOP_HIT' " +
        " AND outcome_date IS NOT NULL AND date IS NOT NULL " +
        "GROUP BY days_to_stop ORDER BY days_to_stop";
    },
    config: {
      xField: 'days_to_stop',
      yField: 'n',
      xTitle: 'Days from entry to stop',
      yTitle: 'Number of stops',
      beginAtZero: true
    }
  });

  // ── 31. MAE distribution ────────────────────────────────
  REG.push({
    id: 'mae_distribution',
    tab: 'post_mortem',
    order: 31,
    title: '📉 MAE distribution',
    subtitle: 'How deep did trades go against you? Bucketed in 0.5% increments.',
    render: 'histogram',
    sql: function (w) {
      return "SELECT " +
        "CAST(mae_pct / 0.5 AS INTEGER) * 0.5 AS mae_bucket, " +
        "COUNT(*) AS n " +
        "FROM signals " + w +
        " AND mae_pct IS NOT NULL " +
        " AND outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS','DAY6_FLAT') " +
        "GROUP BY mae_bucket ORDER BY mae_bucket";
    },
    config: {
      xField: 'mae_bucket',
      yField: 'n',
      xTitle: 'MAE bucket (%)',
      yTitle: 'Signals',
      beginAtZero: true
    }
  });

  // ── 32. MFE distribution ────────────────────────────────
  REG.push({
    id: 'mfe_distribution',
    tab: 'post_mortem',
    order: 32,
    title: '📈 MFE distribution',
    subtitle: 'Peak favorable move per trade. Compare with P&L distribution — gap = "gave back" problem.',
    render: 'histogram',
    sql: function (w) {
      return "SELECT " +
        "CAST(mfe_pct / 0.5 AS INTEGER) * 0.5 AS mfe_bucket, " +
        "COUNT(*) AS n " +
        "FROM signals " + w +
        " AND mfe_pct IS NOT NULL " +
        " AND outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS','DAY6_FLAT') " +
        "GROUP BY mfe_bucket ORDER BY mfe_bucket";
    },
    config: {
      xField: 'mfe_bucket',
      yField: 'n',
      xTitle: 'MFE bucket (%)',
      yTitle: 'Signals',
      beginAtZero: true
    }
  });

  // ── 33. Failures by reason ──────────────────────────────
  REG.push({
    id: 'failures_by_reason',
    tab: 'post_mortem',
    order: 33,
    title: '🏷️ Failures by reason',
    subtitle: 'Groups losing trades by the failure_reason classifier. Which patterns repeat?',
    render: 'table',
    emptyMessage: 'No losing trades in the current filter yet.',
    sql: function (w) {
      return "SELECT " +
        "COALESCE(failure_reason, '(no reason recorded)') AS reason, " +
        "COUNT(*) AS n, " +
        "ROUND(AVG(mae_pct), 2) AS avg_mae, " +
        "ROUND(AVG(pnl_pct), 2) AS avg_pnl " +
        "FROM signals " + w +
        " AND outcome IN ('STOP_HIT','DAY6_LOSS') " +
        "GROUP BY reason ORDER BY n DESC";
    }
  });

  // ── 34. Gap-invalidated signals ─────────────────────────
  REG.push({
    id: 'gap_invalidated',
    tab: 'post_mortem',
    order: 34,
    title: '⚠️ Gap-invalidated signals',
    subtitle: 'Signals where 9:15 gap > entry_valid threshold. The cost of the gap filter.',
    render: 'table',
    emptyMessage: 'No gap-invalidated signals in the current filter.',
    sql: function (w) {
      return "SELECT " +
        "date, symbol, signal, sector, " +
        "ROUND(entry, 2) AS planned_entry, " +
        "ROUND(actual_open, 2) AS actual_open, " +
        "ROUND(gap_pct, 2) AS gap_pct, " +
        "outcome, " +
        "ROUND(pnl_pct, 2) AS pnl " +
        "FROM signals " + w + " AND entry_valid = 0 " +
        "ORDER BY ABS(COALESCE(gap_pct, 0)) DESC";
    },
    minSampleSize: 0
  });

  // ── 35. Sector stop clusters ────────────────────────────
  REG.push({
    id: 'sector_stop_clusters',
    tab: 'post_mortem',
    order: 35,
    title: '🩸 Sector stop clusters',
    subtitle: 'Which sectors are bleeding? Stop rate + avg MAE per sector.',
    render: 'table',
    sql: function (w) {
      return "SELECT " +
        "sector, " +
        "SUM(CASE WHEN outcome = 'STOP_HIT' THEN 1 ELSE 0 END) AS stops, " +
        "COUNT(*) AS total, " +
        "ROUND(" +
        "  CAST(SUM(CASE WHEN outcome = 'STOP_HIT' THEN 1 ELSE 0 END) AS REAL) * 100.0 / " +
        "  NULLIF(COUNT(*), 0)," +
        "  1) AS stop_rate_pct, " +
        "ROUND(AVG(CASE WHEN outcome = 'STOP_HIT' THEN mae_pct END), 2) AS avg_stop_mae " +
        "FROM signals " + w +
        " AND sector IS NOT NULL AND sector != '' " +
        "GROUP BY sector HAVING stops > 0 " +
        "ORDER BY stop_rate_pct DESC";
    }
  });

  // ── 36. Data quality audit ──────────────────────────────
  // NOTE: This card intentionally IGNORES the global filter.
  // Data-quality questions ("how many rejected records?",
  // "how many missing v5 fields?") must count the whole DB,
  // not just what the filter lets through. Using filterWhere()
  // here would hide exactly the drift we're trying to find.
  REG.push({
    id: 'data_quality_audit',
    tab: 'post_mortem',
    order: 36,
    title: '🔧 Data quality audit',
    subtitle: 'Unfiltered reconciliation view. Answers DQ-01: where is the active-count drift?',
    render: 'number_cards',
    minSampleSize: 0,
    sql: function (_w) {
      // Explicitly NOT using _w — we want the whole DB visible here.
      return "SELECT " +
        "(SELECT COUNT(*) FROM signals) AS total_records, " +
        "(SELECT COUNT(*) FROM signals " +
        "   WHERE action='TOOK' AND (outcome IS NULL OR outcome='OPEN')) AS active_open, " +
        "(SELECT COUNT(*) FROM signals WHERE result='REJECTED') AS rejected, " +
        "(SELECT COUNT(*) FROM signals " +
        "   WHERE data_quality='recovery_close_fallback') AS recovery_flagged, " +
        "(SELECT COUNT(*) FROM signals " +
        "   WHERE data_quality='backfill' OR generation=0) AS backfill_records, " +
        "(SELECT COUNT(*) FROM signals WHERE id LIKE '%-REJ') AS rej_records, " +
        "(SELECT COUNT(*) FROM signals " +
        "   WHERE rs_strong IS NULL OR sec_leading IS NULL OR grade_A IS NULL) AS missing_v5_fields, " +
        "(SELECT COUNT(*) FROM signals WHERE entry_valid = 0) AS gap_invalidated";
    }
  });

  console.log('[AN] post_mortem.js registered ' + REG.length + ' plugins');
})();
