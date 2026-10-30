"""D19: resumen de tres líneas para una persona mayor (orden, por qué, a quién llamar)."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.contrato import ContratoSalida, LlamadaHerramienta, ResultadoAgente
from app.respuesta import AVISO_VERDE, ORDENES, linea_oficial, para_telegram, resumen

CSV = Path(__file__).parent.parent / "data" / "semillas" / "canales_oficiales.csv"
CANALES = {f["entidad"]: f["canales"] for f in csv.DictReader(CSV.open(encoding="utf-8"))}


def _resultado(entidad: str | None, suplantada: bool = True, **contrato) -> ResultadoAgente:
    if entidad and suplantada:
        contrato.setdefault("entidad_suplantada", entidad)
    herramientas = []
    if entidad:
        herramientas.append(LlamadaHerramienta(
            nombre="canal_oficial", parametros={"entidad": entidad}, latencia_ms=1,
            resultado={"encontrada": True, "entidad": entidad, "canales": CANALES[entidad]},
        ))
    return ResultadoAgente(ok=True, contrato=ContratoSalida(**contrato), herramientas=herramientas)


@pytest.mark.parametrize("entidad, esperado", [
    ("Bancolombia", "01 8000 9 12345"),
    ("Banco de Bogotá", "01 8000 518 877"),
    ("BBVA", "018000 912 227"),
    ("Policía Nacional", "123"),
    ("Nequi", None),
    ("DIAN", None),
])
def test_linea_oficial_sale_de_los_canales_verificados(entidad, esperado):
    assert linea_oficial(CANALES[entidad]) == esperado


def test_rojo_con_linea_conocida():
    lineas = resumen(_resultado("Bancolombia", explicacion="Te quieren robar la clave."), "rojo")
    assert lineas[0] == ORDENES["rojo"]
    assert lineas[1] == "Te quieren robar la clave."
    assert "Llama tú a Bancolombia: 01 8000 9 12345" in lineas[-1]


def test_entidad_sin_linea_remite_a_su_app_oficial():
    lineas = resumen(_resultado("Nequi"), "rojo")
    assert "app o la página oficial de Nequi" in lineas[-1]


def test_entidad_destino_no_suplantada_no_se_recomienda():
    """'Mándame plata al Nequi': Nequi es el destino, no quien escribe. Manda el consejo del modelo."""
    r = _resultado("Nequi", suplantada=False, que_hacer="Llama a tu hijo al número de siempre.")
    assert resumen(r, "rojo")[-1] == "👉 Llama a tu hijo al número de siempre."


def test_entidad_suplantada_con_sufijo_igual_se_reconoce():
    r = _resultado("Bancolombia", entidad_suplantada="Bancolombia S.A.")
    assert "01 8000 9 12345" in resumen(r, "rojo")[-1]


def test_sin_entidad_usa_que_hacer_del_modelo():
    lineas = resumen(_resultado(None, que_hacer="No respondas el mensaje."), "amarillo")
    assert lineas[0] == ORDENES["amarillo"]
    assert lineas[-1] == "👉 No respondas el mensaje."


def test_verde_sin_entidad_recuerda_la_linea_oficial():
    assert resumen(_resultado(None), "verde")[-1] == f"👉 {AVISO_VERDE}"


def test_verde_con_entidad_da_su_linea():
    assert "Si dudas, llama tú a BBVA: 018000 912 227" in resumen(_resultado("BBVA"), "verde")[-1]


def test_la_orden_no_depende_del_modelo():
    """Aunque el modelo diga que es seguro, la primera línea la fija el semáforo."""
    lineas = resumen(_resultado(None, explicacion="Este mensaje es seguro, págalo."), "rojo")
    assert lineas[0] == ORDENES["rojo"]


def test_telegram_empieza_por_la_orden_en_negrita():
    texto = para_telegram(_resultado("Bancolombia", explicacion="Página falsa."), "rojo")
    assert texto.startswith(f"<b>{ORDENES['rojo']}</b>")
    assert "01 8000 9 12345" in texto
