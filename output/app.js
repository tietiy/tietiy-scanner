// ── app.js ───────────────────────────────────────────
// Renders signal cards, tap panel, and all signal UI
// Depends on window.TIETIY being populated by ui.js
//
// Fixes applied:
// FIX 2 — Scan price shows date + time
// FIX 3 — Open Chart uses location.href (iOS safe)
// FIX 4 — Copy uses execCommand fallback (iOS safe)
// ─────────────────────────────────────────────────────

const SIGNAL_CONFIG = {
  UP_TRI:      { color: '#00C851', arrow: '▲',
                 label: 'UP TRI' },
  DOWN_TRI:    { color: '#f85149', arrow: '▼',
                 label: 'DOWN TRI' },
  BULL_PROXY:  { color: '#58a6ff', arrow: '◆',
                 label: 'BULL PROXY' },
  UP_TRI_SA:   { color: '#00C851', arrow: '▲▲',
                 label: 'UP TRI 2nd' },
  DOWN_TRI_SA: { color: '#f85149', arrow: '▼▼',
                 label: 'DOWN TRI 2nd' },
};

function _sigCfg(signal) {
  return SIGNAL_CONFIG[signal] || {
    color: '#8b949e', arrow: '?', label: signal };
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
  return op.results.find(
    r => r.symbol === symbol) || null;
}

function _getStopAlert(symbol) {
  const sa = window.TIETIY.stopAlerts;
  if (!sa || !sa.alerts) return null;
  return sa.alerts.find(
    a => a.symbol === symbol &&
    ['BREACHED','AT','NEAR'].includes(
      a.alert_level)) || null;
}

function _getEodData(symbol) {
  const ed = window.TIETIY.eodPrices;
  if (!ed || !ed.results) return null;
  return ed.results.find(
    r => r.symbol === symbol) || null;
}

function _calcRR(entry, stop, direction) {
  try {
    entry = parseFloat(entry);
    stop  = parseFloat(stop);
    if (!entry || !stop) return null;
    let risk, target, rr;
    if (direction === 'LONG') {
      risk   = entry - stop;
      if (risk <= 0) return null;
      target = entry + 2 * risk;
      rr     = (target - entry) / risk;
    } else {
      risk   = stop - entry;
      if (risk <= 0) return null;
      target = entry - 2 * risk;
      rr     = (entry - target) / risk;
    }
    return { rr: rr.toFixed(1), target: target };
  } catch(e) { return null; }
}

