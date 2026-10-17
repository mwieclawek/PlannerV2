// Scripts for firebase and firebase messaging
importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js");

// Initialize Firebase app in the service worker with production config
firebase.initializeApp({
  apiKey: "AIzaSyBzP9MzJHrPihaq7P20vpWMdAf_6IJ93qI",
  appId: "1:357153331477:web:3593c50a84a8e0c7ba711c",
  messagingSenderId: "357153331477",
  projectId: "planista-e31fe",
  authDomain: "planista-e31fe.firebaseapp.com",
  storageBucket: "planista-e31fe.firebasestorage.app",
  measurementId: "G-HKRM635THK",
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log('[firebase-messaging-sw.js] Received background message:', payload);
  // If the FCM payload already contains a standard `notification` object,
  // the browser / Firebase SDK displays it automatically unless we deduplicate by tag.
  const notificationTitle =
    payload.notification?.title || payload.data?.title || 'Planista';
  const notificationOptions = {
    body: payload.notification?.body || payload.data?.body || '',
    icon: payload.notification?.icon || '/icons/Icon-192.png',
    badge: '/icons/Icon-192.png',
    tag: payload.data?.tag || 'plannerv2-push',
    renotify: false,
    data: payload.data || {},
  };

  if (payload.notification) {
    // Let the browser replace any auto-displayed notification with the same tag, or skip if already shown
    return self.registration.showNotification(notificationTitle, notificationOptions);
  }

  return self.registration.showNotification(notificationTitle, notificationOptions);
});

self.addEventListener('notificationclick', (event) => {
  console.log('[firebase-messaging-sw.js] Notification click received:', event);
  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow('/');
      }
    })
  );
});
