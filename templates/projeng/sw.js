// Projeng service worker is intentionally disabled.
// If an older SW is still installed, this script unregisters it.
self.addEventListener("install", () => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        self.registration.unregister().then(() => {
            return self.clients.matchAll({ type: "window" }).then((clients) => {
                clients.forEach((client) => client.navigate(client.url));
            });
        })
    );
});

self.addEventListener("fetch", () => {
    // No interception.
});