// ── SIGNAL CARD ───────────────────────────────────────
function _buildCard(sig, isNew, dayNum) {
  const sym       = (sig.symbol || '')
                    .replace('.NS','');
  const signal    = sig.signal || '';
  const cfg       = _sigCfg(signal);
  const score     = sig.score || 0;
  const age       = sig.age   || 0;
  const sector    = sig.sector || '';
  const grade     = sig.grade  || 'C';
  const regime    = sig.regime || '';
  const bearBonus = sig.bear_bonus || false;
  const attempt   = sig.attempt_number || 1;
  const direction = sig.direction || 'LONG';

  const openData  = _getOpenPrice(sig.symbol || sym);
  const entry     = openData && openData.actual_open
    ? openData.actual_open
    : (sig.entry_est || sig.entry || 0);
  const stop      = sig.stop || 0;
  const rrData    = _calcRR(entry, stop, direction);
  const rr        = rrData ? rrData.rr : null;
  const scanTime  = sig.scan_time || '';

  const sc = score >= 7 ? '#00C851' :
             score >= 4 ? '#FFD700' : '#f85149';

  let dayBadge = '';
  if (isNew) {
    dayBadge = `<span style="background:#1a3a1a;
      color:#00C851;border-radius:4px;
      padding:1px 6px;font-size:10px;
      font-weight:700;">NEW</span>`;
  } else if (dayNum) {
    const dayColor = dayNum >= 5 ? '#f85149' :
                     dayNum >= 4 ? '#FFD700' : '#8b949e';
    dayBadge = `<span style="color:${dayColor};
      font-size:10px;font-weight:700;">
      Day ${dayNum} of 6
      ${dayNum >= 5 ? '⚠️' : ''}
    </span>`;
  }

  const flameIcon = bearBonus ? ' 🔥' : '';

  const windowClosed = isNew && _entryWindowClosed()
    ? `<div style="background:#1a0a0a;
         border-radius:4px;padding:3px 8px;
         font-size:10px;color:#f85149;
         margin-top:4px;">
         Entry window closed — monitor only
       </div>` : '';

  let gapBanner = '';
  if (openData) {
    if (openData.gap_status === 'SKIP') {
      gapBanner = `<div style="background:#2a0a0a;
        border-radius:4px;padding:4px 8px;
        font-size:10px;color:#f85149;
        margin-top:6px;">
        ❌ ${openData.note}
      </div>`;
    } else if (openData.gap_status === 'WARNING') {
      gapBanner = `<div style="background:#1a1a0a;
        border-radius:4px;padding:4px 8px;
        font-size:10px;color:#FFD700;
        margin-top:6px;">
        ⚠️ ${openData.note}
      </div>`;
    }
  }

  const stopAlert = _getStopAlert(sig.symbol || sym);
  let stopBadge   = '';
  if (stopAlert) {
    const saColor = stopAlert.alert_level === 'BREACHED'
      ? '#f85149' : stopAlert.alert_level === 'AT'
      ? '#f85149' : '#FFD700';
    stopBadge = `<span style="background:${saColor}22;
      color:${saColor};border-radius:4px;
      padding:1px 6px;font-size:10px;
      animation:pulse 1s infinite;">
      ⚠️ ${stopAlert.alert_level}
    </span>`;
  }

  const eodData = _getEodData(sig.symbol || sym);
  let eodBanner = '';
  if (eodData && eodData.stop_hit) {
    eodBanner = `<div style="background:#2a0a0a;
      border-radius:4px;padding:4px 8px;
      font-size:10px;color:#f85149;
      margin-top:6px;">
      🚨 ${eodData.note}
    </div>`;
  } else if (eodData && eodData.stop_probable) {
    eodBanner = `<div style="background:#1a0a0a;
      border-radius:4px;padding:4px 8px;
      font-size:10px;color:#FFD700;
      margin-top:6px;">
      ⚠️ ${eodData.note}
    </div>`;
  }

  let parentContext = '';
  if (attempt === 2 && sig.parent_date) {
    parentContext = `
      <div style="font-size:10px;color:#555;
        margin-top:4px;padding-top:4px;
        border-top:1px solid #21262d;">
        ↳ 1st attempt ${sig.parent_result || ''}
        on ${fmtDate(sig.parent_date)}
      </div>`;
  }

  const borderGlow = dayNum >= 6
    ? `box-shadow:0 0 8px ${cfg.color}44;` : '';

  const sigData = encodeURIComponent(
    JSON.stringify(sig));

  return `
    <div class="signal-card"
      data-signal="${signal}"
      data-age="${age}"
      data-grade="${grade}"
      data-symbol="${sym}"
      onclick="openTapPanel(this)"
      data-sig="${sigData}"
      style="background:#0d1117;
        border:1px solid #21262d;
        border-left:4px solid ${cfg.color};
        border-radius:8px;
        padding:12px 14px;
        margin-bottom:10px;
        cursor:pointer;
        ${borderGlow}
        transition:opacity 0.2s;">

      <div style="display:flex;
        justify-content:space-between;
        align-items:flex-start;
        margin-bottom:6px;">
        <div>
          <span style="font-size:17px;
            font-weight:700;color:#fff;">
            ${sym}
          </span>
          <span style="color:#555;font-size:11px;
            margin-left:6px;">${sector}</span>
          <span style="color:#444;font-size:10px;
            margin-left:4px;">
            Grade ${grade}
          </span>
        </div>
        <div style="display:flex;
          align-items:center;gap:6px;">
          ${stopBadge}
          ${dayBadge}
        </div>
      </div>

      <div style="color:#8b949e;font-size:11px;
        margin-bottom:8px;">
        <span style="color:${cfg.color};
          font-weight:700;">
          ${cfg.label} ${cfg.arrow}
        </span>
        ${flameIcon}
        &nbsp;·&nbsp; Age:${age}
        &nbsp;·&nbsp; ${regime}
        &nbsp;·&nbsp;
        <span style="color:${sc};">
          Score ${score}/10
        </span>
      </div>

      <div style="display:grid;
        grid-template-columns:1fr 1fr 1fr;
        gap:4px;font-size:12px;
        margin-bottom:4px;">
        <div>
          <span style="color:#555;
            font-size:10px;">Entry</span><br>
          <span style="color:#58a6ff;
            font-weight:700;">
            ${entry ? '₹' + fmt(entry) : '—'}
          </span>
        </div>
        <div>
          <span style="color:#555;
            font-size:10px;">Stop</span><br>
          <span style="color:#f85149;
            font-weight:700;">
            ${stop ? '₹' + fmt(stop) : '—'}
          </span>
        </div>
        <div>
          <span style="color:#555;
            font-size:10px;">R:R</span><br>
          <span style="color:${
            rr >= 2 ? '#00C851' :
            rr >= 1.5 ? '#FFD700' : '#f85149'};
            font-weight:700;">
            ${rr ? rr + 'x' : '—'}
          </span>
        </div>
      </div>

      <!-- FIX 2 — Scan price with date + time -->
      <div style="font-size:10px;color:#444;
        margin-bottom:2px;">
        ${openData && openData.actual_open
          ? `Actual open · ${openData.fetch_time || scanTime}`
          : `Scan price · ${fmtDate(sig.date)} · ${scanTime}`}
      </div>

      ${windowClosed}
      ${gapBanner}
      ${eodBanner}
      ${parentContext}
    </div>`;
}

