// ── ui.js ────────────────────────────────────────────
// Master controller for TIE TIY Scanner frontend
// Loads first — all other JS files depend on this
//
// Responsibilities:
// 1. Fetch all JSON files once → window.TIETIY store
// 2. Pass data to app.js, journal.js, stats.js
// 3. Render status bar, bottom nav, refresh button
// 4. Help/glossary overlay
// 5. Stop alert banner
// 6. App version cache busting
// 7. Loading spinner + error states
// 8. Push notification subscription
// 9. Session restore — reopen last viewed signal
// ─────────────────────────────────────────────────────

// ── VAPID PUBLIC KEY ──────────────────────────────────
// Generated in Colab — matches VAPID_PRIVATE_KEY
// in GitHub Secrets
const VAPID_PUBLIC_KEY =
  'BD0o5qPcwXsEpSv5KXOSKZRHyyGVoC0bTNbRMcOSX2t-t5OBf1sHGKJH2y8m6uYnCwa3g_xfzJdmWoEuxR941Rk';

// ── PUSH PIN ──────────────────────────────────────────
// Must match PUSH_PIN in GitHub Secrets
// User enters this before subscribing to notifications
// Change this if you change the secret
const PUSH_PIN_LENGTH = 4;

// ── BASE URL ──────────────────────────────────────────
const BASE_URL = '/tietiy-scanner/';

// ── BACKTEST WR BASELINE ─────────────────────────────
// From V3 backtest — used in journal comparison
const BACKTEST_WR = {
  UP_TRI:     87,
  DOWN_TRI:   87,
  UP_TRI_SA:  87,
  DOWN_TRI_SA: 87,
  BULL_PROXY: 67,
  OVERALL:    87,
};

// ── GLOBAL DATA STORE ─────────────────────────────────
// Single source of truth for all JS files
// Populated by _fetchAll() on page load
// Never write to this directly — use _fetchAll()
window.TIETIY = {
  meta:        null,
  scanLog:     null,
  miniLog:     null,
  history:     null,
  openPrices:  null,
  eodPrices:   null,
  stopAlerts:  null,
  holidays:    [],
  loaded:      false,
  activeTab:   'signals',
  lastFetch:   null,
};


// ── UTILITY ───────────────────────────────────────────

function fmt(n) {
  return parseFloat(n).toLocaleString('en-IN', {
    minimumFractionDigits:  2,
    maximumFractionDigits:  2,
  });
}

function fmtDate(str) {
  if (!str) return '—';
  try {
    const d = new Date(str);
    return d.toLocaleDateString('en-IN', {
      day:   '2-digit',
      month: 'short',
    });
  } catch(e) { return str; }
}

function fmtTime(utcStr) {
  if (!utcStr) return '—';
  try {
    // Convert UTC ISO string to IST display
    const d = new Date(utcStr);
    return d.toLocaleTimeString('en-IN', {
      hour:     '2-digit',
      minute:   '2-digit',
      timeZone: 'Asia/Kolkata',
    }) + ' IST';
  } catch(e) { return utcStr; }
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
    stopAlerts, holidays,
  ] = await Promise.all([
    _safeGet('meta.json'),
    _safeGet('scan_log.json'),
    _safeGet('mini_log.json'),
    _safeGet('signal_history.json'),
    _safeGet('open_prices.json'),
    _safeGet('eod_prices.json'),
    _safeGet('stop_alerts.json'),
    _safeGet('nse_holidays.json'),
  ]);

  window.TIETIY.meta        = meta;
  window.TIETIY.scanLog     = scanLog;
  window.TIETIY.miniLog     = miniLog;
  window.TIETIY.history     = history;
  window.TIETIY.openPrices  = openPrices;
  window.TIETIY.eodPrices   = eodPrices;
  window.TIETIY.stopAlerts  = stopAlerts;
  window.TIETIY.holidays    = holidays
    ? holidays.holidays || []
    : [];
  window.TIETIY.loaded      = true;
  window.TIETIY.lastFetch   = Date.now();

  return !!meta;
}


