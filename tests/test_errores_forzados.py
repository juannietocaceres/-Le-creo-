"""D13: los tres errores de la sección 11, forzados con FORZAR_ERROR. Sin llamar a ningún proveedor real."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import openai
import pytest

from app import agente, proveedor, respuesta
from app.contrato import ResultadoAgente

CONTRATO_ROJO = json.dumps({
    "fuera_de_alcance": False, "entidad_suplantada": None,
    "tacticas": [{"id": "urgencia", "evidencia": "hoy mismo"}, {"id": "pide_credenciales", "evidencia": "el código"}],
    "pide": ["codigo"], "enlaces": [], "telefonos": [],
    "explicacion": "Te piden el código con afán.", "que_hacer": "No lo compartas.",
})


def _final(contenido: str = CONTRATO_ROJO) -> MagicMock:
    r = MagicMock()
    r.usage.prompt_tokens, r.usage.completion_tokens = 300, 80
    r.choices = [MagicMock(message=MagicMock(content=contenido, tool_calls=None))]
    return r


def _tool_call() -> MagicMock:
    tc = MagicMock()
    tc.id, tc.function.name, tc.function.arguments = "t1", "canal_oficial", '{"entidad": "Nequi"}'
    tc.model_extra = {"extra_content": {"google": {"thought_signature": "firma"}}}
    r = MagicMock()
    r.usage.prompt_tokens, r.usage.completion_tokens = 300, 20
    r.choices = [MagicMock(message=MagicMock(content=None, tool_calls=[tc]))]
    return r


def _error_429():
    return openai.RateLimitError("429", response=MagicMock(status_code=429, headers={}), body=None)


@pytest.fixture
def config_prueba():
    with patch("app.config.PROVEEDOR", "google"), \
         patch("app.config.respaldo", return_value="groq"), \
         patch("app.config.modelo", side_effect=lambda p=None: f"modelo-{p or 'google'}"), \
         patch("app.config.api_key", return_value="llave"), \
         patch("app.config.MAX_ITER", 5), patch("app.config.TIMEOUT_S", 20):
        yield


# ── 1. Error 429 ──────────────────────────────────────────────────────────────

def test_429_forzado_espera_1_2_4_y_responde_el_respaldo(config_prueba):
    with patch("app.config.FORZAR_ERROR", "429"), \
         patch("app.proveedor.time.sleep") as dormir, \
         patch("app.proveedor.responder", return_value=_final()) as llamar:
        r = agente.analizar("NEQUI: comparte el código hoy mismo")
    assert r.ok is True
    assert [c.args[0] for c in dormir.call_args_list] == [1, 2, 4]
    assert all(c.args[4] == "groq" for c in llamar.call_args_list), "el principal forzado nunca se llama"
    assert r.proveedor_usado == "groq" and r.modelo_usado == "modelo-groq"
    assert any("saturado (429)" in a and "groq" in a for a in r.avisos)


def test_429_real_del_principal_pasa_al_respaldo(config_prueba):
    respuestas = {"google": _error_429(), "groq": _final()}

    def llamar(mensajes, herramientas, timeout, sin_herramientas, p):
        r = respuestas[p]
        if isinstance(r, Exception):
            raise r
        return r

    with patch("app.config.FORZAR_ERROR", ""), patch("app.proveedor.time.sleep"), \
         patch("app.proveedor.responder", side_effect=llamar):
        r = agente.analizar("mensaje")
    assert r.ok and r.proveedor_usado == "groq"


def test_tras_pasar_al_respaldo_los_pasos_siguientes_van_directo(config_prueba):
    with patch("app.config.FORZAR_ERROR", "429"), \
         patch("app.proveedor.time.sleep") as dormir, \
         patch("app.proveedor.responder", side_effect=[_tool_call(), _final()]) as llamar, \
         patch("app.herramientas.DESPACHO", {"canal_oficial": lambda entidad: {"encontrada": False}}):
        r = agente.analizar("NEQUI: dame el código")
    assert r.ok and r.iteraciones == 2
    assert len(dormir.call_args_list) == 3, "solo se espera una vez, no en cada paso"
    assert [c.args[4] for c in llamar.call_args_list] == ["groq", "groq"]


def test_429_sin_respaldo_da_error_legible_sin_excepcion(config_prueba):
    with patch("app.config.FORZAR_ERROR", "429"), patch("app.config.respaldo", return_value=None), \
         patch("app.proveedor.time.sleep"):
        r = agente.analizar("mensaje")
    assert r.ok is False and r.error == "proveedor"
    assert "429" in r.detalle
    datos = respuesta.para_web(r, "error")
    assert datos["semaforo"] == "error" and "Traceback" not in json.dumps(datos)


def test_al_cambiar_de_proveedor_se_quitan_los_campos_de_gemini():
    mensajes = [{"role": "assistant", "content": None, "tool_calls": [
        {"id": "t1", "type": "function", "function": {"name": "x", "arguments": "{}"},
         "extra_content": {"google": {"thought_signature": "firma"}}}]}]
    limpios = proveedor._sin_campos_propios(mensajes)
    assert "extra_content" not in limpios[0]["tool_calls"][0]
    assert "extra_content" in mensajes[0]["tool_calls"][0], "no modifica el original"


# ── 2. Timeout ────────────────────────────────────────────────────────────────

def test_timeout_forzado_corta_y_ofrece_reintentar(config_prueba):
    with patch("app.config.FORZAR_ERROR", "timeout"), \
         patch("app.proveedor.time.sleep") as dormir, \
         patch("app.proveedor.responder") as llamar:
        r = agente.analizar("mensaje")
    llamar.assert_not_called()
    assert 0 < dormir.call_args.args[0] <= 20, "espera lo que quedaba del límite de 20 s"
    assert r.ok is False and r.error == "timeout"
    datos = respuesta.para_web(r, "error")
    assert datos["reintentar"] is True
    assert "tardó más de lo permitido" in datos["lineas"][0]


# ── 3. Salida que no cumple el contrato ───────────────────────────────────────

def test_salida_invalida_forzada_se_pide_de_nuevo_y_se_recupera(config_prueba):
    with patch("app.config.FORZAR_ERROR", "invalida"), \
         patch("app.proveedor.responder_con_reintento", side_effect=[_final(), _final()]) as llamar:
        r = agente.analizar("NEQUI: dame el código")
    assert r.ok is True and r.iteraciones == 2
    assert any("no cumplía el formato" in a for a in r.avisos)
    conversacion = llamar.call_args_list[1].args[0]
    assert any(m["role"] == "user" and "no cumple el contrato" in (m["content"] or "") for m in conversacion), \
        "se le devuelve el error al modelo"


def test_salida_invalida_dos_veces_muestra_texto_plano_con_aviso(config_prueba):
    texto_libre = "Esto parece una estafa, no pagues."
    with patch("app.config.FORZAR_ERROR", ""), \
         patch("app.proveedor.responder_con_reintento", side_effect=[_final("no es json"), _final(texto_libre)]):
        r = agente.analizar("mensaje")
    assert r.ok is False and r.error == "contrato_invalido"
    assert r.texto_plano == texto_libre
    datos = respuesta.para_web(r, "error")
    assert datos["semaforo"] == "error", "sin semáforo: no hay señales verificadas"
    assert "sin revisar" in datos["lineas"][1] and texto_libre in datos["lineas"][1]
    assert "Traceback" not in json.dumps(datos)


# ── Trazas ────────────────────────────────────────────────────────────────────

def test_la_traza_marca_el_error_forzado_y_los_avisos(tmp_path):
    from app import trazas
    r = ResultadoAgente(ok=True, avisos=["google estaba saturado (429): respondió el respaldo, groq."])
    with patch("app.config.FORZAR_ERROR", "429"), patch("app.trazas._TRAZAS_DIR", tmp_path), \
         patch("app.trazas._insertar_analisis", return_value=1):
        trazas.registrar(r, "rojo", [])
    linea = json.loads(next(tmp_path.glob("*.jsonl")).read_text(encoding="utf-8"))
    assert linea["forzado"] == "429"
    assert "saturado" in linea["avisos"][0]
