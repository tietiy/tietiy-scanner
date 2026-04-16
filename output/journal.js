// ── journal.js ────────────────────────────────────────
// Trade Journal — tracking screen only.
//
// V1 FIXES APPLIED:
// - U1c  : sticky journal header + filter tabs
// - L5   : Took/Skip personal decision buttons
// - L7   : Signal detail modal (full-screen overlay)
// - R5   : Expiry alerts banner (exit today / tomorrow)
// - R8   : SA (Second Attempt) tracking display
//
// V1.1 FIXES:
// - H3   : Stop proximity traffic light on cards
// - H4   : Unrealized P&L on open journal cards
// - H5   : Capital at risk in portfolio summary
// - H6   : R:R shows gap-adjusted actual
// - H7   : Open Chart wires to TradingView NSE:SYMBOL
// - H14  : Failure reason tag on resolved cards
// - H15  : Win reason tag on resolved cards
// - M2   : Day X/6 shown alongside exit date on cards
// - M6   : Rejection reason summary at top of tab
// - MC4  : Why this trade in plain language
// - LC3  : Full failure reason shown in modal
// - D6-6 : Day 6 open price shown in modal
// - J1   : Resolved tab — WR, wins, losses, avg P&L
// - J2   : TradingView link fixed for iOS PWA —
//          window.open() replaces target="_blank"
// - TR1  : Duplicate signal same stock same date
//          grouped — shows ×N count badge, keeps
//          highest score signal as primary card
//
// V2 FIXES:
// - JJ1  : EXIT TOMORROW count fixed — _renderExpiryAlert
//          and _buildPnlSummary now use exit_date field
//          comparison (same as Telegram bot) instead of
//          getDayNumber(). Fixes Journal showing 3 while
//          Telegram shows 40.
// - JJ2  : Capital deployed > 100% shows red warning
//          banner, not just a color change on the text.
// - JJ3  : Header "took" counter now reads user
//          localStorage decisions, not raw signal count.
//          136 was system signals; now shows genuine
//          user Took-it presses.
// ──────────────────────────────────────────────────────
(function () {

const OUTCOME_DONE = new Set([
  'TARGET_HIT','STOP_HIT',
  'DAY6_WIN','DAY6_LOSS','DAY6_FLAT']);
const OUTCOME_WIN  = new Set(['TARGET_HIT','DAY6_WIN']);
const OUTCOME_LOSS = new Set(['STOP_HIT','DAY6_LOSS']);

let _jFilter = 'took';

window._jFilter = function(f) {
  _jFilter = f;
  if (window.TIETIY) window.renderJournal(window.TIETIY);
};

window._jSigMap = {};

// ── L5: USER DECISION STORE ───────────────────────────
const _UD_KEY = 'tietiy_ud';

function _loadUD() {
  try {
    return JSON.parse(
      localStorage.getItem(_UD_KEY) || '{}');
  } catch(e) { return {}; }
}
function _getUD(id) { return _loadUD()[id] || null; }

window._jTookSkip = function(cardId, action) {
  try {
    const store = _loadUD();
    if (store[cardId] === action) {
      delete store[cardId];
    } else {
      store[cardId] = action;
    }
    localStorage.setItem(
      _UD_KEY, JSON.stringify(store));
  } catch(e) {}
  if (window.TIETIY)
    window.renderJournal(window.TIETIY);
};

// ── JJ3: USER TOOK COUNT FROM LOCALSTORAGE ────────────
// JJ3 FIX: Count only signals where user explicitly
// pressed "Took it" — stored in localStorage.
// Previously counted all system TOOK-flagged signals
// (inflated to 136). Now counts genuine user decisions.
function _countUserTook(signals) {
  const ud = _loadUD();
  return signals.filter(function(s) {
    const sym = _sym(s.symbol || '');
    const cardId = (s.id ||
      (sym + '-' + (s.signal||'')
         + '-' + (s.date||'')))
      .replace(/[^a-zA-Z0-9-]/g, '-');
    return ud[cardId] === 'TOOK';
  }).length;
}

// ── JJ1: DATE HELPERS ─────────────────────────────────
// JJ1 FIX: Use device local date (IST on user's iPad)
// not ISO string which gives UTC date.
function _todayISO() {
  const d = new Date();
  return d.getFullYear() + '-'
    + String(d.getMonth() + 1).padStart(2, '0')
    + '-'
    + String(d.getDate()).padStart(2, '0');
}

function _tomorrowISO() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.getFullYear() + '-'
    + String(d.getMonth() + 1).padStart(2, '0')
    + '-'
    + String(d.getDate()).padStart(2, '0');
}

// ── HELPERS ───────────────────────────────────────────
function _sym(s) {
  return (s || '').replace('.NS', '');
}

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
    ${dayNum >= 5
      ? 'border:1px solid ' + color + '33;' : ''}">
    Day ${dayNum}/6${icon}
  </span>`;
}

function _dayProgress(dayNum) {
  const pct   = Math.min(
    Math.round((dayNum / 6) * 100), 100);
  const color = dayNum >= 6 ? '#f85149' :
                dayNum >= 5 ? '#FF8C00' :
                dayNum >= 3 ? '#FFD700' : '#58a6ff';
  return `
    <div style="margin-bottom:6px;">
      <div style="display:flex;
        justify-content:space-between;
        font-size:10px;color:#555;margin-bottom:3px;">
        <span>Trade progress</span>
        <span style="color:${color};">
          Day ${dayNum} of 6
        </span>
      </div>
      <div style="background:#21262d;border-radius:3px;
        height:5px;overflow:hidden;">
        <div style="background:${color};height:5px;
          width:${pct}%;border-radius:3px;
          transition:width 0.3s ease;"></div>
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
  const e = parseFloat(
    sig.actual_open || sig.entry || 0);
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
  const label = map[reason]
    || (reason || 'Filtered').replace(/_/g,' ');
  return `ALPHA: ${label}`;
}

function _gradeColor(g) {
  return g === 'A' ? '#ffd700'
    : g === 'B' ? '#8b949e' : '#555';
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
      ? ` +${parseFloat(sig.pnl_pct).toFixed(1)}%`
      : '';
    return _badge('#0d2a0d','#00C851',
      `🎯 TARGET${pnl}`);
  }
  if (outcome === 'STOP_HIT') {
    const pnl = sig.pnl_pct != null
      ? ` ${parseFloat(sig.pnl_pct).toFixed(1)}%`
      : '';
    return _badge('#2a0a0a','#f85149',
      `🛑 STOP${pnl}`);
  }
  if (outcome === 'DAY6_WIN') {
    const pnl = sig.pnl_pct != null
      ? ` +${parseFloat(sig.pnl_pct).toFixed(1)}%`
      : '';
    return _badge('#0d2a0d','#00C851',
      `✓ DAY6 WIN${pnl}`);
  }
  if (outcome === 'DAY6_LOSS') {
    const pnl = sig.pnl_pct != null
      ? ` ${parseFloat(sig.pnl_pct).toFixed(1)}%`
      : '';
    return _badge('#2a0a0a','#f85149',
      `✕ DAY6 LOSS${pnl}`);
  }
  if (outcome === 'DAY6_FLAT')
    return _badge('#1a1a0a','#FFD700','~ FLAT');
  if (result === 'REJECTED')
    return _badge('#2a0a0a','#f85149','✕ REJECTED');

  const day = typeof getDayNumber === 'function'
    ? getDayNumber(sig.date) : null;
  if (day !== null) {
    if (day >= 6)
      return _badge('#2a0a0a','#f85149',
        '⚠️ EXIT TODAY');
    if (day >= 5)
      return _badge('#1a0f00','#FF8C00',
        `⚠️ Day ${day}/6`);
    if (day >= 3)
      return _badge('#1a1a0a','#FFD700',
        `Day ${day}/6`);
    return _badge('#1a1a0a','#555',`Day ${day}/6`);
  }
  return _badge('#1a1a0a','#555','OPEN');
}

