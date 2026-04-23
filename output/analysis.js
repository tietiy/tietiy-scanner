/* ────────────────────────────────────────────────────────────
   analysis.js — AN-02 Engine
   
   Core engine for the TIE TIY Analysis page. Plugin architecture:
   bundle files (overview.js, signals.js, etc.) push question
   definitions onto window.AN_PLUGINS[tab]. This engine reads the
   merged registry, wires up tabs, filter bar, and renders every
   card on the fly.

   No coupling to specific questions. Add a question = push onto
   the registry. Engine renders it automatically based on its
   `render` type.

   Boot sequence:
     1. Wait for sql.js ready
     2. Fetch signal_history.json
     3. Build in-memory SQLite
     4. Read window.AN_PLUGINS, render every tab's cards
     5. Wire filter bar + tab strip + auto-refresh on filter change

   Render types supported:
     - number_cards : big number grid
     - table        : sortable, CSV-exportable
     - bar_chart    : Chart.js vertical bars
     - line_chart   : Chart.js line
     - scatter      : Chart.js scatter
     - histogram    : Chart.js bars (distribution)
     - heatmap      : HTML table with color gradient
     - custom       : plugin supplies its own renderer

   Every card renders: title, subtitle, small-n banner if n<10,
   primary render output, card footer with CSV download + SQL
   details expander.
────────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  // ── Config ────────────────────────────────────────────────
  var SQLJS_CDN   = 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/';
  var HISTORY_URL = 'signal_history.json';
  var SMALL_N     = 10;
  var TODAY_ISO   = new Date().toISOString().slice(0, 10); // YYYY-MM-DD

  // ── Schema — 37 columns (adds stock_regime vs AN-01) ────
  var COLUMNS = [
    'id', 'date', 'symbol', 'signal', 'direction',
    'entry', 'stop', 'target', 'score', 'regime',
    'sector', 'grade', 'generation', 'age',
    'vol_confirm', 'rs_strong', 'sec_leading', 'grade_A',
    'is_sa', 'sa_parent_id',
    'result', 'outcome', 'outcome_date', 'outcome_price',
    'pnl_pct', 'r_multiple', 'stop_hit', 'failure_reason',
    'action', 'actual_open', 'gap_pct', 'entry_valid',
    'mae_pct', 'mfe_pct', 'effective_exit_date',
    'data_quality', 'stock_regime'
  ];

  var CREATE_TABLE_SQL = [
    'CREATE TABLE signals (',
    '  id TEXT PRIMARY KEY, date TEXT, symbol TEXT, signal TEXT, direction TEXT,',
    '  entry REAL, stop REAL, target REAL, score REAL, regime TEXT,',
    '  sector TEXT, grade TEXT, generation INTEGER, age INTEGER,',
    '  vol_confirm INTEGER, rs_strong INTEGER, sec_leading INTEGER, grade_A INTEGER,',
    '  is_sa INTEGER, sa_parent_id TEXT,',
    '  result TEXT, outcome TEXT, outcome_date TEXT, outcome_price REAL,',
    '  pnl_pct REAL, r_multiple REAL, stop_hit INTEGER, failure_reason TEXT,',
    '  action TEXT, actual_open REAL, gap_pct REAL, entry_valid INTEGER,',
    '  mae_pct REAL, mfe_pct REAL, effective_exit_date TEXT,',
    '  data_quality TEXT, stock_regime TEXT',
    ');'
  ].join('\n');

  // ── Exports consumed by bundle files via window.AN ──────
  window.AN = window.AN || {};

  // ── Filter clause builder ────────────────────────────────
  // Returns a WHERE fragment for the current filter mode.
  // All plugins MUST use this — it's the single source of
  // truth for "what counts as a live trade."
  window.AN.filterWhere = function (mode) {
    if (mode === 'live') {
      return "WHERE action='TOOK' AND generation>=1 "
           + "AND (result IS NULL OR result != 'REJECTED')";
    }
    if (mode === '30d') {
      return "WHERE action='TOOK' AND generation>=1 "
           + "AND (result IS NULL OR result != 'REJECTED') "
           + "AND date >= date('" + TODAY_ISO + "', '-30 days')";
    }
    if (mode === 'all') {
      return "WHERE action='TOOK' "
           + "AND (result IS NULL OR result != 'REJECTED')";
    }
    throw new Error('Unknown filter mode: ' + mode);
  };

  // ── WR calculation fragment ──────────────────────────────
  // Standard WR math. Reusable in any SELECT.
  window.AN.wrFragment =
    "SUM(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN') THEN 1 ELSE 0 END) AS wins, " +
    "SUM(CASE WHEN outcome IN ('STOP_HIT','DAY6_LOSS')  THEN 1 ELSE 0 END) AS losses, " +
    "SUM(CASE WHEN outcome = 'DAY6_FLAT'                THEN 1 ELSE 0 END) AS flats, " +
    "SUM(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS','DAY6_FLAT') " +
    "         THEN 1 ELSE 0 END) AS resolved, " +
    "ROUND(" +
    "  CAST(SUM(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN') THEN 1 ELSE 0 END) AS REAL) * 100.0 / " +
    "  NULLIF(SUM(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS') THEN 1 ELSE 0 END), 0), " +
    "  1) AS wr_pct";

  window.AN.avgPnlFragment =
    "ROUND(AVG(CASE WHEN outcome IN ('TARGET_HIT','DAY6_WIN','STOP_HIT','DAY6_LOSS','DAY6_FLAT') " +
    "          THEN pnl_pct END), 2) AS avg_pnl";

  window.AN.today = TODAY_ISO;

  // ── App state ────────────────────────────────────────────
  var db          = null;
  var recordCount = 0;
  var curFilter   = 'live';
  var curTab      = 'overview';

  // ── DOM refs ─────────────────────────────────────────────
  var $status = document.getElementById('status');

  // ── Helpers ──────────────────────────────────────────────
  function setStatus(text, cls) {
    $status.textContent = text;
    $status.className = cls || '';
  }

  function escapeHtml(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function toIntBool(v) {
    if (v === null || v === undefined) return null;
    if (typeof v === 'boolean') return v ? 1 : 0;
    if (typeof v === 'number')  return v ? 1 : 0;
    if (typeof v === 'string') {
      var s = v.trim().toLowerCase();
      if (s === 'true' || s === '1') return 1;
      if (s === 'false' || s === '0') return 0;
    }
    return null;
  }
  window.AN.toIntBool = toIntBool;

  function nn(v) { return (v === undefined) ? null : v; }

  function fmtNum(v) {
    if (v === null || v === undefined) return '—';
    if (typeof v !== 'number' || !isFinite(v)) return String(v);
    if (Math.abs(v - Math.round(v)) < 1e-9 && Math.abs(v) < 1e12) {
      return String(Math.round(v));
    }
    var s = v.toFixed(4);
    return s.replace(/\.?0+$/, '');
  }
  window.AN.fmtNum = fmtNum;

  function fmtPct(v)  { return (v === null || v === undefined) ? '—' : fmtNum(v) + '%'; }
  function fmtPnL(v)  {
    if (v === null || v === undefined) return '—';
    return (v >= 0 ? '+' : '') + fmtNum(v) + '%';
  }
  window.AN.fmtPct = fmtPct;
  window.AN.fmtPnL = fmtPnL;

  // Record → row tuple in COLUMNS order
  function mapRecord(r) {
    var target = (r.target_price !== undefined && r.target_price !== null)
      ? r.target_price : (r.target !== undefined ? r.target : null);
    return [
      nn(r.id), nn(r.date), nn(r.symbol), nn(r.signal), nn(r.direction),
      nn(r.entry), nn(r.stop), nn(target), nn(r.score), nn(r.regime),
      nn(r.sector), nn(r.grade), nn(r.generation), nn(r.age),
      toIntBool(r.vol_confirm), toIntBool(r.rs_strong),
      toIntBool(r.sec_leading), toIntBool(r.grade_A),
      toIntBool(r.is_sa), nn(r.sa_parent_id),
      nn(r.result), nn(r.outcome), nn(r.outcome_date), nn(r.outcome_price),
      nn(r.pnl_pct), nn(r.r_multiple), toIntBool(r.stop_hit), nn(r.failure_reason),
      nn(r.action), nn(r.actual_open), nn(r.gap_pct), toIntBool(r.entry_valid),
      nn(r.mae_pct), nn(r.mfe_pct), nn(r.effective_exit_date),
      nn(r.data_quality), nn(r.stock_regime)
    ];
  }

  // ── Boot ─────────────────────────────────────────────────
  function boot() {
    if (typeof initSqlJs !== 'function') {
      setStatus('Failed to load SQL engine (sql.js CDN blocked?)', 'err');
      return;
    }
    if (typeof Chart === 'undefined') {
      setStatus('Failed to load Chart.js (CDN blocked?)', 'err');
      return;
    }

    setStatus('Loading SQL engine…');

    initSqlJs({
      locateFile: function (f) { return SQLJS_CDN + f; }
    }).then(function (SQL) {
      setStatus('Fetching signal_history.json…');
      return fetch(HISTORY_URL, { cache: 'no-cache' })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status + ' ' + res.statusText);
          return res.json();
        })
        .then(function (json) { return buildDb(SQL, json); });
    }).then(function (n) {
      recordCount = n;
      setStatus('Loaded ' + n.toLocaleString() + ' signals · filter: Live only · ready', 'ok');
      wireFilters();
      wireTabs();
      renderAllTabs();
    }).catch(function (err) {
      console.error(err);
      setStatus('Init failed: ' + (err && err.message ? err.message : err), 'err');
    });
  }

  function buildDb(SQL, json) {
    db = new SQL.Database();
    db.run(CREATE_TABLE_SQL);
    window.AN.db = db;

    var history = (json && json.history) ? json.history : [];
    if (!Array.isArray(history)) {
      throw new Error('signal_history.json has no `history` array');
    }

    var placeholders = COLUMNS.map(function () { return '?'; }).join(',');
    var insertSql = 'INSERT OR IGNORE INTO signals (' + COLUMNS.join(',') + ') ' +
                    'VALUES (' + placeholders + ')';
    var stmt = db.prepare(insertSql);
    var loaded = 0, skipped = 0;
    for (var i = 0; i < history.length; i++) {
      try { stmt.run(mapRecord(history[i])); loaded++; }
      catch (e) { skipped++; }
    }
    stmt.free();
    if (skipped > 0) console.warn('[AN] Skipped ' + skipped + ' records on insert');
    return loaded;
  }

  // ── Query runner exposed to bundles ──────────────────────
  window.AN.query = function (sql) {
    try {
      var results = db.exec(sql);
      if (!results || results.length === 0) {
        return { columns: [], values: [] };
      }
      // Return the LAST result set (handles multi-statement queries)
      var last = results[results.length - 1];
      return {
        columns: last.columns.slice(),
        values: last.values.map(function (r) { return r.slice(); })
      };
    } catch (e) {
      throw e;
    }
  };

  // ── Filter bar ───────────────────────────────────────────
  function wireFilters() {
    var btns = document.querySelectorAll('.filter-group button');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function (e) {
        var next = e.currentTarget.getAttribute('data-filter');
        if (next === curFilter) return;
        curFilter = next;
        for (var j = 0; j < btns.length; j++) btns[j].classList.remove('active');
        e.currentTarget.classList.add('active');
        updateStatusAfterFilter();
        renderAllTabs();
      });
    }
  }

  function updateStatusAfterFilter() {
    var label = { live: 'Live only', '30d': 'Last 30d', all: 'All-time' }[curFilter];
    setStatus('Loaded ' + recordCount.toLocaleString() + ' signals · filter: ' + label + ' · ready', 'ok');
  }

  // ── Tabs ─────────────────────────────────────────────────
  function wireTabs() {
    var btns = document.querySelectorAll('#tab-strip button');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function (e) {
        var next = e.currentTarget.getAttribute('data-tab');
        if (next === curTab) return;
        curTab = next;
        for (var j = 0; j < btns.length; j++) btns[j].classList.remove('active');
        e.currentTarget.classList.add('active');
        var panels = document.querySelectorAll('.tab-panel');
        for (var k = 0; k < panels.length; k++) panels[k].classList.remove('active');
        document.getElementById(next + '-tab').classList.add('active');
      });
    }
  }

  // ── Render ───────────────────────────────────────────────
  // Segmentation tab has 12 items — auto-collapse to reduce scroll fatigue.
  // Post-mortem has 8 — leave expanded (higher signal per card).
  var COLLAPSE_BY_DEFAULT = { segmentation: true };

  function renderAllTabs() {
    var tabs = ['overview', 'signals', 'segmentation', 'post_mortem'];
    for (var i = 0; i < tabs.length; i++) {
      renderTab(tabs[i]);
    }
    // Advanced tab is handled by advanced.js bundle — it renders itself once.
    if (window.AN_PLUGINS.advanced && window.AN_PLUGINS.advanced.length > 0 &&
        !document.getElementById('advanced-console')) {
      var adv = window.AN_PLUGINS.advanced[0];
      if (adv && typeof adv.mount === 'function') {
        adv.mount(document.getElementById('advanced-tab'));
      }
    }
  }

  function renderTab(tab) {
    var panel = document.getElementById(tab + '-tab');
    if (!panel) return;
    var plugins = (window.AN_PLUGINS[tab] || []).slice();
    plugins.sort(function (a, b) { return (a.order || 0) - (b.order || 0); });

    // Rebuild from scratch on each filter change.
    panel.innerHTML = '';
    for (var i = 0; i < plugins.length; i++) {
      panel.appendChild(renderCard(plugins[i], tab));
    }
  }

  function renderCard(plugin, tab) {
    var card = document.createElement('div');
    card.className = 'card';
    var collapsed = !!COLLAPSE_BY_DEFAULT[tab];
    if (collapsed) card.classList.add('collapsed');

    // ── Head ──
    var head = document.createElement('div');
    head.className = 'card-head';
    head.innerHTML =
      '<div>' +
        '<div class="card-title">' + escapeHtml(plugin.title) + '</div>' +
        (plugin.subtitle
          ? '<div class="card-subtitle">' + escapeHtml(plugin.subtitle) + '</div>'
          : '') +
      '</div>' +
      '<div class="card-meta" id="meta-' + plugin.id + '"></div>';
    head.addEventListener('click', function () {
      card.classList.toggle('collapsed');
    });
    card.appendChild(head);

    // ── Body ──
    var body = document.createElement('div');
    body.className = 'card-body';
    body.id = 'body-' + plugin.id;
    card.appendChild(body);

    // Render body (lazy: defer heavy work if collapsed & supported)
    try {
      renderPluginBody(plugin, body, card);
    } catch (e) {
      console.error('[AN] render error for ' + plugin.id, e);
      body.innerHTML = '<div class="empty-state">Render error: ' +
                       escapeHtml(String(e.message || e)) + '</div>';
    }

    return card;
  }

  function renderPluginBody(plugin, body, card) {
    // 1. Build SQL (may be string or function(filter))
    var sql;
    if (typeof plugin.sql === 'function') {
      sql = plugin.sql(window.AN.filterWhere(curFilter), curFilter);
    } else {
      sql = plugin.sql;
    }

    // 2. Run query
    var result;
    try {
      result = window.AN.query(sql);
    } catch (e) {
      body.innerHTML =
        '<div class="empty-state" style="color:#f85149;">SQL error: ' +
        escapeHtml(String(e.message || e)) + '</div>';
      appendFooter(body, plugin, sql, null);
      return;
    }

    // 3. Optional transform (plugin post-processing)
    if (typeof plugin.transform === 'function') {
      try { result = plugin.transform(result); } catch (e) { console.error(e); }
    }

    // 4. Compute total-n for small-n warning
    var n = computeN(result, plugin);
    var minN = (typeof plugin.minSampleSize === 'number') ? plugin.minSampleSize : SMALL_N;
    var metaEl = document.getElementById('meta-' + plugin.id);
    if (metaEl) metaEl.textContent = (n != null ? 'n = ' + n : '');

    // Small-n banner
    if (n != null && n < minN && n > 0) {
      card.classList.add('small-n');
      var banner = document.createElement('div');
      banner.className = 'small-n-banner';
      banner.textContent = '⚠ Small sample (n=' + n + '). Wait for more data before acting on this.';
      body.appendChild(banner);
    }

    // Empty state
    if (!result.values || result.values.length === 0) {
      var msg = plugin.emptyMessage || 'No matching signals in the current filter.';
      body.appendChild(createEmptyState(msg));
      appendFooter(body, plugin, sql, result);
      return;
    }

    // 5. Dispatch renderer
    var renderFn = RENDERERS[plugin.render] || RENDERERS.table;
    renderFn(result, plugin, body);

    // 6. Footer
    appendFooter(body, plugin, sql, result);
  }

  function computeN(result, plugin) {
    // If plugin says how to compute n, use it.
    if (typeof plugin.countFn === 'function') {
      try { return plugin.countFn(result); } catch (e) { return null; }
    }
    // Default: look for a column named 'n', 'total', 'resolved', or fall back to row count.
    if (!result.values || result.values.length === 0) return 0;
    var cols = result.columns;
    var nIdx = -1;
    for (var i = 0; i < cols.length; i++) {
      var c = String(cols[i]).toLowerCase();
      if (c === 'n' || c === 'total' || c === 'count' || c === 'resolved') { nIdx = i; break; }
    }
    if (nIdx < 0) return result.values.length;
    var sum = 0;
    for (var j = 0; j < result.values.length; j++) {
      var v = result.values[j][nIdx];
      if (typeof v === 'number') sum += v;
    }
    return sum;
  }

  function createEmptyState(msg) {
    var d = document.createElement('div');
    d.className = 'empty-state';
    d.textContent = msg;
    return d;
  }

  function appendFooter(body, plugin, sql, result) {
    var footer = document.createElement('div');
    footer.className = 'card-footer';

    // CSV export
    if (result && result.values && result.values.length > 0) {
      var csvBtn = document.createElement('button');
      csvBtn.textContent = '⬇ CSV';
      csvBtn.addEventListener('click', function () {
        downloadCsv(plugin.id + '.csv', result);
      });
      footer.appendChild(csvBtn);
    }

    // SQL details
    var details = document.createElement('details');
    var summary = document.createElement('summary');
    summary.textContent = 'Show SQL';
    details.appendChild(summary);
    var pre = document.createElement('pre');
    pre.textContent = (sql || '').trim();
    details.appendChild(pre);
    footer.appendChild(details);

    body.appendChild(footer);
  }

  function downloadCsv(filename, result) {
    var rows = [result.columns];
    for (var i = 0; i < result.values.length; i++) rows.push(result.values[i]);
    var csv = rows.map(function (r) {
      return r.map(function (v) {
        if (v === null || v === undefined) return '';
        var s = String(v);
        if (/[",\r\n]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
        return s;
      }).join(',');
    }).join('\r\n');

    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
  }

  // ── Renderers ─────────────────────────────────────────────
  var RENDERERS = {};

  // ── Number cards ──
  RENDERERS.number_cards = function (result, plugin, body) {
    var cols = result.columns, vals = result.values[0] || [];
    var grid = document.createElement('div');
    grid.className = 'num-grid';
    for (var i = 0; i < cols.length; i++) {
      var label = prettifyLabel(cols[i]);
      var raw = vals[i];
      var formatted = formatForLabel(cols[i], raw);
      var tone = toneForLabel(cols[i], raw);

      var card = document.createElement('div');
      card.className = 'num-card';
      card.innerHTML =
        '<div class="num ' + tone + '">' + escapeHtml(formatted) + '</div>' +
        '<div class="label">' + escapeHtml(label) + '</div>';
      grid.appendChild(card);
    }
    body.appendChild(grid);
  };

  // ── Table ──
  RENDERERS.table = function (result, plugin, body) {
    var cfg = plugin.config || {};
    var wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    var tbl = document.createElement('table');

    // Header
    var thead = document.createElement('thead');
    var htr = document.createElement('tr');
    for (var i = 0; i < result.columns.length; i++) {
      var th = document.createElement('th');
      th.setAttribute('data-idx', i);
      th.textContent = prettifyLabel(result.columns[i]);
      htr.appendChild(th);
    }
    thead.appendChild(htr);
    tbl.appendChild(thead);

    // Body
    var tbody = document.createElement('tbody');
    tbl.appendChild(tbody);

    wrap.appendChild(tbl);
    body.appendChild(wrap);

    var state = { rows: result.values.slice(), sortCol: -1, sortDir: 1 };

    function renderRows() {
      var html = '';
      for (var i = 0; i < state.rows.length; i++) {
        var r = state.rows[i];
        html += '<tr>';
        for (var j = 0; j < r.length; j++) {
          var v = r[j];
          var col = result.columns[j];
          if (v === null || v === undefined) {
            html += '<td class="null">—</td>';
          } else if (typeof v === 'number') {
            var cls = 'num';
            var tone = toneForCell(col, v);
            if (tone) cls += ' ' + tone;
            var formatted = formatForLabel(col, v);
            html += '<td class="' + cls + '">' + escapeHtml(formatted) + '</td>';
          } else {
            html += '<td>' + escapeHtml(v) + '</td>';
          }
        }
        html += '</tr>';
      }
      tbody.innerHTML = html;
    }
    renderRows();

    // Sorting
    var ths = thead.querySelectorAll('th');
    for (var k = 0; k < ths.length; k++) {
      ths[k].addEventListener('click', function (e) {
        var idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
        if (state.sortCol === idx) state.sortDir = -state.sortDir;
        else { state.sortCol = idx; state.sortDir = 1; }
        state.rows.sort(function (a, b) {
          var av = a[idx], bv = b[idx];
          if (av === null || av === undefined) return (bv === null || bv === undefined) ? 0 : 1;
          if (bv === null || bv === undefined) return -1;
          if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * state.sortDir;
          var as = String(av), bs = String(bv);
          if (as < bs) return -1 * state.sortDir;
          if (as > bs) return  1 * state.sortDir;
          return 0;
        });
        for (var m = 0; m < ths.length; m++) {
          ths[m].classList.remove('sort-asc');
          ths[m].classList.remove('sort-desc');
        }
        e.currentTarget.classList.add(state.sortDir === 1 ? 'sort-asc' : 'sort-desc');
        renderRows();
      });
    }
  };

  // ── Heatmap (HTML table with color-gradient cells) ──
  // Result must have columns [rowKey, colKey, n, wr_pct] — enforced by plugin.
  RENDERERS.heatmap = function (result, plugin, body) {
    var cfg = plugin.config || {};
    var rowKey = cfg.rowKey || result.columns[0];
    var colKey = cfg.colKey || result.columns[1];
    var nIdx   = result.columns.indexOf(cfg.nField   || 'n');
    var vIdx   = result.columns.indexOf(cfg.valField || 'wr_pct');
    var rIdx   = result.columns.indexOf(rowKey);
    var cIdx   = result.columns.indexOf(colKey);

    if (rIdx < 0 || cIdx < 0 || nIdx < 0 || vIdx < 0) {
      body.appendChild(createEmptyState('Heatmap config missing required fields.'));
      return;
    }

    // Pivot
    var rowSet = {}, colSet = {}, cells = {};
    for (var i = 0; i < result.values.length; i++) {
      var r = result.values[i];
      var rk = r[rIdx], ck = r[cIdx];
      rowSet[rk] = true; colSet[ck] = true;
      cells[rk + '||' + ck] = { n: r[nIdx], val: r[vIdx] };
    }
    var rows = Object.keys(rowSet).sort();
    var cols = Object.keys(colSet).sort();

    var wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    var tbl = document.createElement('table');
    tbl.className = 'heatmap';

    var thead = document.createElement('thead');
    var htr = document.createElement('tr');
    htr.innerHTML = '<th>' + escapeHtml(prettifyLabel(rowKey)) + '</th>' +
      cols.map(function (c) {
        return '<th>' + escapeHtml(c) + '</th>';
      }).join('');
    thead.appendChild(htr);
    tbl.appendChild(thead);

    var tbody = document.createElement('tbody');
    for (var ri = 0; ri < rows.length; ri++) {
      var tr = document.createElement('tr');
      var rowLabel = rows[ri];
      tr.innerHTML = '<td style="background:#161b22;text-align:left;font-weight:600;">' +
                     escapeHtml(rowLabel) + '</td>';
      for (var ci = 0; ci < cols.length; ci++) {
        var cell = cells[rowLabel + '||' + cols[ci]];
        if (!cell) {
          tr.innerHTML += '<td style="background:#0d1117;color:#484f58;">—</td>';
          continue;
        }
        if (cell.n < 5) {
          tr.innerHTML +=
            '<td style="background:#21262d;color:#6e7681;">' +
              '<div class="cell-n1">n=' + cell.n + '</div>' +
              '<div class="cell-n2">low-n</div>' +
            '</td>';
          continue;
        }
        var bg = wrColor(cell.val);
        tr.innerHTML +=
          '<td style="background:' + bg + ';">' +
            '<div class="cell-n1">' + (cell.val == null ? '—' : cell.val + '%') + '</div>' +
            '<div class="cell-n2">n=' + cell.n + '</div>' +
          '</td>';
      }
      tbody.appendChild(tr);
    }
    tbl.appendChild(tbody);
    wrap.appendChild(tbl);
    body.appendChild(wrap);
  };

  function wrColor(wr) {
    // Gradient: red (0–40) → gray (40–60) → green (60–100)
    if (wr == null) return '#21262d';
    var v = Math.max(0, Math.min(100, wr));
    if (v < 40) {
      // Red band: darker red as v → 0
      var t = v / 40; // 0..1
      return rgb(180 - 40*t, 40 + 30*t, 40 + 20*t);
    } else if (v < 60) {
      // Neutral gray band
      return '#30363d';
    } else {
      // Green band: brighter green as v → 100
      var t2 = (v - 60) / 40;
      return rgb(40 + 20*t2, 120 + 60*t2, 60 + 20*t2);
    }
  }

  function rgb(r, g, b) {
    return 'rgb(' + Math.round(r) + ',' + Math.round(g) + ',' + Math.round(b) + ')';
  }

  // ── Chart.js-based renderers ──
  RENDERERS.bar_chart = function (result, plugin, body) {
    renderChartJs(result, plugin, body, 'bar');
  };
  RENDERERS.line_chart = function (result, plugin, body) {
    renderChartJs(result, plugin, body, 'line');
  };
  RENDERERS.histogram = function (result, plugin, body) {
    renderChartJs(result, plugin, body, 'bar');
  };
  RENDERERS.scatter = function (result, plugin, body) {
    renderChartJs(result, plugin, body, 'scatter');
  };

  function renderChartJs(result, plugin, body, chartType) {
    var cfg = plugin.config || {};
    var wrap = document.createElement('div');
    wrap.className = 'chart-wrap';
    var canvas = document.createElement('canvas');
    wrap.appendChild(canvas);
    body.appendChild(wrap);

    var data = buildChartData(result, cfg, chartType);

    // Also add the underlying table below the chart for completeness
    var tableBody = document.createElement('div');
    tableBody.style.marginTop = '12px';
    body.appendChild(tableBody);
    RENDERERS.table(result, plugin, tableBody);

    new Chart(canvas.getContext('2d'), {
      type: chartType,
      data: data,
      options: buildChartOptions(cfg, chartType)
    });
  }

  function buildChartData(result, cfg, chartType) {
    var cols = result.columns;
    var xField = cfg.xField || cols[0];
    var yField = cfg.yField || findFirstNumericColumn(result);
    var seriesField = cfg.seriesField; // optional — stacked/grouped bars
    var xIdx = cols.indexOf(xField);
    var yIdx = cols.indexOf(yField);

    if (chartType === 'scatter') {
      // Scatter: each row → one point.
      var points = [];
      for (var i = 0; i < result.values.length; i++) {
        var r = result.values[i];
        var x = r[xIdx], y = r[yIdx];
        if (typeof x === 'number' && typeof y === 'number') points.push({ x: x, y: y });
      }
      return {
        datasets: [{
          label: (cfg.seriesLabel || prettifyLabel(yField)),
          data: points,
          backgroundColor: 'rgba(88,166,255,0.5)',
          borderColor: '#58a6ff',
          pointRadius: 3
        }]
      };
    }

    if (seriesField) {
      // Grouped/stacked: pivot by seriesField
      var sIdx = cols.indexOf(seriesField);
      var labelSet = {}, seriesSet = {}, grid = {};
      for (var j = 0; j < result.values.length; j++) {
        var row = result.values[j];
        var xl = String(row[xIdx]);
        var sl = String(row[sIdx]);
        var y  = row[yIdx];
        labelSet[xl] = true; seriesSet[sl] = true;
        grid[sl + '||' + xl] = y;
      }
      var labels = Object.keys(labelSet).sort();
      var seriesNames = Object.keys(seriesSet).sort();
      var palette = ['#58a6ff','#3fb950','#d29922','#f85149','#a371f7','#f78166','#56d364','#79c0ff'];
      var datasets = seriesNames.map(function (s, idx) {
        return {
          label: s,
          data: labels.map(function (l) { return grid[s + '||' + l] || 0; }),
          backgroundColor: palette[idx % palette.length],
          borderColor: palette[idx % palette.length],
          borderWidth: chartType === 'line' ? 2 : 0,
          fill: false,
          tension: 0.2
        };
      });
      return { labels: labels, datasets: datasets };
    }

    // Simple: one series, x from xField, y from yField
    var simpleLabels = [];
    var simpleData = [];
    var simpleColors = [];
    for (var k = 0; k < result.values.length; k++) {
      var rr = result.values[k];
      simpleLabels.push(String(rr[xIdx]));
      var yv = rr[yIdx];
      simpleData.push(yv);
      // Color by value for WR-ish columns
      if (/wr_pct|pnl|win/i.test(yField)) {
        if (typeof yv === 'number') {
          if (yv >= 60)      simpleColors.push('#3fb950');
          else if (yv >= 40) simpleColors.push('#30363d');
          else               simpleColors.push('#f85149');
        } else {
          simpleColors.push('#58a6ff');
        }
      } else {
        simpleColors.push('#58a6ff');
      }
    }
    return {
      labels: simpleLabels,
      datasets: [{
        label: cfg.seriesLabel || prettifyLabel(yField),
        data: simpleData,
        backgroundColor: simpleColors,
        borderColor: '#58a6ff',
        borderWidth: chartType === 'line' ? 2 : 0,
        fill: false,
        tension: 0.2,
        pointRadius: chartType === 'line' ? 2 : 0
      }]
    };
  }

  function buildChartOptions(cfg, chartType) {
    var opts = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: chartType === 'scatter' || cfg.showLegend !== false,
          labels: { color: '#c9d1d9', font: { size: 11 } }
        },
        tooltip: {
          backgroundColor: '#161b22',
          titleColor: '#f0f6fc',
          bodyColor: '#c9d1d9',
          borderColor: '#30363d',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          ticks: { color: '#8b949e', font: { size: 10 } },
          grid: { color: '#21262d' },
          title: cfg.xTitle ? { display: true, text: cfg.xTitle, color: '#8b949e' } : undefined
        },
        y: {
          ticks: { color: '#8b949e', font: { size: 10 } },
          grid: { color: '#21262d' },
          beginAtZero: cfg.beginAtZero !== false,
          title: cfg.yTitle ? { display: true, text: cfg.yTitle, color: '#8b949e' } : undefined
        }
      }
    };
    if (cfg.stacked) {
      opts.scales.x.stacked = true;
      opts.scales.y.stacked = true;
    }
    return opts;
  }

  function findFirstNumericColumn(result) {
    if (!result.values || result.values.length === 0) return result.columns[0];
    var row = result.values[0];
    for (var i = 0; i < row.length; i++) {
      if (typeof row[i] === 'number') return result.columns[i];
    }
    return result.columns[result.columns.length - 1];
  }

  // ── Custom render: plugin supplies its own body-populating function ──
  RENDERERS.custom = function (result, plugin, body) {
    if (typeof plugin.customRender === 'function') {
      plugin.customRender(result, body);
    } else {
      RENDERERS.table(result, plugin, body);
    }
  };

  // ── Label prettifier ──────────────────────────────────────
  function prettifyLabel(raw) {
    if (!raw) return '';
    var map = {
      n: 'n', total: 'Total', wins: 'Wins', losses: 'Losses', flats: 'Flats',
      resolved: 'Resolved', wr_pct: 'WR %', avg_pnl: 'Avg P&L %',
      avg_r: 'Avg R', avg_mfe: 'Avg MFE %', avg_mae: 'Avg MAE %',
      avg_stop_mae: 'Avg stop MAE %',
      pnl: 'P&L %', pnl_pct: 'P&L %', mae: 'MAE %', mfe: 'MFE %',
      mae_pct: 'MAE %', mfe_pct: 'MFE %',
      mae_bucket: 'MAE bucket (%)', mfe_bucket: 'MFE bucket (%)',
      score: 'Score', bonus: 'Bonus count', bonus_count: 'Bonus count',
      stop_rate_pct: 'Stop rate %',
      symbol: 'Symbol', signal: 'Signal', sector: 'Sector', regime: 'Regime',
      grade: 'Grade', age: 'Age', date: 'Date', outcome: 'Outcome',
      outcome_date: 'Exit date',
      entry: 'Entry', stop: 'Stop', target: 'Target',
      planned_entry: 'Planned entry', actual_open: '9:15 open',
      gap_pct: 'Gap %', days_to_stop: 'Days to stop',
      entry_date: 'Entry date', exit_price: 'Exit price',
      failure_reason: 'Failure reason', reason: 'Reason',
      vol_flag: 'Volume', rs_flag: 'RS', sec_flag: 'Sector mom.',
      stock_regime: 'Stock regime',
      parent_outcome: 'Parent outcome', sa_outcome: 'SA outcome',
      worst_trade: 'Worst trade %',
      best: 'Best %', worst: 'Worst %',
      period: 'Period', trade_num: 'Trade #',
      rolling_wr: 'Rolling 20 WR %', rolling_pnl: 'Rolling 20 P&L %',
      stops: 'Stops', stop_rate: 'Stop rate %',
      total_records: 'Total records', active_open: 'Active/open',
      rejected: 'Rejected', recovery_flagged: 'Recovery-flagged',
      backfill_records: 'Backfill', rej_records: 'REJ records',
      missing_v5_fields: 'Missing v5 fields', gap_invalidated: 'Gap-invalidated'
    };
    if (map[raw]) return map[raw];
    return String(raw).replace(/_/g, ' ').replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
  }

  function formatForLabel(col, v) {
    if (v === null || v === undefined) return '—';
    var c = String(col).toLowerCase();
    if (c === 'wr_pct' || c === 'stop_rate_pct' || c === 'rolling_wr') return fmtPct(v);
    if (c === 'pnl' || c === 'pnl_pct' || c === 'avg_pnl' || c === 'rolling_pnl' ||
        c === 'best' || c === 'worst' || c === 'worst_trade') return fmtPnL(v);
    if (c === 'mae' || c === 'mae_pct' || c === 'avg_mae' || c === 'avg_stop_mae' ||
        c === 'mfe' || c === 'mfe_pct' || c === 'avg_mfe') return fmtPnL(v);
    if (c === 'gap_pct') return fmtPnL(v);
    if (typeof v === 'number') return fmtNum(v);
    return String(v);
  }

  function toneForLabel(col, v) {
    if (typeof v !== 'number') return 'neutral';
    var c = String(col).toLowerCase();
    if (c === 'wr_pct' || c === 'rolling_wr') {
      if (v >= 60) return 'good';
      if (v < 40)  return 'bad';
      return 'neutral';
    }
    if (c === 'avg_pnl' || c === 'rolling_pnl' || c === 'pnl_pct' || c === 'pnl') {
      if (v > 0) return 'good';
      if (v < 0) return 'bad';
      return 'neutral';
    }
    if (c === 'stop_rate_pct') {
      if (v < 20) return 'good';
      if (v > 40) return 'bad';
      return 'neutral';
    }
    return 'neutral';
  }

  function toneForCell(col, v) {
    var t = toneForLabel(col, v);
    if (t === 'good') return 'good';
    if (t === 'bad')  return 'bad';
    return '';
  }

  // ── Kick off ─────────────────────────────────────────────
  boot();
})();
