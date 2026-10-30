"""Bot de Telegram de ¿Le creo?: la persona reenvía el mensaje sospechoso y recibe la respuesta.

Uso:  python ui\\bot_telegram.py      (necesita TELEGRAM_BOT_TOKEN en .env)

Es otra puerta al mismo agente que usa la web. Nunca registra el texto del mensaje
(regla 3): en consola solo aparecen el semáforo y la latencia.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import agente, config, reglas, respuesta, trazas

Enviar = Callable[[str, dict[str, Any]], Any]

MAX_ANALISIS_POR_MINUTO = 3

BIENVENIDA = (
    "👋 Hola, soy <b>¿Le creo?</b>\n\n"
    "Si te llega un mensaje que te hace dudar (un paquete retenido, un familiar con número nuevo, "
    "tu banco pidiendo datos), <b>reenvíamelo</b> y te digo si parece estafa y qué hacer.\n\n"
    "No abro los enlaces y no guardo tus mensajes."
)
SOLO_TEXTO = (
    "Por ahora solo puedo leer mensajes de texto. 📝\n"
    "Si te llegó una foto o un audio, copia el texto del mensaje y envíamelo."
)
ESPERA = "Dame un minuto: estoy revisando varios mensajes tuyos seguidos. Inténtalo de nuevo en un momento."

_recientes: dict[int, deque[float]] = defaultdict(deque)


def _permitido(chat_id: int, ahora: float) -> bool:
    ventana = _recientes[chat_id]
    while ventana and ahora - ventana[0] > 60:
        ventana.popleft()
    if len(ventana) >= MAX_ANALISIS_POR_MINUTO:
        return False
    ventana.append(ahora)
    return True


def atender(mensaje: dict[str, Any], enviar: Enviar) -> str:
    """Procesa un mensaje entrante y responde. Devuelve una etiqueta para el registro (sin el texto)."""
    chat = mensaje.get("chat", {})
    if chat.get("type") != "private":
        return "ignorado: no es chat privado"
    chat_id = chat["id"]
    responder = lambda texto: enviar("sendMessage", {  # noqa: E731
        "chat_id": chat_id, "text": texto, "parse_mode": "HTML",
        "reply_parameters": {"message_id": mensaje["message_id"], "allow_sending_without_reply": True},
        "link_preview_options": {"is_disabled": True},
    })

    texto = (mensaje.get("text") or mensaje.get("caption") or "").strip()
    if texto.split(maxsplit=1)[0:1] in (["/start"], ["/ayuda"], ["/help"]):
        responder(BIENVENIDA)
        return "bienvenida"
    if not texto:
        responder(SOLO_TEXTO)
        return "sin texto"
    if not _permitido(chat_id, time.monotonic()):
        responder(ESPERA)
        return "limitado"

    enviar("sendChatAction", {"chat_id": chat_id, "action": "typing"})
    resultado = agente.analizar(texto)
    if resultado.ok and resultado.contrato is not None:
        semaforo, senales = reglas.calcular_semaforo(resultado.contrato, resultado.herramientas)
    else:
        semaforo, senales = "error", []
    try:
        trazas.registrar(resultado, semaforo, senales, tipo_entrada="texto")
    except Exception as exc:
        print(f"  (no se guardó la traza: {type(exc).__name__})")
    responder(respuesta.para_telegram(resultado, semaforo))
    return f"{semaforo} en {resultado.latencia_ms} ms"


# ── Telegram Bot API ──────────────────────────────────────────────────────────

def _api(token: str) -> Enviar:
    base = f"https://api.telegram.org/bot{token}/"

    def llamar(metodo: str, parametros: dict[str, Any], timeout: float = 15) -> Any:
        datos = json.dumps(parametros).encode()
        req = urllib.request.Request(base + metodo, data=datos, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            cuerpo = json.load(resp)
        if not cuerpo.get("ok"):
            raise RuntimeError(cuerpo.get("description", "respuesta no ok"))
        return cuerpo["result"]

    return llamar


def main() -> int:
    if not config.TELEGRAM_BOT_TOKEN:
        print("Falta TELEGRAM_BOT_TOKEN en el .env. Créalo con @BotFather (/newbot).")
        return 1
    api = _api(config.TELEGRAM_BOT_TOKEN)
    try:
        yo = api("getMe", {})
    except (urllib.error.URLError, RuntimeError) as exc:
        # El token va en la URL: no se imprime la excepción completa para no filtrarlo.
        print(f"No pude conectar con Telegram ({type(exc).__name__}). Revisa el token y la conexión.")
        return 1
    api("deleteWebhook", {})
    print(f"Bot @{yo['username']} escuchando · proveedor {config.PROVEEDOR}. Ctrl+C para salir.")

    offset, espera_error = 0, 1
    while True:
        try:
            updates = api("getUpdates", {"offset": offset, "timeout": 50, "allowed_updates": ["message"]}, timeout=60)
            espera_error = 1
        except KeyboardInterrupt:
            print("Bot detenido.")
            return 0
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            print(f"  Telegram no respondió ({type(exc).__name__}); reintento en {espera_error} s")
            time.sleep(espera_error)
            espera_error = min(espera_error * 2, 60)
            continue

        for u in updates:
            offset = u["update_id"] + 1
            if "message" not in u:
                continue
            try:
                etiqueta = atender(u["message"], api)
            except Exception as exc:
                etiqueta = f"falló ({type(exc).__name__})"
            print(f"  update {u['update_id']}: {etiqueta}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Bot detenido.")
