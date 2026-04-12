// ── journal.js ────────────────────────────────────────
// Trade Journal — tracking screen only.
//
// V1 FIXES APPLIED:
// - U1c  : sticky journal header + filter tabs
// - L5   : Took/Skip personal decision buttons
// - L7   : Signal detail modal (full-screen overlay)
// - R5   : Expiry alerts banner (exit today / tomorrow)
// - R8   : SA (Second Attempt) tracking display
// ──────────────────────────────────────────────────────
(function () {

const OUTCOME_DONE = new Set([
  'TARGET_HIT','STOP_HIT','DAY6_WIN','DAY6_LOSS','DAY6_FLAT']);
const OUTCOME_WIN  = new Set(['TARGET_HIT','DAY6_WIN']);
const OUTCOME_LOSS = new Set(['STOP_HIT','DAY6_LOSS']);

let _jFilter = 'took';

window._jFilter = function(f) {
  _jFilter = f;
  if (window.TIETIY) window.renderJournal(window.TIETIY);
};

// ── SIGNAL MAP — for modal lookup (L7) ────────────────
window._jSigMap = {};

// ── L5: USER DECISION STORE ───────────────────────────
const _UD_KEY = 'tietiy_ud';

function _loadUD() {
  try {
    return JSON.parse(localStorage.getItem(_UD_KEY) || '{}');
  } catch(e) { return {}; }
}
function _getUD(id) { return _loadUD()[id] || null; }

window._jTookSkip = function(cardId, action) {
  try {
    const store = _loadUD();
    // tap same action again = toggle off
    if (store[cardId] === action) {
      delete store[cardId];
    } else {
      store[cardId] = action;
    }
    localStorage.setItem(_UD_KEY, JSON.stringify(store));
  } catch(e) {}
  if (window.TIETIY) window.renderJournal(window.TIETIY);
};

// ── HELPERS ───────────────────────────────────────────
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

// R8: second-attempt detection
function _isSA(signal) {
  return (signal || '').toUpperCase().endsWith('_SA');
}

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

function _fmtD(str) {
  if (!str) return '—';
  try {
    const d = new Date(str + 'T00:00:00');
    return d.toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short'
    });
  } catch(e) { return str; }
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

function _gradeColor(g) {
  return g === 'A' ? '#ffd700' : g === 'B' ? '#8b949e' : '#555';
}

function _badge(bg, color, label) {
  return `<span style="background:${bg};color:${color};
    border:1px solid ${color}33;border-radius:4px;
    padding:2px 8px;font-size:10px;font-weight:700;
    white-space:nowrap;">${label}</span>`;
}

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

  const day = typeof getDayNumber === 'function'
    ? getDayNumber(sig.date) : null;
  if (day !== null) {
    if (day >= 6) return _badge('#2a0a0a','#f85149','⚠️ EXIT TODAY');
    if (day >= 5) return _badge('#1a0f00','#FF8C00',`⚠️ Day ${day}/6`);
    if (day >= 3) return _badge('#1a1a0a','#FFD700', `Day ${day}/6`);
    return _badge('#1a1a0a','#555',`Day ${day}/6`);
  }
  return _badge('#1a1a0a','#555','OPEN');
}

// ── L7: QUALITY FLAGS ─────────────────────────────────
function _qualityFlags(sig) {
  const flags = [];
  if (sig.vol_confirm === true || sig.vol_confirm === 'true')
    flags.push({ label: 'Vol ✓',    color: '#58a6ff' });
  if (sig.sec_leading === true || sig.sec_leading === 'true')
    flags.push({ label: 'Sec Lead', color: '#58a6ff' });
  if (sig.rs_strong   === true || sig.rs_strong   === 'true')
    flags.push({ label: 'RS ↑',     color: '#58a6ff' });
  if (sig.grade_A     === true || sig.grade_A     === 'true'
                               || sig.grade === 'A')
    flags.push({ label: 'Grade A',  color: '#ffd700' });
  if (sig.bear_bonus  === true || sig.bear_bonus  === 'true')
    flags.push({ label: '🔥 Bear',  color: '#ffd700' });
  return flags;
}

