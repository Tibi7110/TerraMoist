// TerraMoist Service Worker — handles push notifications and offline caching.

const CACHE = "terramoist-v1";
const PRECACHE = ["/", "/index.html"];

// ── Install: pre-cache shell ──────────────────────────────────────────────
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE))
  );
  self.skipWaiting();
});

// ── Activate: clean old caches ────────────────────────────────────────────
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── Fetch: network-first, fallback to cache ───────────────────────────────
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const clone = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

// ── Push: show notification ───────────────────────────────────────────────
self.addEventListener("push", (e) => {
  const data = e.data?.json() ?? {};
  const title = data.title ?? "TerraMoist Alert";
  const options = {
    body: data.body ?? "Check your field moisture status.",
    icon: "/favicon.svg",
    badge: "/favicon.svg",
    tag: "terramoist-irrigation",   // replaces previous notification
    renotify: true,
    data: { url: data.url ?? "/" },
    actions: [
      { action: "open",   title: "View Map" },
      { action: "dismiss", title: "Dismiss" },
    ],
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

// ── Notification click ────────────────────────────────────────────────────
self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  if (e.action === "dismiss") return;
  const target = e.notification.data?.url ?? "/";
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
      const existing = cs.find((c) => c.url.includes(self.location.origin));
      if (existing) return existing.focus();
      return clients.openWindow(target);
    })
  );
});
