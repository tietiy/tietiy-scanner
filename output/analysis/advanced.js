/* ────────────────────────────────────────────────────────────
   advanced.js — AN-02 Advanced tab (SQL escape hatch)

   A single raw-SQL textarea for power queries the 36 presets
   don't cover. Deliberately tucked away:
     - not visible by default (Advanced tab must be tapped)
     - no presets, no decoration, just a query box
     - reuses the same engine pipeline → CSV export still works
     - results render via the engine's table renderer
       (window.AN_RENDER_TABLE shim from signals.js)

   Plugin shape here is unusual — it's a single-entry plugin
   with a `mount(containerEl)` method the engine calls once.
   No SQL field, no render type. The engine special-cases the
   advanced tab in renderAllTabs().
──────────────────────────────────────────────────────────── */

(function () {
  'use strict';

  var REG = window.AN_PLUGINS.advanced;

  var SEED_QUERY =
    '-- Escape hatch for custom queries.\n' +
    '-- Table: signals (37 columns — see schema in analysis.js)\n' +
    '-- Filter helpers are NOT auto-applied here. Write your own WHERE clause.\n' +
    '\n' +
    'SELECT signal, result, COUNT(*) AS n\n' +
    'FROM signals\n' +
    'GROUP BY signal, result\n' +
    'ORDER BY signal, result;';

  REG.push({
    id: 'sql_console',
    tab: 'advanced',
    title: 'SQL Console',

    // The engine calls mount(containerEl) exactly once for the
    // Advanced tab, then leaves us alone. We own the UI here.
    mount: function (container) {
      // Guard: only mount once, even if renderAllTabs runs again
      if (document.getElementById('advanced-console')) return;

      container.innerHTML =
        '<div id="advanced-console" class="card">' +
          '<div class="card-head" style="cursor:default;">' +
            '<div>' +
              '<div class="card-title">🛠️ SQL Console</div>' +
              '<div class="card-subtitle">' +
                'Escape hatch for questions not in the presets. ' +
                'Writes affect this in-memory DB only — refresh to reset.' +
              '</div>' +
            '</div>' +
            '<div class="card-meta">table: <code>signals</code></div>' +
          '</div>' +
          '<div class="card-body">' +
            '<textarea id="adv-sql" spellcheck="false" autocomplete="off" ' +
              'autocapitalize="off" autocorrect="off"></textarea>' +
            '<div class="adv-actions">' +
              '<button id="adv-run"   class="primary">Run</button>' +
              '<button id="adv-reset" class="ghost"  title="Restore seed query">Reset</button>' +
              '<button id="adv-csv"   class="ghost"  disabled>⬇ CSV</button>' +
              '<button id="adv-schema" class="ghost" title="Show column list">Schema</button>' +
              '<span class="hint"><kbd>⌘</kbd> / <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to run</span>' +
            '</div>' +
            '<div id="advanced-error"></div>' +
            '<div id="advanced-meta" style="margin-top:10px;color:#8b949e;font-size:12px;"></div>' +
            '<div id="advanced-results" style="margin-top:8px;"></div>' +
          '</div>' +
        '</div>';

      var $sql    = document.getElementById('adv-sql');
      var $run    = document.getElementById('adv-run');
      var $reset  = document.getElementById('adv-reset');
      var $csv    = document.getElementById('adv-csv');
      var $schema = document.getElementById('adv-schema');
      var $err    = document.getElementById('advanced-error');
      var $meta   = document.getElementById('advanced-meta');
      var $out    = document.getElementById('advanced-results');

      $sql.value = SEED_QUERY;

      var lastResult = null;

      function clearError() { $err.style.display = 'none'; $err.textContent = ''; }
      function showError(msg) {
        $err.style.display = 'block';
        $err.textContent = msg;
      }

      function run() {
        clearError();
        $out.innerHTML = '';
        $meta.textContent = '';
        $csv.disabled = true;

        var sql = $sql.value.trim();
        if (!sql) { showError('Enter a SQL query.'); return; }

        var t0 = performance.now();
        var result;
        try {
          result = window.AN.query(sql);
        } catch (e) {
          showError('SQL error: ' + (e && e.message ? e.message : e));
          return;
        }
        var ms = Math.round(performance.now() - t0);

        if (!result.columns || result.columns.length === 0) {
          $meta.textContent =
            'Statement executed (no result set). ' +
            'Writes persist until you refresh the page. (' + ms + ' ms)';
          return;
        }

        if (result.values.length === 0) {
          $meta.textContent = '0 rows · ' + ms + ' ms';
          $out.innerHTML = '<div class="empty-state">No rows.</div>';
          return;
        }

        $meta.textContent =
          result.values.length.toLocaleString() + ' row' +
          (result.values.length === 1 ? '' : 's') + ' · ' + ms + ' ms';

        lastResult = result;
        $csv.disabled = false;

        // Render via the engine's table renderer shim (from signals.js).
        // Fallback to a bare table if the shim isn't loaded.
        var pseudoPlugin = { id: 'adv_sql_console', render: 'table' };
        if (typeof window.AN_RENDER_TABLE === 'function') {
          window.AN_RENDER_TABLE(result, pseudoPlugin, $out);
        } else {
          renderTableFallback(result, $out);
        }
      }

      function renderTableFallback(result, container) {
        var wrap = document.createElement('div');
        wrap.className = 'table-wrap';
        var tbl = document.createElement('table');
        var thead = document.createElement('thead');
        var htr = document.createElement('tr');
        for (var i = 0; i < result.columns.length; i++) {
          var th = document.createElement('th');
          th.textContent = result.columns[i];
          htr.appendChild(th);
        }
        thead.appendChild(htr);
        tbl.appendChild(thead);
        var tbody = document.createElement('tbody');
        for (var r = 0; r < result.values.length; r++) {
          var tr = document.createElement('tr');
          for (var c = 0; c < result.values[r].length; c++) {
            var v = result.values[r][c];
            var td = document.createElement('td');
            if (v === null || v === undefined) {
              td.className = 'null'; td.textContent = '—';
            } else if (typeof v === 'number') {
              td.className = 'num'; td.textContent = window.AN.fmtNum(v);
            } else {
              td.textContent = String(v);
            }
            tr.appendChild(td);
          }
          tbody.appendChild(tr);
        }
        tbl.appendChild(tbody);
        wrap.appendChild(tbl);
        container.appendChild(wrap);
      }

      function downloadCsv() {
        if (!lastResult) return;
        var rows = [lastResult.columns];
        for (var i = 0; i < lastResult.values.length; i++) {
          rows.push(lastResult.values[i]);
        }
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
        a.download = 'sql_console_' + Date.now() + '.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
      }

      function showSchema() {
        clearError();
        $out.innerHTML = '';
        try {
          var result = window.AN.query(
            "SELECT name AS column_name, type AS column_type, " +
            "       CASE WHEN pk=1 THEN 'PK' ELSE '' END AS key " +
            "FROM pragma_table_info('signals')"
          );
          $meta.textContent = result.values.length + ' columns in `signals` table';
          var pseudoPlugin = { id: 'adv_schema', render: 'table' };
          if (typeof window.AN_RENDER_TABLE === 'function') {
            window.AN_RENDER_TABLE(result, pseudoPlugin, $out);
          } else {
            renderTableFallback(result, $out);
          }
          lastResult = result;
          $csv.disabled = false;
        } catch (e) {
          showError('Schema query failed: ' + e.message);
        }
      }

      // ── Events ──
      $run.addEventListener('click', run);
      $reset.addEventListener('click', function () {
        $sql.value = SEED_QUERY;
        $sql.focus();
      });
      $csv.addEventListener('click', downloadCsv);
      $schema.addEventListener('click', showSchema);
      $sql.addEventListener('keydown', function (e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
          e.preventDefault();
          run();
        }
      });

      // Don't auto-run. Advanced users want to type first.
    }
  });

  console.log('[AN] advanced.js registered ' + REG.length + ' plugin');
})();
