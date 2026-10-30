"""Verifica que cambiar PROVEEDOR en .env selecciona el base_url y modelo correctos."""
from __future__ import annotations

import importlib
import types
from unittest.mock import MagicMock, patch


def _recargar_config(env: dict) -> types.ModuleType:
    """Recarga app.config con variables de entorno controladas."""
    with patch.dict("os.environ", env, clear=False):
        import app.config as cfg
        importlib.reload(cfg)
        return cfg


def test_google_usa_su_base_url():
    cfg = _recargar_config({
        "PROVEEDOR": "google",
        "GOOGLE_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "GOOGLE_API_KEY": "test-key-google",
        "MODELO_GOOGLE": "gemini-2.0-flash",
    })
    assert cfg.base_url() == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert cfg.modelo() == "gemini-2.0-flash"
    assert cfg.api_key() == "test-key-google"


def test_groq_usa_su_base_url():
    cfg = _recargar_config({
        "PROVEEDOR": "groq",
        "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
        "GROQ_API_KEY": "test-key-groq",
        "MODELO_GROQ": "llama-3.3-70b-versatile",
    })
    assert cfg.base_url() == "https://api.groq.com/openai/v1"
    assert cfg.modelo() == "llama-3.3-70b-versatile"
    assert cfg.api_key() == "test-key-groq"


def test_proveedor_llama_openai_con_base_url_correcta():
    """responder() construye OpenAI con el base_url del proveedor configurado."""
    cfg = _recargar_config({
        "PROVEEDOR": "groq",
        "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
        "GROQ_API_KEY": "fake",
        "MODELO_GROQ": "llama-3.3-70b-versatile",
        "FORZAR_ERROR": "",
    })

    mock_completion = MagicMock()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch.dict("os.environ", {"PROVEEDOR": "groq", "GROQ_API_KEY": "fake",
                                    "MODELO_GROQ": "llama-3.3-70b-versatile",
                                    "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
                                    "FORZAR_ERROR": ""}):
        import app.proveedor as prov
        importlib.reload(prov)
        import app.config as cfg2
        importlib.reload(cfg2)

        with patch("app.proveedor.openai.OpenAI", return_value=mock_client) as mock_cls:
            mensajes = [{"role": "user", "content": "hola"}]
            prov.responder(mensajes)

            _, kwargs = mock_cls.call_args
            assert "groq.com" in kwargs["base_url"]

    mock_client.chat.completions.create.assert_called_once()


def test_modelo_sin_configurar_lanza_error():
    cfg = _recargar_config({
        "PROVEEDOR": "google",
        "MODELO_GOOGLE": "",
    })
    try:
        cfg.modelo()
        assert False, "Debería haber lanzado ValueError"
    except ValueError as e:
        assert "MODELO_GOOGLE" in str(e)


def _error_openai(clase, status: int):
    return clase("error de prueba", response=MagicMock(status_code=status, headers={}), body=None)


def test_429_reintenta_y_luego_responde():
    import openai
    import app.proveedor as prov
    ok = MagicMock()
    with patch("app.proveedor.time.sleep") as dormir, \
         patch("app.proveedor.responder", side_effect=[_error_openai(openai.RateLimitError, 429), ok]):
        assert prov.responder_con_reintento([]) is ok
    dormir.assert_called_once_with(1)


def test_429_persistente_da_error_legible():
    import openai
    import app.proveedor as prov
    with patch("app.proveedor.time.sleep"), \
         patch("app.proveedor.responder", side_effect=_error_openai(openai.RateLimitError, 429)):
        try:
            prov.responder_con_reintento([])
            assert False
        except prov.ProveedorError as e:
            assert "429" in str(e)


def test_llave_vacia_da_error_legible_sin_llamar_a_openai():
    import app.proveedor as prov
    with patch("app.config.modelo", return_value="m"), \
         patch("app.config.api_key", return_value=""), \
         patch("app.proveedor.openai.OpenAI") as cliente:
        try:
            prov.responder_con_reintento([])
            assert False
        except prov.ProveedorError as e:
            assert "_API_KEY" in str(e)
    cliente.assert_not_called()


def test_llave_invalida_da_error_legible_sin_reintentar():
    import openai
    import app.proveedor as prov
    with patch("app.proveedor.responder", side_effect=_error_openai(openai.AuthenticationError, 401)) as llamada:
        try:
            prov.responder_con_reintento([])
            assert False
        except prov.ProveedorError as e:
            assert "API key" in str(e)
    assert llamada.call_count == 1