// ── QUALITY FLAGS ─────────────────────────────────────
function _qualityFlags(sig) {
  const flags = [];
  if (sig.vol_confirm === true
      || sig.vol_confirm === 'true')
    flags.push({ label: 'Vol ✓',    color: '#58a6ff' });
  if (sig.sec_leading === true
      || sig.sec_leading === 'true')
    flags.push({ label: 'Sec Lead', color: '#58a6ff' });
  if (sig.rs_strong === true
      || sig.rs_strong === 'true')
    flags.push({ label: 'RS ↑',     color: '#58a6ff' });
  if (sig.grade_A === true
      || sig.grade_A === 'true'
      || sig.grade === 'A')
    flags.push({ label: 'Grade A',  color: '#ffd700' });
  if (sig.bear_bonus === true
      || sig.bear_bonus === 'true')
    flags.push({ label: '🔥 Bear',  color: '#ffd700' });
  return flags;
}

// ── H3: STOP PROXIMITY ────────────────────────────────
function _getLTP(sig, ltpPrices) {
  if (!ltpPrices) return null;
  const prices   = ltpPrices.prices || ltpPrices || {};
  const symKey   = sig.symbol || '';
  const symClean = _sym(symKey);
  const val = prices[symKey] || prices[symClean];
  if (!val) return null;
  if (typeof val === 'object' && val.ltp)
    return parseFloat(val.ltp);
  return parseFloat(val);
}

function _stopProximityDot(sig, ltpPrices) {
  const ltp  = _getLTP(sig, ltpPrices);
  const stop = parseFloat(sig.stop || 0);
  if (!ltp || !stop) return '';

  const dirn = sig.direction || 'LONG';
  const buf  = dirn === 'LONG'
    ? (ltp - stop) / stop * 100
    : (stop - ltp) / stop * 100;

  const color = buf < 0 ? '#f85149' :
                buf < 2 ? '#f85149' :
                buf < 5 ? '#FF8C00' : '#00C851';
  const title = buf < 0
    ? 'Stop breached'
    : `${buf.toFixed(1)}% above stop`;

  return `<span title="${title}"
    style="display:inline-block;
      width:7px;height:7px;border-radius:50%;
      background:${color};margin-left:4px;
      vertical-align:middle;flex-shrink:0;">
  </span>`;
}

// ── H4: UNREALIZED P&L ────────────────────────────────
function _unrealizedPnl(sig, ltpPrices) {
  const ltp   = _getLTP(sig, ltpPrices);
  const entry = parseFloat(
    sig.actual_open || sig.entry || 0);
  if (!ltp || !entry) return null;
  const dirn = sig.direction || 'LONG';
  const raw  = (ltp - entry) / entry * 100;
  return dirn === 'LONG' ? raw : -raw;
}

// ── H14/H15: FAILURE/WIN REASON TAG ───────────────────
function _reasonTag(sig) {
  const outcome = sig.outcome || '';
  const reason  = sig.failure_reason || '';
  if (!reason) return '';

  const isWin = OUTCOME_WIN.has(outcome);
  const color = isWin ? '#00C851' : '#8b949e';
  const bg    = isWin ? '#0d2a0d' : '#1c2128';

  return `
    <div style="font-size:10px;color:${color};
      background:${bg};border-radius:4px;
      padding:4px 8px;margin-top:6px;
      line-height:1.4;border:1px solid ${color}22;">
      💡 ${reason}
    </div>`;
}

// ── MC4: WHY THIS TRADE ───────────────────────────────
function _whyThisTrade(sig) {
  const stype  = (sig.signal || '').toUpperCase();
  const bear   = sig.bear_bonus === true
    || sig.bear_bonus === 'true';
  const vol    = sig.vol_confirm === true
    || sig.vol_confirm === 'true';
  const sec    = sig.sec_leading === true
    || sig.sec_leading === 'true';
  const age    = parseInt(sig.age || 0);
  const lines  = [];

  if (stype.includes('UP_TRI')) {
    lines.push(
      'Price broke out of a tight range — '
      + 'buyers took control');
    if (age === 0)
      lines.push(
        'Fresh breakout today — most traders '
        + 'haven\'t seen it yet');
    if (bear)
      lines.push(
        'Market is falling but this stock is '
        + 'pushing up — strongest signal type 🔥');
    if (vol)
      lines.push(
        'High volume confirms the breakout — '
        + 'real buyers, not a fake move');
    if (sec)
      lines.push(
        'Sector is leading the market — '
        + 'group momentum supports the trade');
  } else if (stype.includes('DOWN_TRI')) {
    lines.push(
      'Stock failed to hold a key level — '
      + 'sellers stepped in');
    if (age === 0)
      lines.push(
        'Fresh breakdown today — edge is highest '
        + 'at age 0, drops sharply after');
    lines.push(
      'Short opportunity — price likely to fall '
      + 'toward target within 6 days');
    if (vol)
      lines.push(
        'Volume confirms the breakdown — '
        + 'not just a low-activity drift');
  } else if (stype.includes('BULL_PROXY')) {
    lines.push(
      'Stock bounced off a support level '
      + 'with strength');
    lines.push(
      'Risk is defined — stop is just below '
      + 'the support floor');
    if (vol)
      lines.push(
        'Volume confirmed the bounce — '
        + 'buyers defended the level');
    if (sec)
      lines.push(
        'Sector strength adds extra conviction '
        + 'to this bounce');
  }

  if (!lines.length) return [];
  return lines;
}

