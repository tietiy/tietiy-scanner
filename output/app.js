// ── app.js ───────────────────────────────────────────
// Signals tab: compact/expanded cards, filter bar,
// tap panel, conflict detection
//
// CHANGES THIS PASS:
// - U1 FIX: filter bar is now position:sticky;top:0
// - UI2 FIX: sector filter is a <select> dropdown
// - Day 5 orange glow, Day 6 red pulse animation
// - Score breakdown section in tap panel
//
// V1 FIXES APPLIED:
// - R3  : _initSWMessageListener()
// - R8  : SA badge on signal cards + tap panel
//
// V1.1 FIXES:
// - M5  : _buildMorningBrief() — compact urgency bar
// - H1  : Score visual weight on cards —
//         font size + background scales with score
//         9/10 looks clearly stronger than 5/10
// - H2  : Score-based card border colour —
//         gold 8-10, faint white 5-7, grey below 5
// - J2  : TradingView link in tap panel fixed for
//         iOS PWA — window.open() replaces
//         target="_blank" which is blocked in PWA
// ─────────────────────────────────────────────────────

const SIGNAL_CONFIG = {
  UP_TRI:      { color: '#00C851', arrow: '▲',  label: 'UP TRI',       border: '#00C851' },
  DOWN_TRI:    { color: '#f85149', arrow: '▼',  label: 'DOWN TRI',     border: '#f85149' },
  BULL_PROXY:  { color: '#58a6ff', arrow: '◆',  label: 'BULL PROXY',   border: '#58a6ff' },
  UP_TRI_SA:   { color: '#00C851', arrow: '▲▲', label: 'UP TRI 2nd',   border: '#00C851' },
  DOWN_TRI_SA: { color: '#f85149', arrow: '▼▼', label: 'DOWN TRI 2nd', border: '#f85149' },
};

const DEFAULT_CAPITAL = 50000;
const TOP_SCORE_MIN   = 6;
const TOP_MAX_SIGNALS = 7;

// ── HELPERS ───────────────────────────────────────────
function _sigCfg(signal) {
  return SIGNAL_CONFIG[signal] || {
    color: '#8b949e', arrow: '?',
    label: signal, border: '#30363d'
  };
}

function _entryWindowClosed() {
  const now = new Date();
  const ist = new Date(now.toLocaleString(
    'en-US', { timeZone: 'Asia/Kolkata' }));
  const h = ist.getHours();
  const m = ist.getMinutes();
  return h > 9 || (h === 9 && m > 30);
}

function _getOpenPrice(symbol) {
  const op = window.TIETIY.openPrices;
  if (!op || !op.results) return null;
  const clean = symbol.replace('.NS', '');
  return op.results.find(r =>
    (r.symbol || '').replace('.NS', '') === clean
  ) || null;
}

function _getLtp(symbol) {
  const ltp = window.TIETIY.ltpPrices;
  if (!ltp || !ltp.prices) return null;
  const clean = symbol.replace('.NS', '');
  return ltp.prices[symbol]         ||
         ltp.prices[clean + '.NS']  ||
         ltp.prices[clean]          ||
         null;
}

function _getStopAlert(symbol) {
  const sa = window.TIETIY.stopAlerts;
  if (!sa || !sa.alerts) return null;
  const clean = symbol.replace('.NS', '');
  return sa.alerts.find(a =>
    (a.symbol || '').replace('.NS', '') === clean &&
    ['BREACHED','AT','NEAR'].includes(a.alert_level)
  ) || null;
}

function _getEodData(symbol) {
  const ed = window.TIETIY.eodPrices;
  if (!ed || !ed.results) return null;
  const clean = symbol.replace('.NS', '');
  return ed.results.find(r =>
    (r.symbol || '').replace('.NS', '') === clean
  ) || null;
}

function _isBanned(sym) {
  const banned = window.TIETIY.bannedStocks || [];
  return banned.includes(sym.replace('.NS', ''));
}

function _getEntryPrice(sig) {
  for (const f of [
    'actual_open','scan_price','entry','entry_est']) {
    const v = sig[f];
    if (v !== null && v !== undefined) {
      const n = parseFloat(v);
      if (n > 0) return n;
    }
  }
  return null;
}

function _ltpVsEntry(entryPrice, ltpPrice, direction) {
  if (!entryPrice || !ltpPrice ||
      entryPrice <= 0 || ltpPrice <= 0) return null;
  const raw       = (ltpPrice - entryPrice) /
                    entryPrice * 100;
  const favorable = direction === 'SHORT'
    ? raw < 0 : raw > 0;
  return { raw, favorable };
}

function _calcRR(entry, stop, direction) {
  try {
    entry = parseFloat(entry);
    stop  = parseFloat(stop);
    if (!entry || !stop) return null;
    let risk, target;
    if (direction === 'LONG') {
      risk = entry - stop;
      if (risk <= 0) return null;
      target = entry + 2 * risk;
    } else {
      risk = stop - entry;
      if (risk <= 0) return null;
      target = entry - 2 * risk;
    }
    return {
      rr: (Math.abs(target - entry) / risk).toFixed(1),
      target,
    };
  } catch(e) { return null; }
}

function _calcPositionSize(entry, stop) {
  try {
    const e = parseFloat(entry);
    const s = parseFloat(stop);
    if (!e || !s || e <= 0 || s <= 0) return null;
    const riskPerShare = Math.abs(e - s);
    if (riskPerShare <= 0) return null;
    const shares    = Math.floor(
      DEFAULT_CAPITAL / riskPerShare);
    const totalRisk = shares * riskPerShare;
    return {
      shares,
      riskAmt: Math.round(totalRisk),
      riskPer: riskPerShare.toFixed(2),
    };
  } catch(e) { return null; }
}

// ── SCORE COLOR ───────────────────────────────────────
function _scoreColor(score) {
  if (score >= 7) return '#FFD700';
  if (score >= 5) return '#00C851';
  if (score >= 3) return '#8b949e';
  return '#555';
}

// ── H1: SCORE VISUAL WEIGHT ───────────────────────────
// Score 8-10: large gold bold — unmissable
// Score 5-7:  medium green
// Score 3-4:  small grey
// Score 1-2:  tiny dim
function _scoreDisplay(score) {
  const n = parseFloat(score) || 0;
  if (n >= 8) {
    return `<span style="
      color:#FFD700;
      font-size:13px;
      font-weight:700;
      background:#1a1500;
      border:1px solid #FFD70033;
      border-radius:4px;
      padding:1px 7px;
      letter-spacing:0.3px;">
      ${n}/10
    </span>`;
  }
  if (n >= 5) {
    return `<span style="
      color:#00C851;
      font-size:12px;
      font-weight:700;
      background:#0a1a0a;
      border:1px solid #00C85122;
      border-radius:4px;
      padding:1px 6px;">
      ${n}/10
    </span>`;
  }
  if (n >= 3) {
    return `<span style="
      color:#8b949e;
      font-size:11px;
      font-weight:400;
      border-radius:4px;
      padding:1px 5px;">
      ${n}/10
    </span>`;
  }
  return `<span style="
    color:#444;
    font-size:10px;
    font-weight:400;
    padding:1px 4px;">
    ${n}/10
  </span>`;
}

// ── H2: SCORE-BASED CARD BORDER ───────────────────────
// gold 8-10, faint white 5-7, grey below 5
function _cardBorderColor(score) {
  const n = parseFloat(score) || 0;
  if (n >= 8) return '#FFD700';
  if (n >= 5) return '#30363d';
  return '#21262d';
}

