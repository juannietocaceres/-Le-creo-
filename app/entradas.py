"""Entradas que no son texto (F2). Se convierten a texto y luego van al mismo agente.

D11: capturas de pantalla. D12: notas de voz.
Ni el archivo ni el texto extraído se guardan (regla 3).
"""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass

from app import config, proveedor

TIPOS_IMAGEN = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGEN = 5 * 1024 * 1024    # una captura de celular pesa bastante menos
MAX_AUDIO = 10 * 1024 * 1024    # una nota de voz de varios minutos en Opus pesa < 1 MB
EXTENSION_AUDIO = {"audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/wav": "wav", "audio/webm": "webm"}


class EntradaInvalida(ValueError):
    """La entrada no se puede analizar; el mensaje es apto para mostrar a la persona."""


@dataclass
class TextoExtraido:
    texto: str
    tokens_in: int
    tokens_out: int
    latencia_ms: int
    tipo: str = "imagen"   # imagen | audio (va a la traza como tipo_entrada)


def tipo_real(datos: bytes) -> str | None:
    """Tipo según los primeros bytes, no según lo que diga el nombre o el navegador."""
    if datos.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if datos.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    if datos.startswith(b"OggS"):                       # notas de voz de WhatsApp (Opus en OGG)
        return "audio/ogg"
    if datos.startswith(b"ID3") or datos[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    if datos[4:8] == b"ftyp":
        return "audio/mp4"
    if datos[:4] == b"RIFF" and datos[8:12] == b"WAVE":
        return "audio/wav"
    if datos.startswith(b"\x1aE\xdf\xa3"):
        return "audio/webm"
    return None


def texto_de_imagen(datos: bytes) -> TextoExtraido:
    """Valida la captura y extrae su texto. Lanza EntradaInvalida o proveedor.ProveedorError."""
    if not datos:
        raise EntradaInvalida("No llegó ninguna imagen.")
    if len(datos) > MAX_IMAGEN:
        raise EntradaInvalida("La imagen es demasiado pesada. Toma un pantallazo normal del chat.")
    mime = tipo_real(datos)
    if mime not in TIPOS_IMAGEN:
        raise EntradaInvalida("Solo puedo leer capturas en PNG, JPG o WEBP.")

    inicio = time.perf_counter()
    texto, tin, tout = proveedor.transcribir_imagen(
        base64.b64encode(datos).decode("ascii"), mime, timeout=config.TIMEOUT_S
    )
    if not texto or texto.strip().upper() == proveedor.SIN_TEXTO:
        raise EntradaInvalida("No pude leer texto en esa imagen. Toma el pantallazo más de cerca o pega el mensaje.")
    return TextoExtraido(texto, tin, tout, int((time.perf_counter() - inicio) * 1000), "imagen")


def texto_de_audio(datos: bytes) -> TextoExtraido:
    """Valida la nota de voz y la transcribe. Lanza EntradaInvalida o proveedor.ProveedorError."""
    if not datos:
        raise EntradaInvalida("No llegó ningún audio.")
    if len(datos) > MAX_AUDIO:
        raise EntradaInvalida("El audio es demasiado largo. Comparte solo la nota de voz sospechosa.")
    mime = tipo_real(datos)
    if mime not in EXTENSION_AUDIO:
        raise EntradaInvalida("No reconozco ese formato de audio. Comparte la nota de voz directamente desde WhatsApp.")

    inicio = time.perf_counter()
    texto = proveedor.transcribir_audio(datos, f"nota.{EXTENSION_AUDIO[mime]}", mime, timeout=config.TIMEOUT_S)
    if len(texto.split()) < 2:
        # Caso borde 9: audio vacío o inaudible → pedir de nuevo, sin inventar.
        raise EntradaInvalida("No alcancé a entender palabras en ese audio. Intenta con otra nota de voz o escribe el mensaje.")
    return TextoExtraido(texto, 0, 0, int((time.perf_counter() - inicio) * 1000), "audio")


def texto_de_archivo(datos: bytes) -> TextoExtraido:
    """Captura o nota de voz, según su contenido."""
    mime = tipo_real(datos) if datos else None
    if mime in EXTENSION_AUDIO:
        return texto_de_audio(datos)
    if mime in TIPOS_IMAGEN:
        return texto_de_imagen(datos)
    raise EntradaInvalida("Solo puedo revisar capturas (PNG, JPG, WEBP) o notas de voz.")
