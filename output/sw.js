// ── sw.js ────────────────────────────────────────────
// Service Worker for TIE TIY Scanner
//
// V1 FIXES: L4, R3 (offline support, network state)
//
// V2 FIXES:
// - SW1 (v6): cache version bump for stale layout
//
// PHASE 2 SESSION 2 FIXES:
// - SW1 (v8): Data JSON files are NEVER SW-cached.
//   signal_history.json, meta.json, open_prices.json,
//   eod_prices.json, ltp.json, patterns.json,
//   system_health.json — all fetched with
//   cache: 'no-store' and a cache-bust query param.
//   This permanently eliminates "I refreshed but Stats
//   still shows old numbers" problem.
//
// - SW2: On activate, SW messages all clients with
//   type: 'DATA_REFRESH'. app.js/stats.js listen for
//   this and force-reload their JSON data. No more
//   manual SW version bumps to push data changes.
//
// - Cache version bumped v7 → v8 (one-time reinstall
//   to deploy these fixes; after this, data staleness
//   stops being a cache version problem).
// ─────────────────────────────────────────────────────

const CACHE_VERSION = 'v8';
const CACHE_NAME    = 'tietiy-shell-' + CACHE_VERSION;

const SHELL_FILES = [
  '/tietiy-scanner/',
  '/tietiy-scanner/index.html',
  '/tietiy-scanner/manifest.json',
  '/tietiy-scanner/icon-192.png',
  '/tietiy-scanner/icon-512.png',
  '/tietiy-scanner/badge-72.png',
  '/tietiy-scanner/ui.js',
  '/tietiy-scanner/app.js',
  '/tietiy-scanner/journal.js',
  '/tietiy-scanner/stats.js',
];

// SW1: Data JSON files — NEVER cached at SW level
// These files change multiple times per day via workflows.
// Treating them as regular JSON caused the Apr 18 stale
// Stats display bug. Always fetch fresh.
const DATA_JSON_PATTERNS = [
  'signal_history.json',
  'meta.json',
  'open_prices.json',
  'eod_prices.json',
  'ltp.json',
  'patterns.json',
  'system_health.json',
  'stop_alerts.json',
];

function _isDataJson(url) {
  return DATA_JSON_PATTERNS.some(function(pattern) {
    return url.indexOf(pattern) !== -1;
  });
}

// R3: track last known network state
let _lastNetworkOk = true;


// ── R3: BROADCAST NETWORK STATE ───────────────────────
function _broadcastNetworkState(isOnline) {
  if (isOnline === _lastNetworkOk) return;
  _lastNetworkOk = isOnline;

  const msg = { type: isOnline ? 'ONLINE' : 'OFFLINE' };

  self.clients.matchAll({
    includeUncontrolled: true,
    type: 'window',
  }).then(function(clients) {
    clients.forEach(function(client) {
      client.postMessage(msg);
    });
  });
}


// ── SW2: BROADCAST DATA REFRESH ───────────────────────
function _broadcastDataRefresh() {
  const msg = {
    type: 'DATA_REFRESH',
    version: CACHE_VERSION,
    timestamp: Date.now(),
  };

  self.clients.matchAll({
    includeUncontrolled: true,
    type: 'window',
  }).then(function(clients) {
    console.log('[SW] Broadcasting DATA_REFRESH to',
                clients.length, 'clients');
    clients.forEach(function(client) {
      client.postMessage(msg);
    });
  });
}


// ── HELPERS ───────────────────────────────────────────
function _isCacheable(response) {
  return response && response.status === 200;
}