// ── SCORE BREAKDOWN ───────────────────────────────────
function _buildScoreBreakdown(sig) {
  const signal    = sig.signal    || '';
  const age       = sig.age       || 0;
  const regime    = sig.regime    || '';
  const bearBonus = sig.bear_bonus  === true ||
                    sig.bear_bonus  === 'true';
  const volConf   = sig.vol_confirm === true ||
                    sig.vol_confirm === 'true';
  const secMom    = sig.sec_mom   || '';
  const rsQ       = sig.rs_q      || '';
  const grade     = sig.grade     || '';
  const score     = sig.score     || 0;

  const rows = [];

  if (signal === 'DOWN_TRI' ||
      signal === 'DOWN_TRI_SA') {
    rows.push({
      label: 'DOWN TRI base', pts: 2, active: true });
  } else if (signal === 'UP_TRI' ||
             signal === 'UP_TRI_SA') {
    if (age === 0)
      rows.push({
        label: 'Age 0 (fresh breakout)',
        pts: 3, active: true });
    else if (age === 1)
      rows.push({
        label: 'Age 1', pts: 2, active: true });
    else
      rows.push({
        label: `Age ${age}`, pts: 0, active: false });
  } else if (signal === 'BULL_PROXY') {
    rows.push({
      label: 'BULL PROXY base', pts: 1, active: true });
  }

  if (bearBonus) {
    rows.push({
      label: 'Bear regime 🔥', pts: 3, active: true });
  } else if (regime === 'Bull' ||
             regime === 'Choppy') {
    rows.push({
      label: `${regime} regime`,
      pts: 1, active: true });
  } else {
    rows.push({
      label: 'Regime bonus', pts: 0, active: false });
  }

  rows.push({ label: 'Volume confirm',
    pts: 1, active: volConf });
  rows.push({ label: 'Sector leading',
    pts: 1, active: secMom === 'Leading' });
  rows.push({ label: 'RS vs Nifty strong',
    pts: 1, active: rsQ === 'Strong' });
  rows.push({ label: 'Grade A stock',
    pts: 1, active: grade === 'A' });

  const earned = rows
    .filter(r => r.active)
    .reduce((s, r) => s + r.pts, 0);

  const rowsHtml = rows.map(r => `
    <div style="display:flex;
      justify-content:space-between;
      align-items:center;padding:3px 0;
      opacity:${r.active ? 1 : 0.3};">
      <span style="color:${
        r.active ? '#c9d1d9' : '#555'};
        font-size:11px;">
        ${r.active ? '✅' : '○'} ${r.label}
      </span>
      <span style="color:${
        r.active ? '#ffd700' : '#444'};
        font-size:11px;font-weight:700;">
        ${r.active ? '+' + r.pts : ''}
      </span>
    </div>`).join('');

  return `
    <div style="background:#0a0d1a;
      border:1px solid #21262d;
      border-radius:8px;padding:10px 12px;
      margin-bottom:8px;">
      <div style="display:flex;
        justify-content:space-between;
        align-items:center;margin-bottom:8px;">
        <div style="color:#555;font-size:10px;
          letter-spacing:1px;">
          SCORE BREAKDOWN
        </div>
        <div style="color:#ffd700;font-size:15px;
          font-weight:700;">
          ${score}/10
        </div>
      </div>
      ${rowsHtml}
      <div style="border-top:1px solid #21262d;
        margin-top:6px;padding-top:6px;
        display:flex;justify-content:space-between;">
        <span style="color:#555;font-size:10px;">
          Calculated total
        </span>
        <span style="color:#ffd700;font-size:11px;
          font-weight:700;">
          ${earned} pts
        </span>
      </div>
    </div>`;
}

// ── DAY BADGE ─────────────────────────────────────────
function _dayBadge(dayNum, isNew, isBackfill) {
  if (isNew && !isBackfill) {
    return `<span style="background:#1a3a1a;
      color:#00C851;border-radius:4px;
      padding:2px 7px;font-size:10px;
      font-weight:700;">NEW</span>`;
  }
  if (!dayNum) return '';
  if (dayNum >= 6) {
    return `<span style="color:#f85149;
      font-size:10px;font-weight:700;
      animation:pulse 0.8s infinite;">
      Day 6/6 ⚠️ EXIT TODAY
    </span>`;
  }
  if (dayNum >= 5) {
    return `<span style="color:#FF8C00;
      font-size:10px;font-weight:700;">
      Day 5/6 · Exit tomorrow
    </span>`;
  }
  return `<span style="color:#555;font-size:10px;
    font-weight:700;">
    Day ${dayNum}/6
  </span>`;
}

// ── CONFLICT DETECTION ────────────────────────────────
function _buildConflictMap(signals) {
  const map = {};
  signals.forEach(s => {
    const sym = (s.symbol || '').replace('.NS', '');
    if (!map[sym])
      map[sym] = { count: 0, directions: new Set() };
    map[sym].count++;
    map[sym].directions.add(s.direction || 'LONG');
  });
  return map;
}

// ── UNIQUE SECTORS ────────────────────────────────────
function _getUniqueSectors(signals) {
  const sectors = new Set();
  signals.forEach(s => {
    if (s.sector && s.sector !== 'Other'
        && s.sector !== '')
      sectors.add(s.sector);
  });
  return [...sectors].sort();
}

function _getSavedFilter() {
  try {
    return sessionStorage.getItem('tietiy_filter')
      || 'top';
  } catch(e) { return 'top'; }
}

function _getSavedSector() {
  try {
    return sessionStorage.getItem('tietiy_sector')
      || '';
  } catch(e) { return ''; }
}

// ── FILTER BAR ────────────────────────────────────────
function _buildFilterBar(signals,
                         currentFilter,
                         currentSector) {
  const counts = {
    all:        signals.length,
    UP_TRI:     signals.filter(
      s => s.signal === 'UP_TRI').length,
    DOWN_TRI:   signals.filter(
      s => s.signal === 'DOWN_TRI').length,
    BULL_PROXY: signals.filter(
      s => s.signal === 'BULL_PROXY').length,
    SA:         signals.filter(
      s => (s.signal || '').endsWith('_SA')).length,
    age0:       signals.filter(
      s => s.age === _todayIST()
        && s.generation !== 0).length,
    top:        signals.filter(
      s => (s.score || 0) >= TOP_SCORE_MIN).length,
  };

  const filters = [
    { id: 'top',
      label: `TOP (${Math.min(
        counts.top, TOP_MAX_SIGNALS)})` },
    { id: 'all',
      label: `All (${counts.all})` },
    { id: 'UP_TRI',
      label: `UP▲ (${counts.UP_TRI})` },
    { id: 'DOWN_TRI',
      label: `DOWN▼ (${counts.DOWN_TRI})` },
    { id: 'BULL_PROXY',
      label: `◆ Proxy (${counts.BULL_PROXY})` },
    { id: 'age0',
      label: `New Today (${counts.age0})` },
    { id: 'SA',
      label: `2nd Att (${counts.SA})` },
  ];

  const sectors = _getUniqueSectors(signals);

  const sectorDropdown = sectors.length > 0 ? `
    <div style="display:flex;align-items:center;
      gap:8px;padding:4px 14px 8px;
      border-top:1px solid #161b22;">
      <span style="color:#555;font-size:10px;
        white-space:nowrap;flex-shrink:0;">
        Sector:
      </span>
      <select
        id="sector-select"
        onchange="applySector(this.value)"
        style="flex:1;max-width:180px;
          background:#161b22;
          color:${currentSector
            ? '#58a6ff' : '#8b949e'};
          border:1px solid ${currentSector
            ? '#58a6ff' : '#30363d'};
          border-radius:6px;padding:5px 8px;
          font-size:11px;cursor:pointer;
          -webkit-appearance:none;
          appearance:none;">
        <option value="">All Sectors</option>
        ${sectors.map(sec => {
          const cnt = signals.filter(
            s => s.sector === sec).length;
          const sel = currentSector === sec
            ? 'selected' : '';
          return `<option value="${sec}" ${sel}>
            ${sec} (${cnt})
          </option>`;
        }).join('')}
      </select>
      ${currentSector
        ? `<span style="background:#1a2a3a;
             color:#58a6ff;border-radius:4px;
             padding:2px 7px;font-size:10px;
             font-weight:700;">
             ${currentSector}
             <span onclick="applySector('')"
               style="cursor:pointer;
                 margin-left:4px;
                 color:#f85149;font-size:11px;">
               ✕
             </span>
           </span>`
        : ''}
    </div>` : '';

  return `
    <div id="filter-bar"
      style="background:#0d1117;
        border-bottom:1px solid #21262d;
        position:sticky;top:0;z-index:10;">
      <div style="display:flex;flex-wrap:wrap;
        gap:4px;padding:8px 14px 4px;">
        ${filters.map(f => {
          const isActive = f.id === currentFilter;
          return `
            <button
              class="filter-btn ${isActive
                ? 'active' : ''}"
              data-filter="${f.id}"
              onclick="applyFilter('${f.id}', this)"
              style="background:${isActive
                ? '#ffd700' : '#161b22'};
                color:${isActive ? '#000' : '#8b949e'};
                border:1px solid ${isActive
                  ? '#ffd700' : '#30363d'};
                border-radius:6px;
                padding:5px 10px;font-size:10px;
                font-weight:${isActive
                  ? '700' : '400'};
                cursor:pointer;white-space:nowrap;
                -webkit-tap-highlight-color:transparent;">
              ${f.label}
            </button>`;
        }).join('')}
      </div>
      ${sectorDropdown}
    </div>`;
}

