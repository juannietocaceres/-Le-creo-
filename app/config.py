"""Configuración desde .env. Ningún nombre de modelo ni llave vive en el código (regla 6).

D17: si el .env cambia mientras la app corre, se vuelve a leer antes del siguiente análisis,
así el proveedor se cambia en plena demo editando una línea, sin reiniciar ni tocar código.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

RUTA_ENV = Path(__file__).parent.parent / ".env"
_marca_env: float | None = None   # fecha de modificación del .env ya aplicado


def _valor(clave: str, defecto: str = "") -> str:
    return os.getenv(clave, defecto).split("#")[0].strip()


def _aplicar() -> None:
    global PROVEEDOR, _BASES, _KEYS, _MODELOS, MAX_ITER, TIMEOUT_S, PRESUPUESTO_TOKENS
    global FORZAR_ERROR, DATABASE_URL, TELEGRAM_BOT_TOKEN, PROVEEDOR_RESPALDO, PROVEEDOR_TRANSCRIPCION

    PROVEEDOR = _valor("PROVEEDOR", "google").lower()
    _BASES = {
        "google":     _valor("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
        "groq":       _valor("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        "openrouter": _valor("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    }
    _KEYS = {p: _valor(f"{p.upper()}_API_KEY") for p in _BASES}
    _MODELOS = {p: _valor(f"MODELO_{p.upper()}") for p in _BASES}

    MAX_ITER = int(_valor("MAX_ITER", "5"))
    TIMEOUT_S = int(_valor("TIMEOUT_S", "20"))
    PRESUPUESTO_TOKENS = int(_valor("PRESUPUESTO_TOKENS", "8000"))
    # Solo para pruebas y la demo de D13: "" | 429 | timeout | invalida
    FORZAR_ERROR = _valor("FORZAR_ERROR").lower()
    DATABASE_URL = _valor("DATABASE_URL", "postgresql://lecreo:lecreo@localhost:5433/lecreo")
    TELEGRAM_BOT_TOKEN = _valor("TELEGRAM_BOT_TOKEN")
    # Plan B ante un 429 persistente del proveedor principal (sección 11).
    PROVEEDOR_RESPALDO = _valor("PROVEEDOR_RESPALDO", "groq").lower()
    # Notas de voz (D12): la transcripción va por su propio proveedor (Whisper en Groq).
    PROVEEDOR_TRANSCRIPCION = _valor("PROVEEDOR_TRANSCRIPCION", "groq").lower()


def recargar_si_cambio(ruta: Path | None = None) -> bool:
    """Relee el .env solo si cambió desde la última lectura. Devuelve True si recargó.

    La primera lectura no pisa variables que ya estén en el entorno; las siguientes sí,
    porque son ediciones deliberadas del .env con la app corriendo."""
    global _marca_env
    ruta = ruta or RUTA_ENV
    try:
        marca = ruta.stat().st_mtime
    except FileNotFoundError:
        if _marca_env is None:
            _aplicar()
            _marca_env = -1.0
        return False
    if marca == _marca_env:
        return False
    load_dotenv(ruta, override=_marca_env is not None)
    _marca_env = marca
    _aplicar()
    return True


recargar_si_cambio()


def base_url(p: str | None = None) -> str:
    return _BASES[p or PROVEEDOR]


def api_key(p: str | None = None) -> str:
    return _KEYS[p or PROVEEDOR]


def modelo(p: str | None = None) -> str:
    p = p or PROVEEDOR
    m = _MODELOS[p]
    if not m:
        raise ValueError(f"MODELO_{p.upper()} no está configurado en .env")
    return m


def respaldo() -> str | None:
    """Proveedor de respaldo utilizable: distinto del principal y con llave y modelo."""
    p = PROVEEDOR_RESPALDO
    if not p or p == PROVEEDOR or p not in _BASES or not _KEYS.get(p) or not _MODELOS.get(p):
        return None
    return p


def transcripcion() -> tuple[str, str, str]:
    """(base_url, api_key, modelo) para transcribir audio."""
    m = _valor("MODELO_TRANSCRIPCION")
    if not m:
        raise ValueError("MODELO_TRANSCRIPCION no está configurado en .env")
    llave = _KEYS[PROVEEDOR_TRANSCRIPCION]
    if not llave:
        raise ValueError(f"Falta {PROVEEDOR_TRANSCRIPCION.upper()}_API_KEY en .env para transcribir audios")
    return _BASES[PROVEEDOR_TRANSCRIPCION], llave, m
