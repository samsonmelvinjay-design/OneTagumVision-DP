{% load static %}
const CACHE_NAME = "projeng-pwa-v1";
const OFFLINE_URL = "{% url 'projeng:projeng_offline' %}";
const APP_SHELL_URLS = [
    "{% url 'projeng:projeng_dashboard' %}",
    "{% url 'projeng:projeng_my_projects' %}",
    "{% url 'projeng:projeng_map' %}",
    "{% url 'projeng:projeng_my_reports' %}",
    "{% url 'projeng:projeng_notifications' %}",
    OFFLINE_URL,
    "{% static 'img/logo-onetagumvision.png' %}"
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(APP_SHELL_URLS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) =>
            Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName !== CACHE_NAME)
                    .map((cacheName) => caches.delete(cacheName))
            )
        ).then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", (event) => {
    const request = event.request;

    if (request.method !== "GET") {
        return;
    }

    const requestUrl = new URL(request.url);
    const sameOrigin = requestUrl.origin === self.location.origin;

    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
                    return response;
                })
                .catch(() =>
                    caches.match(request).then((cachedResponse) => {
                        return cachedResponse || caches.match(OFFLINE_URL);
                    })
                )
        );
        return;
    }

    if (sameOrigin) {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }

                return fetch(request).then((response) => {
                    if (response && response.status === 200 && response.type === "basic") {
                        const responseClone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
                    }
                    return response;
                });
            })
        );
    }
});