// ── FILTER BAR ────────────────────────────────────────
function _buildFilterBar(signals) {
  const counts = { all: signals.length };
  signals.forEach(s => {
    const sig = s.signal || '';
    if (!counts[sig]) counts[sig] = 0;
    counts[sig]++;
  });

  const filters = [
    { id: 'all',        label: `All (${counts.all})` },
    { id: 'UP_TRI',     label: `UP TRI (${counts.UP_TRI||0})` },
    { id: 'DOWN_TRI',   label: `DOWN (${counts.DOWN_TRI||0})` },
    { id: 'BULL_PROXY', label: `Proxy (${counts.BULL_PROXY||0})` },
    { id: 'SA',         label: `2nd Att` },
    { id: 'age0',       label: `Age 0` },
  ];

  return `
    <div id="filter-bar"
      style="display:flex;flex-wrap:wrap;
        gap:4px;padding:8px 14px;">
      ${filters.map((f, i) => `
        <button
          class="filter-btn ${i===0?'active':''}"
          data-filter="${f.id}"
          onclick="applyFilter('${f.id}', this)"
          style="background:${i===0?'#58a6ff':'#161b22'};
            color:${i===0?'#000':'#8b949e'};
            border:1px solid #30363d;
            border-radius:6px;
            padding:4px 10px;font-size:10px;
            cursor:pointer;">
          ${f.label}
        </button>`).join('')}
    </div>`;
}

function applyFilter(filterId, btn) {
  document.querySelectorAll('.filter-btn')
    .forEach(b => {
      b.style.background = '#161b22';
      b.style.color      = '#8b949e';
    });
  if (btn) {
    btn.style.background = '#58a6ff';
    btn.style.color      = '#000';
  }
  document.querySelectorAll('.signal-card')
    .forEach(card => {
      const sig  = card.dataset.signal || '';
      const age  = card.dataset.age    || '0';
      const show = (
        filterId === 'all' ||
        (filterId === 'UP_TRI'     && sig === 'UP_TRI') ||
        (filterId === 'DOWN_TRI'   && sig === 'DOWN_TRI') ||
        (filterId === 'BULL_PROXY' && sig === 'BULL_PROXY') ||
        (filterId === 'SA'         && sig.endsWith('_SA')) ||
        (filterId === 'age0'       && age === '0')
      );
      card.style.display = show ? '' : 'none';
    });
}

