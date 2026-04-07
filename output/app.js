// ── app.js ───────────────────────────────────────────
// Signals tab: compact/expanded cards, filter bar,
// tap panel, conflict detection
//
// Design pass: TOP filter default, Entry + LTP separate,
// score color system, day badge urgency, conflict warnings
// ─────────────────────────────────────────────────────

const SIGNAL_CONFIG = {
  UP_TRI:      { color: '#00C851', arrow: '▲', label: 'UP TRI',       border: '#00C851' },
  DOWN_TRI:    { color: '#f85149', arrow: '▼', label: 'DOWN TRI',     border: '#f85149' },
  BULL_PROXY:  { color: '#58a6ff', arrow: '◆', label: 'BULL PROXY',   border: '#58a6ff' },
  UP_TRI_SA:   { color: '#00C851', arrow: '▲▲', label: 'UP TRI 2nd',  border: '#00C851' },
  DOWN_TRI_SA: { color: '#f85149', arrow: '▼▼', label: 'DOWN TRI 2nd',border: '#f85149' },
};

const DEFAULT_CAPITAL  = 50000;
const TOP_SCORE_MIN    = 6;
const TOP_MAX_SIGNALS  = 7;

// ── HELPERS ───────────────────────────────────────────
function _sigCfg(signal) {
  return SIGNAL_CONFIG[signal] || {
    color: '#8b949e', arrow: '?', label: signal, border: '#30363d'
  };
}

function _entryWindowClosed() {
  const now = new Date();
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const h   = ist.getHours();
  const m   = ist.getMinutes();
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
  return ltp.prices[symbol] ||
         ltp.prices[clean + '.NS'] ||
         ltp.prices[clean] ||
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

// Entry price for display — actual_open if trade started,
// else scan_price (planned entry)
function _getEntryPrice(sig) {
  for (const f of ['actual_open','scan_price','entry','entry_est']) {
    const v = sig[f];
    if (v !== null && v !== undefined) {
      const n = parseFloat(v);
      if (n > 0) return n;
    }
  }
  return null;
}

// LTP % vs entry — raw % move, favorability for direction
function _ltpVsEntry(entryPrice, ltpPrice, direction) {
  if (!entryPrice || !ltpPrice || entryPrice <= 0 || ltpPrice <= 0) return null;
  const raw      = (ltpPrice - entryPrice) / entryPrice * 100;
  const favorable = direction === 'SHORT' ? raw < 0 : raw > 0;
  return { raw, favorable };
}

function _calcRR(entry, stop, direction) {
  try {
    entry = parseFloat(entry);
    stop  = parseFloat(stop);
    if (!entry || !stop) return null;
    let risk, target;
    if (direction === 'LONG') {
      risk   = entry - stop;
      if (risk <= 0) return null;
      target = entry + 2 * risk;
    } else {
      risk   = stop - entry;
      if (risk <= 0) return null;
      target = entry - 2 * risk;
    }
    return { rr: (Math.abs(target - entry) / risk).toFixed(1), target };
  } catch(e) { return null; }
}

function _calcPositionSize(entry, stop) {
  try {
    const e = parseFloat(entry);
    const s = parseFloat(stop);
    if (!e || !s || e <= 0 || s <= 0) return null;
    const riskPerShare = Math.abs(e - s);
    if (riskPerShare <= 0) return null;
    const shares    = Math.floor(DEFAULT_CAPITAL / riskPerShare);
    const totalRisk = shares * riskPerShare;
    return { shares, riskAmt: Math.round(totalRisk), riskPer: riskPerShare.toFixed(2) };
  } catch(e) { return null; }
}

// ── SCORE COLOR ───────────────────────────────────────
function _scoreColor(score) {
  if (score >= 7) return '#FFD700';  // gold
  if (score >= 5) return '#00C851';  // green
  if (score >= 3) return '#8b949e';  // grey
  return '#555';                      // dim
}

// ── DAY BADGE ─────────────────────────────────────────
function _dayBadge(dayNum, isNew, isBackfill) {
  if (isNew && !isBackfill) {
    return `<span style="background:#1a3a1a;color:#00C851;
      border-radius:4px;padding:2px 7px;font-size:10px;
      font-weight:700;">NEW</span>`;
  }
  if (!dayNum) return '';
  const color = dayNum >= 6 ? '#f85149' :
                dayNum >= 5 ? '#FF8C00' : '#555';
  const icon  = dayNum >= 6 ? ' ⚠️' : '';
  return `<span style="color:${color};font-size:10px;font-weight:700;">
    Day ${dayNum}/6${icon}
  </span>`;
}

// ── CONFLICT DETECTION ────────────────────────────────
// Returns map: cleanSym → { count, directions: Set }
function _buildConflictMap(signals) {
  const map = {};
  signals.forEach(s => {
    const sym = (s.symbol || '').replace('.NS', '');
    if (!map[sym]) map[sym] = { count: 0, directions: new Set() };
    map[sym].count++;
    map[sym].directions.add(s.direction || 'LONG');
  });
  return map;
}

// ── FILTER BAR ────────────────────────────────────────
function _buildFilterBar(signals, currentFilter) {
  const counts = {
    all:        signals.length,
    UP_TRI:     signals.filter(s => s.signal === 'UP_TRI').length,
    DOWN_TRI:   signals.filter(s => s.signal === 'DOWN_TRI').length,
    BULL_PROXY: signals.filter(s => s.signal === 'BULL_PROXY').length,
    SA:         signals.filter(s => (s.signal || '').endsWith('_SA')).length,
    age0:       signals.filter(s => s.age === 0 && s.generation !== 0).length,
    top:        signals.filter(s => (s.score || 0) >= TOP_SCORE_MIN).length,
  };

  const filters = [
    { id: 'top',        label: `TOP (${Math.min(counts.top, TOP_MAX_SIGNALS)})` },
    { id: 'all',        label: `All (${counts.all})` },
    { id: 'UP_TRI',     label: `UP▲ (${counts.UP_TRI})` },
    { id: 'DOWN_TRI',   label: `DOWN▼ (${counts.DOWN_TRI})` },
    { id: 'BULL_PROXY', label: `◆ Proxy (${counts.BULL_PROXY})` },
    { id: 'age0',       label: `New Today (${counts.age0})` },
    { id: 'SA',         label: `2nd Att (${counts.SA})` },
  ];

  return `
    <div id="filter-bar" style="display:flex;flex-wrap:wrap;
      gap:4px;padding:8px 14px;
      background:#0d1117;
      border-bottom:1px solid #21262d;">
      ${filters.map(f => {
        const isActive = f.id === currentFilter;
        return `
          <button
            class="filter-btn ${isActive ? 'active' : ''}"
            data-filter="${f.id}"
            onclick="applyFilter('${f.id}', this)"
            style="background:${isActive ? '#ffd700' : '#161b22'};
              color:${isActive ? '#000' : '#8b949e'};
              border:1px solid ${isActive ? '#ffd700' : '#30363d'};
              border-radius:6px;padding:5px 10px;
              font-size:10px;font-weight:${isActive ? '700' : '400'};
              cursor:pointer;white-space:nowrap;">
            ${f.label}
          </button>`;
      }).join('')}
    </div>`;
}

function applyFilter(filterId, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.style.background  = '#161b22';
    b.style.color       = '#8b949e';
    b.style.border      = '1px solid #30363d';
    b.style.fontWeight  = '400';
  });
  if (btn) {
    btn.style.background = '#ffd700';
    btn.style.color      = '#000';
    btn.style.border     = '1px solid #ffd700';
    btn.style.fontWeight = '700';
  }

  try { sessionStorage.setItem('tietiy_filter', filterId); }
  catch(e) {}

  // Re-render signals with new filter
  if (typeof renderSignals === 'function')
    renderSignals(window.TIETIY);
}

