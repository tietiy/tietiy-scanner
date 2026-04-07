// ── journal.js ───────────────────────────────────────
// Step 21 — Trade Journal
// Renders signal_history.json as a grouped, filterable log
//
// TOOK view  : layer=MINI + action=TOOK  (signals acted on)
// REJECTED   : layer=ALPHA + action=REJECTED (filtered out)
// Groups by date — newest first
// Within each date — sorted by score desc
//
// S9 review  : No UTC date bugs — all date parsing uses
//              T00:00:00 suffix (local time safe)
// ─────────────────────────────────────────────────────

(function () {

  // ── MODULE STATE ─────────────────────────────────────
  // Not localStorage — session only. Resets on reload.
  let _filter = 'took'; // 'took' | 'rejected'

  // Register filter toggle immediately so onclick is
  // always available regardless of render timing
  window._jFilter = function (f) {
    _filter = f;
    if (window.TIETIY) {
      window.renderJournal(window.TIETIY);
    }
  };


  // ── HELPERS ──────────────────────────────────────────

  function _sym(s) {
    return (s || '').replace('.NS', '');
  }

  function _scoreStr(score) {
    const s = parseFloat(score);
    return isNaN(s) ? '—/10' : s.toFixed(0) + '/10';
  }

  function _rr(sig) {
    const e = parseFloat(sig.entry        || 0);
    const s = parseFloat(sig.stop         || 0);
    const t = parseFloat(sig.target_price || 0);
    if (!e || !s || !t) return null;
    const risk   = Math.abs(e - s);
    const reward = Math.abs(t - e);
    if (risk === 0) return null;
    return (reward / risk).toFixed(1);
  }

  function _color(signal) {
    const s = (signal || '').toUpperCase();
    if (s.includes('UP'))   return '#00C851';
    if (s.includes('DOWN')) return '#f85149';
    if (s.includes('BULL')) return '#58a6ff';
    return '#8b949e';
  }

  function _emoji(signal) {
    const s = (signal || '').toUpperCase();
    if (s.includes('UP'))   return '🔺';
    if (s.includes('DOWN')) return '🔻';
    if (s.includes('BULL')) return '🟢';
    return '📌';
  }

  function _gradeColor(g) {
    return g === 'A' ? '#ffd700'
         : g === 'B' ? '#8b949e'
         : '#555';
  }

  function _rejLabel(reason) {
    const map = {
      score_below_threshold: 'Score too low',
      regime_not_aligned:    'Regime mismatch',
      age_expired:           'Age expired',
      vol_too_low:           'Volume too low',
      rr_too_low:            'R:R too low',
    };
    return map[reason] || (reason || 'Filtered');
  }

  // T00:00:00 suffix forces local time — no UTC bleed
  function _fmtDateHeader(str) {
    if (!str) return '—';
    try {
      const d = new Date(str + 'T00:00:00');
      return d.toLocaleDateString('en-IN', {
        weekday: 'long',
        day:     'numeric',
        month:   'short',
        year:    'numeric',
      });
    } catch (e) { return str; }
  }

  function _dayNum(sig) {
    if (typeof getDayNumber === 'function') {
      return getDayNumber(sig.date);
    }
    return null;
  }

  // T00:00:00 suffix forces local time — no UTC bleed
  function _exitDateStr(sig) {
    if (!sig.exit_date) return null;
    try {
      const d = new Date(
        sig.exit_date + 'T00:00:00');
      return d.toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short',
      });
    } catch (e) { return sig.exit_date; }
  }


  // ── STATUS BADGE ─────────────────────────────────────

  function _badge(sig) {
    const outcome = sig.outcome || '';
    const result  = sig.result  || '';

    if (outcome === 'TARGET_HIT') {
      const pnl = sig.pnl_pct != null
        ? ` +${parseFloat(
            sig.pnl_pct).toFixed(1)}%` : '';
      return _badgeHtml(
        '#0d2a0d', '#00C851',
        `🎯 TARGET${pnl}`);
    }
    if (outcome === 'STOP_HIT') {
      const pnl = sig.pnl_pct != null
        ? ` ${parseFloat(
            sig.pnl_pct).toFixed(1)}%` : '';
      return _badgeHtml(
        '#2a0a0a', '#f85149',
        `🛑 STOP${pnl}`);
    }
    if (outcome === 'DAY6_WIN') {
      const pnl = sig.pnl_pct != null
        ? ` +${parseFloat(
            sig.pnl_pct).toFixed(1)}%` : '';
      return _badgeHtml(
        '#0d2a0d', '#00C851',
        `✓ DAY6 WIN${pnl}`);
    }
    if (outcome === 'DAY6_LOSS') {
      const pnl = sig.pnl_pct != null
        ? ` ${parseFloat(
            sig.pnl_pct).toFixed(1)}%` : '';
      return _badgeHtml(
        '#2a0a0a', '#f85149',
        `✕ DAY6 LOSS${pnl}`);
    }
    if (outcome === 'DAY6_FLAT') {
      return _badgeHtml(
        '#1a1a0a', '#FFD700', '~ FLAT');
    }

    if (result === 'REJECTED') {
      return _badgeHtml(
        '#2a0a0a', '#f85149', '✕ REJECTED');
    }

    const day = _dayNum(sig);
    if (day !== null) {
      if (day >= 6) {
        return _badgeHtml(
          '#2a0a0a', '#f85149',
          '⚠️ EXIT TODAY');
      }
      return _badgeHtml(
        '#1a1a0a', '#FFD700',
        `Day ${day}/6`);
    }

    return _badgeHtml('#1a1a0a', '#555', 'PENDING');
  }

  function _badgeHtml(bg, color, label) {
    return `<span style="background:${bg};
      color:${color};
      border:1px solid ${color}33;
      border-radius:4px;
      padding:2px 8px;font-size:10px;
      font-weight:700;
      white-space:nowrap;">${label}</span>`;
  }


  // ── SIGNAL CARD ──────────────────────────────────────

  function _card(sig, isRejView) {
    const sym       = _sym(sig.symbol);
    const stype     = sig.signal   || '?';
    const color     = _color(stype);
    const score     = _scoreStr(sig.score);
    const age       = sig.age != null
                      ? sig.age : '?';
    const sector    = sig.sector   || '';
    const grade     = sig.grade    || '';
    const rr        = _rr(sig);
    const dir       = sig.direction === 'SHORT'
                      ? '↓' : '↑';
    const isBear    = sig.bear_bonus === true
                      || sig.bear_bonus === 'true';
    const stkRegime = sig.stock_regime || null;
    const entry     = sig.entry
      ? '₹' + parseFloat(
          sig.entry).toFixed(2) : '—';
    const stop      = sig.stop
      ? '₹' + parseFloat(
          sig.stop).toFixed(2) : '—';
    const target    = sig.target_price
      ? '₹' + parseFloat(
          sig.target_price).toFixed(2) : '—';
    const exitStr   = _exitDateStr(sig);
    const rejReason = isRejView
                      && sig.rejection_reason
      ? _rejLabel(sig.rejection_reason) : null;
    const rejThresh = isRejView
                      && sig.rejection_threshold
                         != null
      ? `(min: ${sig.rejection_threshold})` : '';

    return `
      <div style="background:#161b22;
        border:1px solid #21262d;
        border-left:3px solid ${color};
        border-radius:8px;padding:10px 12px;
        margin-bottom:8px;">

        <div style="display:flex;
          justify-content:space-between;
          align-items:flex-start;
          margin-bottom:6px;">

          <div style="display:flex;
            align-items:center;
            gap:6px;flex-wrap:wrap;
            flex:1;min-width:0;">
            <span style="color:#c9d1d9;
              font-size:14px;font-weight:700;">
              ${sym}
            </span>
            <span style="color:#555;
              font-size:11px;">
              ${sector}
            </span>
            <span style="color:${_gradeColor(grade)};
              font-size:10px;font-weight:700;
              border:1px solid ${
                _gradeColor(grade)}44;
              border-radius:3px;
              padding:0 4px;">
              ${grade}
            </span>
            ${isBear
              ? '<span style="font-size:10px;">'
                + '🔥</span>'
              : ''}
            ${stkRegime
              ? `<span style="font-size:9px;
                   color:#555;
                   background:#1c2128;
                   border-radius:3px;
                   padding:1px 4px;">
                   stk:${stkRegime}
                 </span>`
              : ''}
          </div>

          <div style="flex-shrink:0;
            margin-left:8px;">
            ${_badge(sig)}
          </div>
        </div>

        <div style="display:flex;
          align-items:center;
          gap:8px;flex-wrap:wrap;
          margin-bottom:6px;">
          <span style="color:${color};
            font-size:12px;font-weight:700;">
            ${_emoji(stype)} ${stype}
          </span>
          <span style="color:#ffd700;
            font-size:11px;font-weight:700;">
            ${score}
          </span>
          <span style="color:#555;font-size:11px;">
            Age&nbsp;${age}
          </span>
          <span style="color:#555;font-size:11px;">
            ${dir}&nbsp;${sig.direction || 'LONG'}
          </span>
          ${rr
            ? `<span style="color:#58a6ff;
                 font-size:11px;">
                 R:R&nbsp;${rr}×
               </span>`
            : ''}
        </div>

        <div style="display:flex;gap:14px;
          flex-wrap:wrap;font-size:11px;
          color:#8b949e;margin-bottom:4px;">
          <span>Entry&nbsp;
            <b style="color:#c9d1d9;">
              ${entry}
            </b>
          </span>
          <span>Stop&nbsp;
            <b style="color:#f85149;">
              ${stop}
            </b>
          </span>
          <span>Target&nbsp;
            <b style="color:#00C851;">
              ${target}
            </b>
          </span>
        </div>

        ${!isRejView && exitStr
          ? `<div style="font-size:10px;
               color:#555;margin-top:2px;">
               Exit: ${exitStr}
             </div>`
          : ''}

        ${rejReason
          ? `<div style="font-size:10px;
               color:#f85149;margin-top:4px;">
               ✕ ${rejReason} ${rejThresh}
             </div>`
          : ''}

      </div>`;
  }


  // ── FILTER TABS ──────────────────────────────────────

  function _filterBar(tookN, rejN) {
    const on  = 'background:#21262d;color:#c9d1d9;';
    const off = 'background:none;color:#555;';

    return `
      <div style="display:flex;gap:8px;
        padding:0 16px;margin-bottom:14px;">

        <button onclick="window._jFilter('took')"
          style="flex:1;
            ${_filter === 'took' ? on : off}
            border:1px solid #30363d;
            border-radius:6px;padding:7px 0;
            font-size:12px;cursor:pointer;">
          📥 Took (${tookN})
        </button>

        <button
          onclick="window._jFilter('rejected')"
          style="flex:1;
            ${_filter === 'rejected' ? on : off}
            border:1px solid #30363d;
            border-radius:6px;padding:7px 0;
            font-size:12px;cursor:pointer;">
          ✕ Rejected (${rejN})
        </button>

      </div>`;
  }


  // ── MAIN RENDER ──────────────────────────────────────

  window.renderJournal = function (tietiy) {
    const el = document.getElementById(
      'tab-content');
    if (!el) return;

    const raw = (tietiy.history
                 && tietiy.history.history)
      ? tietiy.history.history : [];

    const took = raw.filter(
      s => s.layer  === 'MINI'
        && s.action === 'TOOK');
    const rej  = raw.filter(
      s => s.layer  === 'ALPHA'
        && s.action === 'REJECTED');

    const entries   = _filter === 'took'
                      ? took : rej;
    const isRejView = _filter === 'rejected';

    // Group by date — newest first
    const byDate = {};
    entries.forEach(function (sig) {
      const d = sig.date || 'Unknown';
      if (!byDate[d]) byDate[d] = [];
      byDate[d].push(sig);
    });

    const dates = Object.keys(byDate)
      .sort((a, b) => b.localeCompare(a));

    // Sort each group by score desc
    dates.forEach(function (d) {
      byDate[d].sort((a, b) =>
        (parseFloat(b.score) || 0) -
        (parseFloat(a.score) || 0));
    });

    let html = `
      <div style="padding-bottom:80px;">

        <div style="padding:12px 16px 10px;
          display:flex;
          justify-content:space-between;
          align-items:center;">
          <span style="font-size:11px;
            color:#555;letter-spacing:1px;">
            📓 JOURNAL
          </span>
          <span style="font-size:10px;color:#555;">
            ${took.length} took ·
            ${rej.length} rejected
          </span>
        </div>

        ${_filterBar(took.length, rej.length)}`;

    if (entries.length === 0) {
      html += `
        <div style="text-align:center;
          padding:48px 16px;
          color:#555;font-size:13px;">
          No ${isRejView
            ? 'rejected' : 'TOOK'} signals yet.
        </div>`;
    } else {
      dates.forEach(function (dateStr) {
        const group = byDate[dateStr];
        html += `
          <div style="padding:0 16px;">

            <div style="font-size:11px;
              color:#ffd700;font-weight:700;
              letter-spacing:1px;
              margin-bottom:10px;
              padding-top:12px;
              border-top:1px solid #21262d;">
              ${_fmtDateHeader(dateStr)}
              <span style="color:#555;
                font-weight:400;
                margin-left:6px;">
                ${group.length} signal${
                  group.length !== 1
                    ? 's' : ''}
              </span>
            </div>

            ${group.map(
              s => _card(s, isRejView)
            ).join('')}

          </div>`;
      });
    }

    html += `</div>`;
    el.innerHTML = html;
  };

})();
