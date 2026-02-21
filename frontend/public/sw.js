// Service Worker for Push Notifications

self.addEventListener('push', function(event) {
  let data = {};
  try {
    data = event.data.json();
  } catch(e) {
    data = {
      title: 'Hotel Notification',
      body: event.data ? event.data.text() : 'You have a new notification',
    };
  }

  const options = {
    body: data.body || 'Yeni bildiriminiz var',
    icon: data.icon || '/logo192.png',
    badge: data.badge || '/logo192.png',
    data: data.data || {},
    vibrate: [100, 50, 100],
    tag: data.tag || 'hotel-notification',
    renotify: true,
    actions: [
      { action: 'open', title: 'Ac' },
      { action: 'dismiss', title: 'Kapat' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Hotel Notification', options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

self.addEventListener('install', function(event) {
  self.skipWaiting();
});

self.addEventListener('activate', function(event) {
  event.waitUntil(clients.claim());
});