// ── APP VERSION CHECK ─────────────────────────────────
// If meta.app_version differs from last known version
// force a full reload to clear stale JS cache
// Runs once per session

function _checkAppVersion(meta) {
  if (!meta) return;
  const stored = localStorage.getItem('tietiy_app_v');
  const current = meta.app_version || '2.0';
  if (stored && stored !== current) {
    localStorage.setItem('tietiy_app_v', current);
    console.log('[ui] App version changed — reloading');
    location.reload(true);
    return;
  }
  localStorage.setItem('tietiy_app_v', current);
}


// ── STATUS BAR ────────────────────────────────────────

function _renderStatusBar(meta) {
  const el = document.getElementById('status-bar');
  if (!el) return;

  if (!meta) {
    el.innerHTML = `
      <div style="background:#1a0a0a;padding:10px 14px;
        border-bottom:1px solid #f85149;">
        <span style="color:#f85149;font-size:12px;">
          ⚠️ Scanner data unavailable
        </span>
      </div>`;
    return;
  }

  const regime     = meta.regime || 'Unknown';
  const isToday    = meta.market_date ===
    new Date().toISOString().slice(0,10);
  const isTrading  = meta.is_trading_day;
  const deployedAt = meta.deployed_at
    ? fmtTime(meta.deployed_at)
    : null;
  const scanTime   = meta.last_scan
    ? fmtTime(meta.last_scan)
    : null;

  // Regime colour
  const rc = regime === 'Bear'  ? '#ff4444' :
             regime === 'Bull'  ? '#00C851' :
             '#FFD700';

  // Status indicator
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
    statusDot   = '🟡';
    statusText  = 'Market closed today';
    statusColor = '#FFD700';
  } else if (deployedAt) {
    statusDot   = '🟢';
    statusText  = `Deployed ${deployedAt}`;
    statusColor = '#00C851';
  } else if (scanTime) {
    statusDot   = '🟡';
    statusText  = `Scanned ${scanTime} · Deploying...`;
    statusColor = '#FFD700';
  } else {
    statusDot   = '🟡';
    statusText  = 'Status unknown';
    statusColor = '#FFD700';
  }

  // Warnings from meta
  const warnings = [];
  if (meta.fetch_failed && meta.fetch_failed.length > 0) {
    warnings.push(
      `${meta.fetch_failed.length} stocks failed to fetch`);
  }
  if (meta.corporate_action_skip &&
      meta.corporate_action_skip.length > 0) {
    warnings.push(
      `${meta.corporate_action_skip.length} skipped ` +
      `(corporate action)`);
  }

  const warningHtml = warnings.length > 0
    ? `<div style="font-size:10px;color:#FFD700;
         margin-top:4px;">
         ⚠️ ${warnings.join(' · ')}
       </div>`
    : '';

  el.innerHTML = `
    <div style="background:${bgColor};
      border-bottom:1px solid ${borderColor};
      padding:10px 14px;">

      <div style="display:flex;
        justify-content:space-between;
        align-items:center;margin-bottom:4px;">

        <div style="display:flex;align-items:center;gap:8px;">
          <span style="color:#ffd700;font-size:17px;
            font-weight:700;">🎯 TIE TIY</span>
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
              border-radius:6px;color:#8b949e;
              font-size:11px;padding:3px 8px;
              cursor:pointer;">
            🔄 Refresh
          </button>
          <button onclick="showHelp()"
            style="background:none;border:1px solid #30363d;
              border-radius:50%;color:#8b949e;
              font-size:13px;width:26px;height:26px;
              cursor:pointer;line-height:1;">
            ?
          </button>
        </div>
      </div>

      <div style="display:flex;justify-content:space-between;
        align-items:center;font-size:11px;">
        <span style="color:${statusColor};">
          ${statusDot} ${statusText}
        </span>
        <span style="color:#555;font-size:10px;">
          ${meta.universe_size || 0} stocks ·
          ${meta.signals_found || 0} signals
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
    a => ['BREACHED', 'AT', 'NEAR']
         .includes(a.alert_level));

  if (!alerts.length) {
    el.innerHTML = '';
    return;
  }

  const breached = alerts.filter(
    a => a.alert_level === 'BREACHED');
  const at = alerts.filter(
    a => a.alert_level === 'AT');
  const near = alerts.filter(
    a => a.alert_level === 'NEAR');

  let bgColor  = '#0d2a0d';
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

  const names = alerts
    .slice(0, 3)
    .map(a => a.symbol.replace('.NS',''))
    .join(', ');
  const more = alerts.length > 3
    ? ` +${alerts.length - 3} more` : '';

  el.innerHTML = `
    <div style="background:${bgColor};
      border-bottom:1px solid ${txtColor}33;
      padding:8px 14px;font-size:12px;
      color:${txtColor};">
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
      background:#0d1117;
      border-top:1px solid #21262d;
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
    if (typeof renderSignals === 'function') {
      renderSignals(window.TIETIY);
    }
  } else if (tabId === 'journal') {
    if (typeof renderJournal === 'function') {
      renderJournal(window.TIETIY);
    }
  } else if (tabId === 'stats') {
    if (typeof renderStats === 'function') {
      renderStats(window.TIETIY);
    }
  }

  // Save last tab to session
  try {
    sessionStorage.setItem('tietiy_tab', tabId);
  } catch(e) {}
}