// ── POST-TARGET TRACKING ──────────────────────────────
function _buildPostTargetSection(sig) {
  if (sig.outcome !== 'TARGET_HIT') return '';

  const day6Open = sig.day6_open != null
    ? parseFloat(sig.day6_open) : null;
  const postMove = sig.post_target_move != null
    ? parseFloat(sig.post_target_move) : null;
  const exitDay  = sig.exit_day || '—';

  if (day6Open === null && postMove === null) {
    return `
      <div style="background:#0a0d1a;
        border:1px solid #21262d;
        border-radius:6px;padding:8px 10px;
        margin-top:8px;font-size:10px;color:#555;">
        🔭 Shadow tracking: observing till Day 6 open
      </div>`;
  }

  const moveColor = postMove === null  ? '#555' :
                    postMove > 0       ? '#00C851' :
                    postMove < 0       ? '#f85149'
                                       : '#FFD700';
  const moveLabel = postMove === null  ? '—' :
    postMove > 0
      ? `▲ +${postMove.toFixed(1)}% continued`
      : postMove < 0
        ? `▼ ${postMove.toFixed(1)}% reversed`
        : '~ Flat';
  const insight = postMove === null ? '' :
    postMove > 1
      ? 'Holding past target would have gained more'
      : postMove < -1
        ? 'Correct to exit at target — price reversed'
        : 'Price moved sideways after target';

  return `
    <div style="background:#0a0d1a;
      border:1px solid #21262d33;
      border-left:3px solid #ffd70044;
      border-radius:6px;padding:10px 12px;
      margin-top:8px;">
      <div style="font-size:10px;color:#555;
        letter-spacing:1px;margin-bottom:8px;">
        🔭 POST-TARGET SHADOW DATA
      </div>
      <div style="display:grid;
        grid-template-columns:1fr 1fr;
        gap:8px;margin-bottom:6px;">
        <div>
          <div style="font-size:9px;color:#555;
            margin-bottom:2px;">Target hit Day</div>
          <div style="font-size:13px;font-weight:700;
            color:#ffd700;">Day ${exitDay}</div>
        </div>
        <div>
          <div style="font-size:9px;color:#555;
            margin-bottom:2px;">Day 6 open price</div>
          <div style="font-size:13px;font-weight:700;
            color:#c9d1d9;">
            ${day6Open !== null
              ? '₹' + day6Open.toFixed(2)
              : 'Pending'}
          </div>
        </div>
        <div style="grid-column:1/-1;">
          <div style="font-size:9px;color:#555;
            margin-bottom:2px;">
            Move from target → Day 6
          </div>
          <div style="font-size:13px;font-weight:700;
            color:${moveColor};">${moveLabel}</div>
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

// ── J2: SIGNAL DETAIL MODAL ───────────────────────────
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
  const isResolved = OUTCOME_DONE.has(outcome);

  const regime = sig.stock_regime
    || sig.regime || '—';
  const age    = sig.age != null
    ? String(sig.age) : '—';

  const entry  = sig.entry
    ? parseFloat(sig.entry).toFixed(2)        : null;
  const stop   = sig.stop
    ? parseFloat(sig.stop).toFixed(2)         : null;
  const target = sig.target_price
    ? parseFloat(sig.target_price).toFixed(2) : null;

  const mfe = sig.mfe_pct != null
    ? parseFloat(sig.mfe_pct) : null;
  const mae = sig.mae_pct != null
    ? parseFloat(sig.mae_pct) : null;

  const actOpen = sig.actual_open != null
    ? parseFloat(sig.actual_open) : null;
  const gapPct  = sig.gap_pct != null
    ? parseFloat(sig.gap_pct) : null;

  const day6Open = sig.day6_open != null
    ? parseFloat(sig.day6_open) : null;

  const exitDateStr = sig.exit_date
    ? (typeof fmtDate === 'function'
        ? fmtDate(sig.exit_date) : sig.exit_date)
    : '—';

  const regimeColor =
    (regime === 'BEAR' || regime === 'Bear')
      ? '#f85149' :
    (regime === 'BULL' || regime === 'Bull')
      ? '#00C851' : '#FFD700';

  const tvURL = 'https://www.tradingview.com/chart/'
    + '?symbol=NSE:' + sym;

  const whyLines      = _whyThisTrade(sig);
  const failureReason = isResolved && sig.failure_reason
    ? sig.failure_reason : null;

  return `
    <div id="j-modal-overlay"
      style="position:fixed;top:0;left:0;
        right:0;bottom:0;z-index:9999;
        background:rgba(7,7,15,0.96);
        overflow-y:auto;
        -webkit-overflow-scrolling:touch;"
      onclick="window._closeSignalModal()">

      <div style="max-width:480px;margin:0 auto;
        padding:16px 16px 80px;min-height:100%;"
        onclick="event.stopPropagation()">

        <!-- TOP BAR -->
        <div style="display:flex;
          justify-content:space-between;
          align-items:flex-start;
          margin-bottom:14px;">
          <div>
            <div style="display:flex;
              align-items:center;
              gap:8px;flex-wrap:wrap;">
              <span style="color:#c9d1d9;
                font-size:22px;font-weight:700;">
                ${sym}
              </span>
              <span style="color:${sigColor};
                font-size:13px;font-weight:700;">
                ${_sigEmoji(stype)}
                ${stype.replace(/_/g,' ')}
              </span>
              ${isSA_sig
                ? `<span style="background:#1a1a0a;
                     color:#ffd700;font-size:10px;
                     font-weight:700;
                     border:1px solid #ffd70044;
                     border-radius:4px;
                     padding:2px 7px;">2ND ATT</span>`
                : ''}
            </div>
            <div style="font-size:11px;color:#555;
              margin-top:3px;">
              ${sig.sector || ''}
              ${sig.sector && sig.date ? ' · ' : ''}
              ${_fmtD(sig.date)}
            </div>
          </div>
          <button onclick="window._closeSignalModal()"
            style="background:#21262d;
              border:1px solid #30363d;
              color:#c9d1d9;font-size:16px;
              font-weight:700;
              width:32px;height:32px;
              border-radius:6px;cursor:pointer;
              flex-shrink:0;line-height:1;
              -webkit-tap-highlight-color:transparent;">
            ✕
          </button>
        </div>

        <!-- OUTCOME + SCORE + RR -->
        <div style="display:flex;gap:6px;
          flex-wrap:wrap;align-items:center;
          margin-bottom:14px;">
          ${_outcomeBadge(sig)}
          <span style="color:${_scoreColor(score)};
            font-size:13px;font-weight:700;
            background:#1c2128;border-radius:4px;
            padding:2px 8px;
            border:1px solid #30363d;">
            ${score}/10
          </span>
          ${rr
            ? `<span style="color:#58a6ff;
                 font-size:11px;background:#0d1117;
                 border-radius:4px;padding:2px 8px;">
                 R:R ${rr}×
               </span>`
            : ''}
          ${sig.pnl_pct != null
            ? `<span style="font-size:12px;
                 font-weight:700;
                 color:${parseFloat(sig.pnl_pct) >= 0
                   ? '#00C851' : '#f85149'};">
                 P&amp;L:&nbsp;${
                   parseFloat(sig.pnl_pct) >= 0
                     ? '+' : ''}${
                   parseFloat(sig.pnl_pct)
                     .toFixed(1)}%
               </span>`
            : ''}
        </div>

        <!-- LC3: FAILURE REASON -->
        ${failureReason
          ? `<div style="background:#1c2128;
               border:1px solid #30363d;
               border-radius:8px;padding:10px 12px;
               margin-bottom:10px;
               font-size:11px;color:#8b949e;
               line-height:1.6;">
               <span style="color:#555;font-size:10px;
                 letter-spacing:1px;">
                 ${OUTCOME_WIN.has(outcome)
                   ? '✅ WHY THIS WORKED'
                   : '💡 WHY THIS FAILED'}
               </span><br>
               ${failureReason}
             </div>`
          : ''}

        <!-- TRADE LEVELS -->
        <div style="background:#161b22;
          border:1px solid #21262d;
          border-radius:8px;padding:14px;
          margin-bottom:10px;">
          <div style="font-size:10px;color:#555;
            letter-spacing:1px;margin-bottom:10px;">
            TRADE LEVELS
          </div>
          <div style="display:grid;
            grid-template-columns:1fr 1fr 1fr;
            gap:8px;margin-bottom:10px;">
            <div style="text-align:center;
              background:#0d1117;border-radius:6px;
              padding:8px;">
              <div style="font-size:9px;color:#555;
                letter-spacing:1px;margin-bottom:3px;">
                ENTRY
              </div>
              <div style="color:#58a6ff;font-weight:700;
                font-size:14px;">
                ${entry ? '₹' + entry : '—'}
              </div>
            </div>
            <div style="text-align:center;
              background:#0d1117;border-radius:6px;
              padding:8px;">
              <div style="font-size:9px;color:#555;
                letter-spacing:1px;margin-bottom:3px;">
                STOP
              </div>
              <div style="color:#f85149;font-weight:700;
                font-size:14px;">
                ${stop ? '₹' + stop : '—'}
              </div>
            </div>
            <div style="text-align:center;
              background:#0d1117;border-radius:6px;
              padding:8px;">
              <div style="font-size:9px;color:#555;
                letter-spacing:1px;margin-bottom:3px;">
                TARGET
              </div>
              <div style="color:#00C851;font-weight:700;
                font-size:14px;">
                ${target ? '₹' + target : 'Day 6'}
              </div>
            </div>
          </div>

          ${dayNum !== null ? _dayProgress(dayNum) : ''}

          <div style="font-size:10px;color:#555;
            line-height:1.8;margin-top:4px;">
            Entry:
            <b style="color:#8b949e;">
              ${_fmtD(sig.date)}
            </b>
            &nbsp;·&nbsp;
            Exit:
            <b style="color:#8b949e;">
              ${exitDateStr}
            </b>
            ${dayNum !== null
              ? `&nbsp;·&nbsp;
                 <b style="color:${
                   dayNum >= 6 ? '#f85149' :
                   dayNum >= 5 ? '#FF8C00' : '#555'};">
                   Day ${dayNum}/6
                 </b>`
              : ''}
          </div>

          ${actOpen !== null
            ? `<div style="font-size:11px;color:#8b949e;
                 margin-top:6px;">
                 Actual open:
                 <b style="color:#c9d1d9;">
                   ₹${actOpen.toFixed(2)}
                 </b>
                 ${gapPct !== null
                   ? `<span style="margin-left:6px;
                        color:${
                          Math.abs(gapPct) >= 3
                            ? '#f85149' :
                          Math.abs(gapPct) >= 1.5
                            ? '#FFD700' : '#00C851'};">
                        Gap:
                        ${gapPct >= 0 ? '+' : ''}${
                          gapPct.toFixed(1)}%
                        ${sig.entry_valid === false
                          ? '⚠️ Too large' : '✓'}
                      </span>`
                   : ''}
               </div>`
            : ''}

          ${day6Open !== null
            ? `<div style="font-size:11px;
                 color:#8b949e;margin-top:6px;">
                 Day 6 open:
                 <b style="color:#ffd700;">
                   ₹${day6Open.toFixed(2)}
                 </b>
               </div>`
            : ''}
        </div>

        <!-- SIGNAL CONTEXT -->
        <div style="background:#161b22;
          border:1px solid #21262d;
          border-radius:8px;padding:14px;
          margin-bottom:10px;">
          <div style="font-size:10px;color:#555;
            letter-spacing:1px;margin-bottom:10px;">
            SIGNAL CONTEXT
          </div>
          <div style="display:grid;
            grid-template-columns:1fr 1fr;
            gap:10px;font-size:11px;
            margin-bottom:10px;">
            <div>
              <div style="color:#555;margin-bottom:2px;">
                Regime
              </div>
              <b style="color:${regimeColor};">
                ${regime}
              </b>
            </div>
            <div>
              <div style="color:#555;margin-bottom:2px;">
                Age at signal
              </div>
              <b style="color:#c9d1d9;">${age}</b>
            </div>
            <div>
              <div style="color:#555;margin-bottom:2px;">
                Grade
              </div>
              <b style="color:${_gradeColor(
                sig.grade || '')};">
                ${sig.grade || '—'}
              </b>
            </div>
            <div>
              <div style="color:#555;margin-bottom:2px;">
                Generation
              </div>
              <b style="color:${sig.generation === 0
                ? '#555' : '#c9d1d9'};">
                ${sig.generation === 0
                  ? 'Backfill' : 'Live'}
              </b>
            </div>
          </div>

          ${flags.length > 0
            ? `<div style="display:flex;gap:6px;
                 flex-wrap:wrap;padding-top:8px;
                 border-top:1px solid #21262d;">
                 ${flags.map(f =>
                   `<span style="background:#1c2128;
                      color:${f.color};
                      border:1px solid ${f.color}44;
                      border-radius:4px;
                      padding:3px 8px;
                      font-size:10px;font-weight:700;">
                      ${f.label}
                    </span>`
                 ).join('')}
               </div>`
            : ''}

          ${isSA_sig
            ? `<div style="background:#1a1a0a;
                 border:1px solid #ffd70033;
                 border-radius:6px;
                 padding:8px 10px;margin-top:8px;
                 font-size:10px;color:#8b949e;
                 line-height:1.6;">
                 <b style="color:#ffd700;">
                   2nd Attempt
                 </b> —
                 re-test of the same pattern.
                 ${stype.toUpperCase()
                   .startsWith('DOWN')
                   ? 'Age-0 only. If missed at the '
                     + 'break, skip — edge is gone.'
                   : 'Ages 0–1 valid. Same entry '
                     + 'rules as first attempt.'}
               </div>`
            : ''}
        </div>

        <!-- MC4: WHY THIS TRADE -->
        ${whyLines.length > 0
          ? `<div style="background:#161b22;
               border:1px solid #21262d;
               border-radius:8px;padding:14px;
               margin-bottom:10px;">
               <div style="font-size:10px;color:#555;
                 letter-spacing:1px;
                 margin-bottom:10px;">
                 WHY THIS TRADE
               </div>
               ${whyLines.map(line =>
                 `<div style="display:flex;gap:8px;
                    margin-bottom:6px;
                    font-size:11px;color:#8b949e;
                    line-height:1.5;">
                    <span style="color:#555;
                      flex-shrink:0;">·</span>
                    <span>${line}</span>
                  </div>`
               ).join('')}
             </div>`
          : ''}

        <!-- MAE / MFE -->
        ${(mfe !== null || mae !== null)
          ? `<div style="background:#161b22;
               border:1px solid #21262d;
               border-radius:8px;padding:14px;
               margin-bottom:10px;">
               <div style="font-size:10px;color:#555;
                 letter-spacing:1px;
                 margin-bottom:10px;">
                 EXCURSION
               </div>
               <div style="display:flex;gap:20px;
                 font-size:12px;">
                 <span style="color:#555;">
                   Peak gain:
                   <b style="color:${mfe !== null
                     && mfe > 0
                     ? '#00C851' : '#555'};">
                     ${mfe !== null
                       ? '+' + mfe.toFixed(1) + '%'
                       : '—'}
                   </b>
                 </span>
                 <span style="color:#555;">
                   Max drawdown:
                   <b style="color:${mae !== null
                     && mae > 0
                     ? '#f85149' : '#555'};">
                     ${mae !== null
                       ? '-' + mae.toFixed(1) + '%'
                       : '—'}
                   </b>
                 </span>
               </div>
             </div>`
          : ''}

        <!-- J2 FIX: window.open() for iOS PWA -->
        <div style="display:flex;gap:8px;
          margin-bottom:10px;">
          <button
            onclick="window.open('${tvURL}','_blank')"
            style="flex:1;text-align:center;
              background:#1c2128;
              border:1px solid #30363d;
              color:#8b949e;font-size:11px;
              border-radius:6px;padding:8px 0;
              cursor:pointer;
              -webkit-tap-highlight-color:transparent;">
            📈 Open Chart
          </button>
          <button onclick="
            const t = '${sym} ${stype} '
              + 'Entry: ${entry || '—'} '
              + 'Stop: ${stop || '—'} '
              + 'Target: ${target || '—'}';
            if(navigator.clipboard)
              navigator.clipboard.writeText(t);
            this.textContent='✓ Copied';
            setTimeout(()=>
              this.textContent='📋 Copy',1200);"
            style="flex:1;background:#1c2128;
              border:1px solid #30363d;
              color:#8b949e;font-size:11px;
              border-radius:6px;padding:8px 0;
              cursor:pointer;
              -webkit-tap-highlight-color:transparent;">
            📋 Copy
          </button>
        </div>

        <!-- POST-TARGET -->
        ${_buildPostTargetSection(sig)}

      </div>
    </div>`;
}

window._openSignalModal = function(cardId) {
  const sig = window._jSigMap[cardId];
  if (!sig) return;
  const existing =
    document.getElementById('j-modal-overlay');
  if (existing) existing.remove();
  const tmp = document.createElement('div');
  tmp.innerHTML = _buildModalHTML(sig);
  document.body.appendChild(tmp.firstElementChild);
};

window._closeSignalModal = function() {
  const m = document.getElementById('j-modal-overlay');
  if (m) m.remove();
};

window.toggleJournalCard = function() {};

// ── L5: TOOK / SKIP ROW ───────────────────────────────
function _renderTookSkipRow(sig, cardId) {
  const decision = _getUD(cardId);

  if (decision === 'TOOK') {
    return `
      <div style="display:flex;gap:6px;margin-top:8px;
        padding-top:8px;border-top:1px solid #21262d;">
        <span style="flex:1;text-align:center;
          background:#0d2a0d;
          border:1px solid #00C85144;
          color:#00C851;font-size:11px;font-weight:700;
          border-radius:5px;padding:5px 0;">
          ✓ Took it
        </span>
        <button
          onclick="event.stopPropagation();
            window._jTookSkip('${cardId}','TOOK')"
          style="background:none;
            border:1px solid #21262d;
            color:#555;font-size:10px;
            border-radius:5px;padding:5px 10px;
            cursor:pointer;
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
          background:#1c2128;
          border:1px solid #30363d;
          color:#555;font-size:11px;font-weight:700;
          border-radius:5px;padding:5px 0;">
          — Skipped
        </span>
        <button
          onclick="event.stopPropagation();
            window._jTookSkip('${cardId}','SKIPPED')"
          style="background:none;
            border:1px solid #21262d;
            color:#555;font-size:10px;
            border-radius:5px;padding:5px 10px;
            cursor:pointer;
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
          border-radius:5px;padding:6px 0;
          cursor:pointer;
          -webkit-tap-highlight-color:transparent;">
        ✓ Took it
      </button>
      <button
        onclick="event.stopPropagation();
          window._jTookSkip('${cardId}','SKIPPED')"
        style="flex:1;background:#1c2128;
          border:1px solid #30363d;color:#555;
          font-size:11px;font-weight:700;
          border-radius:5px;padding:6px 0;
          cursor:pointer;
          -webkit-tap-highlight-color:transparent;">
        — Skip
      </button>
    </div>`;
}

// ── R5: EXPIRY ALERT BANNER ───────────────────────────
// JJ1 FIX: Use exit_date field comparison instead of
// getDayNumber() — matches Telegram bot source of truth.
// Fixes EXIT TOMORROW showing 3 instead of 40.
function _renderExpiryAlert(took) {
  const open     = took.filter(
    s => !OUTCOME_DONE.has(s.outcome || ''));

  // JJ1 FIX: compare exit_date to today/tomorrow ISO
  const todayISO    = _todayISO();
  const tomorrowISO = _tomorrowISO();

  const today = open.filter(
    s => (s.exit_date || '') === todayISO);
  const tmrw  = open.filter(
    s => (s.exit_date || '') === tomorrowISO);

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

// ── M6: REJECTION SUMMARY ─────────────────────────────
function _renderRejectionSummary(rej) {
  if (!rej.length) return '';

  const byReason = {};
  rej.forEach(function(s) {
    const r = s.rejection_reason || 'unknown';
    byReason[r] = (byReason[r] || 0) + 1;
  });

  const sorted = Object.entries(byReason)
    .sort((a, b) => b[1] - a[1]);

  const items = sorted.map(function([r, n]) {
    const map = {
      score_below_threshold: 'Score too low',
      regime_not_aligned:    'Regime mismatch',
      age_expired:           'Age expired',
      vol_too_low:           'Volume too low',
      rr_too_low:            'R:R too low',
    };
    const label = map[r] || r.replace(/_/g,' ');
    const pct   = Math.round(n / rej.length * 100);
    const width = Math.max(pct, 3);
    return `
      <div style="margin-bottom:7px;">
        <div style="display:flex;
          justify-content:space-between;
          font-size:10px;color:#555;margin-bottom:3px;">
          <span>${label}</span>
          <span style="color:#c9d1d9;">
            ${n}
            <span style="color:#444;">${pct}%</span>
          </span>
        </div>
        <div style="background:#21262d;
          border-radius:2px;height:4px;">
          <div style="background:#f85149;height:4px;
            width:${width}%;border-radius:2px;">
          </div>
        </div>
      </div>`;
  }).join('');

  return `
    <div style="margin:0 16px 12px;
      background:#161b22;border-radius:8px;
      border:1px solid #21262d;padding:10px 12px;">
      <div style="font-size:10px;color:#555;
        letter-spacing:1px;margin-bottom:10px;">
        REJECTION REASONS
      </div>
      ${items}
    </div>`;
}

// ── H5: CAPITAL AT RISK / PORTFOLIO SUMMARY ───────────
// JJ1 FIX: urgency uses exit_date comparison.
// JJ2 FIX: capital > 100% shows red warning banner.
function _buildPnlSummary(took, ltpPrices) {
  const open     = took.filter(
    s => s.outcome === 'OPEN' || !s.outcome);
  const resolved = took.filter(
    s => s.outcome && s.outcome !== 'OPEN');

  const openWithPnl = open.filter(
    s => _unrealizedPnl(s, ltpPrices) !== null);
  const totalUnreal = openWithPnl.reduce(
    function(sum, s) {
      return sum + _unrealizedPnl(s, ltpPrices);
    }, 0);
  const avgUnreal = openWithPnl.length > 0
    ? totalUnreal / openWithPnl.length : null;

  const wins   = resolved.filter(
    s => s.outcome === 'TARGET_HIT'
      || s.outcome === 'DAY6_WIN');
  const losses = resolved.filter(
    s => s.outcome === 'STOP_HIT'
      || s.outcome === 'DAY6_LOSS');
  const flats  = resolved.filter(
    s => s.outcome === 'DAY6_FLAT');

  const winRate = resolved.length > 0
    ? Math.round(wins.length / resolved.length * 100)
    : null;

  const avgWinPnl = wins.length > 0
    ? wins.reduce(
        (s, t) => s + parseFloat(t.pnl_pct || 0), 0)
      / wins.length
    : null;
  const avgLossPnl = losses.length > 0
    ? losses.reduce(
        (s, t) => s + parseFloat(t.pnl_pct || 0), 0)
      / losses.length
    : null;

  // JJ1 FIX: use exit_date field comparison
  const todayISO    = _todayISO();
  const tomorrowISO = _tomorrowISO();

  const exitToday = open.filter(
    s => (s.exit_date || '') === todayISO).length;
  const exitTomorrow = open.filter(
    s => (s.exit_date || '') === tomorrowISO).length;

  const unrealColor = avgUnreal === null ? '#555' :
    avgUnreal > 0 ? '#00C851' :
    avgUnreal < 0 ? '#f85149' : '#FFD700';

  const capitalPct = open.length * 5;

  // JJ2 FIX: capital > 100% = red warning banner.
  // > 100% means leveraged beyond full capital.
  // Previously just changed text color passively.
  const capitalNote = open.length > 0
    ? capitalPct > 100
      ? `<div style="background:#2a0808;
           border:1px solid #f8514966;
           border-radius:6px;padding:6px 8px;
           margin-top:6px;font-size:10px;">
           <span style="color:#f85149;font-weight:700;">
             ⚠️ CAPITAL EXCEEDED
           </span>
           <div style="color:#8b949e;margin-top:2px;">
             ${open.length} positions × 5% =
             ~${capitalPct}% deployed
           </div>
           <div style="color:#555;margin-top:1px;
             font-size:9px;">
             This is tracking mode. Not all signals
             are expected to be taken simultaneously.
           </div>
         </div>`
      : `<div style="font-size:10px;color:#555;
           margin-top:3px;">
           ${open.length} positions × 5% =
           <span style="color:${
             capitalPct > 50 ? '#FF8C00' : '#8b949e'};">
             ~${capitalPct}% deployed
           </span>
         </div>`
    : '';

  const urgencyHtml = (exitToday > 0
    || exitTomorrow > 0)
    ? `<div style="font-size:10px;margin-top:4px;">
         ${exitToday > 0
           ? `<span style="color:#f85149;
               font-weight:700;">
               ⚠️ ${exitToday} exit today
             </span>`
           : ''}
         ${exitTomorrow > 0
           ? `<span style="color:#FF8C00;
               margin-left:8px;">
               ${exitTomorrow} exit tomorrow
             </span>`
           : ''}
       </div>`
    : '';

  return `
    <div style="margin:0 16px 14px;
      background:#161b22;border-radius:8px;
      border:1px solid #21262d;
      padding:12px 14px;">
      <div style="font-size:10px;color:#555;
        letter-spacing:1px;margin-bottom:10px;">
        PORTFOLIO SUMMARY
      </div>
      <div style="display:grid;
        grid-template-columns:1fr 1fr;gap:10px;">
        <div>
          <div style="font-size:10px;color:#555;
            margin-bottom:4px;">Open positions</div>
          <div style="font-size:20px;font-weight:700;
            color:#c9d1d9;">${open.length}</div>
          <div style="font-size:11px;color:#555;
            margin-top:2px;">
            Avg P&amp;L:
            <span style="color:${unrealColor};
              font-weight:700;">
              ${avgUnreal !== null
                ? (avgUnreal >= 0 ? '+' : '')
                  + avgUnreal.toFixed(1) + '%'
                : '—'}
            </span>
          </div>
          ${capitalNote}
          ${urgencyHtml}
        </div>
        <div>
          <div style="font-size:10px;color:#555;
            margin-bottom:4px;">Resolved</div>
          <div style="display:flex;
            align-items:baseline;gap:6px;">
            <span style="font-size:20px;
              font-weight:700;color:#c9d1d9;">
              ${resolved.length}
            </span>
            ${winRate !== null
              ? `<span style="font-size:12px;
                   font-weight:700;
                   color:${winRate >= 70 ? '#00C851' :
                           winRate >= 50 ? '#FFD700'
                                        : '#f85149'};">
                   ${winRate}% WR
                 </span>`
              : ''}
          </div>
          <div style="display:flex;gap:8px;
            font-size:11px;margin-top:4px;">
            <span style="color:#00C851;">
              W:${wins.length}
              ${avgWinPnl !== null
                ? `<span style="color:#555;
                     font-size:10px;">
                     (+${avgWinPnl.toFixed(1)}%)
                   </span>`
                : ''}
            </span>
            <span style="color:#f85149;">
              L:${losses.length}
              ${avgLossPnl !== null
                ? `<span style="color:#555;
                     font-size:10px;">
                     (${avgLossPnl.toFixed(1)}%)
                   </span>`
                : ''}
            </span>
            <span style="color:#FFD700;">
              F:${flats.length}
            </span>
          </div>
        </div>
      </div>
    </div>`;
}

// ── J1: RESOLVED SUMMARY HEADER ───────────────────────
function _buildResolvedSummary(resolved) {
  const wins   = resolved.filter(
    s => OUTCOME_WIN.has(s.outcome));
  const losses = resolved.filter(
    s => OUTCOME_LOSS.has(s.outcome));
  const flats  = resolved.filter(
    s => s.outcome === 'DAY6_FLAT');

  const winPnlArr  = wins.filter(
    s => s.pnl_pct != null)
    .map(s => parseFloat(s.pnl_pct));
  const lossPnlArr = losses.filter(
    s => s.pnl_pct != null)
    .map(s => parseFloat(s.pnl_pct));

  const avgWin = winPnlArr.length
    ? (winPnlArr.reduce((a,b)=>a+b,0)
       / winPnlArr.length).toFixed(1)
    : null;
  const avgLoss = lossPnlArr.length
    ? (lossPnlArr.reduce((a,b)=>a+b,0)
       / lossPnlArr.length).toFixed(1)
    : null;

  const wr = resolved.length
    ? Math.round(wins.length / resolved.length * 100)
    : 0;
  const wrColor = wr >= 60 ? '#00C851'
    : wr >= 40 ? '#FFD700' : '#f85149';

  return `
    <div style="margin:0 16px 12px;
      background:#161b22;border-radius:8px;
      border:1px solid #21262d;padding:12px 14px;">
      <div style="font-size:10px;color:#555;
        letter-spacing:1px;margin-bottom:10px;">
        RESOLVED SUMMARY
      </div>
      <div style="display:flex;gap:8px;
        flex-wrap:wrap;margin-bottom:8px;">
        <div style="flex:1;background:#0d1117;
          border-radius:6px;padding:8px;
          text-align:center;min-width:55px;">
          <div style="color:${wrColor};
            font-size:18px;font-weight:700;">
            ${wr}%
          </div>
          <div style="color:#555;font-size:9px;
            margin-top:2px;">WR</div>
        </div>
        <div style="flex:1;background:#0d1117;
          border-radius:6px;padding:8px;
          text-align:center;min-width:55px;">
          <div style="color:#00C851;font-size:18px;
            font-weight:700;">${wins.length}</div>
          <div style="color:#555;font-size:9px;
            margin-top:2px;">
            Wins${avgWin !== null
              ? ' +' + avgWin + '%' : ''}
          </div>
        </div>
        <div style="flex:1;background:#0d1117;
          border-radius:6px;padding:8px;
          text-align:center;min-width:55px;">
          <div style="color:#f85149;font-size:18px;
            font-weight:700;">${losses.length}</div>
          <div style="color:#555;font-size:9px;
            margin-top:2px;">
            Losses${avgLoss !== null
              ? ' ' + avgLoss + '%' : ''}
          </div>
        </div>
        <div style="flex:1;background:#0d1117;
          border-radius:6px;padding:8px;
          text-align:center;min-width:55px;">
          <div style="color:#FFD700;font-size:18px;
            font-weight:700;">${flats.length}</div>
          <div style="color:#555;font-size:9px;
            margin-top:2px;">Flat</div>
        </div>
      </div>
      ${resolved.length < 5
        ? `<div style="font-size:10px;color:#555;">
             ${5 - resolved.length} more signals
             needed for statistical significance.
           </div>`
        : ''}
    </div>`;
}

// ── TR1: DEDUPLICATE SAME STOCK ───────────────────────
function _deduplicateSignals(signals) {
  const keyMap = {};

  signals.forEach(function(sig) {
    const sym  = _sym(sig.symbol || '');
    const date = sig.date || '';
    const dirn = sig.direction || 'LONG';
    const key  = sym + '|' + date + '|' + dirn;

    if (!keyMap[key]) {
      keyMap[key] = { primary: sig, count: 1 };
    } else {
      keyMap[key].count++;
      const existScore = parseFloat(
        keyMap[key].primary.score || 0);
      const newScore   = parseFloat(
        sig.score || 0);
      if (newScore > existScore) {
        keyMap[key].primary = sig;
      }
    }
  });

  return Object.values(keyMap).map(function(v) {
    return { sig: v.primary, count: v.count };
  });
}

// ── COMPACT CARD ──────────────────────────────────────
function _compactCard(sig, isRejView,
                      ltpPrices, dupCount) {
  const sym       = _sym(sig.symbol
    || sig.stock || '?');
  const stype     = sig.signal    || '?';
  const sigColor  = _sigColor(stype);
  const score     = sig.score     || 0;
  const direction = sig.direction === 'SHORT'
    ? '↓ SHORT' : '↑ LONG';
  const sector    = sig.sector    || '';
  const grade     = sig.grade     || '';
  const bearBonus = sig.bear_bonus === true
    || sig.bear_bonus === 'true';
  const stkRegime  = sig.stock_regime || null;
  const isBackfill = sig.generation === 0;
  const isSA_sig   = _isSA(stype);
  const isResolved = OUTCOME_DONE.has(
    sig.outcome || '');
  const isOpen     = !isResolved;

  const entry  = sig.entry
    ? '₹' + parseFloat(sig.entry).toFixed(2) : '—';
  const stop   = sig.stop
    ? '₹' + parseFloat(sig.stop).toFixed(2)  : '—';
  const target = sig.target_price
    ? '₹' + parseFloat(
        sig.target_price).toFixed(2)          : '—';

  const exitStr = sig.exit_date
    ? _fmtD(sig.exit_date) : null;
  const dayNum  = typeof getDayNumber === 'function'
    ? getDayNumber(sig.date) : null;

  const rr     = _rr(sig);
  const cardId = (sig.id ||
    (sym + '-' + stype + '-' + (sig.date || '')))
    .replace(/[^a-zA-Z0-9-]/g, '-');

  const rejReason = isRejView && sig.rejection_reason
    ? _rejLabel(sig.rejection_reason) : null;
  const rejThresh = isRejView
    && sig.rejection_threshold != null
    ? ` (min: ${sig.rejection_threshold})` : '';

  const stopDot = isOpen && !isRejView
    ? _stopProximityDot(sig, ltpPrices) : '';

  const unreal = isOpen && !isRejView
    ? _unrealizedPnl(sig, ltpPrices) : null;
  const unrealStr = unreal !== null
    ? ((unreal >= 0 ? '+' : '')
       + unreal.toFixed(1) + '%')
    : null;
  const unrealColor = unreal === null ? '#555' :
    unreal > 0 ? '#00C851' :
    unreal < 0 ? '#f85149' : '#FFD700';

  const reasonHtml = isResolved
    ? _reasonTag(sig) : '';

  const dupBadge = (dupCount && dupCount > 1)
    ? `<span style="background:#1a1a0a;
         color:#ffd700;font-size:9px;
         font-weight:700;
         border:1px solid #ffd70033;
         border-radius:3px;
         padding:1px 5px;white-space:nowrap;">
         ×${dupCount}
       </span>`
    : '';

  window._jSigMap[cardId] = sig;

  return `
    <div style="background:#161b22;
      border:1px solid #21262d;
      border-left:3px solid ${sigColor};
      border-radius:8px;padding:10px 12px 8px;
      margin-bottom:8px;
      ${isBackfill ? 'opacity:0.75;' : ''}">

      <div style="display:flex;
        justify-content:space-between;
        align-items:flex-start;margin-bottom:5px;">
        <div style="display:flex;align-items:center;
          gap:5px;flex-wrap:wrap;flex:1;min-width:0;">
          <span style="color:#c9d1d9;font-size:14px;
            font-weight:700;">${sym}</span>
          ${stopDot}
          <span style="color:#555;font-size:11px;">
            ${sector}
          </span>
          ${grade
            ? `<span style="color:${_gradeColor(grade)};
                 font-size:10px;font-weight:700;
                 border:1px solid ${
                   _gradeColor(grade)}44;
                 border-radius:3px;padding:0 4px;">
                 ${grade}
               </span>`
            : ''}
          ${bearBonus
            ? '<span style="font-size:10px;">🔥</span>'
            : ''}
          ${isSA_sig
            ? `<span style="background:#1a1a0a;
                 color:#ffd700;font-size:9px;
                 font-weight:700;
                 border:1px solid #ffd70033;
                 border-radius:3px;
                 padding:1px 5px;">2ND</span>`
            : ''}
          ${dupBadge}
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
                 padding:1px 4px;
                 border:1px solid #30363d;">
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
                  color:#555;font-size:14px;
                  cursor:pointer;padding:0 2px;
                  line-height:1;
                  -webkit-tap-highlight-color:transparent;">
                ▶
              </button>`
            : ''}
        </div>
      </div>

      <div style="display:flex;align-items:center;
        gap:6px;flex-wrap:wrap;margin-bottom:6px;
        font-size:11px;">
        <span style="color:${sigColor};font-weight:700;">
          ${_sigEmoji(stype)}
          ${stype.replace(/_/g,' ')}
        </span>
        <span style="color:${_scoreColor(score)};
          font-weight:700;">
          ${score}/10
        </span>
        <span style="color:#555;">${direction}</span>
        ${rr
          ? `<span style="color:#555;">
               R:R <b style="color:#58a6ff;">
                 ${rr}×
               </b>
             </span>`
          : ''}
        ${unrealStr !== null
          ? `<span style="color:${unrealColor};
               font-weight:700;font-size:10px;
               background:#1c2128;border-radius:3px;
               padding:1px 5px;">
               LTP ${unrealStr}
             </span>`
          : ''}
      </div>

      <div style="display:flex;gap:8px;
        flex-wrap:wrap;font-size:11px;
        color:#8b949e;">
        <span>Entry
          <b style="color:#c9d1d9;">${entry}</b>
        </span>
        <span>Stop
          <b style="color:#f85149;">${stop}</b>
        </span>
        <span>Target
          <b style="color:#00C851;">${target}</b>
        </span>
        ${exitStr
          ? `<span>Exit
               <b style="color:#555;">${exitStr}</b>
             </span>`
          : ''}
        ${dayNum !== null && isOpen
          ? `<span style="color:${
               dayNum >= 6 ? '#f85149' :
               dayNum >= 5 ? '#FF8C00' : '#555'};
               font-weight:${
                 dayNum >= 5 ? '700' : '400'};">
               Day ${dayNum}/6
             </span>`
          : ''}
      </div>

      ${rejReason
        ? `<div style="font-size:10px;color:#f85149;
             margin-top:5px;">
             ✕ ${rejReason}${rejThresh}
           </div>`
        : ''}

      ${reasonHtml}

      ${!isRejView && !isBackfill
        ? _renderTookSkipRow(sig, cardId) : ''}
    </div>`;
}

