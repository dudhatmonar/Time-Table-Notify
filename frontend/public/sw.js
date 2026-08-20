// Service Worker for Timetable Web Push Notifications

self.addEventListener('push', function(event) {
  if (!event.data) {
    console.log('Push event received with no payload.');
    return;
  }

  try {
    const data = event.data.json();
    const title = data.title || '🔔 Timetable Alert';
    
    // Create standard notification options
    const options = {
      body: data.body || 'No details provided.',
      // High-resolution vector data URI for an icon (bell icon)
      icon: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%234f46e5" width="48" height="48"><path d="M12 22a2.98 2.98 0 0 0 2.818-2H9.182A2.98 2.98 0 0 0 12 22zm7-6v-5a7 7 0 0 0-5-6.72V4a2 2 0 0 0-4 0v.28A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2z"/></svg>',
      badge: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%234f46e5" width="24" height="24"><path d="M12 22a2.98 2.98 0 0 0 2.818-2H9.182A2.98 2.98 0 0 0 12 22zm7-6v-5a7 7 0 0 0-5-6.72V4a2 2 0 0 0-4 0v.28A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2z"/></svg>',
      vibrate: [200, 100, 200], // Vibration pattern on mobile devices
      data: {
        url: '/',
        room: data.room,
        subject_code: data.subject_code,
        event_type: data.event_type
      },
      actions: [
        {
          action: 'open',
          title: 'View Timetable'
        }
      ],
      tag: 'timetable-notification', // Replaces existing notification of same type
      requireInteraction: true // Keeps notification visible until user interacts with it
    };

    event.waitUntil(
      self.registration.showNotification(title, options)
    );
  } catch (e) {
    console.error('Error parsing push data:', e);
    
    // Fallback if data is not JSON
    const text = event.data.text();
    event.waitUntil(
      self.registration.showNotification('🔔 Timetable Update', {
        body: text,
        vibrate: [100, 50, 100]
      })
    );
  }
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  // Handle action click or notification body click
  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then(function(clientList) {
      // If a tab is already open, focus it
      for (let i = 0; i < clientList.length; i++) {
        let client = clientList[i];
        if (client.url && 'focus' in client) {
          return client.focus();
        }
      }
      // Otherwise, open a new tab
      if (clients.openWindow) {
        return clients.openWindow('/');
      }
    })
  );
});
