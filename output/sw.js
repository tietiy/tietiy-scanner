// ── sw.js ────────────────────────────────────────────
// Service Worker for TIE TIY Scanner
//
// CACHING STRATEGY:
// JS files    → NEVER cached → always fresh from network
// JSON files  → Network first, cache as fallback
// HTML/icons  → Cache first for offline support
//
// This means:
// Every time you update app.js, ui.js etc
// users automatically get the new version
// No cache name bumping needed ever again
// ─────────────────────────────────────────────────────

const CACHE_NAME = 'tietiy-shell-v1';
// Shell cache name NEVER needs to change
// JS files are excluded from cache entirely

const SHELL_FILES = [
  '/tietiy-scanner/',
  '/tietiy-scanner/index.html',
  '/tietiy-scanner/manifest.json',
  '/tietiy-scanner/icon-192.png',
  '/tietiy-scanner/icon-512.png',
  '/tietiy-scanner/badge-72.png',
];


// ── INSTALL ───────────────────────────────────────────
self.addEventListener('install', function(event) {
  console.log('[SW] Installing v1...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('[SW] Caching shell files');
        // Only cache shell — never JS or JSON
        return cache.addAll(SHELL_FILES);
      })
      .then(function() {
        return self.skipWaiting();
      })
      .catch(function(err) {
        console.log('[SW] Cache install failed:', err);
      })
  );
});


// ── ACTIVATE ──────────────────────────────────────────
self.addEventListener('activate', function(event) {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys()
      .then(function(cacheNames) {
        return Promise.all(
          cacheNames
            .filter(function(name) {
              return name !== CACHE_NAME;
            })
            .map(function(name) {
              console.log('[SW] Deleting old cache:',
                name);
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

  // ── JS FILES — NEVER CACHE ────────────────────────
  // Always fetch fresh from network
  // This means updates deploy instantly
  // No cache busting needed ever
  if (url.includes('.js')) {
    event.respondWith(
      fetch(event.request)
        .catch(function() {
          // If offline and no JS — show offline message
          // gracefully rather than broken page
          return new Response(
            '// offline',
            { headers: { 'Content-Type':
              'application/javascript' }}
          );
        })
    );
    return;
  }

  // ── JSON FILES — NETWORK FIRST ────────────────────
  // Always try network first for fresh data
  // Fall back to cache if offline
  if (url.includes('.json')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          // Cache the fresh response
          const clone = response.clone();
          caches.open(CACHE_NAME)
            .then(function(cache) {
              cache.put(event.request, clone);
            });
          return response;
        })
        .catch(function() {
          return caches.match(event.request);
        })
    );
    return;
  }

  // ── HTML + ICONS — CACHE FIRST ────────────────────
  // Shell loads instantly from cache
  // Gives offline support for the app shell
  event.respondWith(
    caches.match(event.request)
      .then(function(cached) {
        if (cached) return cached;
        return fetch(event.request)
          .then(function(response) {
            const clone = response.clone();
            caches.open(CACHE_NAME)
              .then(function(cache) {
                cache.put(event.request, clone);
              });
            return response;
          });
      })
  );
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
self.addEventListener('notificationclick',
  function(event) {
    console.log('[SW] Notification clicked:',
      event.action);

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
  }
);


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
