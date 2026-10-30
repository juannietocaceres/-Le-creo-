"""Tests de buscar_numero y canal_oficial contra la DB real (Docker debe estar corriendo)."""
from __future__ import annotations

import pytest

from app.herramientas import buscar_numero, canal_oficial, _normalizar_numero

pytestmark = pytest.mark.usefixtures("requiere_db")


# ── Normalización de números ──────────────────────────────────────────────────

def test_normalizar_numero_10_digitos():
    assert _normalizar_numero("3001234567") == "+573001234567"


def test_normalizar_numero_ya_tiene_codigo():
    assert _normalizar_numero("+573001234567") == "+573001234567"


def test_normalizar_numero_con_57():
    assert _normalizar_numero("573001234567") == "+573001234567"


def test_normalizar_numero_extranjero_no_modifica():
    resultado = _normalizar_numero("+12025551234")
    assert resultado == "+12025551234"


# ── buscar_numero contra DB ───────────────────────────────────────────────────

def test_numero_peligroso_tiene_3_o_mas_reportes():
    # +573000000001 tiene 5 reportes (semilla TEMPORAL)
    r = buscar_numero("+573000000001")
    assert r["reportes"] >= 3
    assert r["peligroso"] is True


def test_numero_no_peligroso_menos_de_3_reportes():
    # +573000000006 tiene 1 reporte en numeros_ficticios.csv
    r = buscar_numero("+573000000006")
    assert r["reportes"] < 3
    assert r["peligroso"] is False


def test_numero_con_exactamente_3_reportes_es_peligroso():
    # +573000000003 tiene 3 reportes: el umbral es >= 3
    assert buscar_numero("+573000000003")["peligroso"] is True


def test_numero_desconocido_devuelve_cero_reportes():
    r = buscar_numero("+573099999999")
    assert r["reportes"] == 0
    assert r["peligroso"] is False
    assert "nota" in r


def test_numero_formato_10_digitos_se_normaliza_y_consulta():
    # Consulta con formato sin +57; debe llegar normalizado a la DB
    r = buscar_numero("300 000 0001")
    assert r["numero"] == "+573000000001"
    assert r["reportes"] == 5


# ── canal_oficial contra DB ───────────────────────────────────────────────────

def test_canal_bancolombia_encontrado():
    r = canal_oficial("Bancolombia")
    assert r["encontrada"] is True
    assert r["entidad"] == "Bancolombia"
    assert "canales" in r
    assert "nunca_pide" in r


def test_canal_case_insensitive():
    r = canal_oficial("bancolombia")
    assert r["encontrada"] is True


def test_canal_entidad_desconocida():
    r = canal_oficial("EntidadQuéNoExiste")
    assert r["encontrada"] is False


def test_canal_ignora_tildes_y_espacios():
    assert canal_oficial("Interrapidisimo")["entidad"] == "Inter Rapidísimo"
    assert canal_oficial("banco de bogota")["entidad"] == "Banco de Bogotá"


def test_canal_nombre_con_sufijo():
    assert canal_oficial("Bancolombia S.A.")["entidad"] == "Bancolombia"


def test_canal_no_confunde_davivienda_con_daviplata():
    assert canal_oficial("Daviplata")["entidad"] == "Daviplata"
    assert canal_oficial("Davivienda")["entidad"] == "Davivienda"