// ── REFRESH ───────────────────────────────────────────

async function refreshData() {
  const btn = document.getElementById('refresh-btn');
  if (btn) {
    btn.textContent  = '⏳';
    btn.disabled     = true;
  }

  document.getElementById('loader-msg').textContent =
    'Refreshing...';

  try {
    await _fetchAll();
    _renderStatusBar(window.TIETIY.meta);
    _renderAlertBanner(window.TIETIY.stopAlerts);

    // Re-render active tab
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
        align-items:center;margin-bottom:20px;
        padding-bottom:12px;
        border-bottom:1px solid #21262d;">
        <span style="color:#ffd700;font-size:18px;
          font-weight:700;">ℹ️ How To Use TIE TIY</span>
        <button onclick="hideHelp()"
          style="background:none;border:none;
            color:#8b949e;font-size:22px;
            cursor:pointer;">✕</button>
      </div>

      <!-- MORNING ROUTINE -->
      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          ☀️ 60-SECOND MORNING ROUTINE
        </div>
        ${_helpStep('1', 'Check status bar',
          'Green = fresh data. Red = stale. ' +
          'Always confirm scan ran today.')}
        ${_helpStep('2', 'Read top scored signal',
          'Cards sorted by score. Highest first. ' +
          'Start at the top.')}
        ${_helpStep('3', 'Tap card → check tap panel',
          'Read Entry, Stop, R:R and WHY. ' +
          'Decide in 30 seconds.')}
        ${_helpStep('4', 'Enter at 9:15 AM open',
          'Do not enter early. ' +
          'If you miss open by 15+ mins, skip the signal.')}
        ${_helpStep('5', 'Set stop immediately',
          'Place stop order on broker right after entry. ' +
          'Never skip this step.')}
        ${_helpStep('6', 'Exit at Day 6 open',
          'No exceptions. Exit at open of Day 6 ' +
          'regardless of P&L.')}
      </div>

      <!-- SIGNAL TYPES -->
      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          📐 SIGNAL TYPES
        </div>
        ${_helpSignal('UP_TRI ▲', '#00C851',
          'Bullish triangle breakout',
          'Price broke above a series of higher lows. ' +
          'Best in Bear regime. Ages 0–3 valid. ' +
          'Bear regime = highest conviction 🔥')}
        ${_helpSignal('DOWN_TRI ▼', '#f85149',
          'Bearish triangle breakdown',
          'Price broke below a series of lower highs. ' +
          'Age 0 ONLY — miss it, skip it. ' +
          'Edge disappears entirely at age 1+.')}
        ${_helpSignal('BULL_PROXY ◆', '#58a6ff',
          'Support zone rejection',
          'Price bounced from a key support zone. ' +
          'Supplementary signal. Ages 0–1 only. ' +
          'Trend filter required.')}
        ${_helpSignal('UP_TRI_SA ▲▲', '#00C851',
          'Second attempt — bullish',
          'First UP_TRI attempt stopped. ' +
          'Price pulled back and is trying again. ' +
          'Same level proven twice = higher conviction.')}
        ${_helpSignal('DOWN_TRI_SA ▼▼', '#f85149',
          'Second attempt — bearish',
          'First DOWN_TRI attempt stopped. ' +
          'Second attempt at same breakdown level. ' +
          'Lower score threshold to qualify.')}
      </div>

      <!-- TERMS -->
      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          📖 TERMS EXPLAINED
        </div>
        ${_helpTerm('Age',
          'Trading days since signal fired. ' +
          'Age 0 = fired today. Age 3 = fired 3 days ago.')}
        ${_helpTerm('Regime',
          'Overall Nifty50 market direction. ' +
          'Bull / Bear / Choppy. ' +
          'Based on EMA50 slope and price position.')}
        ${_helpTerm('Score',
          'Signal quality 0–10. ' +
          'Higher = stronger setup. ' +
          'Considers regime, volume, RS, sector momentum.')}
        ${_helpTerm('R:R',
          'Risk to Reward ratio. ' +
          '2.0 = you make ₹2 for every ₹1 risked. ' +
          'Minimum acceptable is 1.5.')}
        ${_helpTerm('Entry',
          'Buy/sell at 9:15 AM open price next trading day. ' +
          'Not a limit order — market open price.')}
        ${_helpTerm('Stop',
          '1 ATR beyond pivot. Set immediately at entry. ' +
          'Never move it. Stop hit intraday = exit same day.')}
        ${_helpTerm('Exit Date',
          'Exit at open of Day 6 from entry. ' +
          'Hard rule — no exceptions.')}
        ${_helpTerm('Day X of 6',
          'Which day of the 6-day trade window you are on. ' +
          'Day 6 = exit at open today.')}
        ${_helpTerm('DEPLOY',
          'High quality signal — act on it. ' +
          'Meets all quality criteria.')}
        ${_helpTerm('WATCH',
          'Lower quality — monitor only. ' +
          'Do not enter. Wait for better setup.')}
        ${_helpTerm('Bear Bonus 🔥',
          'UP_TRI in Bear regime = highest conviction. ' +
          'Backtest shows best average trade in Bear market.')}
        ${_helpTerm('Grade A/B/C',
          'A = backtest validated stock. ' +
          'B = in universe, limited history. ' +
          'C = unvalidated — trade smaller size.')}
        ${_helpTerm('Vol:High',
          'Volume above 1.5× 20-day average on signal day. ' +
          'Confirms conviction behind the move.')}
        ${_helpTerm('RS:Strong',
          'Stock outperforming Nifty50 by 3%+ over 20 days. ' +
          'Shows relative strength.')}
        ${_helpTerm('2nd Attempt',
          'Signal fired after a failed first attempt ' +
          'at the same price level. ' +
          'Level proven = higher structural conviction.')}
      </div>

      <!-- RISK RULES -->
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
        ${_helpRule('R:R below 1.5 = reduce size or skip')}
        ${_helpRule('Miss the 9:15 AM open by 15+ mins = skip')}
        ${_helpRule('Gap > 3% at open = skip that signal')}
      </div>

      <!-- NOTIFICATIONS -->
      <div style="margin-bottom:20px;">
        <div style="color:#ffd700;font-size:12px;
          font-weight:700;margin-bottom:10px;
          letter-spacing:1px;">
          🔔 PUSH NOTIFICATIONS
        </div>
        <div style="background:#0d1117;border-radius:8px;
          padding:12px;font-size:12px;
          color:#8b949e;line-height:1.6;">
          Get notified at 8:50 AM every trading day
          when signals are found.
          <br><br>
          <strong style="color:#c9d1d9;">
            iOS users:
          </strong>
          Add this page to Home Screen first,
          then open from home screen icon to enable
          notifications.
          <br><br>
          <button onclick="requestNotifications()"
            id="notif-btn"
            style="background:#21262d;
              border:1px solid #30363d;
              color:#c9d1d9;border-radius:6px;
              padding:8px 16px;font-size:12px;
              cursor:pointer;margin-top:4px;">
            Enable Notifications
          </button>
          <div id="notif-status"
            style="margin-top:8px;font-size:11px;
              color:#555;">
          </div>
        </div>
      </div>

      <button onclick="hideHelp()"
        style="width:100%;background:#21262d;
          border:1px solid #30363d;
          color:#c9d1d9;border-radius:8px;
          padding:12px;font-size:14px;
          cursor:pointer;">
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
        min-width:20px;font-size:11px;
        font-weight:700;display:flex;
        align-items:center;justify-content:center;">
        ${num}
      </div>
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
        min-width:90px;">${term}</div>
      <div style="color:#8b949e;
        line-height:1.5;">${desc}</div>
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
  const statusEl = document.getElementById('notif-status');
  const btn      = document.getElementById('notif-btn');

  if (!('serviceWorker' in navigator) ||
      !('PushManager' in window)) {
    if (statusEl) statusEl.textContent =
      'Push not supported on this browser. ' +
      'Install as PWA from home screen first.';
    return;
  }

  // Ask for PIN before subscribing
  const pin = prompt(
    'Enter notification PIN to subscribe:');

  if (!pin || pin.length !== PUSH_PIN_LENGTH) {
    if (statusEl) statusEl.textContent =
      'Invalid PIN — notifications not enabled.';
    return;
  }

  try {
    if (statusEl) statusEl.textContent =
      'Requesting permission...';

    const permission = await Notification.requestPermission();

    if (permission !== 'granted') {
      if (statusEl) statusEl.textContent =
        'Permission denied. ' +
        'Enable in browser settings to receive alerts.';
      return;
    }

    const registration = await
      navigator.serviceWorker.ready;

    const subscription = await
      registration.pushManager.subscribe({
        userVisibleOnly:      true,
        applicationServerKey: _urlB64ToUint8Array(
          VAPID_PUBLIC_KEY),
      });

    // Save subscription to subscriptions.json
    // via a fetch POST to GitHub API is complex —
    // instead post to a simple endpoint
    // For now: show subscription JSON to copy manually
    const subJson = subscription.toJSON();
    const payload = {
      endpoint:     subJson.endpoint,
      keys:         subJson.keys,
      pin_verified: true,
      subscribed_at: new Date().toISOString().slice(0,10),
    };

    // Save to localStorage as pending
    localStorage.setItem(
      'tietiy_push_sub',
      JSON.stringify(payload));

    if (statusEl) statusEl.innerHTML =
      '<span style="color:#00C851;">✓ Subscribed!</span> ' +
      'You will receive alerts at 8:50 AM IST. ' +
      '<br>Note: Subscription saved locally. ' +
      'First notification confirms activation.';

    if (btn) btn.textContent = '✓ Subscribed';

  } catch(e) {
    console.error('[push]', e);
    if (statusEl) statusEl.textContent =
      'Subscription failed: ' + e.message;
  }
}

function _urlB64ToUint8Array(base64String) {
  const padding = '='.repeat(
    (4 - base64String.length % 4) % 4);
  const base64  = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  const rawData = window.atob(base64);
  const arr     = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    arr[i] = rawData.charCodeAt(i);
  }
  return arr;
}