function _getSavedFilter() {
  try {
    return sessionStorage.getItem('tietiy_filter') || 'top';
  } catch(e) { return 'top'; }
}

// ── COMPACT CARD ──────────────────────────────────────
function _buildCard(sig, isNew, dayNum, conflictMap) {
  const sym         = (sig.symbol || '').replace('.NS','');
  const signal      = sig.signal || '';
  const cfg         = _sigCfg(signal);
  const score       = sig.score || 0;
  const age         = sig.age   || 0;
  const sector      = sig.sector || '';
  const grade       = sig.grade  || '';
  const regime      = sig.regime || '';
  const direction   = sig.direction || 'LONG';
  const bearBonus   = sig.bear_bonus === true || sig.bear_bonus === 'true';
  const banned      = _isBanned(sig.symbol || sym);
  const isBackfill  = sig.generation === 0;
  const showAsNew   = isNew && !isBackfill;

  // Conflict detection
  const conflict    = conflictMap ? conflictMap[sym] : null;
  const hasOpposite = conflict && conflict.directions.size > 1;
  const hasMultiple = conflict && conflict.count > 1;

  // Prices
  const entryPrice = _getEntryPrice(sig);
  const ltpData    = _getLtp(sig.symbol || sym);
  const ltpPrice   = ltpData && ltpData.ltp > 0 ? ltpData.ltp : null;
  const ltpPct     = _ltpVsEntry(entryPrice, ltpPrice, direction);

  // R:R
  const rrData  = _calcRR(entryPrice || 0, sig.stop || 0, direction);
  const rrValue = rrData ? rrData.rr : null;

  // Stop alert
  const stopAlert = _getStopAlert(sig.symbol || sym);

  // Score styling
  const sc      = _scoreColor(score);
  const lowConv = score <= 2;
  const cardOp  = lowConv ? 'opacity:0.6;' : '';

  // Border glow on day 5+
  const borderGlow = dayNum >= 5
    ? `box-shadow:0 0 6px ${dayNum >= 6 ? '#f85149' : '#FF8C00'}44;` : '';

  // Conflict badge
  let conflictBadge = '';
  if (hasOpposite) {
    conflictBadge = `<span style="background:#2a0a2a;color:#a78bfa;
      border-radius:4px;padding:1px 5px;font-size:9px;
      font-weight:700;margin-left:4px;">⚡ CONFLICT</span>`;
  } else if (hasMultiple) {
    conflictBadge = `<span style="background:#1a1a0a;color:#FFD700;
      border-radius:4px;padding:1px 5px;font-size:9px;
      font-weight:700;margin-left:4px;">×${conflict.count}</span>`;
  }

  // Ban badge
  const banBadge = banned
    ? `<span style="background:#2a0a2a;color:#ff66ff;
        border-radius:4px;padding:1px 5px;font-size:9px;
        font-weight:700;">⛔ BAN</span>`
    : '';

  // Stop alert badge
  const stopBadge = stopAlert
    ? `<span style="background:${stopAlert.alert_level === 'BREACHED' ? '#f85149' : '#FF8C00'}22;
        color:${stopAlert.alert_level === 'BREACHED' ? '#f85149' : '#FF8C00'};
        border-radius:4px;padding:1px 5px;font-size:9px;
        animation:pulse 1s infinite;">
        ⚠️ ${stopAlert.alert_level}
      </span>`
    : '';

  // LTP display
  let ltpDisplay = '';
  if (ltpPrice) {
    const pctNum  = ltpPct ? ltpPct.raw : null;
    const pctCol  = ltpPct ? (ltpPct.favorable ? '#00C851' : '#f85149') : '#8b949e';
    const pctStr  = pctNum !== null
      ? ` <span style="color:${pctCol};font-size:10px;">
           ${pctNum >= 0 ? '▲' : '▼'}${Math.abs(pctNum).toFixed(1)}%
         </span>`
      : '';
    ltpDisplay = `<span style="color:#ffd700;font-weight:700;">
      LTP ₹${fmt(ltpPrice)}${pctStr}
    </span>`;
  } else if (entryPrice) {
    ltpDisplay = `<span style="color:#8b949e;font-size:10px;">
      LTP —
    </span>`;
  }

  // Encode signal data
  const sigData = encodeURIComponent(JSON.stringify(sig));

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
        border:1px solid #21262d;
        border-left:4px solid ${cfg.border};
        border-radius:8px;
        padding:12px 14px 10px;
        margin-bottom:8px;
        cursor:pointer;
        ${borderGlow}
        ${cardOp}
        transition:opacity 0.2s;">

      <!-- Row 1: Stock header -->
      <div style="display:flex;justify-content:space-between;
        align-items:flex-start;margin-bottom:5px;">
        <div style="display:flex;align-items:center;
          flex-wrap:wrap;gap:4px;flex:1;min-width:0;">
          <span style="font-size:16px;font-weight:700;color:#fff;">
            ${sym}
          </span>
          <span style="color:#555;font-size:11px;">
            ${sector}
          </span>
          ${grade
            ? `<span style="color:#444;font-size:10px;
                border:1px solid #30363d;border-radius:3px;
                padding:0 4px;">
                ${grade}
              </span>`
            : ''}
          ${conflictBadge}
          ${bearBonus ? '<span style="font-size:12px;">🔥</span>' : ''}
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

      <!-- Row 2: Signal info -->
      <div style="display:flex;align-items:center;
        gap:8px;flex-wrap:wrap;margin-bottom:7px;">
        <span style="color:${cfg.color};font-size:12px;font-weight:700;">
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
        <span style="color:${sc};font-size:11px;font-weight:700;">
          Score ${score}/10
        </span>
        ${direction === 'SHORT'
          ? `<span style="color:#a78bfa;font-size:10px;">↓SHORT</span>`
          : ''}
      </div>

      <!-- Row 3: Price row -->
      <div style="display:flex;align-items:center;
        gap:0;flex-wrap:wrap;
        background:#161b22;border-radius:6px;
        padding:6px 10px;font-size:11px;">
        ${entryPrice
          ? `<div style="flex:1;min-width:90px;">
               <span style="color:#555;font-size:10px;">Entry</span><br>
               <span style="color:#c9d1d9;font-weight:600;">
                 ₹${fmt(entryPrice)}
               </span>
             </div>`
          : ''}
        <div style="flex:1;min-width:110px;">
          ${ltpDisplay}
        </div>
        <div style="flex:0;min-width:60px;text-align:right;">
          <span style="color:#555;font-size:10px;">R:R</span><br>
          <span style="color:${rrValue && parseFloat(rrValue) >= 2 ? '#00C851' : rrValue ? '#FFD700' : '#555'};
            font-weight:700;">
            ${rrValue ? rrValue + 'x' : '—'}
          </span>
        </div>
      </div>

      <!-- Inline banners if needed -->
      ${banned
        ? `<div style="margin-top:5px;background:#1a001a;
             border-radius:4px;padding:3px 8px;
             font-size:10px;color:#ff66ff;">
             ⛔ F&O ban — cash equity only
           </div>`
        : ''}
      ${direction === 'SHORT'
        ? `<div style="margin-top:5px;background:#1a0a2a;
             border-radius:4px;padding:3px 8px;
             font-size:10px;color:#a78bfa;">
             ↓ SHORT — verify broker supports overnight cash shorts
           </div>`
        : ''}
    </div>`;
}

// ── TAP PANEL — EXPANDED CARD ─────────────────────────
let _currentSig = null;

function openTapPanel(el) {
  try {
    _currentSig = JSON.parse(decodeURIComponent(el.dataset.sig));
  } catch(e) { return; }

  const sig         = _currentSig;
  const sym         = (sig.symbol || '').replace('.NS','');
  const signal      = sig.signal || '';
  const cfg         = _sigCfg(signal);
  const score       = sig.score     || 0;
  const direction   = sig.direction || 'LONG';
  const regime      = sig.regime    || '';
  const stockRegime = sig.stock_regime || '';
  const banned      = _isBanned(sig.symbol || sym);
  const isBackfill  = sig.generation === 0;

  const entryPrice = _getEntryPrice(sig);
  const ltpData    = _getLtp(sig.symbol || sym);
  const ltpPrice   = ltpData && ltpData.ltp > 0 ? ltpData.ltp : null;
  const ltpPct     = _ltpVsEntry(entryPrice, ltpPrice, direction);
  const stopPrice  = sig.stop        ? parseFloat(sig.stop)        : null;
  const targetP    = sig.target_price ? parseFloat(sig.target_price) : null;

  const rrData = _calcRR(entryPrice || 0, sig.stop || 0, direction);
  const rr     = rrData ? rrData.rr : null;

  const sizing = _calcPositionSize(entryPrice, sig.stop);

  const today    = _todayIST();
  const sigDate  = sig.date || today;
  const dayNum   = getDayNumber(sigDate);
  const exitDate = sig.exit_date || getExitDate(sigDate);
  const isNew    = sigDate === today;

  const stopAlert = _getStopAlert(sig.symbol || sym);

  // Score color
  const sc = _scoreColor(score);

  // LTP display for panel
  let ltpPanelValue = ltpPrice ? `₹${fmt(ltpPrice)}` : '—';
  let ltpPanelColor = ltpPrice ? '#ffd700' : '#555';
  let ltpPanelSub   = '';
  if (ltpPrice && ltpPct) {
    const pctCol = ltpPct.favorable ? '#00C851' : '#f85149';
    const pctDir = ltpPct.raw >= 0 ? '▲' : '▼';
    ltpPanelSub  = `<span style="color:${pctCol};font-size:11px;">
      ${pctDir}${Math.abs(ltpPct.raw).toFixed(1)}% vs entry
    </span>`;
  }

  // Entry window status
  const tradeWindowLine =
    isNew && !_entryWindowClosed()
      ? '🟢 Enter at 9:15 AM open'
      : isNew && _entryWindowClosed()
        ? `Day 1 of 6 · Entry was 9:15 AM today`
        : `Day ${dayNum} of 6`;

  // WHY THIS TRADE — concise, max 3 points
  const whyParts = [];
  if (signal === 'UP_TRI' || signal === 'UP_TRI_SA')
    whyParts.push('Triangle breakout above pivot low');
  if (signal === 'DOWN_TRI' || signal === 'DOWN_TRI_SA')
    whyParts.push('Triangle breakdown below pivot high');
  if (signal === 'BULL_PROXY')
    whyParts.push('Support zone rejection with momentum');
  if (sig.attempt_number === 2)
    whyParts.push('Second attempt — same level proven twice');
  if (sig.bear_bonus === true || sig.bear_bonus === 'true')
    whyParts.push('Bear regime = highest UP_TRI conviction 🔥');
  else if (sig.vol_confirm === true)
    whyParts.push('High volume confirmation');
  if (sig.rs_q === 'Strong')
    whyParts.push('Stock outperforming Nifty');

  const whyLines = whyParts.slice(0, 3)
    .map(w => `<div style="color:#8b949e;margin-bottom:3px;">· ${w}</div>`)
    .join('');

  const tvUrl = `https://www.tradingview.com/chart/?symbol=NSE%3A${sym}`;

  const panel = document.getElementById('tap-panel');
  if (!panel) return;

  panel.style.display     = 'block';
  panel.style.transform   = 'translateX(-50%) translateY(100%)';
  panel.style.maxWidth    = window.innerWidth >= 768 ? '860px' : '600px';

  panel.innerHTML = `
    <!-- Drag handle -->
    <div style="width:40px;height:4px;background:#30363d;
      border-radius:2px;margin:0 auto 14px;"></div>

    <!-- Panel header -->
    <div style="display:flex;justify-content:space-between;
      align-items:center;margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="font-size:22px;font-weight:700;color:#fff;">
          ${sym}
        </span>
        <span style="background:${cfg.color}22;color:${cfg.color};
          border-radius:4px;padding:2px 8px;font-size:11px;
          font-weight:700;">
          ${cfg.label} ${cfg.arrow}
        </span>
        ${sig.bear_bonus === true ? '<span style="font-size:14px;">🔥</span>' : ''}
        ${banned
          ? `<span style="background:#2a0a2a;color:#ff66ff;
              border-radius:4px;padding:2px 6px;font-size:10px;
              font-weight:700;">⛔ BAN</span>`
          : ''}
        ${isBackfill
          ? `<span style="color:#444;font-size:10px;
              background:#1c2128;border-radius:3px;
              padding:1px 5px;">Backfill</span>`
          : ''}
      </div>
      <button onclick="closeTapPanel()"
        style="background:none;border:none;color:#555;
          font-size:22px;cursor:pointer;
          flex-shrink:0;">✕</button>
    </div>

    <!-- Warnings -->
    ${stopAlert
      ? `<div style="background:#2a0a0a;border:1px solid #f8514966;
           border-radius:6px;padding:8px 10px;margin-bottom:10px;
           font-size:11px;color:#f85149;">
           ⚠️ ${stopAlert.note || 'Stop alert active'}
         </div>`
      : ''}
    ${banned
      ? `<div style="background:#1a001a;border:1px solid #ff66ff44;
           border-radius:6px;padding:8px 10px;margin-bottom:10px;
           font-size:11px;color:#ff66ff;">
           ⛔ F&O ban — cash equity positions only
         </div>`
      : ''}
    ${direction === 'SHORT'
      ? `<div style="background:#1a0a2a;border:1px solid #a78bfa44;
           border-radius:6px;padding:8px 10px;margin-bottom:10px;
           font-size:11px;color:#a78bfa;">
           ↓ SHORT — verify your broker supports overnight cash equity shorts
         </div>`
      : ''}

    <!-- 1. LTP — large, prominent -->
    <div style="background:#161b22;border-radius:8px;
      padding:12px 14px;margin-bottom:8px;">
      <div style="color:#555;font-size:10px;
        letter-spacing:1px;margin-bottom:4px;">
        CURRENT PRICE
      </div>
      <div style="color:${ltpPanelColor};font-size:24px;
        font-weight:700;margin-bottom:2px;">
        ${ltpPanelValue}
      </div>
      ${ltpPanelSub}
    </div>

    <!-- 2–5. Entry / Stop / Target / R:R grid -->
    <div style="display:grid;grid-template-columns:1fr 1fr;
      gap:6px;margin-bottom:8px;">
      ${_panelStat('ENTRY', entryPrice ? '₹' + fmt(entryPrice) : '—', '#58a6ff')}
      ${_panelStat('STOP',  stopPrice  ? '₹' + fmt(stopPrice)  : '—', '#f85149')}
      ${_panelStat('TARGET', targetP   ? '₹' + fmt(targetP)    : 'Day 6 open', '#00C851')}
      ${_panelStat('R:R',
        rr ? rr + 'x' : '—',
        rr && parseFloat(rr) >= 2   ? '#00C851' :
        rr && parseFloat(rr) >= 1.5 ? '#FFD700' : '#f85149')}
    </div>

    <!-- 6. Size / risk -->
    ${sizing
      ? `<div style="background:#161b22;border-radius:8px;
           padding:10px 12px;margin-bottom:8px;font-size:11px;">
           <div style="color:#555;font-size:10px;
             letter-spacing:1px;margin-bottom:6px;">
             POSITION SIZE
           </div>
           <div style="display:flex;justify-content:space-between;
             margin-bottom:3px;">
             <span style="color:#8b949e;">Shares</span>
             <span style="color:#ffd700;font-weight:700;">
               ${sizing.shares}
             </span>
           </div>
           <div style="display:flex;justify-content:space-between;
             margin-bottom:3px;">
             <span style="color:#8b949e;">Capital at risk</span>
             <span style="color:#ffd700;font-weight:700;">
               ₹${sizing.riskAmt.toLocaleString('en-IN')}
             </span>
           </div>
           <div style="display:flex;justify-content:space-between;">
             <span style="color:#8b949e;">Risk per share</span>
             <span style="color:#c9d1d9;">₹${sizing.riskPer}</span>
           </div>
         </div>`
      : ''}

    <!-- 7. Context block -->
    <div style="background:#161b22;border-radius:8px;
      padding:10px 12px;margin-bottom:8px;font-size:11px;
      line-height:1.9;">
      ${_detailRow('Score',       `${score}/10`, sc)}
      ${_detailRow('Regime',      regime || '—')}
      ${stockRegime
        ? _detailRow('Stock regime', stockRegime,
            stockRegime === 'Bull' ? '#00C851' :
            stockRegime === 'Bear' ? '#f85149' : '#FFD700')
        : ''}
      ${_detailRow('ATR',    sig.atr  ? '₹' + fmt(sig.atr)    : '—')}
      ${_detailRow('Volume', sig.vol_q || '—')}
      ${_detailRow('RS vs Nifty', sig.rs_q   || '—')}
      ${_detailRow('Sector mom',  sig.sec_mom || '—')}
      ${_detailRow('Grade',       sig.grade   || '—')}
      ${_detailRow('Signal age',  `${sig.age || 0} days`)}
    </div>

    <!-- 8. Trade window -->
    <div style="background:#0d1117;border:1px solid #21262d;
      border-radius:8px;padding:10px 12px;margin-bottom:8px;
      font-size:11px;">
      <div style="color:#555;font-size:10px;
        letter-spacing:1px;margin-bottom:4px;">
        TRADE WINDOW
      </div>
      <div style="color:#c9d1d9;font-weight:700;margin-bottom:2px;">
        ${tradeWindowLine}
      </div>
      <div style="color:#555;">
        Exit at open on ${fmtDate(exitDate)}
        ${dayNum >= 6
          ? '<span style="color:#f85149;font-weight:700;"> — EXIT TODAY</span>'
          : dayNum >= 5
            ? '<span style="color:#FF8C00;"> — Exit tomorrow!</span>'
            : ''}
      </div>
      <div style="color:#444;font-size:10px;margin-top:3px;">
        Sell at open Day 6 regardless of P&L
      </div>
    </div>

    <!-- 9. Why this trade -->
    ${whyLines
      ? `<div style="background:#0a0d1a;border:1px solid #21262d;
           border-radius:8px;padding:10px 12px;margin-bottom:12px;
           font-size:11px;">
           <div style="color:#555;font-size:10px;
             letter-spacing:1px;margin-bottom:6px;">
             WHY THIS TRADE
           </div>
           ${whyLines}
         </div>`
      : ''}

    <!-- 10. Action buttons -->
    <div style="display:flex;gap:8px;margin-bottom:6px;">
      <a href="${tvUrl}" target="_blank"
        style="flex:1;background:#161b22;border:1px solid #30363d;
          color:#8b949e;border-radius:6px;padding:10px;
          font-size:12px;cursor:pointer;text-align:center;
          text-decoration:none;display:block;">
        📈 Open Chart
      </a>
      <button onclick="copySignal()"
        style="flex:1;background:#161b22;border:1px solid #30363d;
          color:#8b949e;border-radius:6px;padding:10px;
          font-size:12px;cursor:pointer;">
        📋 Copy
      </button>
    </div>

    <button onclick="closeTapPanel()"
      style="width:100%;background:#21262d;
        border:1px solid #30363d;color:#8b949e;
        border-radius:6px;padding:10px;
        font-size:12px;cursor:pointer;">
      Close
    </button>`;

  const overlay = document.getElementById('tap-overlay');
  if (overlay) {
    overlay.style.display = 'block';
    overlay.onclick       = closeTapPanel;
  }

  requestAnimationFrame(function() {
    panel.style.transform  = 'translateX(-50%) translateY(0)';
    panel.style.transition = 'transform 0.3s ease';
  });
}

function closeTapPanel() {
  const panel   = document.getElementById('tap-panel');
  const overlay = document.getElementById('tap-overlay');
  if (panel) {
    panel.style.transform = 'translateX(-50%) translateY(100%)';
    setTimeout(function() { panel.style.display = 'none'; }, 300);
  }
  if (overlay) overlay.style.display = 'none';
}

function copySignal() {
  if (!_currentSig) return;
  const s         = _currentSig;
  const sym       = (s.symbol || '').replace('.NS','');
  const entry     = _getEntryPrice(s);
  const rrData    = _calcRR(entry || 0, s.stop || 0, s.direction || 'LONG');
  const sizing    = _calcPositionSize(entry, s.stop);
  const banned    = _isBanned(s.symbol || sym);

  const text = [
    `TIE TIY Signal`,
    `${sym} — ${s.signal}`,
    `Date: ${s.date || '—'}`,
    `Entry: ₹${fmt(entry || 0)}`,
    `Stop: ₹${fmt(s.stop || 0)}`,
    `Target: ₹${fmt(s.target_price || 0)}`,
    `R:R: ${rrData ? rrData.rr + 'x' : '—'}`,
    sizing ? `Size: ${sizing.shares} shares · Risk ₹${sizing.riskAmt}` : '',
    `Score: ${s.score}/10`,
    `Regime: ${s.regime}`,
    `Grade: ${s.grade}`,
    banned ? '⛔ F&O BAN PERIOD' : '',
    s.direction === 'SHORT'
      ? '↓ SHORT — verify broker supports overnight shorts' : '',
  ].filter(Boolean).join('\n');

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text)
      .then(() => _showCopyFeedback())
      .catch(() => _fallbackCopy(text));
  } else {
    _fallbackCopy(text);
  }
}

function _fallbackCopy(text) {
  const ta         = document.createElement('textarea');
  ta.value         = text;
  ta.style.position = 'fixed';
  ta.style.top     = '0';
  ta.style.left    = '0';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try { document.execCommand('copy'); _showCopyFeedback(); }
  catch(e) {}
  document.body.removeChild(ta);
}

function _showCopyFeedback() {
  document.querySelectorAll('#tap-panel button').forEach(function(btn) {
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
    <div style="background:#161b22;border-radius:6px;
      padding:8px 10px;">
      <div style="color:#555;font-size:10px;
        margin-bottom:2px;letter-spacing:0.5px;">
        ${label}
      </div>
      <div style="color:${color};font-size:15px;font-weight:700;">
        ${value}
      </div>
    </div>`;
}

