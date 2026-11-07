"""D19: resumen de tres líneas para una persona mayor (orden, por qué, a quién llamar)."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.contrato import ContratoSalida, LlamadaHerramienta, ResultadoAgente
from app.respuesta import AVISO_VERDE, ORDENES, linea_oficial, para_llamar, para_telegram, para_web, resumen

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


# ── B3: botón "Llamar a la línea oficial" ────────────────────────────────────

def test_llamar_trae_la_linea_verificada_lista_para_marcar():
    r = _resultado("Bancolombia", explicacion="Te quieren robar la clave.")
    assert para_llamar(r, "rojo") == {"entidad": "Bancolombia", "numero": "01 8000 9 12345", "marcar": "018000912345"}
    assert para_web(r, "rojo")["llamar"]["marcar"] == "018000912345"


def test_llamar_a_la_policia_marca_123():
    assert para_llamar(_resultado("Policía Nacional"), "rojo")["marcar"] == "123"


def test_sin_linea_conocida_no_hay_boton():
    assert para_llamar(_resultado("Nequi"), "rojo") is None


def test_entidad_que_solo_es_destino_no_da_boton():
    """'Mándame al Nequi' o un banco que no escribe el mensaje: no se ofrece llamarlo."""
    assert para_llamar(_resultado("Bancolombia", suplantada=False), "rojo") is None


def test_el_boton_nunca_sale_del_modelo():
    """Un número que el modelo escriba en que_hacer no se convierte en botón."""
    r = _resultado(None, que_hacer="Llama al 3001234567 ya mismo.")
    assert para_llamar(r, "rojo") is None
    assert para_web(r, "rojo")["llamar"] is None


def test_verde_por_enlace_oficial_no_repite_trucos_ni_consejo_del_modelo():
    """Giro real de Western Union: el modelo vio 'premio inesperado', las reglas lo despejaron."""
    from app.contrato import ContratoSalida, LlamadaHerramienta, Tactica
    from app.agente import ResultadoAgente
    from app import respuesta
    c = ContratoSalida(tacticas=[Tactica(id="premio_inesperado", evidencia="Llegaron 150000 COP")],
                       pide=["clic"], enlaces=["go.wu.com/e/x"],
                       explicacion="Te inventan una transferencia.", que_hacer="No hagas clic.")
    h = [LlamadaHerramienta(nombre="revisar_enlace", parametros={}, latencia_ms=0,
                            resultado={"dominio": "go.wu.com", "es_oficial": True, "entidad": "Western Union"})]
    r = ResultadoAgente(contrato=c, herramientas=h)
    web = respuesta.para_web(r, "verde")
    assert web["trucos"] == [] and web["ademas"] is None
    assert "Western Union" in web["lineas"][1] and "inventan" not in " ".join(web["lineas"])


def test_amarillo_con_enlace_oficial_no_acusa_y_manda_a_la_app():
    """DiDi real cobra una tarifa con enlace de didiglobal.com: sigue 🟡 (piden pagar), sin decir 'inventan'."""
    from app.contrato import ContratoSalida, LlamadaHerramienta, Tactica
    from app.agente import ResultadoAgente
    from app import respuesta
    c = ContratoSalida(tacticas=[Tactica(id="enlace_disfrazado", evidencia="oia.didiglobal.com"),
                                 Tactica(id="pago_anticipado", evidencia="tarifa pendiente")],
                       pide=["transferencia", "clic"], enlaces=["https://oia.didiglobal.com/dlp/x"],
                       explicacion="Te inventan un cobro.")
    h = [LlamadaHerramienta(nombre="revisar_enlace", parametros={}, latencia_ms=0,
                            resultado={"dominio": "oia.didiglobal.com", "es_oficial": True, "entidad": "DiDi"})]
    web = respuesta.para_web(ResultadoAgente(contrato=c, herramientas=h), "amarillo")
    texto = " ".join(web["lineas"])
    assert "inventan" not in texto and "app de DiDi" in texto
    assert [t["nombre"] for t in web["trucos"]] == ["Pago anticipado"]


def test_amarillo_con_un_enlace_no_oficial_explica_la_duda_sin_acusar():
    from app.contrato import ContratoSalida, LlamadaHerramienta
    from app.agente import ResultadoAgente
    from app import respuesta
    c = ContratoSalida(pide=["clic"], enlaces=["didiglobal.com/x", "didi-pagos.xyz/y"], explicacion="Te inventan un cobro.")
    h = [LlamadaHerramienta(nombre="revisar_enlace", parametros={}, latencia_ms=0,
                            resultado={"dominio": d, "es_oficial": o, "entidad": "DiDi" if o else None})
         for d, o in [("didiglobal.com", True), ("didi-pagos.xyz", False)]]
    web = respuesta.para_web(ResultadoAgente(contrato=c, herramientas=h), "amarillo")
    texto = " ".join(web["lineas"])
    assert "inventan" not in texto and "didi-pagos.xyz" in texto and "No tengo pruebas" in texto