// ── POST-TARGET TRACKING DISPLAY ──────────────────────
function _buildPostTargetSection(sig) {
  if (sig.outcome !== 'TARGET_HIT') return '';

  const day6Open   = sig.day6_open != null
    ? parseFloat(sig.day6_open) : null;
  const postMove   = sig.post_target_move != null
    ? parseFloat(sig.post_target_move) : null;
  const exitDay    = sig.exit_day || '—';

  if (day6Open === null && postMove === null) {
    return `
      <div style="background:#0a0d1a;border:1px solid #21262d;
        border-radius:6px;padding:8px 10px;margin-top:8px;
        font-size:10px;color:#555;">
        🔭 Shadow tracking: observing till Day 6 open
      </div>`;
  }

  const moveColor = postMove === null  ? '#555' :
                    postMove > 0       ? '#00C851' :
                    postMove < 0       ? '#f85149' : '#FFD700';
  const moveLabel = postMove === null  ? '—' :
                    postMove > 0
                      ? `▲ +${postMove.toFixed(1)}% continued`
                      : postMove < 0
                        ? `▼ ${postMove.toFixed(1)}% reversed`
                        : '~ Flat';
  const insight   = postMove === null  ? '' :
                    postMove > 1
                      ? 'Holding past target would have gained more'
                      : postMove < -1
                        ? 'Correct to exit at target — price reversed'
                        : 'Price moved sideways after target';

  return `
    <div style="background:#0a0d1a;
      border:1px solid #21262d33;
      border-left:3px solid #ffd70044;
      border-radius:6px;padding:10px 12px;margin-top:8px;">
      <div style="font-size:10px;color:#555;
        letter-spacing:1px;margin-bottom:8px;">
        🔭 POST-TARGET SHADOW DATA
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;
        gap:8px;margin-bottom:6px;">
        <div>
          <div style="font-size:9px;color:#555;margin-bottom:2px;">
            Target hit Day
          </div>
          <div style="font-size:13px;font-weight:700;color:#ffd700;">
            Day ${exitDay}
          </div>
        </div>
        <div>
          <div style="font-size:9px;color:#555;margin-bottom:2px;">
            Day 6 open price
          </div>
          <div style="font-size:13px;font-weight:700;color:#c9d1d9;">
            ${day6Open !== null ? '₹' + day6Open.toFixed(2) : 'Pending'}
          </div>
        </div>
        <div style="grid-column:1/-1;">
          <div style="font-size:9px;color:#555;margin-bottom:2px;">
            Move from target → Day 6
          </div>
          <div style="font-size:13px;font-weight:700;color:${moveColor};">
            ${moveLabel}
          </div>
        </div>
      </div>
      ${insight
        ? `<div style="font-size:10px;color:#555;
             border-top:1px solid #21262d;
             padding-top:6px;line-height:1.5;">
             💡 ${insight}
           </div>`
        : ''}
    </div>`;
}