// ── TAP PANEL ─────────────────────────────────────────
let _currentSig = null;

function openTapPanel(el) {
  try {
    _currentSig = JSON.parse(
      decodeURIComponent(el.dataset.sig));
  } catch(e) { return; }

  const sig       = _currentSig;
  const sym       = (sig.symbol || '')
                    .replace('.NS','');
  const signal    = sig.signal || '';
  const cfg       = _sigCfg(signal);
  const score     = sig.score     || 0;
  const direction = sig.direction || 'LONG';
  const attempt   = sig.attempt_number || 1;

  const openData  = _getOpenPrice(sig.symbol || sym);
  const entry     = openData && openData.actual_open
    ? openData.actual_open
    : (sig.entry_est || sig.entry || 0);
  const stop      = sig.stop || 0;
  const rrData    = _calcRR(entry, stop, direction);
  const rr        = rrData ? rrData.rr    : null;
  const target    = rrData ? rrData.target : null;
  const atr       = sig.atr || 0;
  const scanTime  = sig.scan_time || '—';

  const today    = new Date().toISOString().slice(0,10);
  const sigDate  = sig.date || today;
  const dayNum   = getDayNumber(sigDate);
  const exitDate = sig.exit_date || getExitDate(sigDate);
  const isNew    = sigDate === today;

  const stopAlert = _getStopAlert(sig.symbol || sym);

  const whyParts = [];
  if (signal === 'UP_TRI' || signal === 'UP_TRI_SA')
    whyParts.push('Triangle breakout above pivot low');
  if (signal === 'DOWN_TRI' || signal === 'DOWN_TRI_SA')
    whyParts.push('Triangle breakdown below pivot high');
  if (signal === 'BULL_PROXY')
    whyParts.push('Support zone rejection with momentum');
  if (attempt === 2)
    whyParts.push('Second attempt — level proven twice');
  if (sig.bear_bonus)
    whyParts.push('Bear regime = highest UP_TRI conviction');
  if (sig.vol_confirm)
    whyParts.push('High volume confirmation');
  if (sig.rs_q === 'Strong')
    whyParts.push('Stock outperforming Nifty');
  if (sig.sec_mom === 'Leading')
    whyParts.push('Sector showing leadership');

  const whyText = whyParts.join(' · ') || 'Signal criteria met';

  const riskPerShare = entry && stop
    ? Math.abs(entry - stop).toFixed(2) : '—';

  // FIX 3 — TradingView URL stored in data attribute
  // Use location.href instead of window.open (iOS safe)
  const tvSym = sym.replace('.NS','');
  const tvUrl = `https://www.tradingview.com/chart/?symbol=NSE%3A${tvSym}`;

  const panel = document.getElementById('tap-panel');
  if (!panel) return;

    panel.style.display   = 'block';
  panel.style.maxWidth  = window.innerWidth >= 1024
    ? '960px' : window.innerWidth >= 768
    ? '860px' : '600px';
  panel.style.transform = 'translateX(-50%) translateY(100%)';


  panel.innerHTML = `
    <div style="width:40px;height:4px;
      background:#30363d;border-radius:2px;
      margin:0 auto 14px;"></div>

    <div style="display:flex;
      justify-content:space-between;
      align-items:center;margin-bottom:14px;">
      <div>
        <span style="font-size:22px;
          font-weight:700;color:#fff;">${sym}</span>
        <span style="background:${cfg.color}22;
          color:${cfg.color};border-radius:4px;
          padding:2px 7px;font-size:10px;
          margin-left:8px;font-weight:700;">
          ${cfg.label} ${cfg.arrow}
        </span>
        ${sig.bear_bonus
          ? '<span style="font-size:14px;"> 🔥</span>'
          : ''}
      </div>
      <button onclick="closeTapPanel()"
        style="background:none;border:none;
          color:#555;font-size:22px;
          cursor:pointer;">✕</button>
    </div>

    ${stopAlert ? `
      <div style="background:#2a0a0a;
        border:1px solid #f8514966;
        border-radius:6px;padding:8px 10px;
        margin-bottom:10px;font-size:11px;
        color:#f85149;">
        ⚠️ ${stopAlert.note}
      </div>` : ''}

    <div style="display:grid;
      grid-template-columns:1fr 1fr;
      gap:8px;margin-bottom:10px;">
      ${_panelStat('ENTRY',
        entry ? '₹' + fmt(entry) : '—', '#58a6ff')}
      ${_panelStat('STOP',
        stop  ? '₹' + fmt(stop)  : '—', '#f85149')}
      ${_panelStat('TARGET',
        target ? '₹' + fmt(target) : 'Day 6 open',
        '#00C851')}
      ${_panelStat('R:R',
        rr ? rr + 'x' : '—',
        rr >= 2 ? '#00C851' :
        rr >= 1.5 ? '#FFD700' : '#f85149')}
    </div>

    <div style="background:#161b22;
      border-radius:8px;padding:10px 12px;
      margin-bottom:10px;font-size:11px;
      line-height:1.8;">
      ${_detailRow('Risk/share', '₹' + riskPerShare)}
      ${_detailRow('ATR', atr ? '₹' + fmt(atr) : '—')}
      ${_detailRow('Signal age', sig.age + ' days')}
      ${_detailRow('Score', score + '/10')}
      ${_detailRow('Regime', sig.regime || '—')}
      ${_detailRow('Volume', sig.vol_q  || '—')}
      ${_detailRow('RS vs Nifty', sig.rs_q   || '—')}
      ${_detailRow('Sector mom', sig.sec_mom || '—')}
      ${_detailRow('Grade', sig.grade || '—')}
      ${_detailRow('Scan price',
        (sig.entry_est ? '₹' + fmt(sig.entry_est) : '—') +
        ' · ' + fmtDate(sig.date) +
        ' · ' + scanTime)}
    </div>

    <div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:8px;padding:10px 12px;
      margin-bottom:10px;font-size:11px;">
      <div style="color:#555;margin-bottom:4px;">
        TRADE WINDOW
      </div>
      <div style="color:#c9d1d9;font-weight:700;">
        ${isNew
          ? '🟢 New signal — enter at 9:15 AM open'
          : `Day ${dayNum} of 6`}
      </div>
      <div style="color:#555;margin-top:2px;">
        Exit at open on ${fmtDate(exitDate)}
        ${dayNum >= 5
          ? '<span style="color:#f85149;">— Exit tomorrow!</span>'
          : ''}
        ${dayNum >= 6
          ? '<span style="color:#f85149;">— EXIT TODAY</span>'
          : ''}
      </div>
      <div style="color:#444;font-size:10px;margin-top:4px;">
        Exit rule: Sell at open of Day 6 regardless of P&L
      </div>
    </div>

    ${attempt === 2 ? `
      <div style="background:#0d1a0d;
        border:1px solid #00C85133;
        border-radius:8px;padding:10px 12px;
        margin-bottom:10px;font-size:11px;">
        <div style="color:#00C851;font-weight:700;
          margin-bottom:4px;">2nd Attempt Signal</div>
        <div style="color:#8b949e;">
          First attempt: ${sig.parent_signal || ''} on
          ${fmtDate(sig.parent_date)} —
          ${sig.parent_result || 'prior'}<br>
          Same level proven twice.
          Lower score threshold applied.
        </div>
      </div>` : ''}

    <div style="background:#0a0d1a;
      border:1px solid #21262d;
      border-radius:8px;padding:10px 12px;
      margin-bottom:14px;font-size:11px;">
      <div style="color:#8b949e;margin-bottom:4px;
        font-size:10px;letter-spacing:1px;">
        WHY THIS TRADE
      </div>
      <div style="color:#c9d1d9;line-height:1.6;">
        ${whyText}
      </div>
    </div>

    <!-- FIX 3 — Open Chart as anchor tag (iOS safe) -->
    <div style="display:flex;gap:8px;margin-bottom:8px;">
      <a href="${tvUrl}" target="_blank"
        style="flex:1;background:#161b22;
          border:1px solid #30363d;
          color:#8b949e;border-radius:6px;
          padding:10px;font-size:12px;
          cursor:pointer;text-align:center;
          text-decoration:none;display:block;">
        📈 Open Chart
      </a>
      <button onclick="copySignal()"
        style="flex:1;background:#161b22;
          border:1px solid #30363d;
          color:#8b949e;border-radius:6px;
          padding:10px;font-size:12px;
          cursor:pointer;">
        📋 Copy
      </button>
    </div>

    <button onclick="closeTapPanel()"
      style="width:100%;background:#21262d;
        border:1px solid #30363d;
        color:#8b949e;border-radius:6px;
        padding:10px;font-size:12px;
        cursor:pointer;">
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

  try {
    sessionStorage.setItem(
      'tietiy_last_sig', JSON.stringify(sig));
  } catch(e) {}
}

function closeTapPanel() {
  const panel   = document.getElementById('tap-panel');
  const overlay = document.getElementById('tap-overlay');
  if (panel) {
    panel.style.transform = 'translateX(-50%) translateY(100%)';
    setTimeout(function() {
      panel.style.display = 'none';
    }, 300);
  }
  if (overlay) overlay.style.display = 'none';
}

// FIX 4 — Copy with execCommand fallback (iOS safe)
function copySignal() {
  if (!_currentSig) return;
  const s        = _currentSig;
  const sym      = (s.symbol || '').replace('.NS','');
  const openData = _getOpenPrice(s.symbol || sym);
  const entry    = openData && openData.actual_open
    ? openData.actual_open
    : (s.entry_est || s.entry || 0);
  const rrData   = _calcRR(entry, s.stop,
    s.direction || 'LONG');

  const text = [
    `TIE TIY Signal`,
    `${sym} — ${s.signal}`,
    `Date: ${s.date || '—'}`,
    `Entry: ₹${fmt(entry)}`,
    `Stop: ₹${fmt(s.stop)}`,
    `R:R: ${rrData ? rrData.rr + 'x' : '—'}`,
    `Score: ${s.score}/10`,
    `Regime: ${s.regime}`,
    `Grade: ${s.grade}`,
  ].join('\n');

  // Try modern clipboard API first
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text)
      .then(function() {
        _showCopyFeedback();
      })
      .catch(function() {
        _fallbackCopy(text);
      });
  } else {
    _fallbackCopy(text);
  }
}

// iOS Safari fallback copy method
function _fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value          = text;
  ta.style.position = 'fixed';
  ta.style.top      = '0';
  ta.style.left     = '0';
  ta.style.opacity  = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  try {
    document.execCommand('copy');
    _showCopyFeedback();
  } catch(e) {
    console.log('Copy failed:', e);
  }
  document.body.removeChild(ta);
}

function _showCopyFeedback() {
  // Find copy button and flash it
  const btns = document.querySelectorAll(
    '#tap-panel button');
  btns.forEach(function(btn) {
    if (btn.textContent.includes('Copy')) {
      const orig = btn.innerHTML;
      btn.innerHTML = '✅ Copied';
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
        margin-bottom:2px;">${label}</div>
      <div style="color:${color};font-size:15px;
        font-weight:700;">${value}</div>
    </div>`;
}

