"""D17: cambiar PROVEEDOR en el .env con la app corriendo aplica desde el siguiente análisis."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app import agente, config, respuesta
from app.contrato import ResultadoAgente

_GLOBALES = ("PROVEEDOR", "_BASES", "_KEYS", "_MODELOS", "MAX_ITER", "TIMEOUT_S", "PRESUPUESTO_TOKENS",
             "FORZAR_ERROR", "DATABASE_URL", "TELEGRAM_BOT_TOKEN", "PROVEEDOR_RESPALDO",
             "PROVEEDOR_TRANSCRIPCION", "_marca_env")


@pytest.fixture
def env_temporal(tmp_path):
    """Un .env de prueba; al final se restauran la configuración y las variables de entorno."""
    antes = {g: getattr(config, g) for g in _GLOBALES}
    with patch.dict(os.environ, {}, clear=False):
        ruta = tmp_path / ".env"
        yield ruta
    for g, v in antes.items():
        setattr(config, g, v)


def _escribir(ruta, contenido: str, marca: float) -> None:
    ruta.write_text(contenido, encoding="utf-8")
    os.utime(ruta, (marca, marca))   # fecha explícita: no depende de la resolución del reloj


def test_cambiar_proveedor_en_el_env_aplica_sin_reiniciar(env_temporal):
    _escribir(env_temporal, "PROVEEDOR=google\nMODELO_GOOGLE=m-google\nMODELO_GROQ=m-groq\n", 1_000)
    assert config.recargar_si_cambio(env_temporal) is True
    assert config.PROVEEDOR == "google" and config.modelo() == "m-google"

    _escribir(env_temporal, "PROVEEDOR=groq   # cambio en plena demo\nMODELO_GOOGLE=m-google\nMODELO_GROQ=m-groq\n", 2_000)
    assert config.recargar_si_cambio(env_temporal) is True
    assert config.PROVEEDOR == "groq" and config.modelo() == "m-groq"
    assert config.base_url() == config._BASES["groq"]


def test_sin_cambios_no_vuelve_a_leer(env_temporal):
    _escribir(env_temporal, "PROVEEDOR=groq\n", 1_000)
    assert config.recargar_si_cambio(env_temporal) is True
    config.PROVEEDOR = "parcheado-por-un-test"
    assert config.recargar_si_cambio(env_temporal) is False
    assert config.PROVEEDOR == "parcheado-por-un-test"   # los parches de las pruebas se respetan


def test_la_primera_lectura_no_pisa_el_entorno(env_temporal):
    """Una variable puesta en la consola (p. ej. FORZAR_ERROR para D13) gana al arrancar."""
    os.environ["FORZAR_ERROR"] = "429"
    config._marca_env = None
    _escribir(env_temporal, "FORZAR_ERROR=\n", 1_000)
    config.recargar_si_cambio(env_temporal)
    assert config.FORZAR_ERROR == "429"


def test_env_inexistente_no_falla(env_temporal):
    assert config.recargar_si_cambio(env_temporal) is False


def test_analizar_revisa_el_env_antes_de_cada_analisis():
    with patch.object(config, "recargar_si_cambio") as recargar, \
         patch.object(agente.proveedor, "responder_con_reintento", side_effect=agente.proveedor.ProveedorError("x")):
        agente.analizar("hola")
    recargar.assert_called_once()


def test_la_web_dice_con_que_ia_se_analizo():
    r = ResultadoAgente(ok=False, error="proveedor", proveedor_usado="groq", modelo_usado="m-groq")
    assert respuesta.para_web(r, "error")["analizado_con"] == "groq · m-groq"
