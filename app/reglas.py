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

    _canal_encontrado = False
    for h in herramientas:
        r = h.resultado if isinstance(h.resultado, dict) else {}

        if h.nombre == "revisar_enlace":
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
                _canal_encontrado = True

    # ── Señales del contrato ──────────────────────────────────────────────────

    # Pide clave o código → dura
    for item in contrato.pide:
        if item in {"clave", "codigo"}:
            senales_duras.append(f"pide {item}")
        elif item == "transferencia":
            senales_blandas.append("pide transferencia")

    # Suplantación con canal verificado → dura
    if contrato.entidad_suplantada and _canal_encontrado:
        senales_duras.append(
            f"suplanta a {contrato.entidad_suplantada} pero el canal no coincide con el oficial"
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
