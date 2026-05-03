// OmniHub Service Worker — push notifications + minimal asset cache.
const CACHE_VERSION = 'omnihub-v2';
const STATIC_ASSETS = ['/', '/manifest.json', '/favicon.ico'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network-first for API; cache-first for static (no fetch override on /api/*)
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/ws')) return;
  if (!STATIC_ASSETS.includes(url.pathname) && !url.pathname.match(/\.(png|jpg|jpeg|svg|ico|woff2?)$/)) return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request).then((res) => {
        if (res && res.status === 200 && res.type === 'basic') {
          const clone = res.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(event.request, clone)).catch(() => {});
        }
        return res;
      }).catch(() => cached);
      return cached || network;
    })
  );
});

// ----------------------- Push notifications -------------------------------
self.addEventListener('push', function (event) {
  let data = {};
  try {
    data = event.data.json();
  } catch (e) {
    data = {
      title: 'OmniHub',
      body: event.data ? event.data.text() : 'Yeni bildiriminiz var',
    };
  }

  const isGuestNotif = data.data?.type === 'status_change';
  const tag = isGuestNotif
    ? `guest-${data.data.service_type}-${data.data.status}`
    : (data.tag || 'omnihub-notification');

  const options = {
    body: data.body || 'Yeni bildiriminiz var',
    icon: data.icon || '/logo192.png',
    badge: data.badge || '/logo192.png',
    data: data.data || {},
    vibrate: [200, 100, 200],
    tag: tag,
    renotify: true,
    requireInteraction: isGuestNotif,
    actions: [
      { action: 'open', title: 'Ayrıntılar' },
      { action: 'dismiss', title: 'Kapat' },
    ],
  };

  event.waitUntil(self.registration.showNotification(data.title || 'OmniHub', options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  if (event.action === 'dismiss') return;

  const notifData = event.notification.data || {};
  const urlToOpen = notifData.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (list) {
      for (let i = 0; i < list.length; i++) {
        const c = list[i];
        if (c.url.includes(self.location.origin) && 'focus' in c) {
          c.postMessage({ type: 'NOTIFICATION_CLICKED', data: notifData });
          return c.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(urlToOpen);
    })
  );
});
