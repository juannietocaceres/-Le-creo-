"""Servidor de "Compartir con ¿Le creo?": página instalable (PWA) + API de análisis.

Uso:  python ui\\compartir.py            (http://localhost:8600)

Android muestra la página en el menú Compartir gracias al share_target del manifiesto;
WhatsApp envía el texto por POST a /compartir. El texto nunca viaja en la URL ni se
escribe en registros (regla 3): en consola solo aparecen la ruta y el semáforo.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict, deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import agente, reglas, respuesta, trazas

WEB = Path(__file__).parent / "web"
MAX_CUERPO = 16_000           # bytes; un mensaje de estafa cabe de sobra
MAX_ANALISIS_POR_MINUTO = 5

ESTATICOS = {
    "/manifest.webmanifest": "application/manifest+json",
    "/sw.js": "text/javascript; charset=utf-8",
    "/app.js": "text/javascript; charset=utf-8",
    "/estilos.css": "text/css; charset=utf-8",
    "/icono-192.png": "image/png",
    "/icono-512.png": "image/png",
}
SEGURIDAD = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
                               "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
VACIO = {"semaforo": "vacio", "lineas": [
    "No me llegó ningún texto.",
    "Si compartiste una foto o un audio, copia el texto del mensaje y pégalo aquí.",
]}
ESPERA = {"semaforo": "error", "lineas": [
    "Dame un minuto: estás revisando muchos mensajes seguidos.",
    "Inténtalo de nuevo en un momento.",
]}

_recientes: dict[str, deque[float]] = defaultdict(deque)


def _permitido(cliente: str, ahora: float) -> bool:
    ventana = _recientes[cliente]
    while ventana and ahora - ventana[0] > 60:
        ventana.popleft()
    if len(ventana) >= MAX_ANALISIS_POR_MINUTO:
        return False
    ventana.append(ahora)
    return True


def pagina(compartido: str | None) -> bytes:
    """index.html con el texto compartido incrustado como JSON. Se escapan <, > y &
    para que un '</script>' dentro del mensaje no pueda cerrar la etiqueta e inyectar código."""
    dato = json.dumps(compartido, ensure_ascii=False)
    dato = dato.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    marca = '<script id="compartido" type="application/json">null</script>'
    return html.replace(marca, marca.replace("null", dato)).encode("utf-8")


def analizar(texto: str) -> dict:
    texto = texto.strip()
    if not texto:
        return VACIO
    resultado = agente.analizar(texto)
    if resultado.ok and resultado.contrato is not None:
        semaforo, senales = reglas.calcular_semaforo(resultado.contrato, resultado.herramientas)
    else:
        semaforo, senales = "error", []
    try:
        trazas.registrar(resultado, semaforo, senales, tipo_entrada="texto")
    except Exception as exc:
        print(f"  (no se guardó la traza: {type(exc).__name__})")
    return respuesta.para_web(resultado, semaforo)


class Manejador(BaseHTTPRequestHandler):
    server_version = "LeCreo"
    sys_version = ""

    def log_message(self, formato: str, *args) -> None:
        # Solo método, ruta y estado. Si hay parámetros en la URL se anotan sus nombres, nunca sus valores.
        ruta, _, consulta = self.path.partition("?")
        nombres = sorted(parse_qs(consulta, keep_blank_values=True)) if consulta else []
        extra = f" (parámetros: {','.join(nombres)})" if nombres else ""
        print(f"  {self.command} {ruta}{extra} → {args[1] if len(args) > 1 else ''}")

    def _enviar(self, estado: int, cuerpo: bytes, tipo: str, cache: bool = False) -> None:
        self.send_response(estado)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "public, max-age=300" if cache else "no-store")
        for k, v in SEGURIDAD.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos: dict, estado: int = 200) -> None:
        self._enviar(estado, json.dumps(datos, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _cuerpo(self) -> bytes | None:
        largo = int(self.headers.get("Content-Length") or 0)
        if largo > MAX_CUERPO:
            self._json({"semaforo": "error", "lineas": ["El mensaje es demasiado largo para revisarlo."]},
                       HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return None
        return self.rfile.read(largo)

    def do_GET(self) -> None:
        ruta = self.path.split("?")[0]
        if ruta in ("/", "/index.html"):
            self._enviar(200, pagina(None), "text/html; charset=utf-8")
        elif ruta in ESTATICOS:
            self._enviar(200, (WEB / ruta.lstrip("/")).read_bytes(), ESTATICOS[ruta], cache=True)
        else:
            self._enviar(404, b"No encontrado", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        ruta = self.path.split("?")[0]
        cuerpo = self._cuerpo()
        if cuerpo is None:
            return
        if ruta == "/compartir":
            campos = parse_qs(cuerpo.decode("utf-8", "replace"))
            partes = [campos.get(k, [""])[0].strip() for k in ("text", "url")]
            texto = "\n".join(p for p in partes if p)
            self._enviar(200, pagina(texto), "text/html; charset=utf-8")
        elif ruta == "/api/analizar":
            try:
                texto = str(json.loads(cuerpo or b"{}").get("texto", ""))
            except (json.JSONDecodeError, AttributeError):
                self._json({"semaforo": "error", "lineas": ["No entendí la solicitud."]}, HTTPStatus.BAD_REQUEST)
                return
            if texto.strip() and not _permitido(self.client_address[0], time.monotonic()):
                self._json(ESPERA, HTTPStatus.TOO_MANY_REQUESTS)
                return
            datos = analizar(texto)
            print(f"  análisis → {datos['semaforo']}")
            self._json(datos)
        else:
            self._enviar(404, b"No encontrado", "text/plain; charset=utf-8")


class Servidor(ThreadingHTTPServer):
    # En Windows SO_REUSEADDR deja que un segundo proceso escuche el mismo puerto sin error,
    # y las peticiones caen en cualquiera de los dos (p. ej. una versión vieja).
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


def crear_servidor(puerto: int, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    return Servidor((host, puerto), Manejador)


def main() -> int:
    puerto = int(os.getenv("PUERTO_COMPARTIR", "8600"))
    servidor = crear_servidor(puerto)
    print(f"¿Le creo? (compartir) en http://localhost:{puerto} · Ctrl+C para salir")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("Servidor detenido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
