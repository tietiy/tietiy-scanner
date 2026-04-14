// ── ui.js ────────────────────────────────────────────
// Master controller for TIE TIY Scanner frontend
// Loads first — all other JS files depend on this
//
// V1 FIXES APPLIED:
// - L5  : _seedDefaultTook()
// - L7  : switchTab() closes signal detail modal
// - R3  : Offline banner
// - R8  : _isSA() + _renderSABadge() global helpers
//
// V1.1 FIXES:
// - H9  : Stale warning suppressed before 9 AM IST
// - M8  : Market regime note in status bar
// - S1  : _enforceTabletWidth() — JS-based width
//         enforcement for iPad PWA standalone mode.
// - S4  : Tab bar sizing via _enforceTabletWidth
// - PWA_LAYOUT: Right sidebar on iPad >900px —
//   market context card, dynamic resize.
// - NEWS_PANEL: Left panel iPad >1000px —
//   hybrid news (active+new today), compact cards,
//   tap-to-open drawer, mobile collapsible section.
//   Source: Google News RSS via rss2json proxy.
//   Last 48h only. Session cache 30 min.
//
// PRIOR FIXES RETAINED:
// - Default filter is 'top'
// - P1: LTP updated_at in status bar
// - V1: Open validate time in status bar
// ─────────────────────────────────────────────────────

const VAPID_PUBLIC_KEY =
  'BD0o5qPcwXsEpSv5KXOSKZRHyyGVoC0bTNbRMcOSX2t-' +
  't5OBf1sHGKJH2y8m6uYnCwa3g_xfzJdmWoEuxR941Rk';

const PUSH_PIN_LENGTH = 4;
const BASE_URL        = '/tietiy-scanner/';

const BACKTEST_WR = {
  UP_TRI:      87,
  DOWN_TRI:    87,
  UP_TRI_SA:   87,
  DOWN_TRI_SA: 87,
  BULL_PROXY:  67,
  OVERALL:     87,
};

window.TIETIY = {
  meta:         null,
  scanLog:      null,
  miniLog:      null,
  history:      null,
  openPrices:   null,
  eodPrices:    null,
  stopAlerts:   null,
  ltpPrices:    null,
  bannedStocks: [],
  holidays:     [],
  loaded:       false,
  activeTab:    'signals',
  lastFetch:    null,
  newsCache:    {},
};

