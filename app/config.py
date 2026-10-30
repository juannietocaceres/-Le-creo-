from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

PROVEEDOR: str = os.getenv("PROVEEDOR", "google").lower()

_BASES = {
    "google":      os.getenv("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "groq":        os.getenv("GROQ_BASE_URL",   "https://api.groq.com/openai/v1"),
    "openrouter":  os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
}

_KEYS = {
    "google":     os.getenv("GOOGLE_API_KEY", ""),
    "groq":       os.getenv("GROQ_API_KEY", ""),
    "openrouter": os.getenv("OPENROUTER_API_KEY", ""),
}

_MODELOS = {
    "google":     os.getenv("MODELO_GOOGLE", ""),
    "groq":       os.getenv("MODELO_GROQ", ""),
    "openrouter": os.getenv("MODELO_OPENROUTER", ""),
}

MAX_ITER:           int = int(os.getenv("MAX_ITER", "5"))
TIMEOUT_S:          int = int(os.getenv("TIMEOUT_S", "20"))
PRESUPUESTO_TOKENS: int = int(os.getenv("PRESUPUESTO_TOKENS", "8000"))
FORZAR_ERROR:       str = os.getenv("FORZAR_ERROR", "")
DATABASE_URL:       str = os.getenv("DATABASE_URL", "postgresql://lecreo:lecreo@localhost:5433/lecreo")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").split("#")[0].strip()


def base_url() -> str:
    return _BASES[PROVEEDOR]


def api_key() -> str:
    return _KEYS[PROVEEDOR]


def modelo() -> str:
    m = _MODELOS[PROVEEDOR]
    if not m:
        raise ValueError(f"MODELO_{PROVEEDOR.upper()} no está configurado en .env")
    return m