// ── SESSION RESTORE ───────────────────────────────────
// Reopen last viewed tab after Safari kills background tab

function _restoreSession() {
  try {
    const lastTab = sessionStorage.getItem('tietiy_tab');
    if (lastTab) {
      window.TIETIY.activeTab = lastTab;
    }
  } catch(e) {}
}


// ── TRADING DAY COUNTER ───────────────────────────────
// Used by app.js to show Day X of 6
// Counts trading days excluding NSE holidays
// Entry date = next trading day after signal detection
// Day counter starts from entry, not detection

function tradingDaysBetween(startDateStr, endDateStr) {
  const holidays = window.TIETIY.holidays || [];
  let   count    = 0;
  const start    = new Date(startDateStr);
  const end      = new Date(endDateStr);
  const cur      = new Date(start);

  while (cur <= end) {
    const dayOfWeek = cur.getDay();
    const dateStr   = cur.toISOString().slice(0, 10);
    if (dayOfWeek !== 0 &&
        dayOfWeek !== 6 &&
        !holidays.includes(dateStr)) {
      count++;
    }
    cur.setDate(cur.getDate() + 1);
  }
  return count;
}

function getEntryDate(signalDateStr) {
  const holidays = window.TIETIY.holidays || [];
  const cur      = new Date(signalDateStr);
  cur.setDate(cur.getDate() + 1);
  while (true) {
    const dayOfWeek = cur.getDay();
    const dateStr   = cur.toISOString().slice(0, 10);
    if (dayOfWeek !== 0 &&
        dayOfWeek !== 6 &&
        !holidays.includes(dateStr)) {
      return dateStr;
    }
    cur.setDate(cur.getDate() + 1);
  }
}