function applyFilter(filterId, btn) {
  document.querySelectorAll('.filter-btn')
    .forEach(b => {
      b.style.background = '#161b22';
      b.style.color      = '#8b949e';
      b.style.border     = '1px solid #30363d';
      b.style.fontWeight = '400';
    });
  if (btn) {
    btn.style.background = '#ffd700';
    btn.style.color      = '#000';
    btn.style.border     = '1px solid #ffd700';
    btn.style.fontWeight = '700';
  }
  try {
    sessionStorage.setItem(
      'tietiy_filter', filterId);
  } catch(e) {}
  if (typeof renderSignals === 'function')
    renderSignals(window.TIETIY);
}

function applySector(sector) {
  const sel =
    document.getElementById('sector-select');
  if (sel) sel.value = sector || '';
  try {
    sessionStorage.setItem(
      'tietiy_sector', sector || '');
  } catch(e) {}
  if (typeof renderSignals === 'function')
    renderSignals(window.TIETIY);
}

// ── R8: SA CALLOUT BLOCK FOR TAP PANEL ───────────────
function _buildSACallout(sig) {
  const signal = (sig.signal || '').toUpperCase();
  const isDown = signal.startsWith('DOWN');
  return `
    <div style="background:#1a1a0a;
      border:1px solid #ffd70033;
      border-radius:8px;padding:10px 12px;
      margin-bottom:8px;font-size:11px;
      color:#8b949e;line-height:1.6;">
      <b style="color:#ffd700;">2nd Attempt</b> —
      re-test of the same pattern after a prior signal.
      ${isDown
        ? 'Age 0 only. If missed at the break, '
          + 'skip — edge is gone at age 1+.'
        : 'Ages 0–1 valid. Same entry rules '
          + 'as first attempt.'}
      ${sig.parent_date
        ? `<div style="margin-top:4px;color:#555;
             font-size:10px;">
             Parent signal:
             ${sig.parent_signal || '?'}
             on ${sig.parent_date}
             · result: ${sig.parent_result || '—'}
           </div>`
        : ''}
    </div>`;
}

// ── M5: MORNING BRIEF ────────────────────────────────
function _buildMorningBrief(allSignals, stopAlerts) {
  const today = _todayIST();
  const dayFn = typeof getDayNumber === 'function'
    ? getDayNumber : null;
  if (!dayFn) return '';

  const open = allSignals.filter(
    s => s.result === 'PENDING');

  const exitsToday = open.filter(
    s => dayFn(s.date) >= 6);
  const exitsTmrw  = open.filter(
    s => dayFn(s.date) === 5);
  const newToday   = open.filter(
    s => s.date === today);

  const alertList  = stopAlerts
    ? (stopAlerts.alerts || []).filter(
        a => a.alert_level === 'BREACHED'
          || a.alert_level === 'AT')
    : [];
  const hasAlerts  = alertList.length > 0;

  if (!exitsToday.length && !exitsTmrw.length
      && !newToday.length && !hasAlerts) {
    return '';
  }

  const parts = [];

  if (exitsToday.length) {
    const syms = exitsToday.slice(0, 3)
      .map(s => (s.symbol || '?')
        .replace('.NS', '')).join(', ');
    const more = exitsToday.length > 3
      ? ` +${exitsToday.length - 3}` : '';
    parts.push(`
      <div style="background:#2a0808;
        border:1px solid #f8514944;
        border-radius:6px;padding:7px 10px;
        margin-bottom:6px;">
        <div style="font-size:10px;font-weight:700;
          color:#f85149;margin-bottom:2px;">
          ⚠️ EXIT TODAY — ${exitsToday.length}
          signal${exitsToday.length > 1 ? 's' : ''}
        </div>
        <div style="font-size:11px;color:#c9d1d9;
          font-weight:700;">
          ${syms}${more}
        </div>
        <div style="font-size:10px;color:#555;
          margin-top:2px;">
          Day 6 reached · Sell at open ·
          No extensions
        </div>
      </div>`);
  }

  if (exitsTmrw.length) {
    const syms = exitsTmrw.slice(0, 4)
      .map(s => (s.symbol || '?')
        .replace('.NS', '')).join(', ');
    const more = exitsTmrw.length > 4
      ? ` +${exitsTmrw.length - 4}` : '';
    parts.push(`
      <div style="background:#1a0f00;
        border:1px solid #FF8C0033;
        border-radius:6px;padding:7px 10px;
        margin-bottom:6px;">
        <div style="font-size:10px;font-weight:700;
          color:#FF8C00;margin-bottom:2px;">
          ⏰ EXIT TOMORROW — ${exitsTmrw.length}
          signal${exitsTmrw.length > 1 ? 's' : ''}
        </div>
        <div style="font-size:11px;color:#c9d1d9;">
          ${syms}${more}
        </div>
      </div>`);
  }

  const metaRow = [];

  if (newToday.length) {
    metaRow.push(`
      <span style="background:#0d2a0d;
        color:#00C851;border-radius:4px;
        padding:2px 7px;font-size:10px;
        font-weight:700;">
        🔔 ${newToday.length} new today
      </span>`);
  }

  if (hasAlerts) {
    metaRow.push(`
      <span style="background:#2a0808;
        color:#f85149;border-radius:4px;
        padding:2px 7px;font-size:10px;
        font-weight:700;">
        🚨 ${alertList.length} stop alert${
          alertList.length > 1 ? 's' : ''}
      </span>`);
  }

  if (metaRow.length) {
    parts.push(`
      <div style="display:flex;gap:6px;
        flex-wrap:wrap;margin-bottom:6px;">
        ${metaRow.join('')}
      </div>`);
  }

  if (!parts.length) return '';

  return `
    <div style="padding:8px 14px 2px;">
      ${parts.join('')}
    </div>`;
}