// ── L7: SIGNAL DETAIL MODAL ───────────────────────────
function _buildModalHTML(sig) {
  const sym      = _sym(sig.symbol || sig.stock || '?');
  const stype    = sig.signal    || '?';
  const sigColor = _sigColor(stype);
  const score    = sig.score     || 0;
  const rr       = _rr(sig);
  const isSA_sig = _isSA(stype);
  const flags    = _qualityFlags(sig);
  const outcome  = sig.outcome   || 'OPEN';
  const dayNum   = typeof getDayNumber === 'function'
    ? getDayNumber(sig.date) : null;

  const regime   = sig.stock_regime || sig.regime || '—';
  const age      = sig.age  != null ? String(sig.age) : '—';

  const entry    = sig.entry
    ? parseFloat(sig.entry).toFixed(2)        : null;
  const stop     = sig.stop
    ? parseFloat(sig.stop).toFixed(2)         : null;
  const target   = sig.target_price
    ? parseFloat(sig.target_price).toFixed(2) : null;

  const mfe      = sig.mfe_pct != null ? parseFloat(sig.mfe_pct) : null;
  const mae      = sig.mae_pct != null ? parseFloat(sig.mae_pct) : null;

  const actOpen  = sig.actual_open != null
    ? parseFloat(sig.actual_open) : null;
  const gapPct   = sig.gap_pct    != null
    ? parseFloat(sig.gap_pct)     : null;

  const exitDateStr = sig.exit_date
    ? (typeof fmtDate === 'function'
        ? fmtDate(sig.exit_date) : sig.exit_date)
    : '—';

  const regimeColor =
    (regime === 'BEAR' || regime === 'Bear') ? '#f85149' :
    (regime === 'BULL' || regime === 'Bull') ? '#00C851' : '#FFD700';

  return `
    <div id="j-modal-overlay"
      style="position:fixed;top:0;left:0;right:0;bottom:0;
        z-index:9999;
        background:rgba(7,7,15,0.96);
        overflow-y:auto;
        -webkit-overflow-scrolling:touch;"
      onclick="window._closeSignalModal()">

      <div style="max-width:480px;margin:0 auto;
        padding:16px 16px 80px;min-height:100%;"
        onclick="event.stopPropagation()">

        <!-- TOP BAR -->
        <div style="display:flex;justify-content:space-between;
          align-items:flex-start;margin-bottom:14px;">
          <div>
            <div style="display:flex;align-items:center;
              gap:8px;flex-wrap:wrap;">
              <span style="color:#c9d1d9;font-size:22px;
                font-weight:700;">${sym}</span>
              <span style="color:${sigColor};font-size:13px;
                font-weight:700;">
                ${_sigEmoji(stype)} ${stype.replace(/_/g,' ')}
              </span>
              ${isSA_sig
                ? `<span style="background:#1a1a0a;
                     color:#ffd700;font-size:10px;font-weight:700;
                     border:1px solid #ffd70044;border-radius:4px;
                     padding:2px 7px;">2ND ATT</span>`
                : ''}
            </div>
            <div style="font-size:11px;color:#555;margin-top:3px;">
              ${sig.sector || ''}
              ${sig.sector && sig.date ? ' · ' : ''}
              ${_fmtD(sig.date)}
            </div>
          </div>
          <button onclick="window._closeSignalModal()"
            style="background:#21262d;border:1px solid #30363d;
              color:#c9d1d9;font-size:16px;font-weight:700;
              width:32px;height:32px;border-radius:6px;
              cursor:pointer;flex-shrink:0;line-height:1;
              -webkit-tap-highlight-color:transparent;">✕</button>
        </div>

        <!-- OUTCOME + SCORE + RR -->
        <div style="display:flex;gap:6px;flex-wrap:wrap;
          align-items:center;margin-bottom:14px;">
          ${_outcomeBadge(sig)}
          <span style="color:${_scoreColor(score)};
            font-size:13px;font-weight:700;
            background:#1c2128;border-radius:4px;
            padding:2px 8px;border:1px solid #30363d;">
            ${score}/10
          </span>
          ${rr
            ? `<span style="color:#58a6ff;font-size:11px;
                 background:#0d1117;border-radius:4px;
                 padding:2px 8px;">R:R ${rr}×</span>`
            : ''}
          ${sig.pnl_pct != null
            ? `<span style="font-size:12px;font-weight:700;
                 color:${parseFloat(sig.pnl_pct) >= 0
                   ? '#00C851' : '#f85149'};">
                 P&amp;L:&nbsp;${parseFloat(sig.pnl_pct) >= 0 ? '+' : ''}${
                   parseFloat(sig.pnl_pct).toFixed(1)}%
               </span>`
            : ''}
        </div>

        <!-- TRADE LEVELS -->
        <div style="background:#161b22;border:1px solid #21262d;
          border-radius:8px;padding:14px;margin-bottom:10px;">
          <div style="font-size:10px;color:#555;
            letter-spacing:1px;margin-bottom:10px;">TRADE LEVELS</div>
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;
            gap:8px;margin-bottom:10px;">
            <div style="text-align:center;background:#0d1117;
              border-radius:6px;padding:8px;">
              <div style="font-size:9px;color:#555;
                letter-spacing:1px;margin-bottom:3px;">ENTRY</div>
              <div style="color:#58a6ff;font-weight:700;font-size:14px;">
                ${entry ? '₹' + entry : '—'}
              </div>
            </div>
            <div style="text-align:center;background:#0d1117;
              border-radius:6px;padding:8px;">
              <div style="font-size:9px;color:#555;
                letter-spacing:1px;margin-bottom:3px;">STOP</div>
              <div style="color:#f85149;font-weight:700;font-size:14px;">
                ${stop ? '₹' + stop : '—'}
              </div>
            </div>
            <div style="text-align:center;background:#0d1117;
              border-radius:6px;padding:8px;">
              <div style="font-size:9px;color:#555;
                letter-spacing:1px;margin-bottom:3px;">TARGET</div>
              <div style="color:#00C851;font-weight:700;font-size:14px;">
                ${target ? '₹' + target : 'Day 6'}
              </div>
            </div>
          </div>
          ${dayNum !== null ? _dayProgress(dayNum) : ''}
          <div style="font-size:10px;color:#555;line-height:1.8;
            margin-top:4px;">
            Entry: <b style="color:#8b949e;">${_fmtD(sig.date)}</b>
            &nbsp;·&nbsp;
            Exit: <b style="color:#8b949e;">${exitDateStr}</b>
          </div>
          ${actOpen !== null
            ? `<div style="font-size:11px;color:#8b949e;
                 margin-top:6px;">
                 Actual open:
                 <b style="color:#c9d1d9;">₹${actOpen.toFixed(2)}</b>
                 ${gapPct !== null
                   ? `<span style="margin-left:6px;color:${
                       Math.abs(gapPct) >= 3   ? '#f85149' :
                       Math.abs(gapPct) >= 1.5 ? '#FFD700' : '#00C851'};">
                       Gap: ${gapPct >= 0 ? '+' : ''}${gapPct.toFixed(1)}%
                       ${sig.entry_valid === false
                         ? '⚠️ Too large' : '✓'}
                     </span>`
                   : ''}
               </div>`
            : ''}
        </div>

        <!-- SIGNAL CONTEXT -->
        <div style="background:#161b22;border:1px solid #21262d;
          border-radius:8px;padding:14px;margin-bottom:10px;">
          <div style="font-size:10px;color:#555;
            letter-spacing:1px;margin-bottom:10px;">
            SIGNAL CONTEXT
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;
            gap:10px;font-size:11px;margin-bottom:10px;">
            <div>
              <div style="color:#555;margin-bottom:2px;">Regime</div>
              <b style="color:${regimeColor};">${regime}</b>
            </div>
            <div>
              <div style="color:#555;margin-bottom:2px;">
                Age at signal
              </div>
              <b style="color:#c9d1d9;">${age}</b>
            </div>
            <div>
              <div style="color:#555;margin-bottom:2px;">Grade</div>
              <b style="color:${_gradeColor(sig.grade || '')};">
                ${sig.grade || '—'}
              </b>
            </div>
            <div>
              <div style="color:#555;margin-bottom:2px;">
                Generation
              </div>
              <b style="color:${sig.generation === 0
                ? '#555' : '#c9d1d9'};">
                ${sig.generation === 0 ? 'Backfill' : 'Live'}
              </b>
            </div>
          </div>

          ${flags.length > 0
            ? `<div style="display:flex;gap:6px;flex-wrap:wrap;
                 padding-top:8px;
                 border-top:1px solid #21262d;">
                 ${flags.map(f =>
                   `<span style="background:#1c2128;
                      color:${f.color};
                      border:1px solid ${f.color}44;
                      border-radius:4px;padding:3px 8px;
                      font-size:10px;font-weight:700;">
                      ${f.label}
                    </span>`
                 ).join('')}
               </div>`
            : ''}

          ${isSA_sig
            ? `<div style="background:#1a1a0a;
                 border:1px solid #ffd70033;border-radius:6px;
                 padding:8px 10px;margin-top:8px;
                 font-size:10px;color:#8b949e;line-height:1.6;">
                 <b style="color:#ffd700;">2nd Attempt</b> —
                 re-test of the same pattern after a prior signal.
                 ${stype.toUpperCase().startsWith('DOWN')
                   ? 'Age-0 only. If missed at the break, skip — edge is gone.'
                   : 'Ages 0–1 valid. Same entry rules as first attempt.'}
               </div>`
            : ''}
        </div>

        <!-- MAE / MFE -->
        ${(mfe !== null || mae !== null)
          ? `<div style="background:#161b22;border:1px solid #21262d;
               border-radius:8px;padding:14px;margin-bottom:10px;">
               <div style="font-size:10px;color:#555;
                 letter-spacing:1px;margin-bottom:10px;">
                 EXCURSION
               </div>
               <div style="display:flex;gap:20px;font-size:12px;">
                 <span style="color:#555;">Peak gain:
                   <b style="color:${mfe !== null && mfe > 0
                     ? '#00C851' : '#555'};">
                     ${mfe !== null ? '+' + mfe.toFixed(1) + '%' : '—'}
                   </b>
                 </span>
                 <span style="color:#555;">Max drawdown:
                   <b style="color:${mae !== null && mae > 0
                     ? '#f85149' : '#555'};">
                     ${mae !== null ? '-' + mae.toFixed(1) + '%' : '—'}
                   </b>
                 </span>
               </div>
             </div>`
          : ''}

        <!-- POST-TARGET -->
        ${_buildPostTargetSection(sig)}

      </div>
    </div>`;
}

window._openSignalModal = function(cardId) {
  const sig = window._jSigMap[cardId];
  if (!sig) return;
  const existing = document.getElementById('j-modal-overlay');
  if (existing) existing.remove();
  const tmp = document.createElement('div');
  tmp.innerHTML = _buildModalHTML(sig);
  document.body.appendChild(tmp.firstElementChild);
};

window._closeSignalModal = function() {
  const m = document.getElementById('j-modal-overlay');
  if (m) m.remove();
};

// backward-compat stub — no longer used but may be in cache
window.toggleJournalCard = function() {};

// ── L5: TOOK / SKIP ROW ───────────────────────────────
function _renderTookSkipRow(sig, cardId) {
  const decision = _getUD(cardId);

  if (decision === 'TOOK') {
    return `
      <div style="display:flex;gap:6px;margin-top:8px;
        padding-top:8px;border-top:1px solid #21262d;">
        <span style="flex:1;text-align:center;
          background:#0d2a0d;border:1px solid #00C85144;
          color:#00C851;font-size:11px;font-weight:700;
          border-radius:5px;padding:5px 0;">
          ✓ Took it
        </span>
        <button
          onclick="event.stopPropagation();
            window._jTookSkip('${cardId}','TOOK')"
          style="background:none;border:1px solid #21262d;
            color:#555;font-size:10px;border-radius:5px;
            padding:5px 10px;cursor:pointer;
            -webkit-tap-highlight-color:transparent;">
          undo
        </button>
      </div>`;
  }

  if (decision === 'SKIPPED') {
    return `
      <div style="display:flex;gap:6px;margin-top:8px;
        padding-top:8px;border-top:1px solid #21262d;">
        <span style="flex:1;text-align:center;
          background:#1c2128;border:1px solid #30363d;
          color:#555;font-size:11px;font-weight:700;
          border-radius:5px;padding:5px 0;">
          — Skipped
        </span>
        <button
          onclick="event.stopPropagation();
            window._jTookSkip('${cardId}','SKIPPED')"
          style="background:none;border:1px solid #21262d;
            color:#555;font-size:10px;border-radius:5px;
            padding:5px 10px;cursor:pointer;
            -webkit-tap-highlight-color:transparent;">
          undo
        </button>
      </div>`;
  }

  return `
    <div style="display:flex;gap:6px;margin-top:8px;
      padding-top:8px;border-top:1px solid #21262d;">
      <button
        onclick="event.stopPropagation();
          window._jTookSkip('${cardId}','TOOK')"
        style="flex:1;background:#0d1a0d;
          border:1px solid #00C85144;color:#00C851;
          font-size:11px;font-weight:700;
          border-radius:5px;padding:6px 0;cursor:pointer;
          -webkit-tap-highlight-color:transparent;">
        ✓ Took it
      </button>
      <button
        onclick="event.stopPropagation();
          window._jTookSkip('${cardId}','SKIPPED')"
        style="flex:1;background:#1c2128;
          border:1px solid #30363d;color:#555;
          font-size:11px;font-weight:700;
          border-radius:5px;padding:6px 0;cursor:pointer;
          -webkit-tap-highlight-color:transparent;">
        — Skip
      </button>
    </div>`;
}

// ── R5: EXPIRY ALERT BANNER ───────────────────────────
function _renderExpiryAlert(took) {
  const dayFn = typeof getDayNumber === 'function'
    ? getDayNumber : null;
  if (!dayFn) return '';

  const open  = took.filter(s => !OUTCOME_DONE.has(s.outcome || ''));
  const today = open.filter(s => dayFn(s.date) >= 6);
  const tmrw  = open.filter(s => dayFn(s.date) === 5);

  if (!today.length && !tmrw.length) return '';

  const _syms = function(arr) {
    return arr.map(s =>
      _sym(s.symbol || s.stock || '?')).join(', ');
  };

  return `
    <div style="margin:0 16px 10px;">
      ${today.length
        ? `<div style="background:#2a0808;
             border:1px solid #f8514966;
             border-radius:8px;padding:10px 12px;
             margin-bottom:6px;">
             <div style="font-size:11px;font-weight:700;
               color:#f85149;margin-bottom:4px;">
               ⚠️ EXIT TODAY — ${today.length}
               signal${today.length > 1 ? 's' : ''}
             </div>
             <div style="font-size:12px;color:#c9d1d9;
               font-weight:700;margin-bottom:3px;">
               ${_syms(today)}
             </div>
             <div style="font-size:10px;color:#555;">
               Day 6 reached · Exit at today's open
             </div>
           </div>`
        : ''}
      ${tmrw.length
        ? `<div style="background:#1a0f00;
             border:1px solid #FF8C0066;
             border-radius:8px;padding:10px 12px;">
             <div style="font-size:11px;font-weight:700;
               color:#FF8C00;margin-bottom:4px;">
               ⏰ EXIT TOMORROW — ${tmrw.length}
               signal${tmrw.length > 1 ? 's' : ''}
             </div>
             <div style="font-size:12px;color:#c9d1d9;
               font-weight:700;margin-bottom:3px;">
               ${_syms(tmrw)}
             </div>
             <div style="font-size:10px;color:#555;">
               Day 5 today · Exits at next open
             </div>
           </div>`
        : ''}
    </div>`;
}

// ── P&L SUMMARY ROW ───────────────────────────────────
function _buildPnlSummary(took) {
  const open     = took.filter(s => s.outcome === 'OPEN' || !s.outcome);
  const resolved = took.filter(s => s.outcome && s.outcome !== 'OPEN');

  const openWithPnl = open.filter(s => s.pnl_pct != null);
  const totalUnreal = openWithPnl.reduce(
    (sum, s) => sum + parseFloat(s.pnl_pct || 0), 0);
  const avgUnreal   = openWithPnl.length > 0
    ? (totalUnreal / openWithPnl.length) : null;

  const wins   = resolved.filter(
    s => s.outcome === 'TARGET_HIT' || s.outcome === 'DAY6_WIN');
  const losses = resolved.filter(
    s => s.outcome === 'STOP_HIT'   || s.outcome === 'DAY6_LOSS');
  const flats  = resolved.filter(s => s.outcome === 'DAY6_FLAT');

  const winRate = resolved.length > 0
    ? Math.round(wins.length / resolved.length * 100) : null;

  const avgWinPnl = wins.length > 0
    ? wins.reduce((s, t) => s + parseFloat(t.pnl_pct || 0), 0) /
      wins.length
    : null;
  const avgLossPnl = losses.length > 0
    ? losses.reduce((s, t) => s + parseFloat(t.pnl_pct || 0), 0) /
      losses.length
    : null;

  const exitToday = open.filter(s => {
    const d = typeof getDayNumber === 'function'
      ? getDayNumber(s.date) : 0;
    return d >= 6;
  }).length;
  const exitTomorrow = open.filter(s => {
    const d = typeof getDayNumber === 'function'
      ? getDayNumber(s.date) : 0;
    return d === 5;
  }).length;

  const unrealColor = avgUnreal === null ? '#555' :
                      avgUnreal > 0      ? '#00C851' :
                      avgUnreal < 0      ? '#f85149' : '#FFD700';

  const urgencyHtml = (exitToday > 0 || exitTomorrow > 0)
    ? `<div style="font-size:10px;margin-top:4px;">
         ${exitToday > 0
           ? `<span style="color:#f85149;font-weight:700;">
               ⚠️ ${exitToday} exit today
             </span>`
           : ''}
         ${exitTomorrow > 0
           ? `<span style="color:#FF8C00;margin-left:8px;">
               ${exitTomorrow} exit tomorrow
             </span>`
           : ''}
       </div>`
    : '';

  return `
    <div style="margin:0 16px 14px;
      background:#161b22;border-radius:8px;
      border:1px solid #21262d;padding:12px 14px;">
      <div style="font-size:10px;color:#555;
        letter-spacing:1px;margin-bottom:10px;">
        PORTFOLIO SUMMARY
      </div>
      <div style="display:grid;
        grid-template-columns:1fr 1fr;gap:10px;">
        <div>
          <div style="font-size:10px;color:#555;margin-bottom:4px;">
            Open positions
          </div>
          <div style="font-size:20px;font-weight:700;color:#c9d1d9;">
            ${open.length}
          </div>
          <div style="font-size:11px;color:#555;margin-top:2px;">
            Avg P&amp;L:
            <span style="color:${unrealColor};font-weight:700;">
              ${avgUnreal !== null
                ? (avgUnreal >= 0 ? '+' : '') +
                  avgUnreal.toFixed(1) + '%'
                : '—'}
            </span>
          </div>
          ${urgencyHtml}
        </div>
        <div>
          <div style="font-size:10px;color:#555;margin-bottom:4px;">
            Resolved
          </div>
          <div style="display:flex;align-items:baseline;gap:6px;">
            <span style="font-size:20px;font-weight:700;
              color:#c9d1d9;">${resolved.length}</span>
            ${winRate !== null
              ? `<span style="font-size:12px;font-weight:700;
                  color:${winRate >= 70 ? '#00C851' :
                          winRate >= 50 ? '#FFD700' : '#f85149'};">
                  ${winRate}% WR
                </span>`
              : ''}
          </div>
          <div style="display:flex;gap:8px;font-size:11px;
            margin-top:4px;">
            <span style="color:#00C851;">
              W:${wins.length}
              ${avgWinPnl !== null
                ? `<span style="color:#555;font-size:10px;">
                    (+${avgWinPnl.toFixed(1)}%)</span>` : ''}
            </span>
            <span style="color:#f85149;">
              L:${losses.length}
              ${avgLossPnl !== null
                ? `<span style="color:#555;font-size:10px;">
                    (${avgLossPnl.toFixed(1)}%)</span>` : ''}
            </span>
            <span style="color:#FFD700;">F:${flats.length}</span>
          </div>
        </div>
      </div>
    </div>`;
}

// ── COMPACT CARD ──────────────────────────────────────
function _compactCard(sig, isRejView) {
  const sym        = _sym(sig.symbol || sig.stock || '?');
  const stype      = sig.signal    || '?';
  const sigColor   = _sigColor(stype);
  const score      = sig.score     || 0;
  const direction  = sig.direction === 'SHORT' ? '↓ SHORT' : '↑ LONG';
  const sector     = sig.sector    || '';
  const grade      = sig.grade     || '';
  const bearBonus  = sig.bear_bonus === true || sig.bear_bonus === 'true';
  const stkRegime  = sig.stock_regime || null;
  const isBackfill = sig.generation === 0;
  const isSA_sig   = _isSA(stype);        // R8

  const entry  = sig.entry
    ? '₹' + parseFloat(sig.entry).toFixed(2)        : '—';
  const stop   = sig.stop
    ? '₹' + parseFloat(sig.stop).toFixed(2)         : '—';
  const target = sig.target_price
    ? '₹' + parseFloat(sig.target_price).toFixed(2) : '—';
  const exitStr = sig.exit_date ? _fmtD(sig.exit_date) : null;

  const rr    = _rr(sig);
  const cardId = (sig.id ||
    (sym + '-' + stype + '-' + (sig.date || ''))).replace(/[^a-zA-Z0-9-]/g, '-');

  const rejReason = isRejView && sig.rejection_reason
    ? _rejLabel(sig.rejection_reason) : null;
  const rejThresh = isRejView && sig.rejection_threshold != null
    ? ` (min: ${sig.rejection_threshold})` : '';

  // register in signal map for L7 modal
  window._jSigMap[cardId] = sig;

  return `
    <div style="background:#161b22;
      border:1px solid #21262d;
      border-left:3px solid ${sigColor};
      border-radius:8px;padding:10px 12px 8px;
      margin-bottom:8px;
      ${isBackfill ? 'opacity:0.75;' : ''}">

      <!-- ROW 1: symbol + badges + modal button -->
      <div style="display:flex;justify-content:space-between;
        align-items:flex-start;margin-bottom:5px;">
        <div style="display:flex;align-items:center;
          gap:5px;flex-wrap:wrap;flex:1;min-width:0;">
          <span style="color:#c9d1d9;font-size:14px;
            font-weight:700;">${sym}</span>
          <span style="color:#555;font-size:11px;">${sector}</span>
          ${grade
            ? `<span style="color:${_gradeColor(grade)};
                font-size:10px;font-weight:700;
                border:1px solid ${_gradeColor(grade)}44;
                border-radius:3px;padding:0 4px;">
                ${grade}
              </span>`
            : ''}
          ${bearBonus
            ? '<span style="font-size:10px;">🔥</span>' : ''}
          ${isSA_sig
            ? `<span style="background:#1a1a0a;color:#ffd700;
                font-size:9px;font-weight:700;
                border:1px solid #ffd70033;border-radius:3px;
                padding:1px 5px;">2ND</span>`
            : ''}
          ${stkRegime
            ? `<span style="font-size:9px;color:#555;
                background:#1c2128;border-radius:3px;
                padding:1px 4px;">stk:${stkRegime}</span>`
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
            ? `<button
                onclick="event.stopPropagation();
                  window._openSignalModal('${cardId}')"
                style="background:none;border:none;
                  color:#555;font-size:14px;cursor:pointer;
                  padding:0 2px;line-height:1;
                  -webkit-tap-highlight-color:transparent;">
                ▶
              </button>`
            : ''}
        </div>
      </div>

      <!-- ROW 2: signal type + score -->
      <div style="display:flex;align-items:center;
        gap:6px;flex-wrap:wrap;margin-bottom:6px;font-size:11px;">
        <span style="color:${sigColor};font-weight:700;">
          ${_sigEmoji(stype)} ${stype.replace(/_/g,' ')}
        </span>
        <span style="color:${_scoreColor(score)};font-weight:700;">
          ${score}/10
        </span>
        <span style="color:#555;">${direction}</span>
        ${rr
          ? `<span style="color:#555;">
               R:R <b style="color:#58a6ff;">${rr}×</b>
             </span>`
          : ''}
      </div>

      <!-- ROW 3: levels -->
      <div style="display:flex;gap:12px;flex-wrap:wrap;
        font-size:11px;color:#8b949e;">
        <span>Entry <b style="color:#c9d1d9;">${entry}</b></span>
        <span>Stop  <b style="color:#f85149;">${stop}</b></span>
        <span>Target <b style="color:#00C851;">${target}</b></span>
        ${exitStr
          ? `<span>Exit <b style="color:#555;">${exitStr}</b></span>`
          : ''}
      </div>

      ${rejReason
        ? `<div style="font-size:10px;color:#f85149;margin-top:5px;">
             ✕ ${rejReason}${rejThresh}
           </div>`
        : ''}

      <!-- L5: Took/Skip row (non-backfill, took view only) -->
      ${!isRejView && !isBackfill
        ? _renderTookSkipRow(sig, cardId) : ''}
    </div>`;
}

// ── FILTER TABS ───────────────────────────────────────
function _filterBar(tookN, rejN) {
  const tookActive = _jFilter === 'took';
  return `
    <div style="display:flex;gap:8px;padding:0 16px 10px;">
      <button onclick="window._jFilter('took')"
        style="flex:1;
          background:${tookActive ? '#21262d' : 'none'};
          color:${tookActive ? '#c9d1d9' : '#555'};
          border:1px solid ${tookActive ? '#30363d' : '#21262d'};
          border-radius:6px;padding:7px 0;font-size:12px;
          cursor:pointer;
          font-weight:${tookActive ? '700' : '400'};
          -webkit-tap-highlight-color:transparent;">
        📥 Took (${tookN})
      </button>
      <button onclick="window._jFilter('rejected')"
        style="flex:1;
          background:${!tookActive ? '#21262d' : 'none'};
          color:${!tookActive ? '#c9d1d9' : '#555'};
          border:1px solid ${!tookActive ? '#30363d' : '#21262d'};
          border-radius:6px;padding:7px 0;font-size:12px;
          cursor:pointer;
          font-weight:${!tookActive ? '700' : '400'};
          -webkit-tap-highlight-color:transparent;">
        ✕ Rejected (${rejN})
      </button>
    </div>`;
}

// ── DATE HEADER ───────────────────────────────────────
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

// ── MAIN RENDER ───────────────────────────────────────
window.renderJournal = function(tietiy) {
  const el = document.getElementById('tab-content');
  if (!el) return;

  // reset signal map on each render
  window._jSigMap = {};

  const raw = (tietiy.history && tietiy.history.history)
    ? tietiy.history.history : [];

  const took = raw.filter(
    s => s.layer === 'MINI' && s.action === 'TOOK');
  const rej  = raw.filter(
    s => s.layer === 'ALPHA' && s.action === 'REJECTED');

  const entries   = _jFilter === 'took' ? took : rej;
  const isRejView = _jFilter === 'rejected';

  const byDate = {};
  entries.forEach(function(sig) {
    const d = sig.date || 'Unknown';
    if (!byDate[d]) byDate[d] = [];
    byDate[d].push(sig);
  });

  const dates = Object.keys(byDate)
    .sort((a, b) => b.localeCompare(a));

  dates.forEach(function(d) {
    byDate[d].sort((a, b) =>
      (parseFloat(b.score) || 0) - (parseFloat(a.score) || 0));
  });

  // U1c: sticky header + filter tabs
  let html = `
    <div style="padding-bottom:80px;">

      <div style="position:sticky;top:0;z-index:10;
        background:#07070f;
        border-bottom:1px solid #21262d;">
        <div style="padding:10px 16px 0;
          display:flex;justify-content:space-between;
          align-items:center;">
          <span style="font-size:11px;color:#555;
            letter-spacing:1px;">📓 JOURNAL</span>
          <span style="font-size:10px;color:#555;">
            ${took.length} took · ${rej.length} rejected
          </span>
        </div>
        ${_filterBar(took.length, rej.length)}
      </div>

      <!-- R5: expiry alerts (took view only) -->
      ${_jFilter === 'took' && took.length > 0
        ? _renderExpiryAlert(took) : ''}

      <!-- portfolio summary (took view only) -->
      ${_jFilter === 'took' && took.length > 0
        ? _buildPnlSummary(took) : ''}`;

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
