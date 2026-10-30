"""Bot de Telegram: atender() con Telegram y agente simulados."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.contrato import ContratoSalida, LlamadaHerramienta, ResultadoAgente, Tactica
from app.respuesta import para_telegram
from ui import bot_telegram

TEXTO = "Bancolombia: actualice sus datos en bancolombia-actualizacion.co"

ROJO = ResultadoAgente(
    ok=True, latencia_ms=1200,
    contrato=ContratoSalida(
        entidad_suplantada="Bancolombia",
        tacticas=[Tactica(id="autoridad_falsa", evidencia="Bancolombia: actualice <b>ya</b>")],
        explicacion="Suplanta a Bancolombia con un enlace falso.",
        que_hacer="No abras el enlace.",
    ),
    herramientas=[LlamadaHerramienta(
        nombre="revisar_enlace", parametros={"url": "bancolombia-actualizacion.co"}, latencia_ms=5,
        resultado={"dominio": "bancolombia-actualizacion.co", "imita_a": "Bancolombia", "es_acortador": False},
    )],
)


def _mensaje(**extra):
    base = {"message_id": 7, "chat": {"id": 42, "type": "private"}}
    base.update(extra)
    return base


@pytest.fixture(autouse=True)
def _limpiar_limite():
    bot_telegram._recientes.clear()


def _enviados(enviar: MagicMock, metodo: str = "sendMessage") -> list[dict]:
    return [c.args[1] for c in enviar.call_args_list if c.args[0] == metodo]


def test_texto_reenviado_se_analiza_y_responde_en_el_mismo_chat():
    enviar = MagicMock()
    with patch("app.agente.analizar", return_value=ROJO) as analizar, \
         patch("app.trazas.registrar") as registrar:
        etiqueta = bot_telegram.atender(_mensaje(text=TEXTO), enviar)

    analizar.assert_called_once_with(TEXTO)
    registrar.assert_called_once()
    assert registrar.call_args.kwargs["tipo_entrada"] == "texto"
    (resp,) = _enviados(enviar)
    assert resp["chat_id"] == 42
    assert resp["reply_parameters"]["message_id"] == 7
    assert "🔴" in resp["text"] and "No abras el enlace" in resp["text"]
    assert etiqueta.startswith("rojo")
    assert _enviados(enviar, "sendChatAction"), "debe mostrar 'escribiendo…' mientras analiza"


def test_start_da_bienvenida_sin_analizar():
    enviar = MagicMock()
    with patch("app.agente.analizar") as analizar:
        bot_telegram.atender(_mensaje(text="/start"), enviar)
    analizar.assert_not_called()
    assert "reenvíamelo" in _enviados(enviar)[0]["text"]


def test_foto_sin_texto_pide_el_texto_sin_analizar():
    enviar = MagicMock()
    with patch("app.agente.analizar") as analizar:
        bot_telegram.atender(_mensaje(photo=[{"file_id": "x"}]), enviar)
    analizar.assert_not_called()
    assert "solo puedo leer mensajes de texto" in _enviados(enviar)[0]["text"]


def test_foto_con_pie_de_texto_analiza_el_pie():
    enviar = MagicMock()
    with patch("app.agente.analizar", return_value=ROJO) as analizar, patch("app.trazas.registrar"):
        bot_telegram.atender(_mensaje(photo=[{"file_id": "x"}], caption=TEXTO), enviar)
    analizar.assert_called_once_with(TEXTO)


def test_grupos_se_ignoran_por_privacidad():
    enviar = MagicMock()
    with patch("app.agente.analizar") as analizar:
        etiqueta = bot_telegram.atender({"message_id": 1, "chat": {"id": -5, "type": "group"}, "text": TEXTO}, enviar)
    analizar.assert_not_called()
    enviar.assert_not_called()
    assert "ignorado" in etiqueta


def test_limite_de_3_analisis_por_minuto_por_persona():
    enviar = MagicMock()
    with patch("app.agente.analizar", return_value=ROJO) as analizar, patch("app.trazas.registrar"):
        for _ in range(4):
            bot_telegram.atender(_mensaje(text=TEXTO), enviar)
    assert analizar.call_count == 3
    assert "Dame un minuto" in _enviados(enviar)[-1]["text"]


def test_error_del_agente_responde_sin_detalle_tecnico():
    enviar = MagicMock()
    error = ResultadoAgente(ok=False, error="timeout")
    with patch("app.agente.analizar", return_value=error), patch("app.trazas.registrar"):
        bot_telegram.atender(_mensaje(text=TEXTO), enviar)
    texto = _enviados(enviar)[0]["text"]
    assert "⚠️" in texto and "Traceback" not in texto


def test_traza_que_falla_no_impide_responder():
    enviar = MagicMock()
    with patch("app.agente.analizar", return_value=ROJO), \
         patch("app.trazas.registrar", side_effect=RuntimeError("db caída")):
        bot_telegram.atender(_mensaje(text=TEXTO), enviar)
    assert "🔴" in _enviados(enviar)[0]["text"]


def test_nunca_imprime_el_texto_del_mensaje(capsys):
    """Regla 3: el texto original no queda en ningún registro, tampoco en consola."""
    with patch("app.agente.analizar", return_value=ROJO), \
         patch("app.trazas.registrar", side_effect=RuntimeError("db caída")):
        bot_telegram.atender(_mensaje(text=TEXTO), MagicMock())
    assert "bancolombia-actualizacion" not in capsys.readouterr().out


def test_main_sin_token_avisa_y_sale(capsys):
    with patch("app.config.TELEGRAM_BOT_TOKEN", ""):
        assert bot_telegram.main() == 1
    assert "TELEGRAM_BOT_TOKEN" in capsys.readouterr().out


# ── Formato (app/respuesta.py) ────────────────────────────────────────────────

def test_respuesta_escapa_html_del_mensaje():
    """La evidencia viene del mensaje del estafador: no puede inyectar formato."""
    texto = para_telegram(ROJO, "rojo")
    assert "<b>ya</b>" not in texto
    assert "&lt;b&gt;ya&lt;/b&gt;" in texto


def test_respuesta_muestra_que_reviso():
    assert "imita a Bancolombia" in para_telegram(ROJO, "rojo")


def test_respuesta_verde_incluye_aviso_de_linea_oficial():
    r = ResultadoAgente(ok=True, contrato=ContratoSalida(explicacion="Aviso de entrega."))
    assert "llama tú a la línea oficial" in para_telegram(r, "verde")


def test_respuesta_rechazo_explica_que_hace_el_bot():
    r = ResultadoAgente(ok=True, contrato=ContratoSalida(fuera_de_alcance=True))
    assert "Solo reviso mensajes sospechosos" in para_telegram(r, "rechazo")


def test_respuesta_larga_quita_secciones_completas_sin_romper_html():
    r = ResultadoAgente(ok=True, contrato=ContratoSalida(
        explicacion="corto",
        tacticas=[Tactica(id="urgencia", evidencia="x" * 5000)],
        que_hacer="No pagues.",
    ))
    texto = para_telegram(r, "amarillo")
    assert len(texto) <= 4000
    assert texto.count("<b>") == texto.count("</b>")
    assert "No pagues." in texto