function _detailRow(label, value) {
  return `
    <div style="display:flex;
      justify-content:space-between;">
      <span style="color:#555;">${label}</span>
      <span style="color:#c9d1d9;">${value}</span>
    </div>`;
}

// ── MAIN RENDER ───────────────────────────────────────
function renderSignals(data) {
  const content = document.getElementById('tab-content');
  if (!content) return;

  const scanLog = data.scanLog;
  const today   = new Date().toISOString().slice(0,10);

  let activeSignals = [];
  if (data.history && data.history.history) {
    activeSignals = data.history.history.filter(s => {
      if (s.result !== 'PENDING') return false;
      if (!s.exit_date) return true;
      return s.exit_date >= today;
    });
  }

  const todaySignals = activeSignals.filter(
    s => s.date === today);
  const olderSignals = activeSignals.filter(
    s => s.date !== today);

  const sortByScore = arr => [...arr].sort(
    (a, b) => (b.score || 0) - (a.score || 0));

  const allSignals = [
    ...sortByScore(todaySignals),
    ...sortByScore(olderSignals),
  ];

  const rejected = scanLog
    ? (scanLog.rejected || []) : [];

  if (!allSignals.length) {
    const meta    = data.meta || {};
    const scanned = meta.universe_size || 0;
    const regime  = meta.regime || 'Unknown';
    const scanT   = meta.last_scan
      ? fmtTime(meta.last_scan) : '—';

    content.innerHTML = `
      <div style="padding:14px;">
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
          <div style="font-size:11px;color:#444;">
            ${meta.is_trading_day
              ? `${scanned} stocks checked · 0 signals met criteria · ${regime} regime`
              : `Next scan: next trading day at 8:45 AM IST`}
          </div>
        </div>
        ${rejected.length
          ? _buildRejectedSection(rejected) : ''}
      </div>
      ${_buildStyles()}`;
    _renderNav('signals');
    return;
  }

  content.innerHTML = `
    ${_buildStyles()}
    <div style="padding:0 0 14px;">

      ${_buildFilterBar(allSignals)}

      <div style="padding:0 14px;">
        <div style="color:#8b949e;font-size:11px;
          font-weight:700;letter-spacing:1px;
          padding:8px 0 6px;
          border-left:3px solid #ffd700;
          padding-left:8px;margin-bottom:10px;">
          ACTIVE SIGNALS
          <span style="color:#555;font-weight:400;">
            (${allSignals.length})
          </span>
        </div>

        ${allSignals.map(sig => {
          const isNew  = sig.date === today;
          const dayNum = getDayNumber(sig.date || today);
          return _buildCard(sig, isNew, dayNum);
        }).join('')}
      </div>

      ${rejected.length
        ? `<div style="padding:0 14px;">
             ${_buildRejectedSection(rejected)}
           </div>`
        : ''}
    </div>`;

  _renderNav('signals');

  try {
    sessionStorage.removeItem('tietiy_last_sig');
  } catch(e) {}
}