function _detailRow(label, value, color) {
  return `
    <div style="display:flex;justify-content:space-between;">
      <span style="color:#555;">${label}</span>
      <span style="color:${color || '#c9d1d9'};">${value}</span>
    </div>`;
}

// ── MAIN RENDER ───────────────────────────────────────
function renderSignals(data) {
  const content = document.getElementById('tab-content');
  if (!content) return;

  const today     = _todayIST();
  const scanLog   = data.scanLog;

  // Build active signals from history
  let activeSignals = [];
  if (data.history && data.history.history) {
    activeSignals = data.history.history.filter(s => {
      if (s.result !== 'PENDING') return false;
      if (!s.exit_date) return true;
      return s.exit_date >= today;
    });
  }

  // Current filter
  const currentFilter = _getSavedFilter();

  // Sort all signals: score desc → age asc → signal type
  const SIG_PRIORITY = {
    UP_TRI: 0, DOWN_TRI: 1, BULL_PROXY: 2,
    UP_TRI_SA: 3, DOWN_TRI_SA: 4
  };

  const _sortSignals = arr => [...arr].sort((a, b) => {
    const sd = (b.score || 0) - (a.score || 0);
    if (sd !== 0) return sd;
    const ad = (a.age || 0) - (b.age || 0);
    if (ad !== 0) return ad;
    return (SIG_PRIORITY[a.signal] ?? 99) - (SIG_PRIORITY[b.signal] ?? 99);
  });

  // Today vs older
  const todaySignals = _sortSignals(
    activeSignals.filter(s => s.date === today));
  const olderSignals = _sortSignals(
    activeSignals.filter(s => s.date !== today));
  const allSorted    = [...todaySignals, ...olderSignals];

  // Apply filter
  let displaySignals = allSorted;
  let headerLabel    = `ALL ACTIVE SIGNALS (${allSorted.length})`;
  let topTruncated   = 0;

  if (currentFilter === 'top') {
    const qualifying   = allSorted.filter(s => (s.score || 0) >= TOP_SCORE_MIN);
    topTruncated       = Math.max(0, qualifying.length - TOP_MAX_SIGNALS);
    displaySignals     = qualifying.slice(0, TOP_MAX_SIGNALS);
    headerLabel        = `TOP SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'UP_TRI') {
    displaySignals = allSorted.filter(s => s.signal === 'UP_TRI');
    headerLabel    = `UP TRIANGLE SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'DOWN_TRI') {
    displaySignals = allSorted.filter(s => s.signal === 'DOWN_TRI');
    headerLabel    = `DOWN TRIANGLE SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'BULL_PROXY') {
    displaySignals = allSorted.filter(s => s.signal === 'BULL_PROXY');
    headerLabel    = `BULL PROXY SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'SA') {
    displaySignals = allSorted.filter(s => (s.signal || '').endsWith('_SA'));
    headerLabel    = `2ND ATTEMPT SIGNALS (${displaySignals.length})`;
  } else if (currentFilter === 'age0') {
    displaySignals = allSorted.filter(
      s => s.age === 0 && s.generation !== 0);
    headerLabel    = `NEW TODAY SIGNALS (${displaySignals.length})`;
  }

  // Conflict map from ALL active signals
  const conflictMap = _buildConflictMap(allSorted);

  // Total risk across display signals
  const totalRisk = allSorted.reduce((sum, s) => {
    const e  = parseFloat(s.actual_open || s.scan_price || s.entry || 0);
    const st = parseFloat(s.stop || 0);
    if (!e || !st) return sum;
    const risk   = Math.abs(e - st);
    const shares = risk > 0 ? Math.floor(DEFAULT_CAPITAL / risk) : 0;
    return sum + shares * risk;
  }, 0);

  const riskStr = totalRisk > 0
    ? ` · Total risk ₹${Math.round(totalRisk).toLocaleString('en-IN')}`
    : '';

  // Rejected section from scan log
  const rejected = scanLog ? (scanLog.rejected || []) : [];

  // Empty state
  if (!allSorted.length) {
    const meta    = data.meta || {};
    const scanned = meta.universe_size || 0;
    const regime  = meta.regime || 'Unknown';
    const scanT   = meta.last_scan ? fmtTime(meta.last_scan) : '—';

    content.innerHTML = `
      ${_buildStyles()}
      <div style="padding:14px;">
        ${_buildFilterBar([], currentFilter)}
        <div style="text-align:center;padding:40px 20px;
          color:#555;font-size:13px;">
          <div style="font-size:32px;margin-bottom:12px;">📊</div>
          <div style="color:#8b949e;font-size:15px;
            font-weight:700;margin-bottom:8px;">
            No active signals
          </div>
          <div style="margin-bottom:4px;">
            ${meta.is_trading_day
              ? `Scanned ${scanned} stocks at ${scanT}`
              : 'Market closed today'}
          </div>
          <div style="font-size:11px;color:#444;">
            ${meta.is_trading_day
              ? `${scanned} stocks · 0 signals · ${regime}`
              : 'Next scan: next trading day 8:45 AM IST'}
          </div>
        </div>
        ${rejected.length ? _buildRejectedSection(rejected) : ''}
      </div>`;
    _renderNav('signals');
    return;
  }

  content.innerHTML = `
    ${_buildStyles()}
    <div style="padding-bottom:80px;">

      ${_buildFilterBar(allSorted, currentFilter)}

      <div style="padding:0 14px;">

        <!-- Signal list header -->
        <div style="color:#8b949e;font-size:11px;
          font-weight:700;letter-spacing:1px;
          padding:10px 0 6px;
          border-left:3px solid #ffd700;
          padding-left:8px;
          margin-bottom:10px;">
          ${headerLabel}
          ${currentFilter === 'top'
            ? `<span style="color:#555;font-size:10px;
                font-weight:400;margin-left:6px;">
                Score ${TOP_SCORE_MIN}+ · Best setups only
              </span>`
            : ''}
          <span style="color:#555;font-size:10px;font-weight:400;">
            ${riskStr}
          </span>
        </div>

        <!-- Signal cards -->
        ${displaySignals.map(sig => {
          const isNew  = sig.date === today;
          const dayNum = getDayNumber(sig.date || today);
          return _buildCard(sig, isNew, dayNum, conflictMap);
        }).join('')}

        <!-- Top truncation notice -->
        ${currentFilter === 'top' && topTruncated > 0
          ? `<div style="text-align:center;padding:10px;
               font-size:11px;color:#555;">
               + ${topTruncated} more top signal${topTruncated > 1 ? 's' : ''} ·
               <span style="color:#58a6ff;cursor:pointer;"
                 onclick="applyFilter('all', document.querySelector('[data-filter=all]'))">
                 Switch to All to see everything
               </span>
             </div>`
          : ''}

        <!-- Rejected section -->
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
    const sym    = (s.symbol || s.stock || '').replace('.NS','');
    const signal = s.signal || '';
    const cfg    = _sigCfg(signal);
    const score  = s.score || 0;
    const sc     = _scoreColor(score);
    const reason = 'ALPHA: ' + (
      s.rejection_reason
        ? s.rejection_reason.replace(/_/g,' ')
        : `Score ${score}/10`);

    return `
      <div style="display:flex;justify-content:space-between;
        align-items:center;padding:6px 0;
        border-bottom:1px solid #0c0c1a;font-size:11px;">
        <div>
          <span style="color:#444;font-weight:700;">${sym}</span>
          <span style="color:${cfg.color}44;margin-left:6px;">
            ${cfg.label} ${cfg.arrow}
          </span>
        </div>
        <div style="color:#333;font-size:10px;text-align:right;">
          <span style="color:${sc};">${score}/10</span>
          · ${reason}
        </div>
      </div>`;
  }).join('');

  return `
    <div style="margin-top:16px;">
      <div id="rej-toggle" onclick="toggleRejected()"
        style="color:#444;font-size:11px;font-weight:700;
          border-left:3px solid #333;padding-left:8px;
          cursor:pointer;margin-bottom:6px;">
        ▶ REJECTED TODAY (${rejected.length})
      </div>
      <div id="rej-section" style="display:none;">
        ${rows}
        <div style="font-size:10px;color:#333;padding:6px 0;">
          Shadow mode — all data collected for future analysis.
        </div>
      </div>
    </div>`;
}

function toggleRejected() {
  const sec = document.getElementById('rej-section');
  const tog = document.getElementById('rej-toggle');
  if (!sec) return;
  const open        = sec.style.display !== 'none';
  sec.style.display = open ? 'none' : 'block';
  if (tog) tog.innerHTML = tog.innerHTML
    .replace(open ? '▼' : '▶', open ? '▶' : '▼');
}

function _buildStyles() {
  return `
    <style>
      @keyframes pulse {
        0%   { opacity: 1; }
        50%  { opacity: 0.5; }
        100% { opacity: 1; }
      }
      .signal-card:active { opacity: 0.8; }
    </style>`;
}

// ── PUSH NOTIFICATION ─────────────────────────────────
async function requestNotifications() {
  const statusEl = document.getElementById('notif-status');
  const btn      = document.getElementById('notif-btn');

  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    if (statusEl) statusEl.textContent =
      'Install as PWA from home screen first.';
    return;
  }

  const pin = prompt('Enter 4-digit notification PIN:');
  if (!pin || pin.length !== 4) {
    if (statusEl) statusEl.textContent = 'Invalid PIN.';
    return;
  }

  try {
    if (statusEl) statusEl.textContent = 'Requesting permission…';
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      if (statusEl) statusEl.textContent = 'Permission denied.';
      return;
    }

    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly:      true,
      applicationServerKey: _urlB64ToUint8Array(
        window.VAPID_PUBLIC_KEY ||
        'BD0o5qPcwXsEpSv5KXOSKZRHyyGVoC0bTNbRMcOSX2t-' +
        't5OBf1sHGKJH2y8m6uYnCwa3g_xfzJdmWoEuxR941Rk'),
    });

    const subJson = sub.toJSON();
    if (statusEl) statusEl.innerHTML =
      '<span style="color:#00C851;">✓ Subscribed!</span> ' +
      'Alerts at 8:50 AM IST.';
    if (btn) btn.textContent = '✓ Subscribed';

    try {
      localStorage.setItem('tietiy_push_sub', JSON.stringify({
        endpoint:      subJson.endpoint,
        keys:          subJson.keys,
        subscribed_at: new Date().toISOString().slice(0,10),
      }));
    } catch(e) {}

  } catch(e) {
    if (statusEl) statusEl.textContent = 'Failed: ' + e.message;
  }
}

function _urlB64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64  = (base64String + padding)
    .replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const arr     = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) arr[i] = rawData.charCodeAt(i);
  return arr;
}
