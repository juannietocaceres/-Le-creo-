"""Ejecuta la app Streamlit real (AppTest) con el agente simulado y hace clic en Analizar."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.contrato import ContratoSalida, LlamadaHerramienta, ResultadoAgente, Tactica

APP = str(Path(__file__).parent.parent / "ui" / "app_streamlit.py")


def _correr(resultado: ResultadoAgente, texto: str = "Servientrega: pague aquí bit.ly/x") -> AppTest:
    with patch("app.config.modelo", return_value="modelo-prueba"), \
         patch("app.agente.analizar", return_value=resultado), \
         patch("app.trazas.registrar", return_value=1) as registrar:
        at = AppTest.from_file(APP, default_timeout=30).run()
        at.text_area[0].input(texto)
        at.button[0].click().run()
    at.registrar = registrar  # type: ignore[attr-defined]
    return at


def _texto(at: AppTest) -> str:
    partes = [e.value for grupo in (at.markdown, at.error, at.warning, at.success, at.info, at.caption) for e in grupo]
    return "\n".join(str(p) for p in partes)


def test_rojo_muestra_semaforo_tacticas_que_hacer_y_que_reviso():
    r = ResultadoAgente(
        ok=True, iteraciones=2, tokens_in=300, tokens_out=80, latencia_ms=900,
        proveedor_usado="google", modelo_usado="modelo-prueba",
        contrato=ContratoSalida(
            entidad_suplantada="Servientrega",
            tacticas=[Tactica(id="paquete_retenido", evidencia="su paquete está retenido")],
            pide=["clic"],
            explicacion="Suplanta a Servientrega y usa un enlace acortado.",
            que_hacer="No abras el enlace. Consulta tu guía en servientrega.com.",
        ),
        herramientas=[LlamadaHerramienta(
            nombre="revisar_enlace", parametros={"url": "bit.ly/x"}, latencia_ms=3,
            resultado={"dominio": "bit.ly", "imita_a": None, "es_acortador": True, "sospechoso": True},
        ), LlamadaHerramienta(
            nombre="canal_oficial", parametros={"entidad": "Servientrega"}, latencia_ms=2,
            resultado={"encontrada": True, "entidad": "Servientrega"},
        )],
    )
    at = _correr(r)
    assert not at.exception, at.exception
    texto = _texto(at)
    assert "🔴" in texto and "NO pagues" in texto          # D19: la orden va primero
    assert "página oficial de Servientrega" in texto       # acción con el canal verificado
    assert "Paquete retenido" in texto                     # táctica con evidencia
    assert "Además" in texto and "servientrega.com" in texto
    assert any("Ver qué hizo el agente" in e.label for e in at.expander)
    assert "revisar_enlace" in texto
    at.registrar.assert_called_once()                      # se pidió guardar la traza


def test_verde_incluye_aviso_de_linea_oficial():
    r = ResultadoAgente(ok=True, contrato=ContratoSalida(explicacion="Aviso de entrega normal."),
                        proveedor_usado="google", modelo_usado="m")
    at = _correr(r, "Inter Rapidísimo: su envío fue entregado")
    assert not at.exception
    assert "🟢" in _texto(at)
    assert "llama tú a la línea oficial" in _texto(at)


def test_rechazo_explica_que_hace_la_app():
    r = ResultadoAgente(ok=True, contrato=ContratoSalida(fuera_de_alcance=True))
    at = _correr(r, "¿Qué cripto compro?")
    assert not at.exception
    assert "fuera de lo que reviso" in _texto(at)


def test_error_se_muestra_sin_stack_trace():
    r = ResultadoAgente(ok=False, error="proveedor", detalle="La API key de google no es válida. Revisa el .env.")
    at = _correr(r)
    assert not at.exception
    assert "API key" in _texto(at)


def test_entidad_no_encontrada_avisa_que_no_se_verifico():
    r = ResultadoAgente(
        ok=True, contrato=ContratoSalida(entidad_suplantada="Banco Inventado"),
        herramientas=[LlamadaHerramienta(nombre="canal_oficial", parametros={"entidad": "Banco Inventado"},
                                         resultado={"encontrada": False}, latencia_ms=1)],
    )
    at = _correr(r, "Banco Inventado le informa...")
    assert not at.exception
    assert "No pudimos verificar el canal oficial" in _texto(at)
