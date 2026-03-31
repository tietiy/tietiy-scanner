// ── sw.js ────────────────────────────────────────────
// Service Worker for TIE TIY Scanner
// Two responsibilities:
// 1. Web Push notification handling
// 2. Offline cache — page loads even without internet
//
// Registered by index.html on page load
// ─────────────────────────────────────────────────────

const CACHE_NAME    = 'tietiy-v2';
const CACHE_TIMEOUT = 24 * 60 * 60 * 1000; // 24 hours

// ── FILES TO CACHE FOR OFFLINE ────────────────────────
// Shell files only — JSON data always fetched fresh
const CACHE_FILES = [
  '/tietiy-scanner/',
  '/tietiy-scanner/index.html',
  '/tietiy-scanner/manifest.json',
];


// ── INSTALL ───────────────────────────────────────────
// Cache shell files on first install
self.addEventListener('install', function(event) {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('[SW] Caching shell files');
        return cache.addAll(CACHE_FILES);
      })
      .then(function() {
        // Activate immediately — don't wait for old SW
        return self.skipWaiting();
      })
      .catch(function(err) {
        console.log('[SW] Cache install failed:', err);
      })
  );
});


// ── ACTIVATE ──────────────────────────────────────────
// Clean up old caches on activation
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
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(function() {
        // Take control of all pages immediately
        return self.clients.claim();
      })
  );
});


// ── FETCH ─────────────────────────────────────────────
// Strategy:
// JSON files → Network first, cache fallback
// JS files   → Network first (always want latest)
// HTML/other → Cache first for speed
self.addEventListener('fetch', function(event) {
  const url = event.request.url;

  // JSON data files — always fetch fresh
  // Cache only as fallback if network fails
  if (url.includes('.json')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          // Clone and cache the fresh response
          const clone = response.clone();
          caches.open(CACHE_NAME)
            .then(function(cache) {
              cache.put(event.request, clone);
            });
          return response;
        })
        .catch(function() {
          // Network failed — serve from cache
          return caches.match(event.request);
        })
    );
    return;
  }

  // JS files — network first, no cache fallback
  // Always want latest JS
  if (url.includes('.js')) {
    event.respondWith(
      fetch(event.request)
        .catch(function() {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Everything else — cache first
  event.respondWith(
    caches.match(event.request)
      .then(function(cached) {
        if (cached) {
          return cached;
        }
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
// Fired when push_sender.py sends a notification
// Shows notification on device even if page is closed
self.addEventListener('push', function(event) {
  console.log('[SW] Push received');

  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch(e) {
    payload = {
      title: 'TIE TIY Scanner',
      body:  event.data ? event.data.text() : 'New scan available',
    };
  }

  const title   = payload.title  || 'TIE TIY Scanner';
  const options = {
    body:    payload.body    || 'New signals available',
    icon:    payload.icon    || '/tietiy-scanner/icon-192.png',
    badge:   payload.badge   || '/tietiy-scanner/badge-72.png',
    tag:     payload.tag     || 'tietiy-scan',
    renotify: payload.renotify !== false,
    data:    payload.data    || {},
    actions: [
      {
        action: 'open',
        title:  'View Signals',
      },
      {
        action: 'dismiss',
        title:  'Dismiss',
      }
    ],
    // Vibrate pattern for mobile
    vibrate: [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});


// ── NOTIFICATION CLICK ────────────────────────────────
// Fired when user taps the notification
// Opens or focuses the scanner page
self.addEventListener('notificationclick', function(event) {
  console.log('[SW] Notification clicked:', event.action);

  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  // Open or focus the scanner page
  const targetUrl = '/tietiy-scanner/';

  event.waitUntil(
    clients.matchAll({
      type:          'window',
      includeUncontrolled: true,
    })
    .then(function(windowClients) {
      // If page already open — focus it
      for (let client of windowClients) {
        if (client.url.includes('tietiy-scanner') &&
            'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise open new window
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});


// ── PUSH SUBSCRIPTION CHANGE ──────────────────────────
// Fired when browser auto-renews push subscription
// Saves updated token to subscriptions.json
self.addEventListener('pushsubscriptionchange',
  function(event) {
    console.log('[SW] Push subscription changed');
    event.waitUntil(
      self.registration.pushManager.subscribe(
        event.oldSubscription.options
      )
      .then(function(subscription) {
        // Send new subscription to page
        // Page will save it to subscriptions.json
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
