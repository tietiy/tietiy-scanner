// ── journal.js ───────────────────────────────────────
// Trade Journal — tracking screen only.
// NOT for re-deciding trades.
//
// Design pass:
// - Inline expand/collapse cards
// - Compact: name, sector, grade, day, signal, score,
//   direction, entry, stop, target, exit date
// - Expanded: entry/stop/target grid, R:R, grade,
//   day progress bar, timing, MFE/MAE, open/gap, outcome
// - No "Why This Trade", no Open Chart
// - Rejected: compact, read-only, reason only
// - Day badge: grey 1-4, orange 5, red⚠️ 6
// ─────────────────────────────────────────────────────
(function () {

let _jFilter = 'took';

window._jFilter = function(f) {
  _jFilter = f;
  if (window.TIETIY) window.renderJournal(window.TIETIY);
};

// ── HELPERS ──────────────────────────────────────────
function _sym(s) { return (s || '').replace('.NS', ''); }

function _scoreColor(score) {
  const n = parseFloat(score);
  if (isNaN(n)) return '#555';
  if (n >= 7)   return '#FFD700';
  if (n >= 5)   return '#00C851';
  if (n >= 3)   return '#8b949e';
  return '#555';
}

function _sigColor(signal) {
  const s = (signal || '').toUpperCase();
  if (s.includes('UP'))   return '#00C851';
  if (s.includes('DOWN')) return '#f85149';
  if (s.includes('BULL')) return '#58a6ff';
  return '#8b949e';
}

function _sigEmoji(signal) {
  const s = (signal || '').toUpperCase();
  if (s.includes('UP'))   return '🔺';
  if (s.includes('DOWN')) return '🔻';
  if (s.includes('BULL')) return '🟢';
  return '📌';
}

// Day badge with urgency colors
function _dayBadge(dayNum) {
  if (!dayNum) return '';
  const color = dayNum >= 6 ? '#f85149' :
                dayNum >= 5 ? '#FF8C00' : '#555';
  const icon  = dayNum >= 6 ? ' ⚠️' : '';
  const bg    = dayNum >= 6 ? '#2a0a0a' :
                dayNum >= 5 ? '#1a0f00' : 'transparent';
  return `<span style="color:${color};font-size:10px;
    font-weight:700;background:${bg};
    border-radius:4px;padding:1px 5px;
    ${dayNum >= 5 ? 'border:1px solid ' + color + '33;' : ''}">
    Day ${dayNum}/6${icon}
  </span>`;
}

// Day progress bar
function _dayProgress(dayNum) {
  const pct   = Math.min(Math.round((dayNum / 6) * 100), 100);
  const color = dayNum >= 6 ? '#f85149' :
                dayNum >= 5 ? '#FF8C00' :
                dayNum >= 3 ? '#FFD700' : '#58a6ff';
  return `
    <div style="margin-bottom:6px;">
      <div style="display:flex;justify-content:space-between;
        font-size:10px;color:#555;margin-bottom:3px;">
        <span>Trade progress</span>
        <span style="color:${color};">Day ${dayNum} of 6</span>
      </div>
      <div style="background:#21262d;border-radius:3px;
        height:5px;overflow:hidden;">
        <div style="background:${color};height:5px;
          width:${pct}%;border-radius:3px;
          transition:width 0.3s ease;">
        </div>
      </div>
    </div>`;
}

// Date formatter (T00:00:00 prevents UTC bleed)
function _fmtD(str) {
  if (!str) return '—';
  try {
    const d = new Date(str + 'T00:00:00');
    return d.toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short'
    });
  } catch(e) { return str; }
}

// R:R from stored fields
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

// Rejection reason label
function _rejLabel(reason) {
  const map = {
    score_below_threshold: 'Score too low',
    regime_not_aligned:    'Regime mismatch',
    age_expired:           'Age expired',
    vol_too_low:           'Volume too low',
    rr_too_low:            'R:R too low',
  };
  const label = map[reason] || (reason || 'Filtered').replace(/_/g,' ');
  return `ALPHA: ${label}`;
}

// Grade color
function _gradeColor(g) {
  return g === 'A' ? '#ffd700' : g === 'B' ? '#8b949e' : '#555';
}

