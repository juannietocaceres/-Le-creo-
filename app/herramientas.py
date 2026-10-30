"""Herramientas del agente: funciones + esquemas OpenAI tool-calling."""
from __future__ import annotations

import re
from typing import Any

from app import db


# ── Funciones ────────────────────────────────────────────────────────────────

def buscar_numero(numero: str) -> dict[str, Any]:
    """Normaliza a +57 y consulta reportes en la base."""
    numero = _normalizar_numero(numero)
    return db.buscar_numero(numero)


def canal_oficial(entidad: str) -> dict[str, Any]:
    """Devuelve cómo contacta de verdad la entidad y qué nunca pide."""
    return db.canal_oficial(entidad)


def revisar_enlace(url: str) -> dict[str, Any]:
    """Analiza el texto de la URL sin abrirla ni descargar nada.

    Detecta:
    - Dominio oficial exacto
    - Imitación de marca (contiene el nombre de una marca oficial pero no es el dominio oficial)
    - Distancia de edición ≤ 2 respecto a un dominio oficial
    - Acortador conocido
    - Punycode (xn--)
    """
    dominio = _extraer_dominio(url)
    oficiales = db.dominios_oficiales()

    # Exacto o subdominio de un oficial (sucursal.bancolombia.com es de Bancolombia)
    es_oficial = any(dominio == d or dominio.endswith("." + d) for d, _ in oficiales)
    imita_a: str | None = None
    motivos: list[str] = []

    usa_arroba = "@" in url.split("//", 1)[-1].split("/", 1)[0]
    if usa_arroba:
        motivos.append("usa '@' en la dirección: el destino real es lo que va después")

    if not es_oficial:
        # 1. ¿Contiene la marca de un dominio oficial?
        for dom_oficial, entidad in oficiales:
            marca = dom_oficial.split(".")[0]  # "bancolombia.com" → "bancolombia"
            if _contiene_marca(dominio, marca):
                imita_a = entidad
                motivos.append(f"contiene '{marca}' pero no es {dom_oficial}")
                break

        # 2. Muy parecido a una marca oficial (typosquatting), sin contar el TLD
        if not imita_a:
            base = dominio.split(".")[0]
            for dom_oficial, entidad in oficiales:
                marca = dom_oficial.split(".")[0]
                if len(marca) < 5 or base == marca:
                    continue
                tope = 1 if len(marca) < 8 else 2
                if _levenshtein(base, marca) <= tope:
                    imita_a = entidad
                    motivos.append(f"muy parecido a {dom_oficial} (distancia ≤ {tope})")
                    break

    # 3. ¿Acortador?
    acortador = db.es_acortador(dominio)
    if acortador:
        motivos.append("dominio acortador — oculta el destino real")

    # 4. ¿Punycode?
    punycode = dominio.startswith("xn--") or ".xn--" in dominio
    if punycode:
        motivos.append("contiene punycode (xn--) — puede imitar caracteres visualmente")

    sospechoso = bool(imita_a or acortador or punycode or usa_arroba)

    return {
        "dominio":      dominio,
        "es_oficial":   es_oficial,
        "imita_a":      imita_a,
        "es_acortador": acortador,
        "sospechoso":   sospechoso,
        "motivo":       "; ".join(motivos) if motivos else "ninguno",
    }


# ── Utilidades ───────────────────────────────────────────────────────────────

def _extraer_dominio(url: str) -> str:
    """Extrae el host real (sin protocolo, usuario@, puerto, www ni path)."""
    url = url.strip().lower()
    for prefix in ("https://", "http://", "//"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    url = url.split("/")[0].split("?")[0].split("#")[0]
    url = url.rsplit("@", 1)[-1].split(":")[0].rstrip(".")
    if url.startswith("www."):
        url = url[4:]
    return url


def _contiene_marca(dominio: str, marca: str) -> bool:
    """Marcas largas: en cualquier parte. Cortas (<6): solo al inicio de una etiqueta
    o tras un guion, para no confundir 'meridian.com' con DIAN."""
    if not marca:
        return False
    if len(marca) >= 6:
        return marca in dominio
    return re.search(r"(^|[.\-])" + re.escape(marca), dominio) is not None


def _levenshtein(a: str, b: str) -> int:
    """Distancia de edición entre dos cadenas."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def _normalizar_numero(numero: str) -> str:
    """Normaliza un número colombiano al formato +57XXXXXXXXXX."""
    limpio = "".join(c for c in numero if c.isdigit() or c == "+")
    if limpio.startswith("+"):
        return limpio
    if limpio.startswith("57") and len(limpio) == 12:
        return "+" + limpio
    if len(limpio) == 10 and limpio.startswith("3"):
        return "+57" + limpio
    return limpio  # número extranjero u otro formato: devolver tal cual


# ── Esquemas para el agente (OpenAI tool-calling) ────────────────────────────

ESQUEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "buscar_numero",
            "description": (
                "Úsala cuando el mensaje traiga un número de teléfono, o cuando el usuario "
                "diga desde qué número le escribieron. Normaliza el número a +57 y consulta "
                "cuántas veces ha sido reportado. "
                "No la uses para números de cuentas bancarias ni para cédulas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "numero": {
                        "type": "string",
                        "description": "Número de teléfono tal como aparece en el mensaje.",
                    }
                },
                "required": ["numero"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "canal_oficial",
            "description": (
                "Úsala cuando el mensaje diga venir de un banco, una billetera (Nequi, Daviplata), "
                "una transportadora, la DIAN o la Policía. Devuelve cómo contacta de verdad esa "
                "entidad y qué nunca pide. "
                "No la uses si el mensaje no menciona ninguna entidad."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entidad": {
                        "type": "string",
                        "description": "Nombre de la entidad mencionada en el mensaje (ej: 'Bancolombia', 'Nequi').",
                    }
                },
                "required": ["entidad"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "revisar_enlace",
            "description": (
                "Úsala cuando el mensaje contenga un enlace o algo que parezca dirección web. "
                "Revisa solo el texto de la URL: si imita un dominio oficial, si usa un acortador "
                "o si tiene caracteres engañosos. "
                "No abre el enlace ni descarga nada. "
                "No la uses si el mensaje no tiene enlaces."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL o fragmento de URL tal como aparece en el mensaje.",
                    }
                },
                "required": ["url"],
            },
        },
    },
]


DESPACHO: dict[str, Any] = {
    "buscar_numero":  buscar_numero,
    "canal_oficial":  canal_oficial,
    "revisar_enlace": revisar_enlace,
}