// ── COMPACT CARD ──────────────────────────────────────
function _buildCard(sig, isNew, dayNum, conflictMap) {
  const sym        = (sig.symbol || '')
                     .replace('.NS','');
  const signal     = sig.signal    || '';
  const cfg        = _sigCfg(signal);
  const score      = sig.score     || 0;
  const age        = sig.age       || 0;
  const sector     = sig.sector    || '';
  const grade      = sig.grade     || '';
  const regime     = sig.regime    || '';
  const direction  = sig.direction || 'LONG';
  const bearBonus  = sig.bear_bonus === true ||
                     sig.bear_bonus === 'true';
  const banned     = _isBanned(sig.symbol || sym);
  const isBackfill = sig.generation === 0;
  const showAsNew  = isNew && !isBackfill;

  const isSA = typeof window._isSA === 'function'
    ? window._isSA(signal)
    : signal.endsWith('_SA');

  const conflict    = conflictMap
    ? conflictMap[sym] : null;
  const hasOpposite = conflict
    && conflict.directions.size > 1;
  const hasMultiple = conflict
    && conflict.count > 1;

  const entryPrice = _getEntryPrice(sig);
  const ltpData    = _getLtp(sig.symbol || sym);
  const ltpPrice   = ltpData && ltpData.ltp > 0
    ? ltpData.ltp : null;
  const ltpPct     = _ltpVsEntry(
    entryPrice, ltpPrice, direction);

  const rrData  = _calcRR(
    entryPrice || 0, sig.stop || 0, direction);
  const rrValue = rrData ? rrData.rr : null;

  const stopAlert = _getStopAlert(sig.symbol || sym);
  const sc        = _scoreColor(score);
  const lowConv   = score <= 2;
  const cardOp    = lowConv ? 'opacity:0.6;' : '';

  // H2: outer card border based on score
  const scoreBorder = _cardBorderColor(score);

  let borderGlow = '';
  let cardAnim   = '';
  if (dayNum >= 6) {
    borderGlow =
      'box-shadow:0 0 10px #f8514966;' +
      'border-color:#f85149 !important;';
    cardAnim =
      'animation:exitPulse 1.5s infinite;';
  } else if (dayNum >= 5) {
    borderGlow =
      'box-shadow:0 0 6px #FF8C0044;';
  }

  let conflictBadge = '';
  if (hasOpposite) {
    conflictBadge = `
      <span style="background:#2a0a2a;
        color:#a78bfa;border-radius:4px;
        padding:1px 5px;font-size:9px;
        font-weight:700;margin-left:4px;">
        ⚡ CONFLICT
      </span>`;
  } else if (hasMultiple) {
    conflictBadge = `
      <span style="background:#1a1a0a;
        color:#FFD700;border-radius:4px;
        padding:1px 5px;font-size:9px;
        font-weight:700;margin-left:4px;">
        ×${conflict.count}
      </span>`;
  }

  const banBadge = banned
    ? `<span style="background:#2a0a2a;
         color:#ff66ff;border-radius:4px;
         padding:1px 5px;font-size:9px;
         font-weight:700;">
         ⛔ BAN
       </span>`
    : '';

  const stopBadge = stopAlert
    ? `<span style="background:${
        stopAlert.alert_level === 'BREACHED'
          ? '#f85149' : '#FF8C00'}22;
        color:${stopAlert.alert_level === 'BREACHED'
          ? '#f85149' : '#FF8C00'};
        border-radius:4px;padding:1px 5px;
        font-size:9px;animation:pulse 1s infinite;">
        ⚠️ ${stopAlert.alert_level}
      </span>`
    : '';

  const saBadge = isSA
    ? (typeof window._renderSABadge === 'function'
        ? window._renderSABadge()
        : `<span style="background:#1a1a0a;
             color:#ffd700;font-size:9px;
             font-weight:700;
             border:1px solid #ffd70033;
             border-radius:3px;
             padding:1px 5px;">2ND</span>`)
    : '';

  let ltpDisplay = '';
  if (ltpPrice) {
    const pctNum = ltpPct ? ltpPct.raw : null;
    const pctCol = ltpPct
      ? (ltpPct.favorable ? '#00C851' : '#f85149')
      : '#8b949e';
    const pctStr = pctNum !== null
      ? ` <span style="color:${pctCol};
           font-size:10px;">
           ${pctNum >= 0 ? '▲' : '▼'}${
             Math.abs(pctNum).toFixed(1)}%
         </span>`
      : '';
    ltpDisplay = `<span style="color:#ffd700;
      font-weight:700;">
      LTP ₹${fmt(ltpPrice)}${pctStr}
    </span>`;
  } else if (entryPrice) {
    ltpDisplay = `<span style="color:#8b949e;
      font-size:10px;">LTP —</span>`;
  }

  const sigData = encodeURIComponent(
    JSON.stringify(sig));

  return `
    <div class="signal-card"
      data-signal="${signal}"
      data-age="${age}"
      data-grade="${grade}"
      data-score="${score}"
      data-symbol="${sym}"
      onclick="openTapPanel(this)"
      data-sig="${sigData}"
      style="background:#0d1117;
        border:1px solid ${scoreBorder};
        border-left:4px solid ${cfg.border};
        border-radius:8px;
        padding:12px 14px 10px;
        margin-bottom:8px;
        cursor:pointer;
        ${borderGlow}
        ${cardAnim}
        ${cardOp}
        transition:opacity 0.2s;">

      <!-- Row 1: Stock header -->
      <div style="display:flex;
        justify-content:space-between;
        align-items:flex-start;margin-bottom:5px;">
        <div style="display:flex;align-items:center;
          flex-wrap:wrap;gap:4px;
          flex:1;min-width:0;">
          <span style="font-size:16px;font-weight:700;
            color:#fff;">${sym}</span>
          <span style="color:#555;font-size:11px;">
            ${sector}
          </span>
          ${grade
            ? `<span style="color:#444;
                 font-size:10px;
                 border:1px solid #30363d;
                 border-radius:3px;
                 padding:0 4px;">
                 ${grade}
               </span>`
            : ''}
          ${conflictBadge}
          ${bearBonus
            ? '<span style="font-size:12px;">🔥</span>'
            : ''}
          ${saBadge}
          ${lowConv
            ? `<span style="color:#444;font-size:9px;
                 background:#1c2128;border-radius:3px;
                 padding:1px 4px;">LOW</span>`
            : ''}
        </div>
        <div style="display:flex;align-items:center;
          gap:4px;flex-shrink:0;margin-left:8px;">
          ${banBadge}
          ${stopBadge}
          ${_dayBadge(dayNum, showAsNew, isBackfill)}
        </div>
      </div>

      <!-- Row 2: Signal info + H1 score display -->
      <div style="display:flex;align-items:center;
        gap:8px;flex-wrap:wrap;margin-bottom:7px;">
        <span style="color:${cfg.color};
          font-size:12px;font-weight:700;">
          ${cfg.label} ${cfg.arrow}
        </span>
        <span style="color:#555;font-size:11px;">
          Age:${age}
        </span>
        <span style="color:#444;font-size:11px;">·</span>
        <span style="color:#555;font-size:11px;">
          ${regime || '—'}
        </span>
        <span style="color:#444;font-size:11px;">·</span>
        ${_scoreDisplay(score)}
        ${direction === 'SHORT'
          ? `<span style="color:#a78bfa;
               font-size:10px;">
               ↓SHORT
             </span>`
          : ''}
      </div>

      <!-- Row 3: Price row -->
      <div style="display:flex;align-items:center;
        background:#161b22;border-radius:6px;
        padding:6px 10px;font-size:11px;">
        ${entryPrice
          ? `<div style="flex:1;min-width:90px;">
               <span style="color:#555;
                 font-size:10px;">Entry</span><br>
               <span style="color:#c9d1d9;
                 font-weight:600;">
                 ₹${fmt(entryPrice)}
               </span>
             </div>`
          : ''}
        <div style="flex:1;min-width:110px;">
          ${ltpDisplay}
        </div>
        <div style="flex:0;min-width:60px;
          text-align:right;">
          <span style="color:#555;font-size:10px;">
            R:R
          </span><br>
          <span style="color:${
            rrValue && parseFloat(rrValue) >= 2
              ? '#00C851'
              : rrValue ? '#FFD700' : '#555'};
            font-weight:700;">
            ${rrValue ? rrValue + 'x' : '—'}
          </span>
        </div>
      </div>

      ${banned
        ? `<div style="margin-top:5px;
             background:#1a001a;border-radius:4px;
             padding:3px 8px;font-size:10px;
             color:#ff66ff;">
             ⛔ F&O ban — cash equity only
           </div>`
        : ''}
      ${direction === 'SHORT'
        ? `<div style="margin-top:5px;
             background:#1a0a2a;border-radius:4px;
             padding:3px 8px;font-size:10px;
             color:#a78bfa;">
             ↓ SHORT — verify broker supports
             overnight cash shorts
           </div>`
        : ''}
    </div>`;
}

// ── TAP PANEL ─────────────────────────────────────────
let _currentSig = null;

function openTapPanel(el) {
  try {
    _currentSig = JSON.parse(
      decodeURIComponent(el.dataset.sig));
  } catch(e) { return; }

  const sig         = _currentSig;
  const sym         = (sig.symbol || '')
                      .replace('.NS','');
  const signal      = sig.signal      || '';
  const cfg         = _sigCfg(signal);
  const score       = sig.score       || 0;
  const direction   = sig.direction   || 'LONG';
  const regime      = sig.regime      || '';
  const stockRegime = sig.stock_regime || '';
  const banned      = _isBanned(sig.symbol || sym);
  const isBackfill  = sig.generation === 0;

  const isSA = typeof window._isSA === 'function'
    ? window._isSA(signal)
    : signal.endsWith('_SA');

  const entryPrice = _getEntryPrice(sig);
  const ltpData    = _getLtp(sig.symbol || sym);
  const ltpPrice   = ltpData && ltpData.ltp > 0
    ? ltpData.ltp : null;
  const ltpPct     = _ltpVsEntry(
    entryPrice, ltpPrice, direction);
  const stopPrice  = sig.stop
    ? parseFloat(sig.stop)         : null;
  const targetP    = sig.target_price
    ? parseFloat(sig.target_price) : null;

  const rrData = _calcRR(
    entryPrice || 0, sig.stop || 0, direction);
  const rr     = rrData ? rrData.rr : null;
  const sizing = _calcPositionSize(
    entryPrice, sig.stop);

  const today    = _todayIST();
  const sigDate  = sig.date || today;
  const dayNum   = getDayNumber(sigDate);
  const exitDate = sig.exit_date
    || getExitDate(sigDate);
  const isNew    = sigDate === today;

  const stopAlert = _getStopAlert(sig.symbol || sym);
  const sc        = _scoreColor(score);

  let ltpPanelValue = ltpPrice
    ? `₹${fmt(ltpPrice)}` : '—';
  let ltpPanelColor = ltpPrice ? '#ffd700' : '#555';
  let ltpPanelSub   = '';
  if (ltpPrice && ltpPct) {
    const pctCol = ltpPct.favorable
      ? '#00C851' : '#f85149';
    const pctDir = ltpPct.raw >= 0 ? '▲' : '▼';
    ltpPanelSub  = `<span style="color:${pctCol};
      font-size:11px;">
      ${pctDir}${Math.abs(ltpPct.raw).toFixed(1)}%
      vs entry
    </span>`;
  }

  const tradeWindowLine =
    isNew && !_entryWindowClosed()
      ? '🟢 Enter at 9:15 AM open'
      : isNew && _entryWindowClosed()
        ? `Day 1 of 6 · Entry was 9:15 AM today`
        : `Day ${dayNum} of 6`;

  const whyParts = [];
  if (signal === 'UP_TRI' ||
      signal === 'UP_TRI_SA')
    whyParts.push(
      'Triangle breakout above pivot low');
  if (signal === 'DOWN_TRI' ||
      signal === 'DOWN_TRI_SA')
    whyParts.push(
      'Triangle breakdown below pivot high');
  if (signal === 'BULL_PROXY')
    whyParts.push(
      'Support zone rejection with momentum');
  if (sig.attempt_number === 2)
    whyParts.push(
      'Second attempt — same level proven twice');
  if (sig.bear_bonus === true ||
      sig.bear_bonus === 'true')
    whyParts.push(
      'Bear regime = highest UP_TRI conviction 🔥');
  else if (sig.vol_confirm === true)
    whyParts.push('High volume confirmation');
  if (sig.rs_q === 'Strong')
    whyParts.push('Stock outperforming Nifty');

  const whyLines = whyParts.slice(0, 3)
    .map(w => `<div style="color:#8b949e;
      margin-bottom:3px;">· ${w}</div>`)
    .join('');

  const panelSABadge = isSA
    ? `<span style="background:#1a1a0a;
         color:#ffd700;font-size:10px;
         font-weight:700;
         border:1px solid #ffd70044;
         border-radius:4px;
         padding:2px 8px;">2ND ATT</span>`
    : '';

  // J2 FIX: use window.open — works in iOS PWA
  const tvUrl =
    `https://www.tradingview.com/chart/` +
    `?symbol=NSE%3A${sym}`;

  const panel = document.getElementById('tap-panel');
  if (!panel) return;

  panel.style.display   = 'block';
  panel.style.transform =
    'translateX(-50%) translateY(100%)';
  panel.style.maxWidth  =
    window.innerWidth >= 768 ? '860px' : '600px';

  panel.innerHTML = `
    <div style="width:40px;height:4px;
      background:#30363d;border-radius:2px;
      margin:0 auto 14px;"></div>

    <div style="display:flex;
      justify-content:space-between;
      align-items:center;margin-bottom:12px;">
      <div style="display:flex;align-items:center;
        gap:8px;flex-wrap:wrap;">
        <span style="font-size:22px;font-weight:700;
          color:#fff;">${sym}</span>
        <span style="background:${cfg.color}22;
          color:${cfg.color};border-radius:4px;
          padding:2px 8px;font-size:11px;
          font-weight:700;">
          ${cfg.label} ${cfg.arrow}
        </span>
        ${panelSABadge}
        ${sig.bear_bonus === true
          ? '<span style="font-size:14px;">🔥</span>'
          : ''}
        ${banned
          ? `<span style="background:#2a0a2a;
               color:#ff66ff;border-radius:4px;
               padding:2px 6px;font-size:10px;
               font-weight:700;">⛔ BAN</span>`
          : ''}
        ${isBackfill
          ? `<span style="color:#444;font-size:10px;
               background:#1c2128;border-radius:3px;
               padding:1px 5px;">Backfill</span>`
          : ''}
      </div>
      <button onclick="closeTapPanel()"
        style="background:none;border:none;
          color:#555;font-size:22px;cursor:pointer;
          flex-shrink:0;
          -webkit-tap-highlight-color:transparent;">
        ✕
      </button>
    </div>

    ${stopAlert
      ? `<div style="background:#2a0a0a;
           border:1px solid #f8514966;
           border-radius:6px;padding:8px 10px;
           margin-bottom:10px;font-size:11px;
           color:#f85149;">
           ⚠️ ${stopAlert.note || 'Stop alert active'}
         </div>`
      : ''}
    ${banned
      ? `<div style="background:#1a001a;
           border:1px solid #ff66ff44;
           border-radius:6px;padding:8px 10px;
           margin-bottom:10px;font-size:11px;
           color:#ff66ff;">
           ⛔ F&O ban — cash equity positions only
         </div>`
      : ''}
    ${direction === 'SHORT'
      ? `<div style="background:#1a0a2a;
           border:1px solid #a78bfa44;
           border-radius:6px;padding:8px 10px;
           margin-bottom:10px;font-size:11px;
           color:#a78bfa;">
           ↓ SHORT — verify your broker supports
           overnight cash equity shorts
         </div>`
      : ''}

    <div style="background:#161b22;border-radius:8px;
      padding:12px 14px;margin-bottom:8px;">
      <div style="color:#555;font-size:10px;
        letter-spacing:1px;margin-bottom:4px;">
        CURRENT PRICE
      </div>
      <div style="color:${ltpPanelColor};
        font-size:24px;font-weight:700;
        margin-bottom:2px;">
        ${ltpPanelValue}
      </div>
      ${ltpPanelSub}
    </div>

    <div style="display:grid;
      grid-template-columns:1fr 1fr;
      gap:6px;margin-bottom:8px;">
      ${_panelStat('ENTRY',
        entryPrice ? '₹' + fmt(entryPrice) : '—',
        '#58a6ff')}
      ${_panelStat('STOP',
        stopPrice  ? '₹' + fmt(stopPrice)  : '—',
        '#f85149')}
      ${_panelStat('TARGET',
        targetP ? '₹' + fmt(targetP) : 'Day 6 open',
        '#00C851')}
      ${_panelStat('R:R',
        rr ? rr + 'x' : '—',
        rr && parseFloat(rr) >= 2   ? '#00C851' :
        rr && parseFloat(rr) >= 1.5 ? '#FFD700' :
        '#f85149')}
    </div>

    ${sizing
      ? `<div style="background:#161b22;
           border-radius:8px;padding:10px 12px;
           margin-bottom:8px;font-size:11px;">
           <div style="color:#555;font-size:10px;
             letter-spacing:1px;margin-bottom:6px;">
             POSITION SIZE
           </div>
           <div style="display:flex;
             justify-content:space-between;
             margin-bottom:3px;">
             <span style="color:#8b949e;">Shares</span>
             <span style="color:#ffd700;
               font-weight:700;">
               ${sizing.shares}
             </span>
           </div>
           <div style="display:flex;
             justify-content:space-between;
             margin-bottom:3px;">
             <span style="color:#8b949e;">
               Capital at risk
             </span>
             <span style="color:#ffd700;
               font-weight:700;">
               ₹${sizing.riskAmt
                 .toLocaleString('en-IN')}
             </span>
           </div>
           <div style="display:flex;
             justify-content:space-between;">
             <span style="color:#8b949e;">
               Risk per share
             </span>
             <span style="color:#c9d1d9;">
               ₹${sizing.riskPer}
             </span>
           </div>
         </div>`
      : ''}

    ${_buildScoreBreakdown(sig)}

    ${isSA ? _buildSACallout(sig) : ''}

    <div style="background:#161b22;border-radius:8px;
      padding:10px 12px;margin-bottom:8px;
      font-size:11px;line-height:1.9;">
      ${_detailRow('Regime', regime || '—')}
      ${stockRegime
        ? _detailRow('Stock regime', stockRegime,
            stockRegime === 'Bull' ? '#00C851' :
            stockRegime === 'Bear' ? '#f85149' :
            '#FFD700')
        : ''}
      ${_detailRow('ATR',
        sig.atr ? '₹' + fmt(sig.atr) : '—')}
      ${_detailRow('Volume',      sig.vol_q   || '—')}
      ${_detailRow('RS vs Nifty', sig.rs_q    || '—')}
      ${_detailRow('Sector mom',  sig.sec_mom || '—')}
      ${_detailRow('Grade',       sig.grade   || '—')}
      ${_detailRow('Signal age',
        `${sig.age || 0} days`)}
    </div>

    <div style="background:#0d1117;
      border:1px solid #21262d;border-radius:8px;
      padding:10px 12px;margin-bottom:8px;
      font-size:11px;">
      <div style="color:#555;font-size:10px;
        letter-spacing:1px;margin-bottom:4px;">
        TRADE WINDOW
      </div>
      <div style="color:#c9d1d9;font-weight:700;
        margin-bottom:2px;">
        ${tradeWindowLine}
      </div>
      <div style="color:#555;">
        Exit at open on ${fmtDate(exitDate)}
        ${dayNum >= 6
          ? `<span style="color:#f85149;
               font-weight:700;">
               — EXIT TODAY
             </span>`
          : dayNum >= 5
            ? `<span style="color:#FF8C00;">
                 — Exit tomorrow!
               </span>`
            : ''}
      </div>
      <div style="color:#444;font-size:10px;
        margin-top:3px;">
        Sell at open Day 6 regardless of P&L
      </div>
    </div>

    ${whyLines
      ? `<div style="background:#0a0d1a;
           border:1px solid #21262d;
           border-radius:8px;padding:10px 12px;
           margin-bottom:12px;font-size:11px;">
           <div style="color:#555;font-size:10px;
             letter-spacing:1px;margin-bottom:6px;">
             WHY THIS TRADE
           </div>
           ${whyLines}
         </div>`
      : ''}

    <!-- J2 FIX: window.open for iOS PWA -->
    <div style="display:flex;gap:8px;
      margin-bottom:6px;">
      <button
        onclick="window.open('${tvUrl}','_blank')"
        style="flex:1;background:#161b22;
          border:1px solid #30363d;color:#8b949e;
          border-radius:6px;padding:10px;
          font-size:12px;cursor:pointer;
          text-align:center;
          -webkit-tap-highlight-color:transparent;">
        📈 Open Chart
      </button>
      <button onclick="copySignal()"
        style="flex:1;background:#161b22;
          border:1px solid #30363d;color:#8b949e;
          border-radius:6px;padding:10px;
          font-size:12px;cursor:pointer;
          -webkit-tap-highlight-color:transparent;">
        📋 Copy
      </button>
    </div>

    <button onclick="closeTapPanel()"
      style="width:100%;background:#21262d;
        border:1px solid #30363d;color:#8b949e;
        border-radius:6px;padding:10px;
        font-size:12px;cursor:pointer;
        -webkit-tap-highlight-color:transparent;">
      Close
    </button>`;

  const overlay =
    document.getElementById('tap-overlay');
  if (overlay) {
    overlay.style.display = 'block';
    overlay.onclick       = closeTapPanel;
  }

  requestAnimationFrame(function() {
    panel.style.transform  =
      'translateX(-50%) translateY(0)';
    panel.style.transition =
      'transform 0.3s ease';
  });
}

function closeTapPanel() {
  const panel   = document.getElementById('tap-panel');
  const overlay =
    document.getElementById('tap-overlay');
  if (panel) {
    panel.style.transform =
      'translateX(-50%) translateY(100%)';
    setTimeout(function() {
      panel.style.display = 'none';
    }, 300);
  }
  if (overlay) overlay.style.display = 'none';
}

function copySignal() {
  if (!_currentSig) return;
  const s      = _currentSig;
  const sym    = (s.symbol || '').replace('.NS','');
  const entry  = _getEntryPrice(s);
  const rrData = _calcRR(
    entry || 0, s.stop || 0, s.direction || 'LONG');
  const sizing = _calcPositionSize(entry, s.stop);
  const banned = _isBanned(s.symbol || sym);

  const text = [
    `TIE TIY Signal`,
    `${sym} — ${s.signal}`,
    `Date: ${s.date || '—'}`,
    `Entry: ₹${fmt(entry || 0)}`,
    `Stop: ₹${fmt(s.stop || 0)}`,
    `Target: ₹${fmt(s.target_price || 0)}`,
    `R:R: ${rrData ? rrData.rr + 'x' : '—'}`,
    sizing
      ? `Size: ${sizing.shares} shares · `
        + `Risk ₹${sizing.riskAmt}`
      : '',
    `Score: ${s.score}/10`,
    `Regime: ${s.regime}`,
    `Grade: ${s.grade}`,
    banned ? '⛔ F&O BAN PERIOD' : '',
    s.direction === 'SHORT'
      ? '↓ SHORT — verify broker supports '
        + 'overnight shorts'
      : '',
  ].filter(Boolean).join('\n');

  if (navigator.clipboard &&
      navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text)
      .then(() => _showCopyFeedback())
      .catch(() => _fallbackCopy(text));
  } else {
    _fallbackCopy(text);
  }
}

function _fallbackCopy(text) {
  const ta          =
    document.createElement('textarea');
  ta.value          = text;
  ta.style.position = 'fixed';
  ta.style.top      = '0';
  ta.style.left     = '0';
  ta.style.opacity  = '0';
  document.body.appendChild(ta);
  ta.focus(); ta.select();
  try {
    document.execCommand('copy');
    _showCopyFeedback();
  } catch(e) {}
  document.body.removeChild(ta);
}

function _showCopyFeedback() {
  document.querySelectorAll('#tap-panel button')
    .forEach(function(btn) {
      if (btn.textContent.includes('Copy')) {
        const orig      = btn.innerHTML;
        btn.innerHTML   = '✅ Copied';
        btn.style.color = '#00C851';
        setTimeout(function() {
          btn.innerHTML   = orig;
          btn.style.color = '#8b949e';
        }, 1500);
      }
    });
}

function _panelStat(label, value, color) {
  return `
    <div style="background:#161b22;
      border-radius:6px;padding:8px 10px;">
      <div style="color:#555;font-size:10px;
        margin-bottom:2px;letter-spacing:0.5px;">
        ${label}
      </div>
      <div style="color:${color};font-size:15px;
        font-weight:700;">
        ${value}
      </div>
    </div>`;
}

function _detailRow(label, value, color) {
  return `
    <div style="display:flex;
      justify-content:space-between;">
      <span style="color:#555;">${label}</span>
      <span style="color:${color || '#c9d1d9'};">
        ${value}
      </span>
    </div>`;
}

// ── MAIN RENDER ───────────────────────────────────────
function renderSignals(data) {
  const content =
    document.getElementById('tab-content');
  if (!content) return;

  const today   = _todayIST();
  const scanLog = data.scanLog;

  let activeSignals = [];
  if (data.history && data.history.history) {
    activeSignals = data.history.history.filter(s => {
      if (s.result !== 'PENDING') return false;
      if (!s.exit_date) return true;
      return s.exit_date >= today;
    });
  }

  const currentFilter = _getSavedFilter();
  const currentSector = _getSavedSector();

  const SIG_PRIORITY = {
    UP_TRI: 0, DOWN_TRI: 1, BULL_PROXY: 2,
    UP_TRI_SA: 3, DOWN_TRI_SA: 4,
  };

  const _sortSignals = arr =>
    [...arr].sort((a, b) => {
      const sd = (b.score || 0) - (a.score || 0);
      if (sd !== 0) return sd;
      const ad = (a.age || 0) - (b.age || 0);
      if (ad !== 0) return ad;
      return (SIG_PRIORITY[a.signal] ?? 99) -
             (SIG_PRIORITY[b.signal] ?? 99);
    });

  const todaySignals = _sortSignals(
    activeSignals.filter(s => s.date === today));
  const olderSignals = _sortSignals(
    activeSignals.filter(s => s.date !== today));
  let allSorted =
    [...todaySignals, ...olderSignals];

  let sectorFiltered = allSorted;
  if (currentSector) {
    sectorFiltered = allSorted.filter(
      s => s.sector === currentSector);
  }

  let displaySignals = sectorFiltered;
  let headerLabel    =
    `ALL ACTIVE SIGNALS (${sectorFiltered.length})`;
  let topTruncated   = 0;

  if (currentFilter === 'top') {
    const qualifying = sectorFiltered.filter(
      s => (s.score || 0) >= TOP_SCORE_MIN);
    topTruncated   = Math.max(
      0, qualifying.length - TOP_MAX_SIGNALS);
    displaySignals = qualifying.slice(
      0, TOP_MAX_SIGNALS);
    headerLabel    =
      `TOP SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'UP_TRI') {
    displaySignals = sectorFiltered.filter(
      s => s.signal === 'UP_TRI');
    headerLabel    =
      `UP TRIANGLE SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'DOWN_TRI') {
    displaySignals = sectorFiltered.filter(
      s => s.signal === 'DOWN_TRI');
    headerLabel    =
      `DOWN TRIANGLE SIGNALS `
      + `(${displaySignals.length})`;
  } else if (currentFilter === 'BULL_PROXY') {
    displaySignals = sectorFiltered.filter(
      s => s.signal === 'BULL_PROXY');
    headerLabel    =
      `BULL PROXY SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'SA') {
    displaySignals = sectorFiltered.filter(
      s => (s.signal || '').endsWith('_SA'));
    headerLabel    =
      `2ND ATTEMPT SIGNALS `
      + `(${displaySignals.length})`;
   } else if (currentFilter === 'age0') {
    displaySignals = sectorFiltered.filter(
      s => s.date === _todayIST()
        && s.generation !== 0);
    headerLabel    =
      `NEW TODAY SIGNALS (${displaySignals.length})`;

  }

  const conflictMap = _buildConflictMap(allSorted);

  const totalRisk = allSorted.reduce((sum, s) => {
    const e  = parseFloat(
      s.actual_open || s.scan_price ||
      s.entry || 0);
    const st = parseFloat(s.stop || 0);
    if (!e || !st) return sum;
    const risk   = Math.abs(e - st);
    const shares = risk > 0
      ? Math.floor(DEFAULT_CAPITAL / risk) : 0;
    return sum + shares * risk;
  }, 0);

  const riskStr     = totalRisk > 0
    ? ` · Total risk ₹${Math.round(totalRisk)
        .toLocaleString('en-IN')}` : '';
  const sectorLabel = currentSector
    ? ` · ${currentSector} only` : '';
  const rejected    = scanLog
    ? (scanLog.rejected || []) : [];

  if (!allSorted.length) {
    const meta    = data.meta || {};
    const scanned = meta.universe_size || 0;
    const scanT   = meta.last_scan
      ? fmtTime(meta.last_scan) : '—';

    content.innerHTML = `
      ${_buildStyles()}
      <div style="padding:14px;">
        ${_buildFilterBar(
          [], currentFilter, currentSector)}
        <div style="text-align:center;
          padding:40px 20px;
          color:#555;font-size:13px;">
          <div style="font-size:32px;
            margin-bottom:12px;">📊</div>
          <div style="color:#8b949e;font-size:15px;
            font-weight:700;margin-bottom:8px;">
            No active signals
          </div>
          <div style="margin-bottom:4px;">
            ${meta.is_trading_day
              ? `Scanned ${scanned} stocks at ${scanT}`
              : 'Market closed today'}
          </div>
        </div>
        ${rejected.length
          ? _buildRejectedSection(rejected) : ''}
      </div>`;
    _renderNav('signals');
    return;
  }

  content.innerHTML = `
    ${_buildStyles()}
    <div style="padding-bottom:80px;">
      ${_buildFilterBar(
        allSorted, currentFilter, currentSector)}
      ${_buildMorningBrief(
        allSorted, data.stopAlerts)}
      <div style="padding:0 14px;">
        <div style="color:#8b949e;font-size:11px;
          font-weight:700;letter-spacing:1px;
          padding:10px 0 6px;
          border-left:3px solid #ffd700;
          padding-left:8px;margin-bottom:10px;">
          ${headerLabel}
          ${currentFilter === 'top'
            ? `<span style="color:#555;
                 font-size:10px;font-weight:400;
                 margin-left:6px;">
                 Score ${TOP_SCORE_MIN}+ ·
                 Best setups only
               </span>`
            : ''}
          <span style="color:#555;font-size:10px;
            font-weight:400;">
            ${riskStr}${sectorLabel}
          </span>
        </div>

        ${displaySignals.map(sig => {
          const isNew  = sig.date === today;
          const dayNum = getDayNumber(
            sig.date || today);
          return _buildCard(
            sig, isNew, dayNum, conflictMap);
        }).join('')}

        ${currentFilter === 'top'
            && topTruncated > 0
          ? `<div style="text-align:center;
               padding:10px;font-size:11px;
               color:#555;">
               + ${topTruncated} more top signal${
                 topTruncated > 1 ? 's' : ''}  ·
               <span style="color:#58a6ff;
                 cursor:pointer;"
                 onclick="applyFilter('all',
                   document.querySelector(
                     '[data-filter=all]'))">
                 Switch to All
               </span>
             </div>`
          : ''}

        ${rejected.length
          ? `<div style="margin-top:6px;">
               ${_buildRejectedSection(rejected)}
             </div>`
          : ''}
      </div>
    </div>`;

  _renderNav('signals');
}

