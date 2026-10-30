"""Criterios 'Listo cuando' de C1–C5 (docs/TAREAS_COMPANERO.md) y validación de cargar_semillas."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.cargar_semillas import ENCABEZADOS, SemillaInvalida, leer, validar

RAIZ = Path(__file__).parent.parent
CAMPOS_TACTICA = {"id", "nombre", "descripcion", "senales", "ejemplo", "fuerza"}


@pytest.fixture(scope="module")
def datos():
    return {nombre: leer(nombre) for nombre in ENCABEZADOS}


def test_c1_entre_12_y_15_tacticas_con_6_campos():
    tacticas = json.loads((RAIZ / "data" / "tacticas.json").read_text(encoding="utf-8"))
    assert 12 <= len(tacticas) <= 15
    for t in tacticas:
        assert set(t) == CAMPOS_TACTICA
        assert all(t[c] for c in CAMPOS_TACTICA), f"{t['id']} tiene campos vacíos"
        assert re.fullmatch(r"[a-z_]+", t["id"])
        assert t["fuerza"] in {"fuerte", "media"}


def test_c1_ejemplos_sin_numeros_reales():
    texto = (RAIZ / "data" / "tacticas.json").read_text(encoding="utf-8")
    for numero in re.findall(r"\+57[\d ]{10,13}", texto):
        assert re.sub(r"\D", "", numero).startswith("573000000"), numero


def test_c2_al_menos_10_canales_con_fuente_oficial(datos):
    canales = datos["canales_oficiales.csv"]
    assert len(canales) >= 10
    assert all(f["fuente_url"].startswith("https://") for f in canales)


def test_c3_cada_entidad_tiene_dominio_y_hay_8_acortadores(datos):
    entidades = {f["entidad"] for f in datos["canales_oficiales.csv"]}
    con_dominio = {f["entidad"] for f in datos["dominios_oficiales.csv"]}
    assert entidades <= con_dominio, f"sin dominio: {entidades - con_dominio}"
    assert len(datos["acortadores.csv"]) >= 8


def test_c4_diez_numeros_5_peligrosos_5_no(datos):
    numeros = datos["numeros_ficticios.csv"]
    assert len(numeros) == 10
    peligrosos = [n for n in numeros if int(n["reportes"]) >= 3]
    assert len(peligrosos) == 5


def test_validar_acepta_las_semillas(datos):
    validar(datos)


def test_validar_rechaza_numero_real(datos):
    malos = {k: [dict(f) for f in v] for k, v in datos.items()}
    malos["numeros_ficticios.csv"][0]["numero"] = "+573214567890"
    with pytest.raises(SemillaInvalida):
        validar(malos)


def test_c5_doce_casos_con_la_mezcla_pedida():
    casos = [json.loads(l) for l in (RAIZ / "eval" / "casos.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(casos) == 12
    assert len({c["id"] for c in casos}) == 12
    semaforos = [c["esperado"]["semaforo"] for c in casos]
    assert semaforos.count("verde") == 3
    assert semaforos.count("rechazo") == 1
    assert sum(s in {"rojo", "amarillo"} for s in semaforos) == 8
    assert any("asistente" in c["entrada"].lower() for c in casos), "falta el caso de inyección"
    for c in casos:
        assert c["por_que"]
        for num in re.findall(r"3\d{2} ?\d{3} ?\d{4}", c["entrada"]):
            assert re.sub(r"\D", "", num).startswith("3000000"), f"{c['id']}: número no ficticio {num}"


def test_c5_tacticas_min_existen_en_el_catalogo():
    ids = {t["id"] for t in json.loads((RAIZ / "data" / "tacticas.json").read_text(encoding="utf-8"))}
    for linea in (RAIZ / "eval" / "casos.jsonl").read_text(encoding="utf-8").splitlines():
        caso = json.loads(linea)
        assert set(caso["esperado"]["tacticas_min"]) <= ids, caso["id"]
