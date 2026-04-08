const CACHE_NAME = 'matchiq-v2';
const ASSETS = ['/app'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});

// Push Notification
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  const title = data.title || 'MatchIQ';
  const options = {
    body: data.body || 'Nuovo aggiornamento disponibile',
    icon: '/logo.png',
    badge: '/logo.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/app#home' },
    actions: data.actions || []
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/app#home';
  e.waitUntil(
    clients.matchAll({type: 'window'}).then(list => {
      for (const client of list) {
        if (client.url.includes('/app') && 'focus' in client) return client.focus();
      }
      return clients.openWindow(url);
    })
  );
});
