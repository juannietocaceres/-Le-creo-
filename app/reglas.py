"""Semáforo determinista. El LLM aporta señales; esta función decide el color.

Reglas (spec sección 9.5) — sin LLM:
  RECHAZO  → fuera_de_alcance = True
  ROJO     → al menos una señal dura
  AMARILLO → señales blandas sin ninguna dura
  VERDE    → ninguna señal
"""
from __future__ import annotations

import json
from pathlib import Path

from app.contrato import ContratoSalida, LlamadaHerramienta

_TACTICAS_JSON = Path(__file__).parent.parent / "data" / "tacticas.json"

# La fuerza de cada táctica la define el catálogo (data/tacticas.json, campo "fuerza").
_TACTICAS_FUERTES = {
    t["id"]
    for t in json.loads(_TACTICAS_JSON.read_text(encoding="utf-8"))
    if t.get("fuerza") == "fuerte"
}


def _digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())


def calcular_semaforo(
    contrato: ContratoSalida,
    herramientas: list[LlamadaHerramienta],
) -> tuple[str, list[str]]:
    """Devuelve (semaforo, lista_de_señales_para_UI).

    semaforo: "rojo" | "amarillo" | "verde" | "rechazo"
    """
    if contrato.fuera_de_alcance:
        return "rechazo", ["fuera_de_alcance"]

    senales_duras: list[str] = []
    senales_blandas: list[str] = []

    # ── Señales de las herramientas ───────────────────────────────────────────

    canal: dict | None = None
    enlaces_no_oficiales: list[str] = []
    for h in herramientas:
        r = h.resultado if isinstance(h.resultado, dict) else {}

        if h.nombre == "revisar_enlace":
            if r.get("dominio") and not r.get("es_oficial"):
                enlaces_no_oficiales.append(r["dominio"])
            if r.get("imita_a"):
                senales_duras.append(f"enlace imita a {r['imita_a']}: {r.get('dominio', '')}")
            elif r.get("es_acortador"):
                senales_blandas.append(f"enlace acortador: {r.get('dominio', '')}")

        elif h.nombre == "buscar_numero":
            if r.get("peligroso"):
                senales_duras.append(
                    f"número con {r.get('reportes', '?')} reportes: {r.get('numero', '')}"
                )

        elif h.nombre == "canal_oficial":
            if r.get("encontrada"):
                canal = r

    # ── Señales del contrato ──────────────────────────────────────────────────

    # Pide clave o código → dura
    for item in contrato.pide:
        if item in {"clave", "codigo"}:
            senales_duras.append(f"pide {item}")
        elif item == "transferencia":
            senales_blandas.append("pide transferencia")

    # Dice ser una entidad conocida pero da un enlace o un teléfono que no son los suyos → dura.
    # Es una comparación de datos, no un juicio del modelo: un aviso real del banco que no trae
    # contacto, o que trae su dominio oficial, no cae aquí.
    if contrato.entidad_suplantada and canal:
        oficiales = _digitos(canal.get("canales", ""))
        telefonos_ajenos = [t for t in contrato.telefonos if _digitos(t) and _digitos(t) not in oficiales]
        ajenos = enlaces_no_oficiales + telefonos_ajenos
        if ajenos:
            senales_duras.append(
                f"dice ser {contrato.entidad_suplantada} pero da un contacto que no es el oficial: {', '.join(ajenos)}"
            )

    # Tácticas fuertes
    tacticas_fuertes_detectadas = [
        t for t in contrato.tacticas if t.id in _TACTICAS_FUERTES
    ]
    if len(tacticas_fuertes_detectadas) >= 2:
        ids = ", ".join(t.id for t in tacticas_fuertes_detectadas)
        senales_duras.append(f"2 o más tácticas fuertes: {ids}")
    elif len(tacticas_fuertes_detectadas) == 1:
        senales_blandas.append(f"táctica fuerte: {tacticas_fuertes_detectadas[0].id}")

    # Tácticas medias (las que no son fuertes)
    tacticas_medias = [t for t in contrato.tacticas if t.id not in _TACTICAS_FUERTES]
    for t in tacticas_medias:
        senales_blandas.append(f"táctica media: {t.id}")

    # ── Decisión ──────────────────────────────────────────────────────────────

    if senales_duras:
        return "rojo", senales_duras + senales_blandas

    if senales_blandas:
        return "amarillo", senales_blandas

    return "verde", []
