"""Servidor de "Compartir con ¿Le creo?": página instalable (PWA) + API de análisis.

Uso:  python ui\\compartir.py            (http://localhost:8600)

Android muestra la página en el menú Compartir gracias al share_target del manifiesto;
WhatsApp envía el texto o la captura por POST a /compartir. Nada de lo compartido viaja en
la URL ni se escribe en registros (regla 3): en consola solo aparecen la ruta y el semáforo.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict, deque
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import agente, entradas, proveedor, reglas, respuesta, trazas

WEB = Path(__file__).parent / "web"
MAX_CUERPO = 16_000                         # bytes para texto: un mensaje de estafa cabe de sobra
MAX_CUERPO_IMAGEN = entradas.MAX_IMAGEN + 64_000
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
    "Si compartiste un audio, copia el texto del mensaje y pégalo aquí.",
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


def pagina(compartido: dict | None) -> bytes:
    """index.html con lo compartido incrustado como JSON. Se escapan <, > y & para que un
    '</script>' dentro del mensaje no pueda cerrar la etiqueta e inyectar código."""
    dato = json.dumps(compartido, ensure_ascii=False)
    dato = dato.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    marca = '<script id="compartido" type="application/json">null</script>'
    return html.replace(marca, marca.replace("null", dato)).encode("utf-8")


def leer_multipart(cuerpo: bytes, tipo: str) -> tuple[dict[str, str], bytes | None]:
    """Campos de texto y la primera imagen de un formulario multipart/form-data."""
    mensaje = BytesParser(policy=policy.default).parsebytes(
        f"Content-Type: {tipo}\r\n\r\n".encode("latin-1") + cuerpo
    )
    campos: dict[str, str] = {}
    imagen: bytes | None = None
    if not mensaje.is_multipart():
        return campos, imagen
    for parte in mensaje.iter_parts():
        if parte.get_filename() is not None or parte.get_content_maintype() == "image":
            if imagen is None:
                imagen = parte.get_payload(decode=True) or b""
        elif nombre := parte.get_param("name", header="content-disposition"):
            campos[nombre] = str(parte.get_content()).strip()
    return campos, imagen


def analizar(texto: str, tipo_entrada: str = "texto", extra: entradas.TextoExtraido | None = None) -> dict:
    texto = texto.strip()
    if not texto:
        return VACIO
    resultado = agente.analizar(texto)
    if extra:  # el costo y el tiempo de leer la imagen también son parte del análisis
        resultado.tokens_in += extra.tokens_in
        resultado.tokens_out += extra.tokens_out
        resultado.latencia_ms += extra.latencia_ms
    if resultado.ok and resultado.contrato is not None:
        semaforo, senales = reglas.calcular_semaforo(resultado.contrato, resultado.herramientas)
    else:
        semaforo, senales = "error", []
    try:
        trazas.registrar(resultado, semaforo, senales, tipo_entrada=tipo_entrada)
    except Exception as exc:
        print(f"  (no se guardó la traza: {type(exc).__name__})")
    return respuesta.para_web(resultado, semaforo)


def analizar_imagen(imagen: bytes, pie: str = "") -> dict:
    """Captura → texto → mismo agente. Si la captura trae un pie de foto, se agrega al texto leído."""
    try:
        extraido = entradas.texto_de_imagen(imagen)
    except entradas.EntradaInvalida as exc:
        return {"semaforo": "error", "lineas": [str(exc)]}
    except proveedor.ProveedorError as exc:
        mensaje = "La lectura de la imagen tardó demasiado. Inténtalo de nuevo." if str(exc) == "timeout" else str(exc)
        return {"semaforo": "error", "lineas": [mensaje]}
    texto = "\n".join(p for p in (pie.strip(), extraido.texto) if p)
    datos = analizar(texto, "imagen", extraido)
    return {**datos, "leido": extraido.texto}


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
        limite = MAX_CUERPO_IMAGEN if self._es_multipart() else MAX_CUERPO
        if largo > limite:
            # Se descarta el cuerpo (con tope) antes de responder: si no, en Windows la conexión
            # se corta y el cliente no alcanza a leer el 413.
            if largo <= 2 * MAX_CUERPO_IMAGEN:
                self.rfile.read(largo)
            self.close_connection = True
            self._json({"semaforo": "error", "lineas": ["El mensaje es demasiado grande para revisarlo."]},
                       HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return None
        return self.rfile.read(largo)

    def _es_multipart(self) -> bool:
        return (self.headers.get("Content-Type") or "").lower().startswith("multipart/form-data")

    def _formulario(self, cuerpo: bytes) -> tuple[dict[str, str], bytes | None]:
        if self._es_multipart():
            return leer_multipart(cuerpo, self.headers["Content-Type"])
        campos = parse_qs(cuerpo.decode("utf-8", "replace"))
        return {k: v[0].strip() for k, v in campos.items()}, None

    def _limitado(self) -> bool:
        if _permitido(self.client_address[0], time.monotonic()):
            return False
        self._json(ESPERA, HTTPStatus.TOO_MANY_REQUESTS)
        return True

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
            campos, imagen = self._formulario(cuerpo)
            texto = "\n".join(p for p in (campos.get("text", ""), campos.get("url", "")) if p)
            if imagen is not None:
                # La captura se analiza aquí mismo y la página llega con el resultado.
                if _permitido(self.client_address[0], time.monotonic()):
                    datos = analizar_imagen(imagen, texto)
                else:
                    datos = ESPERA
                print(f"  análisis (captura) → {datos['semaforo']}")
                self._enviar(200, pagina({"origen": "imagen", "resultado": datos}), "text/html; charset=utf-8")
            else:
                self._enviar(200, pagina({"origen": "texto", "texto": texto}), "text/html; charset=utf-8")

        elif ruta == "/api/analizar":
            try:
                texto = str(json.loads(cuerpo or b"{}").get("texto", ""))
            except (json.JSONDecodeError, AttributeError):
                self._json({"semaforo": "error", "lineas": ["No entendí la solicitud."]}, HTTPStatus.BAD_REQUEST)
                return
            if texto.strip() and self._limitado():
                return
            datos = analizar(texto)
            print(f"  análisis → {datos['semaforo']}")
            self._json(datos)

        elif ruta == "/api/analizar_imagen":
            if not self._es_multipart():
                self._json({"semaforo": "error", "lineas": ["Envía la captura como formulario."]}, HTTPStatus.BAD_REQUEST)
                return
            _, imagen = self._formulario(cuerpo)
            if imagen is None:
                self._json({"semaforo": "error", "lineas": ["No llegó ninguna imagen."]}, HTTPStatus.BAD_REQUEST)
                return
            if self._limitado():
                return
            datos = analizar_imagen(imagen)
            print(f"  análisis (captura) → {datos['semaforo']}")
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