// ── REJECTED SECTION ──────────────────────────────────
function _buildRejectedSection(rejected) {
  if (!rejected.length) return '';

  const rows = rejected.slice(0, 12).map(s => {
    const sym    = (s.symbol || s.stock || '')
                   .replace('.NS','');
    const signal = s.signal || '';
    const cfg    = _sigCfg(signal);
    const score  = s.score || 0;
    const sc     = _scoreColor(score);
    const reason = 'ALPHA: ' + (
      s.rejection_reason
        ? s.rejection_reason.replace(/_/g,' ')
        : `Score ${score}/10`);

    return `
      <div style="display:flex;
        justify-content:space-between;
        align-items:center;padding:6px 0;
        border-bottom:1px solid #0c0c1a;
        font-size:11px;">
        <div>
          <span style="color:#444;font-weight:700;">
            ${sym}
          </span>
          <span style="color:${cfg.color}44;
            margin-left:6px;">
            ${cfg.label} ${cfg.arrow}
          </span>
        </div>
        <div style="color:#333;font-size:10px;
          text-align:right;">
          <span style="color:${sc};">
            ${score}/10
          </span>
          · ${reason}
        </div>
      </div>`;
  }).join('');

  return `
    <div style="margin-top:16px;">
      <div id="rej-toggle"
        onclick="toggleRejected()"
        style="color:#444;font-size:11px;
          font-weight:700;
          border-left:3px solid #333;
          padding-left:8px;cursor:pointer;
          margin-bottom:6px;">
        ▶ REJECTED TODAY (${rejected.length})
      </div>
      <div id="rej-section" style="display:none;">
        ${rows}
        <div style="font-size:10px;color:#333;
          padding:6px 0;">
          Shadow mode — all data collected for
          future analysis.
        </div>
      </div>
    </div>`;
}

