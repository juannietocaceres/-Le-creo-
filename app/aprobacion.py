"""Supervisión humana exigida por el código (regla dura 4, decisión 5).

Toda acción que publica algo hacia afuera (reportar un número) o escribe la opinión de la
persona (feedback) necesita un permiso que el servidor emite junto con el resultado de un
análisis y que solo se usa cuando la persona hace clic. El permiso:
  - está firmado (HMAC): no se puede fabricar ni cambiar de número o de análisis,
  - vence a los 30 minutos,
  - sirve una sola vez.
El agente no recibe estos permisos: la IA no puede reportar nada por su cuenta.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time

VIGENCIA_S = 30 * 60
_SECRETO = (os.getenv("LECREO_SECRETO") or secrets.token_hex(32)).encode()  # sin .env: uno nuevo por arranque
_usados: dict[str, float] = {}
_candado = threading.Lock()


def _firma(accion: str, analisis_id: int, valor: str, vence: int) -> str:
    mensaje = f"{accion}|{analisis_id}|{valor}|{vence}".encode()
    return hmac.new(_SECRETO, mensaje, hashlib.sha256).hexdigest()


def emitir(accion: str, analisis_id: int, valor: str = "", ahora: float | None = None) -> str:
    vence = int((ahora if ahora is not None else time.time()) + VIGENCIA_S)
    return f"{vence}.{_firma(accion, analisis_id, valor, vence)}"


def usar(permiso: str, accion: str, analisis_id: int, valor: str = "", ahora: float | None = None) -> bool:
    """True solo si el permiso es auténtico, vigente y no se había usado. Lo marca como usado."""
    ahora = ahora if ahora is not None else time.time()
    try:
        vence_txt, firma = permiso.split(".", 1)
        vence = int(vence_txt)
    except (ValueError, AttributeError):
        return False
    if vence < ahora or not hmac.compare_digest(firma, _firma(accion, analisis_id, valor, vence)):
        return False
    with _candado:
        for p, v in list(_usados.items()):   # olvida los vencidos
            if v < ahora:
                del _usados[p]
        if permiso in _usados:
            return False
        _usados[permiso] = vence
    return True
