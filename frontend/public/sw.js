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

  const isGuestNotif = data.data?.type === 'status_change';
  const tag = isGuestNotif
    ? `guest-${data.data.service_type}-${data.data.status}`
    : (data.tag || 'hotel-notification');

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

  event.waitUntil(
    self.registration.showNotification(data.title || 'Hotel Notification', options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const notifData = event.notification.data || {};
  let urlToOpen = '/';

  if (notifData.type === 'status_change' && notifData.room_code) {
    urlToOpen = notifData.url || '/';
  } else if (notifData.url) {
    urlToOpen = notifData.url;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.postMessage({ type: 'NOTIFICATION_CLICKED', data: notifData });
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