// Outcome badge
function _outcomeBadge(sig) {
  const outcome = sig.outcome || '';
  const result  = sig.result  || '';

  if (outcome === 'TARGET_HIT') {
    const pnl = sig.pnl_pct != null
      ? ` +${parseFloat(sig.pnl_pct).toFixed(1)}%` : '';
    return _badge('#0d2a0d','#00C851', `🎯 TARGET${pnl}`);
  }
  if (outcome === 'STOP_HIT') {
    const pnl = sig.pnl_pct != null
      ? ` ${parseFloat(sig.pnl_pct).toFixed(1)}%` : '';
    return _badge('#2a0a0a','#f85149', `🛑 STOP${pnl}`);
  }
  if (outcome === 'DAY6_WIN') {
    const pnl = sig.pnl_pct != null
      ? ` +${parseFloat(sig.pnl_pct).toFixed(1)}%` : '';
    return _badge('#0d2a0d','#00C851', `✓ DAY6 WIN${pnl}`);
  }
  if (outcome === 'DAY6_LOSS') {
    const pnl = sig.pnl_pct != null
      ? ` ${parseFloat(sig.pnl_pct).toFixed(1)}%` : '';
    return _badge('#2a0a0a','#f85149', `✕ DAY6 LOSS${pnl}`);
  }
  if (outcome === 'DAY6_FLAT')
    return _badge('#1a1a0a','#FFD700', '~ FLAT');
  if (result === 'REJECTED')
    return _badge('#2a0a0a','#f85149', '✕ REJECTED');

  // PENDING — show day badge with urgency
  const day = typeof getDayNumber === 'function'
    ? getDayNumber(sig.date) : null;
  if (day !== null) {
    if (day >= 6)  return _badge('#2a0a0a','#f85149','⚠️ EXIT TODAY');
    if (day >= 5)  return _badge('#1a0f00','#FF8C00',`⚠️ Day ${day}/6`);
    if (day >= 3)  return _badge('#1a1a0a','#FFD700', `Day ${day}/6`);
    return _badge('#1a1a0a','#555',`Day ${day}/6`);
  }
  return _badge('#1a1a0a','#555','OPEN');
}

function _badge(bg, color, label) {
  return `<span style="background:${bg};color:${color};
    border:1px solid ${color}33;border-radius:4px;
    padding:2px 8px;font-size:10px;font-weight:700;
    white-space:nowrap;">${label}</span>`;
}