// ── UTILITY ───────────────────────────────────────────
function fmt(n) {
  return parseFloat(n).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function fmtDate(str) {
  if (!str) return '—';
  try {
    const d = new Date(str + 'T00:00:00');
    return d.toLocaleDateString('en-IN', {
      day:   '2-digit',
      month: 'short',
    });
  } catch(e) { return str; }
}

function fmtTime(utcStr) {
  if (!utcStr) return '—';
  try {
    const d = new Date(utcStr);
    return d.toLocaleTimeString('en-IN', {
      hour:     '2-digit',
      minute:   '2-digit',
      timeZone: 'Asia/Kolkata',
    }) + ' IST';
  } catch(e) { return utcStr; }
}

function _todayIST() {
  return new Date().toLocaleDateString(
    'en-CA', { timeZone: 'Asia/Kolkata' });
}

function _bust(url) {
  return url + '?t=' + Date.now();
}

function _safeGet(url) {
  return fetch(_bust(url))
    .then(function(r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })
    .catch(function() { return null; });
}

// ── H9: CURRENT IST HOUR ──────────────────────────────
function _istHour() {
  try {
    return parseInt(
      new Date().toLocaleString('en-IN', {
        hour:     'numeric',
        hour12:   false,
        timeZone: 'Asia/Kolkata',
      }), 10);
  } catch(e) {
    return (new Date().getUTCHours()
      + 5 + Math.floor((new Date().getUTCMinutes()
      + 30) / 60)) % 24;
  }
}

function _isTodayTradingDay() {
  const holidays = window.TIETIY.holidays || [];
  const today    = _todayIST();
  const dow = new Date(today + 'T00:00:00').getDay();
  if (dow === 0 || dow === 6) return false;
  return !holidays.includes(today);
}

// ── R8: SA GLOBAL HELPERS ─────────────────────────────
window._isSA = function(signalType) {
  return (signalType || '')
    .toUpperCase().endsWith('_SA');
};

window._renderSABadge = function() {
  return `<span style="background:#1a1a0a;
    color:#ffd700;font-size:9px;font-weight:700;
    border:1px solid #ffd70033;border-radius:3px;
    padding:1px 5px;white-space:nowrap;">2ND</span>`;
};

// ── L5: SEED DEFAULT TOOK ─────────────────────────────
function _seedDefaultTook() {
  const hist = window.TIETIY.history;
  if (!hist || !hist.history) return;

  let store;
  try {
    store = JSON.parse(
      localStorage.getItem('tietiy_ud') || '{}');
  } catch(e) { store = {}; }

  let changed = false;

  hist.history.forEach(function(s) {
    if (s.layer      !== 'MINI') return;
    if (s.action     !== 'TOOK') return;
    if (s.generation === 0)      return;

    const sym    = (s.symbol || '').replace('.NS', '');
    const cardId = (s.id ||
      (sym + '-' + (s.signal || '') + '-'
       + (s.date || '')))
      .replace(/[^a-zA-Z0-9-]/g, '-');

    if (!store[cardId]) {
      store[cardId] = 'TOOK';
      changed = true;
    }
  });

  if (changed) {
    try {
      localStorage.setItem(
        'tietiy_ud', JSON.stringify(store));
    } catch(e) {}
  }
}

// ── FETCH ALL DATA ────────────────────────────────────
async function _fetchAll() {
  const [
    meta, scanLog, miniLog,
    history, openPrices, eodPrices,
    stopAlerts, holidays, bannedStocks,
    ltpPrices,
  ] = await Promise.all([
    _safeGet('meta.json'),
    _safeGet('scan_log.json'),
    _safeGet('mini_log.json'),
    _safeGet('signal_history.json'),
    _safeGet('open_prices.json'),
    _safeGet('eod_prices.json'),
    _safeGet('stop_alerts.json'),
    _safeGet('nse_holidays.json'),
    _safeGet('banned_stocks.json'),
    _safeGet('ltp_prices.json'),
  ]);

  window.TIETIY.meta         = meta;
  window.TIETIY.scanLog      = scanLog;
  window.TIETIY.miniLog      = miniLog;
  window.TIETIY.history      = history;
  window.TIETIY.openPrices   = openPrices;
  window.TIETIY.eodPrices    = eodPrices;
  window.TIETIY.stopAlerts   = stopAlerts;
  window.TIETIY.ltpPrices    = ltpPrices;
  window.TIETIY.holidays     = holidays
    ? holidays.holidays || [] : [];
  window.TIETIY.bannedStocks = bannedStocks
    ? bannedStocks.banned || [] : [];
  window.TIETIY.loaded       = true;
  window.TIETIY.lastFetch    = Date.now();

  return !!meta;
}

// ── APP VERSION CHECK ─────────────────────────────────
function _checkAppVersion(meta) {
  if (!meta) return;
  const stored  = localStorage.getItem('tietiy_app_v');
  const current = meta.app_version || '2.0';
  if (stored && stored !== current) {
    localStorage.setItem('tietiy_app_v', current);
    location.reload(true);
    return;
  }
  localStorage.setItem('tietiy_app_v', current);
}

// ── NEXT TRADING DAY ──────────────────────────────────
function _getNextTradingDay() {
  const holidays = window.TIETIY.holidays || [];
  const cur      = new Date();
  cur.setDate(cur.getDate() + 1);
  for (let i = 0; i < 30; i++) {
    const dayOfWeek = cur.getDay();
    const dateStr   = cur.toLocaleDateString(
      'en-CA', { timeZone: 'Asia/Kolkata' });
    if (dayOfWeek !== 0 && dayOfWeek !== 6 &&
        !holidays.includes(dateStr)) {
      return cur.toLocaleDateString('en-IN', {
        weekday:  'short',
        day:      'numeric',
        month:    'short',
        timeZone: 'Asia/Kolkata',
      });
    }
    cur.setDate(cur.getDate() + 1);
  }
  return 'next trading day';
}

// ── TODAY SIGNAL COUNT ────────────────────────────────
function _countTodaySignals() {
  const today = _todayIST();
  const hist  = window.TIETIY.history;
  if (!hist || !hist.history) return 0;
  return hist.history.filter(
    s => s.date === today
      && s.result === 'PENDING'
  ).length;
}

// ── SIDEBAR HELPERS ───────────────────────────────────

function _countTodayExits() {
  const today = _todayIST();
  const hist  = window.TIETIY.history;
  if (!hist || !hist.history) return 0;
  const done = ['TARGET_HIT','STOP_HIT',
    'DAY6_WIN','DAY6_LOSS','DAY6_FLAT'];
  return hist.history.filter(function(s) {
    return s.exit_date === today
      && s.result    === 'PENDING'
      && s.action    === 'TOOK'
      && done.indexOf(s.outcome || '') === -1;
  }).length;
}

function _countResolvedGen1() {
  const hist = window.TIETIY.history;
  if (!hist || !hist.history) return 0;
  const done = ['TARGET_HIT','STOP_HIT',
    'DAY6_WIN','DAY6_LOSS','DAY6_FLAT'];
  return hist.history.filter(function(s) {
    return s.action === 'TOOK'
      && (s.generation || 0) >= 1
      && done.indexOf(s.outcome || '') !== -1;
  }).length;
}

function _sidebarLayout() {
  const vw = window.innerWidth
    || document.documentElement.clientWidth
    || 375;

  if (vw < 900) return { show: false };

  const bodyWidth     = vw >= 1024 ? 720 : 680;
  const bodyRightEdge = (vw + bodyWidth) / 2;
  const available     = vw - bodyRightEdge - 8;

  if (available < 120) return { show: false };

  const sidebarWidth = Math.min(260, available - 8);
  const sidebarLeft  = bodyRightEdge + 8;
  const compact      = sidebarWidth < 180;

  return {
    show:    true,
    left:    Math.round(sidebarLeft),
    width:   Math.round(sidebarWidth),
    compact: compact,
  };
}

// ── RENDER SIDEBAR ────────────────────────────────────
function _renderSidebar() {
  const el = document.getElementById('sidebar');
  if (!el) return;

  const layout = _sidebarLayout();

  if (!layout.show) {
    el.style.display = 'none';
    return;
  }

  el.style.display   = 'block';
  el.style.left      = layout.left + 'px';
  el.style.width     = layout.width + 'px';
  el.style.top       = '0';
  el.style.height    = '100vh';
  el.style.overflowY = 'auto';
  el.style.paddingBottom = '80px';

  const meta    = window.TIETIY.meta;
  const compact = layout.compact;
  const p       = compact ? '10px 8px' : '12px 10px';
  const fs      = compact ? '10px' : '11px';
  const fsL     = compact ? '13px' : '15px';
  const gap     = compact ? '8px' : '10px';

  if (!meta) { el.innerHTML = ''; return; }

  const regime = meta.regime || '—';
  const active = meta.active_signals_count || 0;
  const rc     = regime === 'Bear'  ? '#ff4444'
               : regime === 'Bull'  ? '#00C851'
               : '#FFD700';

  const exitsToday = _countTodayExits();
  const newToday   = _countTodaySignals();
  const resolved   = _countResolvedGen1();
  const phasePct   = Math.min(
    100, Math.round(resolved / 30 * 100));
  const banned     = window.TIETIY.bannedStocks || [];
  const nextDay    = _getNextTradingDay();
  const isTrading  = meta.is_trading_day;

  const card = (content) =>
    `<div style="background:#0d1117;
      border:1px solid #21262d;
      border-radius:10px;
      padding:${p};
      margin-bottom:${gap};">
      ${content}
    </div>`;

  const label = (txt) =>
    `<div style="color:#444;font-size:9px;
      font-weight:700;letter-spacing:1px;
      text-transform:uppercase;
      margin-bottom:6px;">${txt}</div>`;

  const row = (icon, lbl, val, valColor) =>
    `<div style="display:flex;
      justify-content:space-between;
      align-items:center;
      margin-bottom:5px;
      font-size:${fs};">
      <span style="color:#555;">${icon} ${lbl}</span>
      <span style="color:${valColor || '#c9d1d9'};
        font-weight:600;">${val}</span>
    </div>`;

  let html = '';

  html += card(`
    ${label('Market')}
    <div style="display:flex;align-items:center;
      justify-content:space-between;">
      <span style="background:${rc};color:#000;
        border-radius:5px;padding:2px 8px;
        font-size:${fsL};font-weight:700;">
        ${regime}
      </span>
      ${regime === 'Bear'
        ? '<span style="font-size:16px;">🔥</span>'
        : ''}
    </div>
  `);

  html += card(`
    ${label('Today')}
    ${row('📊', 'Active', active, '#c9d1d9')}
    ${row('🚪', 'Exits',
      exitsToday > 0
        ? `<span style="color:#f85149;
            font-weight:700;">${exitsToday}</span>`
        : '0',
      exitsToday > 0 ? '#f85149' : '#555')}
    ${row('🔔', 'New',
      newToday > 0
        ? `<span style="color:#00C851;">
            ${newToday}</span>`
        : '0',
      newToday > 0 ? '#00C851' : '#555')}
    ${exitsToday > 0
      ? `<div style="color:#f85149;font-size:9px;
           margin-top:6px;padding:4px 6px;
           background:#2a0a0a;border-radius:5px;
           text-align:center;">
           Sell at 9:15 AM
         </div>`
      : ''}
  `);

  html += card(`
    ${label('Next Scan')}
    <div style="color:#8b949e;font-size:${fs};
      line-height:1.6;">
      ${isTrading
        ? `<span style="color:#00C851;">● Today
           </span><br>
           <span style="color:#555;">
             8:45 AM IST
           </span>`
        : `<span style="color:#c9d1d9;">
             ${nextDay}
           </span><br>
           <span style="color:#555;">
             8:45 AM IST
           </span>`}
    </div>
  `);

  const phaseBar = Array.from({length: 10},
    (_, i) => i < Math.round(phasePct / 10)
      ? `<span style="color:#ffd700;">█</span>`
      : `<span style="color:#21262d;">█</span>`
  ).join('');

  html += card(`
    ${label('Phase 1')}
    <div style="font-size:${fsL};color:#ffd700;
      font-weight:700;margin-bottom:4px;">
      ${resolved} / 30
    </div>
    <div style="font-size:9px;letter-spacing:1px;
      margin-bottom:4px;">${phaseBar}</div>
    <div style="color:#444;font-size:9px;">
      ${30 - resolved > 0
        ? `${30 - resolved} more needed`
        : '✅ Unlocked'}
    </div>
  `);

  if (banned.length > 0) {
    const banNames = banned.slice(0, 4)
      .map(b => b.replace('.NS','')).join(', ');
    const more = banned.length > 4
      ? ` +${banned.length - 4}` : '';
    html += card(`
      ${label('F&O Ban')}
      <div style="color:#f85149;font-size:${fs};
        line-height:1.6;">
        ⚠️ ${banNames}${more}
      </div>
    `);
  }

  el.innerHTML = html;
}

// ── NEWS PANEL ────────────────────────────────────────
// Left panel iPad >1000px — hybrid news feed
// Stocks: active positions + new today (max 10)
// Source: Google News RSS via rss2json.com proxy
// Last 48h only. Session cache 30 min per stock.
// Mobile: collapsible section above Signals tab.

function _newsLayout() {
  const vw = window.innerWidth
    || document.documentElement.clientWidth
    || 375;

  if (vw < 1000) return { show: false };

  // On vw >= 1024, body = 720px centered
  const bodyWidth    = 720;
  const bodyLeftEdge = (vw - bodyWidth) / 2;
  const available    = bodyLeftEdge - 16;

  if (available < 100) return { show: false };

  return {
    show:  true,
    left:  8,
    width: Math.round(Math.min(200, available - 8)),
  };
}

function _getNewsStocks() {
  const hist = window.TIETIY.history;
  if (!hist || !hist.history) return [];

  const today = _todayIST();
  const done  = ['TARGET_HIT','STOP_HIT',
    'DAY6_WIN','DAY6_LOSS','DAY6_FLAT'];
  const seen  = new Set();
  const syms  = [];

  // Active positions first
  hist.history.forEach(function(s) {
    if (s.action !== 'TOOK') return;
    if ((s.generation || 0) < 1) return;
    if (done.indexOf(s.outcome || '') !== -1) return;
    const sym = (s.symbol || '').replace('.NS','');
    if (!sym || seen.has(sym)) return;
    seen.add(sym);
    syms.push(sym);
  });

  // New today signals not already in list
  hist.history.forEach(function(s) {
    if (s.date !== today) return;
    if ((s.generation || 0) < 1) return;
    const sym = (s.symbol || '').replace('.NS','');
    if (!sym || seen.has(sym)) return;
    seen.add(sym);
    syms.push(sym);
  });

  return syms.slice(0, 10);
}

function _timeAgo(pubDate) {
  try {
    const diff  = Date.now() -
      new Date(pubDate).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1)  return 'just now';
    if (hours < 24) return hours + 'h ago';
    return Math.floor(hours / 24) + 'd ago';
  } catch(e) { return ''; }
}

async function _fetchStockNews(symbol) {
  // Check session cache — valid 30 min
  const cache = window.TIETIY.newsCache[symbol];
  if (cache &&
      (Date.now() - cache.fetchedAt) < 1800000) {
    return cache.items;
  }

  try {
    const query = encodeURIComponent(
      symbol + ' NSE stock');
    const rssUrl = encodeURIComponent(
      'https://news.google.com/rss/search?q='
      + query
      + '&hl=en-IN&gl=IN&ceid=IN:en');
       
    const url =
      'https://api.rss2json.com/v1/api.json'
      + '?rss_url=' + rssUrl;


    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status);

    const data  = await r.json();
    const items = (data.items || [])
      .filter(function(item) {
        // Last 30 days only
        try {
          const age = Date.now() -
            new Date(item.pubDate).getTime();
          return age < 2592000000;
        } catch(e) { return false; }

      })
      .slice(0, 2);

    window.TIETIY.newsCache[symbol] = {
      items:     items,
      fetchedAt: Date.now(),
    };
    return items;

  } catch(e) {
    // Cache empty to avoid repeated failures
    window.TIETIY.newsCache[symbol] = {
      items:     [],
      fetchedAt: Date.now(),
    };
    return [];
  }
}

async function _fetchNewsForStocks(symbols) {
  const results = [];
  for (const sym of symbols) {
    const items = await _fetchStockNews(sym);
    if (items.length > 0) {
      results.push({ symbol: sym, item: items[0] });
    }
  }
  return results;
}

function _openNewsCard(title, source, link, ago) {
  const overlay =
    document.getElementById('news-overlay');
  const drawer  =
    document.getElementById('news-drawer');
  if (!overlay || !drawer) return;

  drawer.innerHTML = `
    <div style="display:flex;
      justify-content:space-between;
      align-items:flex-start;
      margin-bottom:14px;">
      <div style="color:#8b949e;font-size:11px;">
        📰 ${source || 'News'} · ${ago || ''}
      </div>
      <button onclick="_closeNewsCard()"
        style="background:none;border:none;
          color:#555;font-size:20px;cursor:pointer;
          padding:0;line-height:1;
          -webkit-tap-highlight-color:transparent;">
        ✕
      </button>
    </div>
    <div style="color:#c9d1d9;font-size:14px;
      font-weight:600;line-height:1.6;
      margin-bottom:20px;">
      ${title || ''}
    </div>
    ${link
      ? `<a href="${link}"
           target="_blank"
           rel="noopener noreferrer"
           style="display:block;
             background:#ffd700;color:#000;
             border-radius:8px;
             padding:12px 14px;
             font-size:13px;font-weight:700;
             text-align:center;
             text-decoration:none;">
           Read Full Article →
         </a>`
      : ''}`;

  overlay.style.display = 'block';
  drawer.style.display  = 'block';
}

window._closeNewsCard = function() {
  const overlay =
    document.getElementById('news-overlay');
  const drawer  =
    document.getElementById('news-drawer');
  if (overlay) overlay.style.display = 'none';
  if (drawer)  drawer.style.display  = 'none';
};

function _newsCardHtml(sym, item, compact) {
  const title  = (item.title || '').trim();
  const source = (item.author || '')
    .replace(/.*on /i, '').trim()
    || (item.source && item.source.name) || '';
  const link   = item.link || '';
  const ago    = _timeAgo(item.pubDate);
  const maxLen = compact ? 55 : 80;
  const short  = title.length > maxLen
    ? title.slice(0, maxLen) + '…' : title;
  const escaped = short
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  // Safely encode for onclick attribute
  const safeTitle  = JSON.stringify(title);
  const safeSource = JSON.stringify(source);
  const safeLink   = JSON.stringify(link);

  return `
    <div onclick="_openNewsCard(
        ${safeTitle},${safeSource},
        ${safeLink},'${ago}')"
      style="background:#0d1117;
        border:1px solid #21262d;
        border-radius:8px;
        padding:8px;margin:0 6px 8px;
        cursor:pointer;
        -webkit-tap-highlight-color:transparent;">
      <div style="color:#ffd700;font-size:10px;
        font-weight:700;margin-bottom:3px;">
        ${sym}
      </div>
      <div style="color:#c9d1d9;font-size:10px;
        line-height:1.4;margin-bottom:4px;">
        ${escaped}
      </div>
      <div style="color:#444;font-size:9px;">
        ${source ? source + ' · ' : ''}${ago}
      </div>
    </div>`;
}

function _newsMobileItemHtml(sym, item) {
  const title  = (item.title || '').trim();
  const source = (item.author || '')
    .replace(/.*on /i, '').trim() || '';
  const link   = item.link || '';
  const ago    = _timeAgo(item.pubDate);
  const short  = title.length > 90
    ? title.slice(0, 90) + '…' : title;
  const escaped = short
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const safeTitle  = JSON.stringify(title);
  const safeSource = JSON.stringify(source);
  const safeLink   = JSON.stringify(link);

  return `
    <div onclick="_openNewsCard(
        ${safeTitle},${safeSource},
        ${safeLink},'${ago}')"
      style="padding:8px 14px;
        border-bottom:1px solid #161b22;
        cursor:pointer;
        -webkit-tap-highlight-color:transparent;">
      <div style="display:flex;
        justify-content:space-between;
        margin-bottom:3px;">
        <span style="color:#ffd700;
          font-size:11px;font-weight:700;">
          ${sym}
        </span>
        <span style="color:#444;font-size:10px;">
          ${ago}
        </span>
      </div>
      <div style="color:#8b949e;font-size:11px;
        line-height:1.4;">
        ${escaped}
      </div>
    </div>`;
}

async function _renderNewsPanel() {
  const vw       = window.innerWidth || 375;
  const panel    = document.getElementById(
    'news-panel');
  const mobileEl = document.getElementById(
    'mobile-news-section');

  if (!panel) return;

  const layout = _newsLayout();

  if (!layout.show) {
    panel.style.display = 'none';
    // Mobile section for phone/fold
    if (mobileEl && vw < 900) {
      await _renderMobileNewsSection(mobileEl);
    } else if (mobileEl) {
      mobileEl.style.display = 'none';
    }
    return;
  }

  // Desktop panel — hide mobile section
  if (mobileEl) mobileEl.style.display = 'none';

  // Position
  panel.style.display      = 'block';
  panel.style.left         = layout.left + 'px';
  panel.style.top          = '0';
  panel.style.width        = layout.width + 'px';
  panel.style.height       = '100vh';

  const header = `
    <div style="padding:10px 8px 8px;
      border-bottom:1px solid #21262d;
      margin-bottom:8px;">
      <div style="color:#444;font-size:9px;
        font-weight:700;letter-spacing:1px;
        text-transform:uppercase;">
        📰 News
      </div>
    </div>`;

  const stocks = _getNewsStocks();

  if (stocks.length === 0) {
    panel.innerHTML = header +
      `<div style="color:#333;font-size:10px;
        padding:8px;text-align:center;
        line-height:1.6;">
        No active<br>signals
      </div>`;
    return;
  }

  // Show loading state
  panel.innerHTML = header +
    `<div style="color:#333;font-size:10px;
      padding:8px;text-align:center;">
      Loading…
    </div>`;

  // Fetch news (uses cache after first load)
  const newsItems = await _fetchNewsForStocks(stocks);

  if (newsItems.length === 0) {
    panel.innerHTML = header +
      `<div style="color:#333;font-size:10px;
        padding:8px;text-align:center;
        line-height:1.6;">
        No recent<br>news
      </div>`;
    return;
  }

  let html = header;
  const compact = layout.width < 160;
  newsItems.forEach(function(n) {
    html += _newsCardHtml(n.symbol, n.item, compact);
  });

  panel.innerHTML = html;
}

async function _renderMobileNewsSection(el) {
  if (!el) return;

  const stocks = _getNewsStocks();
  if (stocks.length === 0) {
    el.style.display = 'none';
    return;
  }

  el.style.display = 'block';
  const expanded =
    window._mobileNewsExpanded || false;

  el.innerHTML = `
    <div onclick="window._toggleMobileNews()"
      style="background:#0d1117;
        border-bottom:1px solid #21262d;
        padding:8px 14px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        cursor:pointer;
        -webkit-tap-highlight-color:transparent;">
      <span style="color:#555;font-size:11px;
        font-weight:700;">
        📰 News
      </span>
      <span id="mobile-news-arrow"
        style="color:#444;font-size:11px;">
        ${expanded ? '▲' : '▼'}
      </span>
    </div>
    <div id="mobile-news-body"
      style="display:${expanded
        ? 'block' : 'none'};
        background:#0d1117;">
      <div style="color:#444;font-size:10px;
        padding:8px 14px;text-align:center;">
        Loading…
      </div>
    </div>`;

  if (!expanded) return;

  // Fetch and populate
  const newsItems = await _fetchNewsForStocks(stocks);
  _populateMobileNewsBody(newsItems);
}

function _populateMobileNewsBody(newsItems) {
  const body = document.getElementById(
    'mobile-news-body');
  if (!body) return;

  if (!newsItems || newsItems.length === 0) {
    body.innerHTML =
      `<div style="color:#333;font-size:11px;
        padding:8px 14px;text-align:center;">
        No recent news
      </div>`;
    return;
  }

  let html = '';
  newsItems.forEach(function(n) {
    html += _newsMobileItemHtml(n.symbol, n.item);
  });
  body.innerHTML = html;
}

window._toggleMobileNews = function() {
  window._mobileNewsExpanded =
    !(window._mobileNewsExpanded || false);

  const body  = document.getElementById(
    'mobile-news-body');
  const arrow = document.getElementById(
    'mobile-news-arrow');

  if (!body) return;

  if (window._mobileNewsExpanded) {
    if (arrow) arrow.textContent = '▲';
    body.style.display = 'block';

    // Fetch if still showing loading
    if (body.textContent.trim()
        .includes('Loading')) {
      const stocks = _getNewsStocks();
      if (stocks.length > 0) {
        _fetchNewsForStocks(stocks).then(
          _populateMobileNewsBody);
      }
    }
  } else {
    if (arrow) arrow.textContent = '▼';
    body.style.display = 'none';
  }
};

// ── R3: OFFLINE BANNER ────────────────────────────────
function _ensureOfflineBannerEl() {
  let el = document.getElementById('offline-banner');
  if (!el) {
    el = document.createElement('div');
    el.id = 'offline-banner';
    el.style.cssText = [
      'position:fixed',
      'top:0',
      'left:50%',
      'transform:translateX(-50%)',
      'width:100%',
      'max-width:720px',
      'z-index:999',
      'display:none',
    ].join(';');
    document.body.appendChild(el);
  }
  return el;
}

function _showOfflineBanner() {
  const el = _ensureOfflineBannerEl();
  el.innerHTML = `
    <div style="background:#2a0808;
      border-bottom:2px solid #f85149;
      padding:8px 14px;font-size:12px;
      color:#f85149;font-weight:700;
      display:flex;justify-content:space-between;
      align-items:center;">
      <span>📵 Offline — showing cached data</span>
      <span style="color:#555;font-size:10px;
        font-weight:400;">Reconnecting…</span>
    </div>`;
  el.style.display = 'block';
}

function _hideOfflineBanner() {
  const el =
    document.getElementById('offline-banner');
  if (!el) return;
  el.innerHTML = `
    <div style="background:#0d2a0d;
      border-bottom:2px solid #00C851;
      padding:8px 14px;font-size:12px;
      color:#00C851;font-weight:700;">
      ✓ Back online
    </div>`;
  el.style.display = 'block';
  setTimeout(function() {
    el.style.display = 'none';
  }, 2000);
}

window.addEventListener('offline', function() {
  _showOfflineBanner();
});

window.addEventListener('online', function() {
  _hideOfflineBanner();
  setTimeout(function() {
    if (window.TIETIY.loaded) refreshData();
  }, 1000);
});

// ── S1: TABLET WIDTH ENFORCEMENT ─────────────────────
function _enforceTabletWidth() {
  const vw = window.innerWidth
    || document.documentElement.clientWidth
    || 375;

  if (vw < 768) {
    document.body.style.maxWidth  = '';
    document.body.style.margin    = '0 auto';
    document.body.style.overflowX = 'hidden';
    const sidebar =
      document.getElementById('sidebar');
    if (sidebar) sidebar.style.display = 'none';
    // Reposition news panel if visible
    const newsPanel =
      document.getElementById('news-panel');
    if (newsPanel) newsPanel.style.display = 'none';
    console.log('[ui] Phone width: ' + vw + 'px');
    return;
  }

  const cap   = vw >= 1024 ? '720px' : '680px';

  document.body.style.maxWidth  = cap;
  document.body.style.margin    = '0 auto';
  document.body.style.overflowX = 'hidden';

  const tapPanel =
    document.getElementById('tap-panel');
  if (tapPanel) tapPanel.style.maxWidth = cap;

  const helpOverlay =
    document.getElementById('help-overlay');
  if (helpOverlay) {
    helpOverlay.style.maxWidth  = cap;
    helpOverlay.style.left      = '50%';
    helpOverlay.style.transform = 'translateX(-50%)';
    helpOverlay.style.position  = 'fixed';
  }

  // Reposition news panel without re-fetching
  const newsPanel =
    document.getElementById('news-panel');
  if (newsPanel &&
      newsPanel.style.display !== 'none') {
    const nl = _newsLayout();
    if (nl.show) {
      newsPanel.style.left  = nl.left + 'px';
      newsPanel.style.width = nl.width + 'px';
    } else {
      newsPanel.style.display = 'none';
    }
  }

  _renderSidebar();

  console.log('[ui] Tablet width: '
    + cap + ' (vw: ' + vw + 'px)');
}

window.addEventListener('orientationchange',
  function() {
    setTimeout(function() {
      _enforceTabletWidth();
      if (window.TIETIY && window.TIETIY.activeTab) {
        _renderNav(window.TIETIY.activeTab);
      }
    }, 350);
  }
);

window.addEventListener('resize', function() {
  _enforceTabletWidth();
});

// ── STATUS BAR ────────────────────────────────────────
function _renderStatusBar(meta) {
  const el = document.getElementById('status-bar');
  if (!el) return;

  if (!meta) {
    el.innerHTML = `
      <div style="background:#1a0a0a;
        padding:10px 14px;
        border-bottom:1px solid #f85149;">
        <span style="color:#f85149;font-size:12px;">
          ⚠️ Scanner data unavailable
        </span>
      </div>`;
    return;
  }

  const regime    = meta.regime || 'Unknown';
  const today     = _todayIST();
  const isToday   = meta.market_date === today;
  const isTrading = meta.is_trading_day;
  const scanTime  = meta.last_scan
    ? fmtTime(meta.last_scan)
    : meta.scan_time || null;
  const newToday  = _countTodaySignals();

  const stopAlerts  = window.TIETIY.stopAlerts;
  const ltpUpdated  = stopAlerts
    ? (stopAlerts.ltp_updated_at
       || stopAlerts.check_time || null)
    : null;

  const openPrices  = window.TIETIY.openPrices;
  const openValTime = (openPrices
    && openPrices.fetch_time
    && openPrices.count > 0)
    ? openPrices.fetch_time : null;

  const activeCount =
    meta.active_signals_count != null
      ? meta.active_signals_count
      : meta.signals_found || 0;

  const rc = regime === 'Bear'  ? '#ff4444' :
             regime === 'Bull'  ? '#00C851' : '#FFD700';

  let statusDot   = '';
  let statusText  = '';
  let statusColor = '';
  let bgColor     = '#0d1117';
  let borderColor = '#21262d';

  if (!isToday) {
    const hour           = _istHour();
    const todayIsTrading = _isTodayTradingDay();
    const nextDay        = _getNextTradingDay();

    if (!todayIsTrading) {
      statusDot   = '🟡';
      statusText  = `Market closed · Next scan: `
        + `${nextDay} 8:45 AM`;
      statusColor = '#FFD700';
    } else if (hour < 9) {
      statusDot   = '🟡';
      statusText  = `Scan pending · Runs at 8:45 AM IST`;
      statusColor = '#FFD700';
    } else {
      statusDot   = '🔴';
      statusText  = "Yesterday's data · "
        + "Scanner not run today";
      statusColor = '#f85149';
      bgColor     = '#1a0a0a';
      borderColor = '#f85149';
    }
  } else if (!isTrading) {
    const nextDay = _getNextTradingDay();
    statusDot   = '🟡';
    statusText  = `Market closed · Next scan: `
      + `${nextDay} 8:45 AM`;
    statusColor = '#FFD700';
  } else {
    statusDot   = '🟢';
    const parts = [];
    if (scanTime)    parts.push(`Scan ${scanTime}`);
    if (openValTime) parts.push(`Open ${openValTime}`);
    if (ltpUpdated)  parts.push(`LTP ${ltpUpdated}`);
    statusText  = parts.length > 0
      ? parts.join(' · ') : 'Scanned today';
    statusColor = '#00C851';
  }

  const warnings = [];
  if (meta.fetch_failed
      && meta.fetch_failed.length > 0)
    warnings.push(
      `${meta.fetch_failed.length} stocks failed`);
  if (meta.corporate_action_skip
      && meta.corporate_action_skip.length > 0)
    warnings.push(
      `${meta.corporate_action_skip.length} CA skip`);
  const banned = window.TIETIY.bannedStocks || [];
  if (banned.length > 0)
    warnings.push(
      `${banned.length} stocks in F&O ban`);

  const warningHtml = warnings.length > 0
    ? `<div style="font-size:10px;color:#FFD700;
         margin-top:4px;">
         ⚠️ ${warnings.join(' · ')}
       </div>`
    : '';

  const newTodayHtml = newToday > 0
    ? `<span style="background:#1a3a1a;
         color:#00C851;border-radius:4px;
         padding:1px 6px;font-size:10px;
         font-weight:700;margin-left:6px;">
         ${newToday} new today
       </span>`
    : '';

  const regimeNote = isToday && isTrading
    ? `<div style="font-size:9px;color:#444;
         margin-top:3px;">
         Market regime ·
         <span style="color:#333;">
           stock regime on cards may differ
         </span>
       </div>`
    : '';

  el.innerHTML = `
    <div style="background:${bgColor};
      border-bottom:1px solid ${borderColor};
      padding:10px 14px;">

      <div style="display:flex;
        justify-content:space-between;
        align-items:center;margin-bottom:4px;">
        <div style="display:flex;
          align-items:center;gap:8px;">
          <span style="color:#ffd700;font-size:17px;
            font-weight:700;">
            🎯 TIE TIY
          </span>
          <div>
            <span style="background:${rc};color:#000;
              border-radius:4px;padding:1px 7px;
              font-size:11px;font-weight:700;">
              ${regime}
            </span>
            ${regimeNote}
          </div>
        </div>
        <div style="display:flex;
          align-items:center;gap:8px;">
          <button onclick="refreshData()"
            id="refresh-btn"
            style="background:none;
              border:1px solid #30363d;
              border-radius:6px;color:#8b949e;
              font-size:11px;padding:3px 8px;
              cursor:pointer;
              -webkit-tap-highlight-color:transparent;">
            🔄 Refresh
          </button>
          <button onclick="showHelp()"
            style="background:none;
              border:1px solid #30363d;
              border-radius:50%;color:#8b949e;
              font-size:13px;width:26px;height:26px;
              cursor:pointer;line-height:1;
              -webkit-tap-highlight-color:transparent;">
            ?
          </button>
        </div>
      </div>

      <div style="display:flex;
        justify-content:space-between;
        align-items:center;font-size:11px;">
        <span style="color:${statusColor};
          display:flex;align-items:center;">
          ${statusDot} ${statusText}
          ${newTodayHtml}
        </span>
        <span style="color:#555;font-size:10px;">
          ${meta.universe_size || 0} stocks ·
          ${activeCount} signals
        </span>
      </div>

      ${warningHtml}
    </div>`;
}

// ── STOP ALERT BANNER ─────────────────────────────────
function _renderAlertBanner(stopAlerts) {
  const el = document.getElementById('alert-banner');
  if (!el) return;

  if (!stopAlerts || !stopAlerts.has_alerts) {
    el.innerHTML = '';
    return;
  }

  const alerts = (stopAlerts.alerts || []).filter(
    a => ['BREACHED','AT','NEAR'].includes(
      a.alert_level));

  if (!alerts.length) { el.innerHTML = ''; return; }

  const breached = alerts.filter(
    a => a.alert_level === 'BREACHED');
  const at       = alerts.filter(
    a => a.alert_level === 'AT');

  let bgColor  = '#1a1a0a';
  let txtColor = '#FFD700';
  let icon     = '🟡';
  if (breached.length > 0) {
    bgColor  = '#2a0a0a';
    txtColor = '#f85149';
    icon     = '🚨';
  } else if (at.length > 0) {
    bgColor  = '#1a0a0a';
    txtColor = '#f85149';
    icon     = '🔴';
  }

  const names = alerts.slice(0, 3)
    .map(a => a.symbol.replace('.NS', ''))
    .join(', ');
  const more = alerts.length > 3
    ? ` +${alerts.length - 3} more` : '';

  el.innerHTML = `
    <div style="background:${bgColor};
      border-bottom:1px solid ${txtColor}33;
      padding:8px 14px;font-size:12px;
      color:${txtColor};cursor:pointer;"
      onclick="switchTab('signals')">
      ${icon} Stop alert: ${names}${more} ·
      <span style="font-size:10px;color:#888;">
        ${stopAlerts.check_time || ''}
      </span>
    </div>`;
}

// ── BOTTOM NAV ────────────────────────────────────────
function _renderNav(activeTab) {
  const el = document.getElementById('bottom-nav');
  if (!el) return;
  window.TIETIY.activeTab = activeTab;

  const tabs = [
    { id: 'signals', icon: '📊', label: 'Signals' },
    { id: 'journal', icon: '📓', label: 'Journal' },
    { id: 'stats',   icon: '📈', label: 'Stats'   },
  ];

  const vw  = window.innerWidth || 375;
  const cap = vw >= 1024
    ? 'min(720px,100vw)'
    : vw >= 768
      ? 'min(680px,100vw)'
      : '100%';

  el.innerHTML = `
    <div style="position:fixed;bottom:0;left:50%;
      transform:translateX(-50%);
      width:100%;max-width:${cap};
      background:#0d1117;
      border-top:1px solid #21262d;
      display:flex;z-index:50;
      padding-bottom:env(safe-area-inset-bottom);">
      ${tabs.map(t => {
        const active    = t.id === activeTab;
        const iconSize  = vw >= 768 ? '22px' : '18px';
        const labelSize = vw >= 768 ? '11px' : '10px';
        const padTop    = vw >= 768 ? '12px' : '10px';
        return `
          <button onclick="switchTab('${t.id}')"
            style="flex:1;background:none;
              border:none;
              padding:${padTop} 0 8px;
              cursor:pointer;
              display:flex;flex-direction:column;
              align-items:center;gap:2px;
              -webkit-tap-highlight-color:transparent;">
            <span style="font-size:${iconSize};
              opacity:${active ? 1 : 0.4};">
              ${t.icon}
            </span>
            <span style="font-size:${labelSize};
              color:${active ? '#ffd700' : '#555'};
              font-weight:${active ? '700' : '400'};">
              ${t.label}
            </span>
          </button>`;
      }).join('')}
    </div>`;
}

// ── TAB SWITCHING ─────────────────────────────────────
function switchTab(tabId) {
  if (typeof window._closeSignalModal === 'function') {
    window._closeSignalModal();
  }

  window.TIETIY.activeTab = tabId;
  _renderNav(tabId);
  const content =
    document.getElementById('tab-content');
  if (!content) return;

  if (tabId === 'signals') {
    if (typeof renderSignals === 'function')
      renderSignals(window.TIETIY);

  } else if (tabId === 'journal') {
    _seedDefaultTook();
    if (typeof renderJournal === 'function')
      renderJournal(window.TIETIY);

  } else if (tabId === 'stats') {
    if (typeof renderStats === 'function')
      renderStats(window.TIETIY);
  }

  try {
    sessionStorage.setItem('tietiy_tab', tabId);
  } catch(e) {}
}

// ── REFRESH ───────────────────────────────────────────
async function refreshData() {
  const btn = document.getElementById('refresh-btn');
  if (btn) {
    btn.textContent = '⏳';
    btn.disabled    = true;
  }

  try {
    await _fetchAll();
    // Clear news cache on refresh
    window.TIETIY.newsCache = {};

    _renderStatusBar(window.TIETIY.meta);
    _renderAlertBanner(window.TIETIY.stopAlerts);
    _renderSidebar();
    // Re-fetch news on refresh
    _renderNewsPanel();
    switchTab(window.TIETIY.activeTab);

    if (btn) {
      btn.textContent = '✓';
      setTimeout(function() {
        btn.textContent = '🔄 Refresh';
        btn.disabled    = false;
      }, 1500);
    }
  } catch(e) {
    if (btn) {
      btn.textContent = '🔄 Refresh';
      btn.disabled    = false;
    }
  }
}

// ── HELP OVERLAY ──────────────────────────────────────
function showHelp() {
  const el = document.getElementById('help-overlay');
  if (!el) return;
  el.style.display = 'block';
  el.innerHTML = `
    <div style="max-width:600px;margin:0 auto;
      padding:16px 16px 80px;">

      <div style="display:flex;
        justify-content:space-between;
        align-items:center;margin-bottom:20px;
        padding-bottom:12px;
        border-bottom:1px solid #21262d;">
        <span style="color:#ffd700;font-size:18px;
          font-weight:700;">
          ℹ️ How To Use TIE TIY
        </span>
        <button onclick="hideHelp()"
          style="background:none;border:none;
            color:#8b949e;font-size:22px;
            cursor:pointer;
            -webkit-tap-highlight-color:transparent;">
          ✕
        </button>
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          ☀️ 60-SECOND MORNING ROUTINE
        </div>
        ${_helpStep('1','Check status bar',
          'Green = fresh data. Red = stale. '
          + 'Confirm scan ran today.')}
        ${_helpStep('2','Review TOP filter',
          'Shows score 6+ only. Best setups first. '
          + 'Start here.')}
        ${_helpStep('3','Tap card for full detail',
          'Read Entry, Stop, R:R and WHY. '
          + 'Decide in 30 seconds.')}
        ${_helpStep('4','Enter at 9:15 AM open',
          'Do not enter early. '
          + 'Miss by 15+ mins = skip.')}
        ${_helpStep('5','Set stop immediately',
          'Place stop order right after entry. '
          + 'Never skip.')}
        ${_helpStep('6','Exit at Day 6 open',
          'No exceptions. Exit at open of Day 6 '
          + 'regardless of P&L.')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          📐 SIGNAL TYPES
        </div>
        ${_helpSignal('UP TRI ▲','#00C851',
          'Triangle breakout above pivot low',
          'Best in Bear regime. Ages 0–3. '
          + 'Bear 🔥 = highest conviction.')}
        ${_helpSignal('DOWN TRI ▼','#f85149',
          'Triangle breakdown below pivot high',
          'Age 0 ONLY — miss it, skip it. '
          + 'No second chances.')}
        ${_helpSignal('BULL PROXY ◆','#58a6ff',
          'Support zone rejection with momentum',
          'Supplementary signal. Ages 0–1 only.')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          🌡️ REGIME EXPLAINED
        </div>
        <div style="background:#0d1117;
          border-radius:8px;padding:10px 12px;
          font-size:11px;color:#8b949e;
          line-height:1.7;">
          <b style="color:#c9d1d9;">Market regime</b>
          = Nifty50 trend — shown in the header.<br>
          <b style="color:#c9d1d9;">Stock regime</b>
          = individual stock trend — on each card
          as "stk:Bear" etc.<br><br>
          These can differ. Score uses
          <b style="color:#ffd700;">market</b>
          regime for Bear bonus (+3) —
          not stock regime.
        </div>
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          🎯 SCORE SYSTEM
        </div>
        ${_helpTerm('7–8 / 10 (gold)',
          'Best setups. High conviction.')}
        ${_helpTerm('5–6 / 10 (green)',
          'Good setups. Worth entering.')}
        ${_helpTerm('3–4 / 10 (grey)',
          'Weaker. Consider carefully.')}
        ${_helpTerm('1–2 / 10 (dim)',
          'Low conviction. Skip or reduce size.')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          ⚠️ RISK RULES — NON NEGOTIABLE
        </div>
        ${_helpRule('Max 5% capital per trade')}
        ${_helpRule('Stop is set immediately at entry')}
        ${_helpRule('Stop is never moved')}
        ${_helpRule('Stop hit intraday = exit same day')}
        ${_helpRule('No adding to an open position')}
        ${_helpRule(
          'R:R below 1.5 = reduce size or skip')}
        ${_helpRule(
          'Miss 9:15 AM by 15+ mins = skip')}
        ${_helpRule('Gap > 3% at open = skip signal')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          🔔 PUSH NOTIFICATIONS
        </div>
        <div style="background:#0d1117;
          border-radius:8px;padding:12px;
          font-size:12px;color:#8b949e;
          line-height:1.6;">
          Get notified at 8:50 AM every trading day.
          <br><br>
          <strong style="color:#c9d1d9;">
            iOS users:
          </strong>
          Add to Home Screen first, then open from
          home screen icon to enable notifications.
          <br><br>
          <button onclick="requestNotifications()"
            id="notif-btn"
            style="background:#21262d;
              border:1px solid #30363d;
              color:#c9d1d9;border-radius:6px;
              padding:8px 16px;font-size:12px;
              cursor:pointer;margin-top:4px;
              -webkit-tap-highlight-color:transparent;">
            Enable Notifications
          </button>
          <div id="notif-status"
            style="margin-top:8px;font-size:11px;
              color:#555;"></div>
        </div>
      </div>

      <button onclick="hideHelp()"
        style="width:100%;background:#21262d;
          border:1px solid #30363d;color:#c9d1d9;
          border-radius:8px;padding:12px;
          font-size:14px;cursor:pointer;
          -webkit-tap-highlight-color:transparent;">
        Close
      </button>
    </div>`;
}

function hideHelp() {
  const el = document.getElementById('help-overlay');
  if (el) el.style.display = 'none';
}

function _helpStep(num, title, desc) {
  return `
    <div style="display:flex;gap:10px;
      margin-bottom:10px;">
      <div style="background:#ffd700;color:#000;
        border-radius:50%;width:20px;height:20px;
        min-width:20px;font-size:11px;font-weight:700;
        display:flex;align-items:center;
        justify-content:center;">${num}</div>
      <div>
        <div style="color:#c9d1d9;font-size:12px;
          font-weight:700;">${title}</div>
        <div style="color:#666;font-size:11px;
          margin-top:2px;line-height:1.5;">
          ${desc}
        </div>
      </div>
    </div>`;
}

function _helpSignal(name, color, subtitle, desc) {
  return `
    <div style="background:#0d1117;
      border-left:3px solid ${color};
      border-radius:0 6px 6px 0;
      padding:8px 10px;margin-bottom:8px;">
      <div style="color:${color};font-size:12px;
        font-weight:700;">${name}</div>
      <div style="color:#c9d1d9;font-size:11px;
        margin:2px 0;">${subtitle}</div>
      <div style="color:#666;font-size:11px;
        line-height:1.5;">${desc}</div>
    </div>`;
}

function _helpTerm(term, desc) {
  return `
    <div style="display:flex;gap:8px;
      margin-bottom:8px;font-size:11px;">
      <div style="color:#ffd700;font-weight:700;
        min-width:120px;">${term}</div>
      <div style="color:#8b949e;line-height:1.5;">
        ${desc}
      </div>
    </div>`;
}

function _helpRule(rule) {
  return `
    <div style="display:flex;gap:8px;
      margin-bottom:6px;font-size:12px;
      color:#c9d1d9;">
      <span style="color:#f85149;">✕</span>
      ${rule}
    </div>`;
}

// ── PUSH NOTIFICATIONS ────────────────────────────────
async function requestNotifications() {
  const statusEl =
    document.getElementById('notif-status');
  const btn = document.getElementById('notif-btn');

  if (!('serviceWorker' in navigator) ||
      !('PushManager' in window)) {
    if (statusEl) statusEl.textContent =
      'Push not supported. Install as PWA first.';
    return;
  }

  const pin = prompt(
    'Enter notification PIN to subscribe:');
  if (!pin || pin.length !== PUSH_PIN_LENGTH) {
    if (statusEl) statusEl.textContent =
      'Invalid PIN — notifications not enabled.';
    return;
  }

  try {
    if (statusEl) statusEl.textContent =
      'Requesting permission…';
    const permission =
      await Notification.requestPermission();
    if (permission !== 'granted') {
      if (statusEl) statusEl.textContent =
        'Permission denied. '
        + 'Enable in browser settings.';
      return;
    }

    const registration =
      await navigator.serviceWorker.ready;
    const subscription =
      await registration.pushManager.subscribe({
        userVisibleOnly:      true,
        applicationServerKey: _urlB64ToUint8Array(
          VAPID_PUBLIC_KEY),
      });

    const subJson = subscription.toJSON();
    const payload = {
      endpoint:      subJson.endpoint,
      keys:          subJson.keys,
      pin_verified:  true,
      subscribed_at: new Date()
        .toISOString().slice(0, 10),
    };

    localStorage.setItem(
      'tietiy_push_sub', JSON.stringify(payload));

    if (statusEl) statusEl.innerHTML =
      '<span style="color:#00C851;">'
      + '✓ Subscribed!</span>'
      + ' Alerts at 8:50 AM IST.';
    if (btn) btn.textContent = '✓ Subscribed';

  } catch(e) {
    if (statusEl) statusEl.textContent =
      'Subscription failed: ' + e.message;
  }
}

function _urlB64ToUint8Array(base64String) {
  const padding =
    '='.repeat((4 - base64String.length % 4) % 4);
  const base64  = (base64String + padding)
    .replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const arr     = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    arr[i] = rawData.charCodeAt(i);
  }
  return arr;
}

// ── SESSION RESTORE ───────────────────────────────────
function _restoreSession() {
  try {
    const lastTab =
      sessionStorage.getItem('tietiy_tab');
    if (lastTab) window.TIETIY.activeTab = lastTab;
  } catch(e) {}
}

// ── TRADING DAY COUNTER ───────────────────────────────
function tradingDaysBetween(startDateStr, endDateStr) {
  const holidays = window.TIETIY.holidays || [];
  let   count    = 0;
  const start    = new Date(
    startDateStr + 'T00:00:00');
  const end      = new Date(
    endDateStr   + 'T00:00:00');
  const cur      = new Date(start);
  while (cur <= end) {
    const dayOfWeek = cur.getDay();
    const dateStr   = cur.toLocaleDateString(
      'en-CA', { timeZone: 'Asia/Kolkata' });
    if (dayOfWeek !== 0 && dayOfWeek !== 6 &&
        !holidays.includes(dateStr)) {
      count++;
    }
    cur.setDate(cur.getDate() + 1);
  }
  return count;
}

function getEntryDate(signalDateStr) {
  const holidays = window.TIETIY.holidays || [];
  const cur = new Date(
    signalDateStr + 'T00:00:00');
  cur.setDate(cur.getDate() + 1);
  while (true) {
    const dayOfWeek = cur.getDay();
    const dateStr   = cur.toLocaleDateString(
      'en-CA', { timeZone: 'Asia/Kolkata' });
    if (dayOfWeek !== 0 && dayOfWeek !== 6 &&
        !holidays.includes(dateStr)) {
      return dateStr;
    }
    cur.setDate(cur.getDate() + 1);
  }
}

function getDayNumber(signalDateStr) {
  const entryDate = getEntryDate(signalDateStr);
  const today     = _todayIST();
  if (today < entryDate) return 1;
  const days = tradingDaysBetween(entryDate, today);
  return Math.min(Math.max(days, 1), 6);
}

function getExitDate(signalDateStr) {
  const holidays  = window.TIETIY.holidays || [];
  const entryDate = getEntryDate(signalDateStr);
  let   count     = 0;
  const cur = new Date(entryDate + 'T00:00:00');
  while (count < 5) {
    cur.setDate(cur.getDate() + 1);
    const dayOfWeek = cur.getDay();
    const dateStr   = cur.toLocaleDateString(
      'en-CA', { timeZone: 'Asia/Kolkata' });
    if (dayOfWeek !== 0 && dayOfWeek !== 6 &&
        !holidays.includes(dateStr)) {
      count++;
    }
  }
  return cur.toLocaleDateString(
    'en-CA', { timeZone: 'Asia/Kolkata' });
}

// ── MAIN INIT ─────────────────────────────────────────
async function initApp() {
  const loader    =
    document.getElementById('app-loader');
  const errorDiv  =
    document.getElementById('app-error');
  const appRoot   =
    document.getElementById('app-root');
  const loaderMsg =
    document.getElementById('loader-msg');

  _enforceTabletWidth();
  _ensureOfflineBannerEl();
  _restoreSession();

  try {
    if (loaderMsg)
      loaderMsg.textContent = 'Loading scanner data…';
    const success = await _fetchAll();

    if (!success || !window.TIETIY.meta) {
      if (loader)
        loader.style.display   = 'none';
      if (errorDiv)
        errorDiv.style.display = 'block';
      return;
    }

    _checkAppVersion(window.TIETIY.meta);

    if (loader)  loader.style.display  = 'none';
    if (appRoot) appRoot.style.display = 'block';

    _enforceTabletWidth();

    _renderStatusBar(window.TIETIY.meta);
    _renderAlertBanner(window.TIETIY.stopAlerts);
    _renderSidebar();
    // News panel — async, fires after main UI renders
    _renderNewsPanel();
    _renderNav(window.TIETIY.activeTab);
    switchTab(window.TIETIY.activeTab);

    if (!navigator.onLine) _showOfflineBanner();

  } catch(e) {
    console.error('[ui] Init error:', e);
    if (loader)
      loader.style.display   = 'none';
    if (errorDiv)
      errorDiv.style.display = 'block';
  }
}

window.addEventListener('load', initApp);