function _offlineHTML() {
  return new Response(
    `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TIE TIY — Offline</title>
<style>
  body { background:#07070f; color:#c9d1d9;
    font-family:system-ui,sans-serif;
    display:flex; align-items:center;
    justify-content:center; min-height:100vh;
    margin:0; text-align:center; padding:20px; }
  h1 { color:#ffd700; font-size:24px; margin-bottom:12px; }
  p  { color:#8b949e; font-size:14px; line-height:1.6; }
  button {
    margin-top:20px; background:#21262d;
    border:1px solid #30363d; color:#c9d1d9;
    border-radius:8px; padding:10px 24px;
    font-size:14px; cursor:pointer; }
</style>
</head>
<body>
  <div>
    <h1>📵 TIE TIY</h1>
    <p>You're offline.<br>
       Cached data is shown when available.</p>
    <button onclick="location.reload()">
      Retry
    </button>
  </div>
</body>
</html>`,
    { headers: { 'Content-Type': 'text/html' } }
  );
}

function _offlineJS() {
  return new Response(
    '// TIE TIY — offline placeholder',
    { headers: { 'Content-Type':
      'application/javascript' }}
  );
}


// ── INSTALL ───────────────────────────────────────────
self.addEventListener('install', function(event) {
  console.log('[SW] Installing ' + CACHE_VERSION + '...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('[SW] Caching shell + JS files');
        return cache.addAll(SHELL_FILES);
      })
      .then(function() {
        return self.skipWaiting();
      })
      .catch(function(err) {
        console.warn('[SW] Cache install partial:', err);
        return self.skipWaiting();
      })
  );
});


// ── ACTIVATE ──────────────────────────────────────────
self.addEventListener('activate', function(event) {
  console.log('[SW] Activating ' + CACHE_VERSION + '...');
  event.waitUntil(
    caches.keys()
      .then(function(cacheNames) {
        return Promise.all(
          cacheNames
            .filter(function(name) {
              return name !== CACHE_NAME;
            })
            .map(function(name) {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(function() {
        return self.clients.claim();
      })
      .then(function() {
        // SW2: Tell all clients to reload their data JSONs.
        // New SW is now in charge, any stale in-memory data
        // should be refreshed.
        _broadcastDataRefresh();
      })
  );
});


// ── FETCH ─────────────────────────────────────────────
self.addEventListener('fetch', function(event) {
  const url = event.request.url;

  if (event.request.method !== 'GET') return;

  // ── SW1: DATA JSON FILES — BYPASS ALL CACHES ──────
  // signal_history.json, meta.json, open_prices.json, etc.
  // These change multiple times per day. Never cache.
  if (_isDataJson(url)) {
    // Build cache-busted request
    const urlObj = new URL(url);
    urlObj.searchParams.set('sw', Date.now().toString());

    const freshRequest = new Request(urlObj.toString(), {
      method:       'GET',
      headers:      event.request.headers,
      credentials:  event.request.credentials,
      cache:        'no-store',
      mode:         'cors',
    });

    event.respondWith(
      fetch(freshRequest, { cache: 'no-store' })
        .then(function(response) {
          if (_isCacheable(response)) {
            _broadcastNetworkState(true);
          }
          return response;
        })
        .catch(function() {
          _broadcastNetworkState(false);
          // No fallback — fail fast so client knows
          // it needs to handle offline state
          return new Response(
            JSON.stringify({
              error: 'offline',
              sw_cache_bypass: true
            }),
            {
              status: 503,
              headers: {
                'Content-Type': 'application/json'
              }
            }
          );
        })
    );
    return;
  }

  // ── JS FILES — NETWORK FIRST + CACHE FALLBACK ─────
  if (url.includes('.js')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (_isCacheable(response)) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
            _broadcastNetworkState(true);
          }
          return response;
        })
        .catch(function() {
          _broadcastNetworkState(false);
          return caches.match(event.request)
            .then(function(cached) {
              return cached || _offlineJS();
            });
        })
    );
    return;
  }

  // ── OTHER JSON (not data) — NETWORK FIRST ─────────
  // Catches things like external JSON requests.
  if (url.includes('.json')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (_isCacheable(response)) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
            _broadcastNetworkState(true);
          }
          return response;
        })
        .catch(function() {
          _broadcastNetworkState(false);
          return caches.match(event.request)
            .then(function(cached) {
              return cached || new Response(
                '{"error":"offline"}',
                { headers: {
                  'Content-Type': 'application/json'
                }}
              );
            });
        })
    );
    return;
  }

  // ── CSS FILES — NETWORK FIRST + CACHE FALLBACK ────
  if (url.includes('.css')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (_isCacheable(response)) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
          }
          return response;
        })
        .catch(function() {
          return caches.match(event.request)
            .then(function(cached) {
              return cached || new Response(
                '', { headers: {
                  'Content-Type': 'text/css'
                }}
              );
            });
        })
    );
    return;
  }

  // ── HTML + ICONS — CACHE FIRST ────────────────────
  event.respondWith(
    caches.match(event.request)
      .then(function(cached) {
        const networkFetch = fetch(event.request)
          .then(function(response) {
            if (_isCacheable(response)) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then(function(cache) {
                cache.put(event.request, clone);
              });
              _broadcastNetworkState(true);
            }
            return response;
          })
          .catch(function() {
            _broadcastNetworkState(false);
            return null;
          });

        if (cached) return cached;

        return networkFetch.then(function(response) {
          if (!response) {
            const isHTML = event.request.headers.get(
              'Accept') || '';
            if (isHTML.includes('text/html')) {
              return _offlineHTML();
            }
          }
          return response;
        });
      })
  );
});