function toggleRejected() {
  const sec =
    document.getElementById('rej-section');
  const tog =
    document.getElementById('rej-toggle');
  if (!sec) return;
  const open        = sec.style.display !== 'none';
  sec.style.display = open ? 'none' : 'block';
  if (tog) tog.innerHTML = tog.innerHTML
    .replace(open ? '▼' : '▶',
             open ? '▶' : '▼');
}

function _buildStyles() {
  return `
    <style>
      @keyframes pulse {
        0%   { opacity: 1;   }
        50%  { opacity: 0.5; }
        100% { opacity: 1;   }
      }
      @keyframes exitPulse {
        0%   { box-shadow: 0 0 6px  #f8514966; }
        50%  { box-shadow: 0 0 14px #f85149cc; }
        100% { box-shadow: 0 0 6px  #f8514966; }
      }
      .signal-card:active { opacity: 0.8; }
    </style>`;
}

// ── PUSH NOTIFICATIONS ────────────────────────────────
async function requestNotifications() {
  const statusEl =
    document.getElementById('notif-status');
  const btn = document.getElementById('notif-btn');

  if (!('serviceWorker' in navigator) ||
      !('PushManager' in window)) {
    if (statusEl) statusEl.textContent =
      'Install as PWA from home screen first.';
    return;
  }

  const pin = prompt(
    'Enter 4-digit notification PIN:');
  if (!pin || pin.length !== 4) {
    if (statusEl) statusEl.textContent =
      'Invalid PIN.';
    return;
  }

  try {
    if (statusEl) statusEl.textContent =
      'Requesting permission…';
    const permission =
      await Notification.requestPermission();
    if (permission !== 'granted') {
      if (statusEl) statusEl.textContent =
        'Permission denied.';
      return;
    }

    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly:      true,
      applicationServerKey: _urlB64ToUint8Array(
        window.VAPID_PUBLIC_KEY ||
        'BD0o5qPcwXsEpSv5KXOSKZRHyyGVoC0bTNbRMcOSX2t-'
        + 't5OBf1sHGKJH2y8m6uYnCwa3g_xfzJdmWoEuxR941Rk'),
    });

    const subJson = sub.toJSON();
    if (statusEl) statusEl.innerHTML =
      '<span style="color:#00C851;">'
      + '✓ Subscribed!</span>'
      + ' Alerts at 8:50 AM IST.';
    if (btn) btn.textContent = '✓ Subscribed';

    try {
      localStorage.setItem(
        'tietiy_push_sub', JSON.stringify({
          endpoint:      subJson.endpoint,
          keys:          subJson.keys,
          subscribed_at: new Date()
            .toISOString().slice(0, 10),
        }));
    } catch(e) {}

  } catch(e) {
    if (statusEl) statusEl.textContent =
      'Failed: ' + e.message;
  }
}

