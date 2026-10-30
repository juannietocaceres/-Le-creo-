// Service worker mínimo: permite instalar la página. No guarda nada en caché:
// el análisis siempre va al servidor y los mensajes no quedan en el celular.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