// ── COMPACT CARD ─────────────────────────────────────
function _compactCard(sig, isRejView) {
  const sym       = _sym(sig.symbol);
  const stype     = sig.signal    || '?';
  const sigColor  = _sigColor(stype);
  const score     = sig.score     || 0;
  const sc        = _scoreColor(score);
  const direction = sig.direction === 'SHORT' ? '↓ SHORT' : '↑ LONG';
  const sector    = sig.sector    || '';
  const grade     = sig.grade     || '';
  const bearBonus = sig.bear_bonus === true ||
                    sig.bear_bonus === 'true';
  const stkRegime = sig.stock_regime || null;
  const isBackfill = sig.generation === 0;

  const entry     = sig.entry
    ? '₹' + parseFloat(sig.entry).toFixed(2) : '—';
  const stop      = sig.stop
    ? '₹' + parseFloat(sig.stop).toFixed(2) : '—';
  const target    = sig.target_price
    ? '₹' + parseFloat(sig.target_price).toFixed(2) : '—';
  const exitStr   = sig.exit_date ? _fmtD(sig.exit_date) : null;

  const dayNum    = typeof getDayNumber === 'function'
    ? getDayNumber(sig.date) : null;

  const cardId  = (sig.id || (sym + '-' + stype + '-' + sig.date || ''))
    .replace(/[^a-zA-Z0-9-]/g, '-');

  const rejReason = isRejView && sig.rejection_reason
    ? _rejLabel(sig.rejection_reason)
    : null;
  const rejThresh = isRejView && sig.rejection_threshold != null
    ? ` (min: ${sig.rejection_threshold})`
    : '';

  return `
    <div style="background:#161b22;
      border:1px solid #21262d;
      border-left:3px solid ${sigColor};
      border-radius:8px;padding:10px 12px 8px;
      margin-bottom:8px;
      ${isBackfill ? 'opacity:0.75;' : ''}">

      <!-- Row 1: Header -->
      <div style="display:flex;justify-content:space-between;
        align-items:flex-start;margin-bottom:5px;">
        <div style="display:flex;align-items:center;
          gap:5px;flex-wrap:wrap;flex:1;min-width:0;">
          <span style="color:#c9d1d9;font-size:14px;font-weight:700;">
            ${sym}
          </span>
          <span style="color:#555;font-size:11px;">${sector}</span>
          ${grade
            ? `<span style="color:${_gradeColor(grade)};
                font-size:10px;font-weight:700;
                border:1px solid ${_gradeColor(grade)}44;
                border-radius:3px;padding:0 4px;">
                ${grade}
              </span>`
            : ''}
          ${bearBonus ? '<span style="font-size:10px;">🔥</span>' : ''}
          ${stkRegime
            ? `<span style="font-size:9px;color:#555;
                background:#1c2128;border-radius:3px;
                padding:1px 4px;">
                stk:${stkRegime}
              </span>`
            : ''}
          ${isBackfill
            ? `<span style="font-size:9px;color:#444;
                background:#1c2128;border-radius:3px;
                padding:1px 4px;border:1px solid #30363d;">
                gen:0
              </span>`
            : ''}
        </div>
        <div style="display:flex;align-items:center;
          gap:4px;flex-shrink:0;margin-left:8px;">
          ${_outcomeBadge(sig)}
          ${!isRejView && !isBackfill
            ? `<button onclick="event.stopPropagation();
                 toggleJournalCard('${cardId}')"
                id="ja-${cardId}"
                style="background:none;border:none;
                  color:#555;font-size:14px;cursor:pointer;
                  padding:0 2px;line-height:1;">▶</button>`
            : ''}
        </div>
      </div>

      <!-- Row 2: Signal info -->
      <div style="display:flex;align-items:center;
        gap:6px;flex-wrap:wrap;margin-bottom:6px;
        font-size:11px;">
        <span style="color:${sigColor};font-weight:700;">
          ${_sigEmoji(stype)} ${stype}
        </span>
        <span style="color:#ffd700;font-weight:700;">${score}/10</span>
        <span style="color:#555;">${direction}</span>
      </div>

      <!-- Row 3: Price summary -->
      <div style="display:flex;gap:12px;flex-wrap:wrap;
        font-size:11px;color:#8b949e;">
        <span>Entry <b style="color:#c9d1d9;">${entry}</b></span>
        <span>Stop <b style="color:#f85149;">${stop}</b></span>
        <span>Target <b style="color:#00C851;">${target}</b></span>
        ${exitStr ? `<span>Exit <b style="color:#555;">${exitStr}</b></span>` : ''}
      </div>

      <!-- Rejection reason -->
      ${rejReason
        ? `<div style="font-size:10px;color:#f85149;margin-top:5px;">
             ✕ ${rejReason}${rejThresh}
           </div>`
        : ''}

      <!-- Inline expand detail -->
      ${!isRejView ? _expandDetail(sig, cardId, dayNum) : ''}
    </div>`;
}

// ── EXPANDED DETAIL SECTION ───────────────────────────
function _expandDetail(sig, cardId, dayNum) {
  const entry  = parseFloat(sig.entry || 0);
  const stop   = parseFloat(sig.stop  || 0);
  const target = parseFloat(sig.target_price || 0);
  const rr     = _rr(sig);

  const actualOpen = sig.actual_open
    ? parseFloat(sig.actual_open) : null;
  const gapPct     = sig.gap_pct != null
    ? parseFloat(sig.gap_pct) : null;
  const entryValid = sig.entry_valid;

  const entryDate = sig.date
    ? (typeof getEntryDate === 'function'
        ? getEntryDate(sig.date) : sig.date)
    : '—';

  const mfe = sig.mfe_pct != null ? parseFloat(sig.mfe_pct) : null;
  const mae = sig.mae_pct != null ? parseFloat(sig.mae_pct) : null;

  const outcome = sig.outcome || 'OPEN';

  return `
    <div id="jd-${cardId}"
      style="display:none;
        border-top:1px solid #21262d;
        margin-top:8px;padding-top:10px;">

      <!-- Entry / Stop / Target grid -->
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;
        gap:6px;margin-bottom:8px;">
        <div style="background:#0d1117;border-radius:6px;
          padding:6px 8px;text-align:center;">
          <div style="color:#555;font-size:9px;
            letter-spacing:1px;margin-bottom:2px;">ENTRY</div>
          <div style="color:#58a6ff;font-weight:700;font-size:13px;">
            ${entry > 0 ? '₹' + entry.toFixed(2) : '—'}
          </div>
        </div>
        <div style="background:#0d1117;border-radius:6px;
          padding:6px 8px;text-align:center;">
          <div style="color:#555;font-size:9px;
            letter-spacing:1px;margin-bottom:2px;">STOP</div>
          <div style="color:#f85149;font-weight:700;font-size:13px;">
            ${stop > 0 ? '₹' + stop.toFixed(2) : '—'}
          </div>
        </div>
        <div style="background:#0d1117;border-radius:6px;
          padding:6px 8px;text-align:center;">
          <div style="color:#555;font-size:9px;
            letter-spacing:1px;margin-bottom:2px;">TARGET</div>
          <div style="color:#00C851;font-weight:700;font-size:13px;">
            ${target > 0 ? '₹' + target.toFixed(2) : 'Day 6'}
          </div>
        </div>
      </div>

      <!-- R:R / Score / Grade row -->
      <div style="display:flex;gap:12px;flex-wrap:wrap;
        font-size:11px;color:#8b949e;margin-bottom:8px;">
        ${rr ? `<span>R:R <b style="color:#58a6ff;">${rr}×</b></span>` : ''}
        <span>Score <b style="color:${_scoreColor(sig.score)};">
          ${sig.score || 0}/10
        </b></span>
        <span>Grade <b style="color:${_gradeColor(sig.grade || '')};">
          ${sig.grade || '—'}
        </b></span>
      </div>

      <!-- Day progress bar -->
      ${dayNum !== null ? _dayProgress(dayNum) : ''}

      <!-- Timing -->
      <div style="font-size:10px;color:#555;
        margin-bottom:6px;line-height:1.7;">
        <span style="margin-right:12px;">
          Entry date: <b style="color:#8b949e;">
            ${typeof fmtDate === 'function' ? fmtDate(entryDate) : entryDate}
          </b>
        </span>
        <span>Exit: <b style="color:#8b949e;">
          ${sig.exit_date
            ? (typeof fmtDate === 'function'
                ? fmtDate(sig.exit_date) : sig.exit_date)
            : '—'}
        </b></span>
      </div>

      <!-- Actual open / gap -->
      ${actualOpen
        ? `<div style="font-size:11px;color:#8b949e;margin-bottom:6px;">
             Actual open: <b style="color:#c9d1d9;">
               ₹${actualOpen.toFixed(2)}
             </b>
             ${gapPct !== null
               ? `<span style="color:${Math.abs(gapPct) >= 3 ? '#f85149' : Math.abs(gapPct) >= 1.5 ? '#FFD700' : '#00C851'};
                   margin-left:6px;">
                   Gap: ${gapPct >= 0 ? '+' : ''}${gapPct.toFixed(1)}%
                   ${entryValid === false ? '⚠️ Gap too large' : '✓ OK'}
                 </span>`
               : ''}
           </div>`
        : ''}

      <!-- MFE / MAE -->
      <div style="display:flex;gap:12px;font-size:11px;
        color:#8b949e;margin-bottom:6px;">
        <span>Max Fav:
          <b style="color:${mfe !== null && mfe > 0 ? '#00C851' : '#555'};">
            ${mfe !== null ? '+' + mfe.toFixed(1) + '%' : '—'}
          </b>
        </span>
        <span>Max Adv:
          <b style="color:${mae !== null && mae > 0 ? '#f85149' : '#555'};">
            ${mae !== null ? '-' + mae.toFixed(1) + '%' : '—'}
          </b>
        </span>
      </div>

      <!-- Outcome status -->
      <div style="font-size:11px;color:#555;">
        Status:
        <b style="color:${
          outcome === 'OPEN'         ? '#FFD700' :
          outcome === 'TARGET_HIT'   ? '#00C851' :
          outcome === 'DAY6_WIN'     ? '#00C851' :
          outcome === 'STOP_HIT'     ? '#f85149' :
          outcome === 'DAY6_LOSS'    ? '#f85149' :
          '#8b949e'
        };">
          ${outcome === 'OPEN'
            ? 'OPEN — tracking active'
            : outcome.replace(/_/g, ' ')}
        </b>
        ${sig.pnl_pct != null
          ? ` · P&L: <b style="color:${parseFloat(sig.pnl_pct) >= 0 ? '#00C851' : '#f85149'};">
               ${parseFloat(sig.pnl_pct) >= 0 ? '+' : ''}${parseFloat(sig.pnl_pct).toFixed(1)}%
             </b>`
          : ''}
      </div>
    </div>`;
}

// Toggle inline detail
window.toggleJournalCard = function(cardId) {
  const detail = document.getElementById('jd-' + cardId);
  const arrow  = document.getElementById('ja-' + cardId);
  if (!detail) return;
  const open        = detail.style.display !== 'none';
  detail.style.display = open ? 'none' : 'block';
  if (arrow) arrow.textContent = open ? '▶' : '▼';
};

// ── FILTER TABS ──────────────────────────────────────
function _filterBar(tookN, rejN) {
  const tookActive = _jFilter === 'took';
  return `
    <div style="display:flex;gap:8px;
      padding:0 16px;margin-bottom:14px;">
      <button onclick="window._jFilter('took')"
        style="flex:1;
          background:${tookActive ? '#21262d' : 'none'};
          color:${tookActive ? '#c9d1d9' : '#555'};
          border:1px solid ${tookActive ? '#30363d' : '#21262d'};
          border-radius:6px;padding:7px 0;
          font-size:12px;cursor:pointer;
          font-weight:${tookActive ? '700' : '400'};">
        📥 Took (${tookN})
      </button>
      <button onclick="window._jFilter('rejected')"
        style="flex:1;
          background:${!tookActive ? '#21262d' : 'none'};
          color:${!tookActive ? '#c9d1d9' : '#555'};
          border:1px solid ${!tookActive ? '#30363d' : '#21262d'};
          border-radius:6px;padding:7px 0;
          font-size:12px;cursor:pointer;
          font-weight:${!tookActive ? '700' : '400'};">
        ✕ Rejected (${rejN})
      </button>
    </div>`;
}

// ── DATE HEADER ──────────────────────────────────────
function _dateHeader(dateStr) {
  if (!dateStr || dateStr === 'Unknown') return '—';
  try {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-IN', {
      weekday: 'long', day: 'numeric',
      month: 'short', year: 'numeric',
    });
  } catch(e) { return dateStr; }
}

// ── MAIN RENDER ──────────────────────────────────────
window.renderJournal = function(tietiy) {
  const el = document.getElementById('tab-content');
  if (!el) return;

  const raw = (tietiy.history && tietiy.history.history)
    ? tietiy.history.history : [];

  const took = raw.filter(
    s => s.layer === 'MINI' && s.action === 'TOOK');
  const rej  = raw.filter(
    s => s.layer === 'ALPHA' && s.action === 'REJECTED');

  const entries   = _jFilter === 'took' ? took : rej;
  const isRejView = _jFilter === 'rejected';

  // Group by date, newest first
  const byDate = {};
  entries.forEach(function(sig) {
    const d = sig.date || 'Unknown';
    if (!byDate[d]) byDate[d] = [];
    byDate[d].push(sig);
  });

  const dates = Object.keys(byDate)
    .sort((a, b) => b.localeCompare(a));

  // Sort each group by score desc
  dates.forEach(function(d) {
    byDate[d].sort((a, b) =>
      (parseFloat(b.score) || 0) - (parseFloat(a.score) || 0));
  });

  let html = `
    <div style="padding-bottom:80px;">

      <!-- Journal header -->
      <div style="padding:12px 16px 10px;
        display:flex;justify-content:space-between;
        align-items:center;">
        <span style="font-size:11px;color:#555;
          letter-spacing:1px;">📓 JOURNAL</span>
        <span style="font-size:10px;color:#555;">
          ${took.length} took · ${rej.length} rejected
        </span>
      </div>

      ${_filterBar(took.length, rej.length)}`;

  if (entries.length === 0) {
    html += `
      <div style="text-align:center;padding:48px 16px;
        color:#555;font-size:13px;">
        No ${isRejView ? 'rejected' : 'TOOK'} signals yet.
      </div>`;
  } else {
    dates.forEach(function(dateStr) {
      const group = byDate[dateStr];
      html += `
        <div style="padding:0 16px;">
          <div style="font-size:11px;color:#ffd700;
            font-weight:700;letter-spacing:1px;
            margin-bottom:10px;padding-top:12px;
            border-top:1px solid #21262d;">
            ${_dateHeader(dateStr)}
            <span style="color:#555;font-weight:400;
              margin-left:6px;">
              ${group.length} signal${group.length !== 1 ? 's' : ''}
            </span>
          </div>
          ${group.map(s => _compactCard(s, isRejView)).join('')}
        </div>`;
    });
  }

  html += '</div>';
  el.innerHTML = html;
};

})();