// ── R3: MESSAGE FROM CLIENT ───────────────────────────
self.addEventListener('message', function(event) {
  if (!event.data) return;

  if (event.data.type === 'PROBE_NETWORK') {
    fetch('/tietiy-scanner/meta.json?probe=' + Date.now(),
          { cache: 'no-store' })
      .then(function() {
        _broadcastNetworkState(true);
      })
      .catch(function() {
        _broadcastNetworkState(false);
      });
  }

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  // SW2: Client can request a manual data refresh
  if (event.data.type === 'REQUEST_DATA_REFRESH') {
    _broadcastDataRefresh();
  }
});


// ── PUSH NOTIFICATION RECEIVED ────────────────────────
self.addEventListener('push', function(event) {
  console.log('[SW] Push received');

  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch(e) {
    payload = {
      title: 'TIE TIY Scanner',
      body:  event.data
        ? event.data.text()
        : 'New scan available',
    };
  }

  const title   = payload.title  || 'TIE TIY Scanner';
  const options = {
    body:     payload.body    || 'New signals available',
    icon:     payload.icon    || '/tietiy-scanner/icon-192.png',
    badge:    payload.badge   || '/tietiy-scanner/badge-72.png',
    tag:      payload.tag     || 'tietiy-scan',
    renotify: payload.renotify !== false,
    data:     payload.data    || {},
    actions: [
      { action: 'open',    title: 'View Signals' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    vibrate: [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});


// ── NOTIFICATION CLICK ────────────────────────────────
self.addEventListener('notificationclick', function(event) {
  console.log('[SW] Notification clicked:', event.action);

  event.notification.close();

  if (event.action === 'dismiss') return;

  const targetUrl = '/tietiy-scanner/';

  event.waitUntil(
    clients.matchAll({
      type:                'window',
      includeUncontrolled: true,
    })
    .then(function(windowClients) {
      for (let client of windowClients) {
        if (client.url.includes('tietiy-scanner') &&
            'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});


// ── PUSH SUBSCRIPTION CHANGE ──────────────────────────
self.addEventListener('pushsubscriptionchange',
  function(event) {
    console.log('[SW] Push subscription changed');
    event.waitUntil(
      self.registration.pushManager.subscribe(
        event.oldSubscription.options
      )
      .then(function(subscription) {
        return self.clients.matchAll()
          .then(function(clients) {
            clients.forEach(function(client) {
              client.postMessage({
                type:         'SUBSCRIPTION_UPDATED',
                subscription: subscription.toJSON(),
              });
            });
          });
      })
    );
  }
);
