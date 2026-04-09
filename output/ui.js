// ── ui.js ────────────────────────────────────────────
// Master controller for TIE TIY Scanner frontend
// Loads first — all other JS files depend on this
//
// Changes in this pass:
// - Default filter is now 'top' (was 'all')
// - _buildConflictMap exported as window helper
// - Status bar wording refined
// - P1 FIX: LTP updated_at shown in status bar
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

// IST date helper — prevents UTC bleed after 6:30 PM IST
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
    s => s.date === today && s.result === 'PENDING'
  ).length;
}

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

  // P1 FIX: Read LTP updated_at from stop_alerts.json
  const stopAlerts  = window.TIETIY.stopAlerts;
  const ltpUpdated  = stopAlerts
    ? (stopAlerts.ltp_updated_at || stopAlerts.check_time || null)
    : null;

  const activeCount = meta.active_signals_count != null
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
    statusDot   = '🔴';
    statusText  = "Yesterday's data · Scanner not run today";
    statusColor = '#f85149';
    bgColor     = '#1a0a0a';
    borderColor = '#f85149';
  } else if (!isTrading) {
    const nextDay = _getNextTradingDay();
    statusDot   = '🟡';
    statusText  = `Market closed · Next scan: ${nextDay} 8:45 AM`;
    statusColor = '#FFD700';
  } else {
    statusDot   = '🟢';
    // P1 FIX: Show scan time + LTP time together
    if (scanTime && ltpUpdated) {
      statusText = `Scan ${scanTime} · LTP ${ltpUpdated}`;
    } else if (scanTime) {
      statusText = `Scanned ${scanTime}`;
    } else {
      statusText = 'Scanned today';
    }
    statusColor = '#00C851';
  }

  const warnings = [];
  if (meta.fetch_failed && meta.fetch_failed.length > 0)
    warnings.push(`${meta.fetch_failed.length} stocks failed`);
  if (meta.corporate_action_skip &&
      meta.corporate_action_skip.length > 0)
    warnings.push(
      `${meta.corporate_action_skip.length} CA skip`);
  const banned = window.TIETIY.bannedStocks || [];
  if (banned.length > 0)
    warnings.push(`${banned.length} stocks in F&O ban`);

  const warningHtml = warnings.length > 0
    ? `<div style="font-size:10px;color:#FFD700;margin-top:4px;">
         ⚠️ ${warnings.join(' · ')}
       </div>`
    : '';

  const newTodayHtml = newToday > 0
    ? `<span style="background:#1a3a1a;color:#00C851;
         border-radius:4px;padding:1px 6px;font-size:10px;
         font-weight:700;margin-left:6px;">
         ${newToday} new today
       </span>`
    : '';

  el.innerHTML = `
    <div style="background:${bgColor};
      border-bottom:1px solid ${borderColor};
      padding:10px 14px;">

      <div style="display:flex;
        justify-content:space-between;
        align-items:center;margin-bottom:4px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="color:#ffd700;font-size:17px;font-weight:700;">
            🎯 TIE TIY
          </span>
          <span style="background:${rc};color:#000;
            border-radius:4px;padding:1px 7px;
            font-size:11px;font-weight:700;">
            ${regime}
          </span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <button onclick="refreshData()"
            id="refresh-btn"
            style="background:none;border:1px solid #30363d;
              border-radius:6px;color:#8b949e;font-size:11px;
              padding:3px 8px;cursor:pointer;">
            🔄 Refresh
          </button>
          <button onclick="showHelp()"
            style="background:none;border:1px solid #30363d;
              border-radius:50%;color:#8b949e;font-size:13px;
              width:26px;height:26px;cursor:pointer;line-height:1;">
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
    a => ['BREACHED','AT','NEAR'].includes(a.alert_level));

  if (!alerts.length) { el.innerHTML = ''; return; }

  const breached = alerts.filter(
    a => a.alert_level === 'BREACHED');
  const at       = alerts.filter(
    a => a.alert_level === 'AT');

  let bgColor  = '#1a1a0a';
  let txtColor = '#FFD700';
  let icon     = '🟡';
  if (breached.length > 0) {
    bgColor = '#2a0a0a'; txtColor = '#f85149'; icon = '🚨';
  } else if (at.length > 0) {
    bgColor = '#1a0a0a'; txtColor = '#f85149'; icon = '🔴';
  }

  const names = alerts.slice(0, 3)
    .map(a => a.symbol.replace('.NS',''))
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

  el.innerHTML = `
    <div style="position:fixed;bottom:0;left:50%;
      transform:translateX(-50%);
      width:100%;max-width:min(960px,100vw);
      background:#0d1117;border-top:1px solid #21262d;
      display:flex;z-index:50;
      padding-bottom:env(safe-area-inset-bottom);">
      ${tabs.map(t => {
        const active = t.id === activeTab;
        return `
          <button onclick="switchTab('${t.id}')"
            style="flex:1;background:none;border:none;
              padding:10px 0 8px;cursor:pointer;
              display:flex;flex-direction:column;
              align-items:center;gap:2px;">
            <span style="font-size:18px;
              opacity:${active ? 1 : 0.4};">
              ${t.icon}
            </span>
            <span style="font-size:10px;
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
  window.TIETIY.activeTab = tabId;
  _renderNav(tabId);
  const content = document.getElementById('tab-content');
  if (!content) return;

  if (tabId === 'signals') {
    if (typeof renderSignals === 'function')
      renderSignals(window.TIETIY);
  } else if (tabId === 'journal') {
    if (typeof renderJournal === 'function')
      renderJournal(window.TIETIY);
  } else if (tabId === 'stats') {
    if (typeof renderStats === 'function')
      renderStats(window.TIETIY);
  }

  try { sessionStorage.setItem('tietiy_tab', tabId); }
  catch(e) {}
}

// ── REFRESH ───────────────────────────────────────────
async function refreshData() {
  const btn = document.getElementById('refresh-btn');
  if (btn) { btn.textContent = '⏳'; btn.disabled = true; }

  try {
    await _fetchAll();
    _renderStatusBar(window.TIETIY.meta);
    _renderAlertBanner(window.TIETIY.stopAlerts);
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

      <div style="display:flex;justify-content:space-between;
        align-items:center;margin-bottom:20px;padding-bottom:12px;
        border-bottom:1px solid #21262d;">
        <span style="color:#ffd700;font-size:18px;font-weight:700;">
          ℹ️ How To Use TIE TIY
        </span>
        <button onclick="hideHelp()"
          style="background:none;border:none;
            color:#8b949e;font-size:22px;cursor:pointer;">
          ✕
        </button>
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;font-weight:700;
          margin-bottom:10px;letter-spacing:1px;">
          ☀️ 60-SECOND MORNING ROUTINE
        </div>
        ${_helpStep('1','Check status bar',
          'Green = fresh data. Red = stale. Confirm scan ran today.')}
        ${_helpStep('2','Review TOP filter',
          'Shows score 6+ only. Best setups first. Start here.')}
        ${_helpStep('3','Tap card for full detail',
          'Read Entry, Stop, R:R and WHY. Decide in 30 seconds.')}
        ${_helpStep('4','Enter at 9:15 AM open',
          'Do not enter early. Miss by 15+ mins = skip.')}
        ${_helpStep('5','Set stop immediately',
          'Place stop order right after entry. Never skip.')}
        ${_helpStep('6','Exit at Day 6 open',
          'No exceptions. Exit at open of Day 6 regardless of P&L.')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;font-weight:700;
          margin-bottom:10px;letter-spacing:1px;">
          📐 SIGNAL TYPES
        </div>
        ${_helpSignal('UP TRI ▲','#00C851',
          'Triangle breakout above pivot low',
          'Best in Bear regime. Ages 0–3. Bear 🔥 = highest conviction.')}
        ${_helpSignal('DOWN TRI ▼','#f85149',
          'Triangle breakdown below pivot high',
          'Age 0 ONLY — miss it, skip it. No second chances.')}
        ${_helpSignal('BULL PROXY ◆','#58a6ff',
          'Support zone rejection with momentum',
          'Supplementary signal. Ages 0–1 only.')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;font-weight:700;
          margin-bottom:10px;letter-spacing:1px;">
          🎯 SCORE SYSTEM
        </div>
        ${_helpTerm('7–8 / 10 (gold)','Best setups. High conviction.')}
        ${_helpTerm('5–6 / 10 (green)','Good setups. Worth entering.')}
        ${_helpTerm('3–4 / 10 (grey)','Weaker. Consider carefully.')}
        ${_helpTerm('1–2 / 10 (dim)','Low conviction. Skip or reduce size.')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;font-weight:700;
          margin-bottom:10px;letter-spacing:1px;">
          ⚠️ RISK RULES — NON NEGOTIABLE
        </div>
        ${_helpRule('Max 5% capital per trade')}
        ${_helpRule('Stop is set immediately at entry')}
        ${_helpRule('Stop is never moved')}
        ${_helpRule('Stop hit intraday = exit same day')}
        ${_helpRule('No adding to an open position')}
        ${_helpRule('R:R below 1.5 = reduce size or skip')}
        ${_helpRule('Miss 9:15 AM by 15+ mins = skip')}
        ${_helpRule('Gap > 3% at open = skip signal')}
      </div>

      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;font-weight:700;
          margin-bottom:10px;letter-spacing:1px;">
          🔔 PUSH NOTIFICATIONS
        </div>
        <div style="background:#0d1117;border-radius:8px;
          padding:12px;font-size:12px;color:#8b949e;line-height:1.6;">
          Get notified at 8:50 AM every trading day.<br><br>
          <strong style="color:#c9d1d9;">iOS users:</strong>
          Add to Home Screen first, then open from home screen
          icon to enable notifications.<br><br>
          <button onclick="requestNotifications()"
            id="notif-btn"
            style="background:#21262d;border:1px solid #30363d;
              color:#c9d1d9;border-radius:6px;padding:8px 16px;
              font-size:12px;cursor:pointer;margin-top:4px;">
            Enable Notifications
          </button>
          <div id="notif-status"
            style="margin-top:8px;font-size:11px;color:#555;">
          </div>
        </div>
      </div>

      <button onclick="hideHelp()"
        style="width:100%;background:#21262d;
          border:1px solid #30363d;color:#c9d1d9;
          border-radius:8px;padding:12px;
          font-size:14px;cursor:pointer;">
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
    <div style="display:flex;gap:10px;margin-bottom:10px;">
      <div style="background:#ffd700;color:#000;border-radius:50%;
        width:20px;height:20px;min-width:20px;font-size:11px;
        font-weight:700;display:flex;align-items:center;
        justify-content:center;">${num}</div>
      <div>
        <div style="color:#c9d1d9;font-size:12px;font-weight:700;">
          ${title}
        </div>
        <div style="color:#666;font-size:11px;margin-top:2px;
          line-height:1.5;">
          ${desc}
        </div>
      </div>
    </div>`;
}

function _helpSignal(name, color, subtitle, desc) {
  return `
    <div style="background:#0d1117;border-left:3px solid ${color};
      border-radius:0 6px 6px 0;padding:8px 10px;margin-bottom:8px;">
      <div style="color:${color};font-size:12px;font-weight:700;">
        ${name}
      </div>
      <div style="color:#c9d1d9;font-size:11px;margin:2px 0;">
        ${subtitle}
      </div>
      <div style="color:#666;font-size:11px;line-height:1.5;">
        ${desc}
      </div>
    </div>`;
}

function _helpTerm(term, desc) {
  return `
    <div style="display:flex;gap:8px;margin-bottom:8px;font-size:11px;">
      <div style="color:#ffd700;font-weight:700;min-width:120px;">
        ${term}
      </div>
      <div style="color:#8b949e;line-height:1.5;">${desc}</div>
    </div>`;
}

function _helpRule(rule) {
  return `
    <div style="display:flex;gap:8px;margin-bottom:6px;
      font-size:12px;color:#c9d1d9;">
      <span style="color:#f85149;">✕</span> ${rule}
    </div>`;
}

// ── PUSH NOTIFICATIONS ────────────────────────────────
async function requestNotifications() {
  const statusEl = document.getElementById('notif-status');
  const btn      = document.getElementById('notif-btn');

  if (!('serviceWorker' in navigator) ||
      !('PushManager' in window)) {
    if (statusEl) statusEl.textContent =
      'Push not supported. Install as PWA from home screen first.';
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
        'Permission denied. Enable in browser settings.';
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

    const subJson  = subscription.toJSON();
    const payload  = {
      endpoint:      subJson.endpoint,
      keys:          subJson.keys,
      pin_verified:  true,
      subscribed_at: new Date()
        .toISOString().slice(0, 10),
    };

    localStorage.setItem(
      'tietiy_push_sub', JSON.stringify(payload));

    if (statusEl) statusEl.innerHTML =
      '<span style="color:#00C851;">✓ Subscribed!</span> ' +
      'Alerts at 8:50 AM IST.';
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
    const lastTab = sessionStorage.getItem('tietiy_tab');
    if (lastTab) window.TIETIY.activeTab = lastTab;
  } catch(e) {}
}

// ── TRADING DAY COUNTER ───────────────────────────────
function tradingDaysBetween(startDateStr, endDateStr) {
  const holidays = window.TIETIY.holidays || [];
  let   count    = 0;
  const start    = new Date(startDateStr + 'T00:00:00');
  const end      = new Date(endDateStr   + 'T00:00:00');
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
  const cur      = new Date(signalDateStr + 'T00:00:00');
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
  const cur       = new Date(entryDate + 'T00:00:00');
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
  const loader    = document.getElementById('app-loader');
  const errorDiv  = document.getElementById('app-error');
  const appRoot   = document.getElementById('app-root');
  const loaderMsg = document.getElementById('loader-msg');

  _restoreSession();

  try {
    if (loaderMsg)
      loaderMsg.textContent = 'Loading scanner data…';
    const success = await _fetchAll();

    if (!success || !window.TIETIY.meta) {
      if (loader)   loader.style.display  = 'none';
      if (errorDiv) errorDiv.style.display = 'block';
      return;
    }

    _checkAppVersion(window.TIETIY.meta);

    if (loader)  loader.style.display  = 'none';
    if (appRoot) appRoot.style.display = 'block';

    _renderStatusBar(window.TIETIY.meta);
    _renderAlertBanner(window.TIETIY.stopAlerts);
    _renderNav(window.TIETIY.activeTab);
    switchTab(window.TIETIY.activeTab);

  } catch(e) {
    console.error('[ui] Init error:', e);
    if (loader)   loader.style.display  = 'none';
    if (errorDiv) errorDiv.style.display = 'block';
  }
}

window.addEventListener('load', initApp);