// ── REJECTED SECTION ──────────────────────────────────
function _buildRejectedSection(rejected) {
  if (!rejected.length) return '';

  const rows = rejected.slice(0, 10).map(s => {
    const sym    = (s.symbol || s.stock || '')
                   .replace('.NS','');
    const signal = s.signal || '';
    const cfg    = _sigCfg(signal);
    const score  = s.score || 0;
    const age    = s.age   || 0;
    const reason = s.rejection_reason
      || (age > 0 && signal === 'DOWN_TRI'
          ? 'DOWN_TRI age>0 — edge gone'
          : `Score ${score}/10`);
    return `
      <div style="display:flex;
        justify-content:space-between;
        align-items:center;
        padding:6px 0;
        border-bottom:1px solid #0c0c1a;
        font-size:11px;">
        <div>
          <span style="color:#444;
            font-weight:700;">${sym}</span>
          <span style="color:${cfg.color}55;
            margin-left:6px;">
            ${cfg.label} ${cfg.arrow}
          </span>
        </div>
        <div style="color:#333;
          font-size:10px;text-align:right;">
          ${score}/10 · ${reason}
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
          padding-left:8px;
          cursor:pointer;margin-bottom:6px;">
        ▶ REJECTED TODAY (${rejected.length})
      </div>
      <div id="rej-section" style="display:none;">
        ${rows}
        <div style="font-size:10px;color:#333;
          padding:6px 0;">
          Detected but did not meet criteria.
          Shadow mode active — all data collected
          for future filter validation.
        </div>
      </div>
    </div>`;
}

function toggleRejected() {
  const sec = document.getElementById('rej-section');
  const tog = document.getElementById('rej-toggle');
  if (!sec) return;
  const open = sec.style.display !== 'none';
  sec.style.display = open ? 'none' : 'block';
  if (tog) tog.innerHTML = tog.innerHTML
    .replace(open ? '▼' : '▶',
             open ? '▶' : '▼');
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
