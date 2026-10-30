"""Única puerta al LLM. Ningún otro módulo importa openai directamente."""
from __future__ import annotations

import time
from typing import Any

import openai

from app import config


class ProveedorError(RuntimeError):
    """Fallo del proveedor con un mensaje apto para mostrar al usuario."""


class HerramientaInventada(ProveedorError):
    """El modelo llamó una herramienta que no existe (Groq: 400 tool_use_failed).
    Pasa con gpt-oss cuando intenta entregar el JSON final como si fuera una herramienta."""


def responder(
    mensajes: list[dict[str, Any]],
    herramientas: list[dict[str, Any]] | None = None,
    timeout: float | None = None,
    sin_herramientas: bool = False,
) -> Any:
    """Llama al proveedor configurado en .env y devuelve la respuesta completa."""
    try:
        modelo = config.modelo()
    except ValueError as exc:
        raise ProveedorError(str(exc)) from exc
    if not config.api_key():
        raise ProveedorError(f"Falta {config.PROVEEDOR.upper()}_API_KEY en el .env.")

    cliente = openai.OpenAI(
        api_key=config.api_key(),
        base_url=config.base_url(),
        timeout=timeout if timeout is not None else config.TIMEOUT_S,
        max_retries=0,
    )
    kwargs: dict[str, Any] = {"model": modelo, "messages": mensajes}
    if herramientas:
        kwargs["tools"] = herramientas
        if sin_herramientas:
            kwargs["tool_choice"] = "none"
    return cliente.chat.completions.create(**kwargs)


def responder_con_reintento(
    mensajes: list[dict[str, Any]],
    herramientas: list[dict[str, Any]] | None = None,
    timeout: float | None = None,
    sin_herramientas: bool = False,
) -> Any:
    """Reintenta solo ante 429 (espera 1s y 2s). Un timeout no se reintenta:
    el límite de tiempo del análisis ya se consumió."""
    for espera in (1, 2, None):
        try:
            return responder(mensajes, herramientas, timeout, sin_herramientas)
        except openai.RateLimitError as exc:
            if espera is None:
                raise ProveedorError("El proveedor está saturado (429). Intenta de nuevo en un momento.") from exc
            time.sleep(espera)
        except openai.APITimeoutError as exc:
            raise ProveedorError("timeout") from exc
        except openai.AuthenticationError as exc:
            raise ProveedorError(f"La API key de {config.PROVEEDOR} no es válida. Revisa el .env.") from exc
        except openai.BadRequestError as exc:
            if "tool_use_failed" in str(exc):
                raise HerramientaInventada("el modelo llamó una herramienta que no existe") from exc
            raise ProveedorError(f"Error del proveedor {config.PROVEEDOR}: solicitud rechazada (400)") from exc
        except openai.NotFoundError as exc:
            raise ProveedorError(f"El modelo '{config.modelo()}' no existe en {config.PROVEEDOR}. Revisa el .env.") from exc
        except openai.OpenAIError as exc:
            raise ProveedorError(f"Error del proveedor {config.PROVEEDOR}: {type(exc).__name__}") from exc
    raise AssertionError("inalcanzable")