function _urlB64ToUint8Array(base64String) {
  const padding =
    '='.repeat((4 - base64String.length % 4) % 4);
  const base64  = (base64String + padding)
    .replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const arr     = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++)
    arr[i] = rawData.charCodeAt(i);
  return arr;
}

// ── R3: SERVICE WORKER MESSAGE LISTENER ───────────────
let _swListenerAttached = false;

function _initSWMessageListener() {
  if (_swListenerAttached) return;
  if (!('serviceWorker' in navigator)) return;

  navigator.serviceWorker.addEventListener(
    'message',
    function(event) {
      if (!event.data) return;
      const type = event.data.type;
      if (type === 'OFFLINE') {
        if (typeof window._showOfflineBanner
            === 'function') {
          window._showOfflineBanner();
        }
      } else if (type === 'ONLINE') {
        if (typeof window._hideOfflineBanner
            === 'function') {
          window._hideOfflineBanner();
        }
      }
    }
  );

  _swListenerAttached = true;
  console.log('[app] SW message listener attached');
}

if ('serviceWorker' in navigator) {
  if (navigator.serviceWorker.controller) {
    _initSWMessageListener();
  } else {
    navigator.serviceWorker.addEventListener(
      'controllerchange',
      function() {
        _initSWMessageListener();
      }
    );
  }
}
