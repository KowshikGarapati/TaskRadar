self.addEventListener("push", function (event) {
    console.log("📩 Push received:", event);

    let data = {};
    try {
        // Try parsing JSON
        data = event.data ? event.data.json() : {};
    } catch (e) {
        // If not JSON, fall back to text
        data = {
            head: "Notification",
            body: event.data ? event.data.text() : "You have a new alert.",
            icon: "/static/icons/bell.png"
        };
    }

    const title = data.title || data.head || "Notification";
    const options = {
        body: data.body || "You have a new alert.",
        icon: data.icon || "/static/icons/bell.png"
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow("/") // 👈 redirect user to homepage (customize if needed)
    );
});