// ── J1: FILTER BAR — 3 TABS ───────────────────────────
function _filterBar(tookN, rejN, resolvedN) {
  const isTook     = _jFilter === 'took';
  const isResolved = _jFilter === 'resolved';
  const isRej      = _jFilter === 'rejected';

  const _tab = function(filter, label, active) {
    return `
      <button onclick="window._jFilter('${filter}')"
        style="flex:1;min-width:70px;
          background:${active ? '#21262d' : 'none'};
          color:${active ? '#c9d1d9' : '#555'};
          border:1px solid ${active
            ? '#30363d' : '#21262d'};
          border-radius:6px;padding:7px 0;
          font-size:11px;cursor:pointer;
          font-weight:${active ? '700' : '400'};
          white-space:nowrap;
          -webkit-tap-highlight-color:transparent;">
        ${label}
      </button>`;
  };

  return `
    <div style="display:flex;gap:6px;
      padding:0 16px 10px;
      overflow-x:auto;
      -webkit-overflow-scrolling:touch;">
      ${_tab('took',     `📥 Took (${tookN})`,
             isTook)}
      ${_tab('resolved', `✓ Resolved (${resolvedN})`,
             isResolved)}
      ${_tab('rejected', `✕ Rejected (${rejN})`,
             isRej)}
    </div>`;
}

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

  window._jSigMap = {};

  const raw = (tietiy.history
    && tietiy.history.history)
    ? tietiy.history.history : [];

  const ltpPrices = tietiy.ltp_prices || null;

  const took = raw.filter(
    s => s.layer === 'MINI' && s.action === 'TOOK');
  const rej  = raw.filter(
    s => s.layer === 'ALPHA'
      && s.action === 'REJECTED');

  const resolved = took.filter(
    s => OUTCOME_DONE.has(s.outcome || ''));

  // JJ3 FIX: Count user-confirmed trades from
  // localStorage, not raw system signal count.
  const userTookCount = _countUserTook(took);

  let entries;
  if (_jFilter === 'resolved') {
    entries = resolved;
  } else if (_jFilter === 'rejected') {
    entries = rej;
  } else {
    entries = took;
  }

  const isRejView      = _jFilter === 'rejected';
  const isResolvedView = _jFilter === 'resolved';

  let groupedEntries;
  if (!isRejView) {
    groupedEntries = _deduplicateSignals(entries);
  } else {
    groupedEntries = entries.map(
      s => ({ sig: s, count: 1 }));
  }

  const byDate = {};
  groupedEntries.forEach(function(item) {
    const d = item.sig.date || 'Unknown';
    if (!byDate[d]) byDate[d] = [];
    byDate[d].push(item);
  });

  const dates = Object.keys(byDate)
    .sort((a, b) => b.localeCompare(a));

  dates.forEach(function(d) {
    byDate[d].sort((a, b) =>
      (parseFloat(b.sig.score) || 0)
      - (parseFloat(a.sig.score) || 0));
  });

  // JJ3 FIX: header shows user confirmed count
  // alongside total tracked count.
  const headerCountStr = userTookCount > 0
    ? `${userTookCount} confirmed · `
      + `${took.length} tracked · `
      + `${resolved.length} resolved · `
      + `${rej.length} rejected`
    : `${took.length} took · `
      + `${resolved.length} resolved · `
      + `${rej.length} rejected`;

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
            ${headerCountStr}
          </span>
        </div>
        ${_filterBar(
          took.length,
          rej.length,
          resolved.length)}
      </div>`;

  if (isResolvedView && resolved.length > 0) {
    html += _buildResolvedSummary(resolved);
  }

  if (_jFilter === 'took' && took.length > 0) {
    html += _renderExpiryAlert(took);
    html += _buildPnlSummary(took, ltpPrices);
  }

  if (isRejView && rej.length > 0) {
    html += _renderRejectionSummary(rej);
  }

  if (groupedEntries.length === 0) {
    html += `
      <div style="text-align:center;
        padding:48px 16px;color:#555;
        font-size:13px;">
        No ${isResolvedView ? 'resolved'
          : isRejView ? 'rejected'
          : 'TOOK'} signals yet.
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
              ${group.length} signal${
                group.length !== 1 ? 's' : ''}
            </span>
          </div>
          ${group.map(function(item) {
            return _compactCard(
              item.sig,
              isRejView,
              ltpPrices,
              item.count);
          }).join('')}
        </div>`;
    });
  }

  html += '</div>';
  el.innerHTML = html;
};

})();
