// ── sw.js ────────────────────────────────────────────
// Service Worker for TIE TIY Scanner
//
// V1 FIXES APPLIED:
// - L4  : Offline caching strategy improved
//         JS files now network-first + cache fallback
//         (was never-cached → broke app offline entirely)
//         JS added to install-time shell cache
//         Cache name bumped to v2 for clean reinstall
// - R3  : SW-side offline support
//         _broadcastNetworkState() posts OFFLINE/ONLINE
//         messages to all clients on fetch failure/recovery
//         Offline fallback HTML when shell unavailable
//
// CACHING STRATEGY (updated):
// JS files    → Network first, cache fallback (L4 fix)
// JSON files  → Network first, cache as fallback
// HTML/icons  → Cache first for offline support
// CSS files   → Network first, cache fallback
//
// Network state:
// Fetch failure → broadcast OFFLINE to all clients
// Fetch success after failure → broadcast ONLINE
// ─────────────────────────────────────────────────────

const CACHE_NAME = 'tietiy-shell-v5';
// Bumped v1→v2: JS files now included in cache scope

const SHELL_FILES = [
  '/tietiy-scanner/',
  '/tietiy-scanner/index.html',
  '/tietiy-scanner/manifest.json',
  '/tietiy-scanner/icon-192.png',
  '/tietiy-scanner/icon-512.png',
  '/tietiy-scanner/badge-72.png',
  // L4: JS files cached at install for offline support
  '/tietiy-scanner/ui.js',
  '/tietiy-scanner/app.js',
  '/tietiy-scanner/journal.js',
  '/tietiy-scanner/stats.js',
];

// R3: track last known network state
let _lastNetworkOk = true;


// ── R3: BROADCAST NETWORK STATE ───────────────────────
// Posts {type:'OFFLINE'} or {type:'ONLINE'} to all
// controlled clients so ui.js can show/hide the banner.
function _broadcastNetworkState(isOnline) {
  if (isOnline === _lastNetworkOk) return; // no change
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


// ── HELPERS ───────────────────────────────────────────
function _isCacheable(response) {
  // Never cache opaque responses (cross-origin, status 0)
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
  console.log('[SW] Installing v2...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('[SW] Caching shell + JS files');
        // L4: JS files included in install cache
        return cache.addAll(SHELL_FILES);
      })
      .then(function() {
        return self.skipWaiting();
      })
      .catch(function(err) {
        // Non-fatal: proceed even if some assets missing
        console.warn('[SW] Cache install partial:', err);
        return self.skipWaiting();
      })
  );
});


// ── ACTIVATE ──────────────────────────────────────────
self.addEventListener('activate', function(event) {
  console.log('[SW] Activating v2...');
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
  );
});


// ── FETCH ─────────────────────────────────────────────
self.addEventListener('fetch', function(event) {
  const url = event.request.url;

  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  // ── JS FILES — NETWORK FIRST + CACHE FALLBACK ─────
  // L4 FIX: was never-cached (broke offline entirely).
  // Now: try network first for freshness, fall back to
  // cached version if offline. Cache updated on success.
  if (url.includes('.js')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (_isCacheable(response)) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
            _broadcastNetworkState(true);   // R3
          }
          return response;
        })
        .catch(function() {
          _broadcastNetworkState(false);    // R3
          return caches.match(event.request)
            .then(function(cached) {
              return cached || _offlineJS();
            });
        })
    );
    return;
  }

  // ── JSON FILES — NETWORK FIRST + CACHE FALLBACK ───
  // Try network for fresh data every time.
  // Cache updated on success.
  // Falls back to last cached version if offline.
  if (url.includes('.json')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (_isCacheable(response)) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
            _broadcastNetworkState(true);   // R3
          }
          return response;
        })
        .catch(function() {
          _broadcastNetworkState(false);    // R3
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
  // Shell loads instantly from cache.
  // Network fetch updates cache in background.
  // R3: offline fallback HTML if nothing cached.
  event.respondWith(
    caches.match(event.request)
      .then(function(cached) {
        // Serve cached immediately, refresh in background
        const networkFetch = fetch(event.request)
          .then(function(response) {
            if (_isCacheable(response)) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then(function(cache) {
                cache.put(event.request, clone);
              });
              _broadcastNetworkState(true);  // R3
            }
            return response;
          })
          .catch(function() {
            _broadcastNetworkState(false);   // R3
            return null;
          });

        if (cached) return cached;

        // Nothing cached — must wait for network
        return networkFetch.then(function(response) {
          // R3: offline fallback for HTML requests
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
// Client can ask SW to attempt a network probe
// to verify connectivity (used on manual refresh).
self.addEventListener('message', function(event) {
  if (!event.data) return;

  if (event.data.type === 'PROBE_NETWORK') {
    // Lightweight probe — fetch meta.json
    fetch('/tietiy-scanner/meta.json?probe=' + Date.now())
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
