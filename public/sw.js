// Service worker mínimo: hace la app instalable. Siempre va a la red,
// así nunca ves datos viejos. (Modo sin conexión: fase 4 del roadmap.)
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
