"""Verifica que registrar() escribe JSONL con todos los campos y fila en analisis."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.contrato import ContratoSalida, LlamadaHerramienta, ResultadoAgente
from app.trazas import registrar

pytestmark = pytest.mark.usefixtures("requiere_db")


def _resultado_ejemplo() -> ResultadoAgente:
    return ResultadoAgente(
        contrato=ContratoSalida(
            tacticas=[],
            pide=[],
            explicacion="Sin señales.",
            que_hacer="Si dudas, llama.",
        ),
        ok=True,
        iteraciones=2,
        tokens_in=310,
        tokens_out=95,
        latencia_ms=1450,
        herramientas=[
            LlamadaHerramienta(
                nombre="buscar_numero",
                parametros={"numero": "+573000000001"},
                resultado={"reportes": 5, "peligroso": True},
                latencia_ms=32,
            ),
        ],
        proveedor_usado="groq",
        modelo_usado="llama-3.3-70b-versatile",
    )


def test_registrar_crea_fila_en_analisis(tmp_path: Path):
    """registrar() inserta una fila en analisis y devuelve un id > 0."""
    r = _resultado_ejemplo()
    with patch("app.trazas._TRAZAS_DIR", tmp_path):  # no ensuciar las trazas reales
        fila_id = registrar(r, semaforo="rojo", senales=["número peligroso"], tipo_entrada="texto")
    assert isinstance(fila_id, int)
    assert fila_id > 0


def test_registrar_crea_jsonl_con_campos_obligatorios(tmp_path: Path):
    """La línea JSONL contiene herramientas, orden, parámetros, tokens y latencia."""
    r = _resultado_ejemplo()

    with patch("app.trazas._TRAZAS_DIR", tmp_path):
        fila_id = registrar(r, semaforo="rojo", senales=["número peligroso"])

    archivos = list(tmp_path.glob("*.jsonl"))
    assert len(archivos) == 1

    linea = json.loads(archivos[0].read_text(encoding="utf-8").strip())

    # Campos de trazabilidad
    assert linea["tokens_in"] == 310
    assert linea["tokens_out"] == 95
    assert linea["latencia_ms"] == 1450
    assert linea["iteraciones"] == 2
    assert linea["semaforo"] == "rojo"
    assert linea["ok"] is True
    assert linea["analisis_id"] == fila_id

    # Herramientas con orden y parámetros
    assert len(linea["herramientas"]) == 1
    h = linea["herramientas"][0]
    assert h["orden"] == 1
    assert h["nombre"] == "buscar_numero"
    assert h["parametros"]["numero"] == "+573000000001"
    assert h["latencia_ms"] == 32
    assert "resultado_resumido" in h


def test_jsonl_acumula_multiples_analisis(tmp_path: Path):
    """Dos llamadas a registrar() acumulan dos líneas en el mismo archivo del día."""
    r = _resultado_ejemplo()
    with patch("app.trazas._TRAZAS_DIR", tmp_path):
        registrar(r, semaforo="verde", senales=[])
        registrar(r, semaforo="rojo",  senales=["número peligroso"])

    archivos = list(tmp_path.glob("*.jsonl"))
    assert len(archivos) == 1
    lineas = archivos[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 2


def test_resultado_largo_se_resume(tmp_path: Path):
    """Resultados de herramienta > 500 chars quedan truncados en la traza."""
    resultado_grande = {"dato": "x" * 1000}
    r = ResultadoAgente(
        ok=True,
        iteraciones=1,
        tokens_in=100, tokens_out=50, latencia_ms=200,
        herramientas=[
            LlamadaHerramienta(
                nombre="canal_oficial",
                parametros={"entidad": "Bancolombia"},
                resultado=resultado_grande,
                latencia_ms=10,
            )
        ],
        proveedor_usado="google",
        modelo_usado="gemini-test",
    )
    with patch("app.trazas._TRAZAS_DIR", tmp_path):
        registrar(r, semaforo="verde", senales=[])

    linea = json.loads(list(tmp_path.glob("*.jsonl"))[0].read_text().strip())
    resumido = linea["herramientas"][0]["resultado_resumido"]
    assert len(resumido) <= 510  # 500 + "…"
