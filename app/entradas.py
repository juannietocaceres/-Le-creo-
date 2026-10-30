"""Entradas que no son texto (F2). Se convierten a texto y luego van al mismo agente.

D11: capturas de pantalla. Ni la imagen ni el texto extraído se guardan (regla 3).
"""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass

from app import config, proveedor

TIPOS_IMAGEN = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGEN = 5 * 1024 * 1024  # 5 MB: una captura de celular pesa bastante menos


class EntradaInvalida(ValueError):
    """La entrada no se puede analizar; el mensaje es apto para mostrar a la persona."""


@dataclass
class TextoExtraido:
    texto: str
    tokens_in: int
    tokens_out: int
    latencia_ms: int


def _tipo_real(datos: bytes) -> str | None:
    """Tipo según los primeros bytes, no según lo que diga el nombre o el navegador."""
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    return None


def texto_de_imagen(datos: bytes) -> TextoExtraido:
    """Valida la captura y extrae su texto. Lanza EntradaInvalida o proveedor.ProveedorError."""
    if not datos:
        raise EntradaInvalida("No llegó ninguna imagen.")
    if len(datos) > MAX_IMAGEN:
        raise EntradaInvalida("La imagen es demasiado pesada. Toma un pantallazo normal del chat.")
    mime = _tipo_real(datos)
    if mime not in TIPOS_IMAGEN:
        raise EntradaInvalida("Solo puedo leer capturas en PNG, JPG o WEBP.")

    inicio = time.perf_counter()
    texto, tin, tout = proveedor.transcribir_imagen(
        base64.b64encode(datos).decode("ascii"), mime, timeout=config.TIMEOUT_S
    )
    if not texto or texto.strip().upper() == proveedor.SIN_TEXTO:
        raise EntradaInvalida("No pude leer texto en esa imagen. Toma el pantallazo más de cerca o pega el mensaje.")
    return TextoExtraido(texto, tin, tout, int((time.perf_counter() - inicio) * 1000))