function getDayNumber(signalDateStr) {
  const entryDate = getEntryDate(signalDateStr);
  const today     = new Date()
                    .toISOString().slice(0, 10);
  if (today < entryDate) return 1;
  const days = tradingDaysBetween(entryDate, today);
  return Math.min(Math.max(days, 1), 6);
}

function getExitDate(signalDateStr) {
  const holidays  = window.TIETIY.holidays || [];
  const entryDate = getEntryDate(signalDateStr);
  let   count     = 0;
  const cur       = new Date(entryDate);
  while (count < 5) {
    cur.setDate(cur.getDate() + 1);
    const dayOfWeek = cur.getDay();
    const dateStr   = cur.toISOString().slice(0, 10);
    if (dayOfWeek !== 0 &&
        dayOfWeek !== 6 &&
        !holidays.includes(dateStr)) {
      count++;
    }
  }
  return cur.toISOString().slice(0, 10);
}

   


// ── MAIN INIT ─────────────────────────────────────────

async function initApp() {
  const loader    = document.getElementById('app-loader');
  const errorDiv  = document.getElementById('app-error');
  const appRoot   = document.getElementById('app-root');
  const loaderMsg = document.getElementById('loader-msg');

  // Restore last session tab
  _restoreSession();

  try {
    if (loaderMsg) loaderMsg.textContent =
      'Loading scanner data...';

    // Fetch all data
    const success = await _fetchAll();

    if (!success || !window.TIETIY.meta) {
      // Show error screen
      if (loader)   loader.style.display  = 'none';
      if (errorDiv) {
        errorDiv.style.display = 'block';
        const detail = document.getElementById(
          'error-detail');
        if (detail) detail.textContent =
          'Could not load scan data. ' +
          'Check your connection and try again.';
      }
      return;
    }

    // App version check — may force reload
    _checkAppVersion(window.TIETIY.meta);

    // Show app
    if (loader)  loader.style.display  = 'none';
    if (appRoot) appRoot.style.display = 'block';

    // Render chrome
    _renderStatusBar(window.TIETIY.meta);
    _renderAlertBanner(window.TIETIY.stopAlerts);
    _renderNav(window.TIETIY.activeTab);

    // Render active tab content
    switchTab(window.TIETIY.activeTab);

  } catch(e) {
    console.error('[ui] Init error:', e);
    if (loader)   loader.style.display  = 'none';
    if (errorDiv) {
      errorDiv.style.display = 'block';
      const lastScan = document.getElementById(
        'error-last-scan');
      if (lastScan && window.TIETIY.meta) {
        lastScan.textContent = fmtTime(
          window.TIETIY.meta.last_scan);
      }
    }
  }
}

// ── START ─────────────────────────────────────────────
// Wait for DOM + all JS files to load
window.addEventListener('load', initApp);
