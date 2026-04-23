/* ────────────────────────────────────────────────────────────
   segmentation.js — AN-02 Segmentation tab plugins (12 questions)
   
   Slicing the data by every dimension that matters:
   
     17. wr_by_sector           — WR + avg P&L per sector
     18. wr_by_sector_signal    — heatmap (14 sectors × 3 signals)
     19. wr_by_regime           — WR per market regime
     20. wr_by_regime_signal    — heatmap (3 regimes × 3 signals)
     21. wr_by_score            — WR per score bucket (scorer calibration)
     22. score_calibration      — scatter: score vs actual P&L
     23. wr_by_stock_regime     — stock regime vs market regime
     24. vol_confirm_impact     — does the +1 vol bonus earn its keep?
     25. rs_strong_impact       — same for RS-strong flag
     26. sec_leading_impact     — same for sector-leading flag
     27. grade_impact           — A / B / C performance split
     28. bonus_stack            — 0/1/2/3/4 quality bonuses × WR

   Segmentation tab auto-collapses all cards on load (set in
   engine's COLLAPSE_BY_DEFAULT) to reduce scroll fatigue.
   Tap a card header to expand.
──────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  var AN  = window.AN;
  var REG = window.AN_PLUGINS.segmentation;
  var WR  = AN.wrFragment;
  var PNL = AN.avgPnlFragment;

  // Shared WR-only fragment (no flats/resolved columns — leaner for heatmaps)
  var WR_ONLY =
    "ROUND(" +
    "  CAST(SUM(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN') THEN 1 ELSE 0 END) AS REAL) * 100.0 / " +
    "  NULLIF(SUM(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS') THEN 1 ELSE 0 END), 0), " +
    "  1) AS wr_pct";

  // ── 17. WR by sector ────────────────────────────────────
  REG.push({
    id: 'wr_by_sector',
    tab: 'segmentation',
    order: 17,
    title: '🏢 WR by sector',
    subtitle: 'Which sectors are earning / bleeding — sorted by sample size',
    render: 'table',
    sql: function (w) {
      return "SELECT sector, COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w +
        " AND sector IS NOT NULL AND sector != '' " +
        "GROUP BY sector ORDER BY n DESC";
    }
  });

  // ── 18. WR by sector × signal (heatmap) ─────────────────
  REG.push({
    id: 'wr_by_sector_signal',
    tab: 'segmentation',
    order: 18,
    title: '🗺️ WR by sector × signal (heatmap)',
    subtitle: 'Where each signal type works best. Gray cells = n<5. Red=0–40%, Gray=40–60%, Green=60–100%',
    render: 'heatmap',
    minSampleSize: 0,
    sql: function (w) {
      return "SELECT sector, signal, COUNT(*) AS n, " + WR_ONLY + " " +
        "FROM signals " + w +
        " AND sector IS NOT NULL AND sector != '' " +
        " AND signal IS NOT NULL " +
        "GROUP BY sector, signal ORDER BY sector, signal";
    },
    config: {
      rowKey: 'sector',
      colKey: 'signal',
      nField: 'n',
      valField: 'wr_pct'
    }
  });

  // ── 19. WR by regime ────────────────────────────────────
  REG.push({
    id: 'wr_by_regime',
    tab: 'segmentation',
    order: 19,
    title: '🌤️ WR by regime',
    subtitle: 'Bull / Bear / Choppy performance across all signal types',
    render: 'table',
    sql: function (w) {
      return "SELECT regime, COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w +
        " AND regime IS NOT NULL AND regime != '' " +
        "GROUP BY regime ORDER BY n DESC";
    }
  });

  // ── 20. WR by regime × signal (heatmap) ─────────────────
  REG.push({
    id: 'wr_by_regime_signal',
    tab: 'segmentation',
    order: 20,
    title: '🗺️ WR by regime × signal (heatmap)',
    subtitle: 'The scoring justification view. Expect Bear × UP_TRI = green; Bull × DOWN_TRI = red.',
    render: 'heatmap',
    minSampleSize: 0,
    sql: function (w) {
      return "SELECT regime, signal, COUNT(*) AS n, " + WR_ONLY + " " +
        "FROM signals " + w +
        " AND regime IS NOT NULL AND regime != '' " +
        " AND signal IS NOT NULL " +
        "GROUP BY regime, signal ORDER BY regime, signal";
    },
    config: {
      rowKey: 'regime',
      colKey: 'signal',
      nField: 'n',
      valField: 'wr_pct'
    }
  });

  // ── 21. WR by score bucket ──────────────────────────────
  REG.push({
    id: 'wr_by_score',
    tab: 'segmentation',
    order: 21,
    title: '🎯 WR by score bucket',
    subtitle: 'Does higher score = higher WR? If flat, the scorer is broken.',
    render: 'bar_chart',
    sql: function (w) {
      return "SELECT CAST(score AS INTEGER) AS score, COUNT(*) AS n, " +
        WR + ", " + PNL + " " +
        "FROM signals " + w + " AND score IS NOT NULL " +
        "GROUP BY CAST(score AS INTEGER) ORDER BY score";
    },
    config: {
      xField: 'score',
      yField: 'wr_pct',
      xTitle: 'Score',
      yTitle: 'WR %',
      beginAtZero: true
    }
  });

  // ── 22. Score vs P&L scatter ────────────────────────────
  REG.push({
    id: 'score_calibration',
    tab: 'segmentation',
    order: 22,
    title: '📈 Score vs P&L scatter',
    subtitle: 'Each dot = one resolved trade. Tight upward scatter = good calibration.',
    render: 'scatter',
    sql: function (w) {
      return "SELECT score, pnl_pct, signal, symbol " +
        "FROM signals " + w +
        " AND pnl_pct IS NOT NULL AND score IS NOT NULL " +
        " AND outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS','DAY6_FLAT') " +
        "ORDER BY score";
    },
    config: {
      xField: 'score',
      yField: 'pnl_pct',
      xTitle: 'Score',
      yTitle: 'P&L %',
      beginAtZero: false
    },
    minSampleSize: 0,
    countFn: function (r) { return r.values.length; }
  });

  // ── 23. WR by stock regime ──────────────────────────────
  REG.push({
    id: 'wr_by_stock_regime',
    tab: 'segmentation',
    order: 23,
    title: '📉 WR by stock regime',
    subtitle: 'Per-stock trend (Bull/Bear/Choppy) — different from market regime',
    render: 'table',
    emptyMessage: 'No stock_regime data on records. (Older signals may lack this field.)',
    sql: function (w) {
      return "SELECT " +
        "COALESCE(NULLIF(stock_regime, ''), '(missing)') AS stock_regime, " +
        "COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " " +
        "GROUP BY stock_regime ORDER BY n DESC";
    }
  });

  // ── 24. Volume confirmation impact ──────────────────────
  REG.push({
    id: 'vol_confirm_impact',
    tab: 'segmentation',
    order: 24,
    title: '🔊 Volume-confirmed impact',
    subtitle: 'Does the +1 vol_confirm bonus actually earn its keep?',
    render: 'table',
    sql: function (w) {
      return "SELECT " +
        "CASE WHEN vol_confirm = 1 THEN 'Vol confirmed' " +
        "     WHEN vol_confirm = 0 THEN 'No vol confirm' " +
        "     ELSE '(unknown)' END AS vol_flag, " +
        "COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " " +
        "GROUP BY vol_flag ORDER BY n DESC";
    }
  });

  // ── 25. RS-strong impact ────────────────────────────────
  REG.push({
    id: 'rs_strong_impact',
    tab: 'segmentation',
    order: 25,
    title: '💪 RS-strong impact',
    subtitle: 'Does the relative-strength bonus pay off?',
    render: 'table',
    sql: function (w) {
      return "SELECT " +
        "CASE WHEN rs_strong = 1 THEN 'RS strong' " +
        "     WHEN rs_strong = 0 THEN 'RS not strong' " +
        "     ELSE '(unknown)' END AS rs_flag, " +
        "COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " " +
        "GROUP BY rs_flag ORDER BY n DESC";
    }
  });

  // ── 26. Sector-leading impact ───────────────────────────
  REG.push({
    id: 'sec_leading_impact',
    tab: 'segmentation',
    order: 26,
    title: '🔝 Sector-leading impact',
    subtitle: 'Does being in a leading sector actually help?',
    render: 'table',
    sql: function (w) {
      return "SELECT " +
        "CASE WHEN sec_leading = 1 THEN 'Sector leading' " +
        "     WHEN sec_leading = 0 THEN 'Sector not leading' " +
        "     ELSE '(unknown)' END AS sec_flag, " +
        "COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " " +
        "GROUP BY sec_flag ORDER BY n DESC";
    }
  });

  // ── 27. Grade A/B/C impact ──────────────────────────────
  REG.push({
    id: 'grade_impact',
    tab: 'segmentation',
    order: 27,
    title: '🏆 Grade A / B / C impact',
    subtitle: 'Does stock grade predict signal outcome?',
    render: 'table',
    sql: function (w) {
      return "SELECT grade, COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " AND grade IS NOT NULL AND grade != '' " +
        "GROUP BY grade ORDER BY grade";
    }
  });

  // ── 28. Quality bonus stacking ──────────────────────────
  REG.push({
    id: 'bonus_stack',
    tab: 'segmentation',
    order: 28,
    title: '🧱 Quality bonus stacking',
    subtitle: 'Signals with 0 vs 1 vs 2 vs 3 vs 4 quality bonuses. Rising WR = bonuses compound.',
    render: 'bar_chart',
    sql: function (w) {
      return "SELECT " +
        "(COALESCE(vol_confirm, 0) + COALESCE(rs_strong, 0) + " +
        " COALESCE(sec_leading, 0) + COALESCE(grade_A, 0)) AS bonus_count, " +
        "COUNT(*) AS n, " + WR + ", " + PNL + " " +
        "FROM signals " + w + " " +
        "GROUP BY bonus_count ORDER BY bonus_count";
    },
    config: {
      xField: 'bonus_count',
      yField: 'wr_pct',
      xTitle: 'Quality bonuses stacked',
      yTitle: 'WR %',
      beginAtZero: true
    }
  });

  console.log('[AN] segmentation.js registered ' + REG.length + ' plugins');
})();
