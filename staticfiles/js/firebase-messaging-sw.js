self.addEventListener('push', function(event) {
  let data = {};
  if (event.data) {
    data = event.data.json();
  }

  const title = data.head || "Notification";
  const options = {
    body: data.body || "You have a new alert",
    icon: "/static/icons/bell.png" // optional icon
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});
