"""Servidor de 'Compartir con ¿Le creo?' levantado de verdad, con el agente simulado."""
from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

import pytest

from app.contrato import ContratoSalida, LlamadaHerramienta, ResultadoAgente, Tactica
from app.respuesta import ORDENES
from ui import compartir

TEXTO = "Bancolombia: actualice sus datos en bancolombia-actualizacion.co"
ROJO = ResultadoAgente(
    ok=True,
    contrato=ContratoSalida(
        entidad_suplantada="Bancolombia",
        tacticas=[Tactica(id="autoridad_falsa", evidencia="Bancolombia: actualice")],
        explicacion="Te quieren llevar a una página falsa.",
        que_hacer="No abras el enlace.",
    ),
    herramientas=[LlamadaHerramienta(
        nombre="canal_oficial", parametros={"entidad": "Bancolombia"}, latencia_ms=1,
        resultado={"encontrada": True, "entidad": "Bancolombia", "canales": "resto del país 01 8000 9 12345"},
    ), LlamadaHerramienta(
        nombre="revisar_enlace", parametros={"url": "bancolombia-actualizacion.co"}, latencia_ms=1,
        resultado={"dominio": "bancolombia-actualizacion.co", "es_oficial": False, "imita_a": "Bancolombia",
                   "es_acortador": False},
    )],
)


@pytest.fixture
def servidor():
    compartir._recientes.clear()
    srv = compartir.crear_servidor(0)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.status, dict(r.headers), r.read().decode("utf-8")


def _post(url, cuerpo: bytes, tipo: str):
    req = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": tipo})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def _api(base, texto):
    return _post(f"{base}/api/analizar", json.dumps({"texto": texto}).encode(), "application/json")


def test_no_se_pueden_levantar_dos_servidores_en_el_mismo_puerto(servidor):
    """En Windows, SO_REUSEADDR permitía un segundo servidor 'encima' sin error."""
    puerto = int(servidor.rsplit(":", 1)[1])
    with pytest.raises(OSError):
        compartir.crear_servidor(puerto)


def test_pagina_principal_con_manifiesto_y_cabeceras_de_seguridad(servidor):
    estado, cab, html = _get(servidor + "/")
    assert estado == 200
    assert 'rel="manifest"' in html
    assert "script-src 'self'" in cab["Content-Security-Policy"]
    assert cab["X-Content-Type-Options"] == "nosniff"


def test_manifiesto_declara_share_target_por_post(servidor):
    _, _, cuerpo = _get(servidor + "/manifest.webmanifest")
    m = json.loads(cuerpo)
    assert m["share_target"]["method"] == "POST", "el texto no debe viajar en la URL"
    assert m["share_target"]["action"] == "/compartir"
    assert m["share_target"]["params"]["text"] == "text"
    assert {i["sizes"] for i in m["icons"]} == {"192x192", "512x512"}


@pytest.mark.parametrize("ruta", ["/../app/config.py", "/..%2f.env", "/.env", "/web/index.html"])
def test_no_sirve_archivos_fuera_de_la_lista(servidor, ruta):
    with pytest.raises(urllib.error.HTTPError) as e:
        _get(servidor + ruta)
    assert e.value.code == 404


def test_compartir_incrusta_el_texto_en_la_pagina(servidor):
    cuerpo = urllib.parse.urlencode({"title": "", "text": TEXTO, "url": ""}).encode()
    estado, html = _post(servidor + "/compartir", cuerpo, "application/x-www-form-urlencoded")
    assert estado == 200
    dato = re.search(r'<script id="compartido" type="application/json">(.*?)</script>', html).group(1)
    assert json.loads(dato) == {"origen": "texto", "texto": TEXTO}


def test_compartir_junta_texto_y_url(servidor):
    cuerpo = urllib.parse.urlencode({"text": "Pague aquí", "url": "https://bit.ly/x"}).encode()
    _, html = _post(servidor + "/compartir", cuerpo, "application/x-www-form-urlencoded")
    dato = re.search(r'type="application/json">(.*?)</script>', html).group(1)
    assert json.loads(dato)["texto"] == "Pague aquí\nhttps://bit.ly/x"


def test_un_mensaje_con_script_no_puede_inyectar_codigo(servidor):
    malicioso = 'hola</script><script>alert(1)</script>'
    cuerpo = urllib.parse.urlencode({"text": malicioso}).encode()
    _, html = _post(servidor + "/compartir", cuerpo, "application/x-www-form-urlencoded")
    assert "<script>alert(1)" not in html
    assert html.count("<script") == 2, "solo los dos scripts propios de la página"
    dato = re.search(r'type="application/json">(.*?)</script>', html).group(1)
    assert json.loads(dato)["texto"] == malicioso


# ── D11: capturas ─────────────────────────────────────────────────────────────

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


def _multipart(campos: dict[str, str], imagen: bytes | None, nombre_archivo="captura.png", tipo="image/png"):
    limite = "----lecreo1234"
    partes = []
    for k, v in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    if imagen is not None:
        partes.append(
            f'--{limite}\r\nContent-Disposition: form-data; name="imagen"; filename="{nombre_archivo}"\r\n'
            f"Content-Type: {tipo}\r\n\r\n".encode() + imagen + b"\r\n"
        )
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def _extraido(texto=TEXTO):
    from app.entradas import TextoExtraido
    return TextoExtraido(texto=texto, tokens_in=900, tokens_out=60, latencia_ms=800)


def test_manifiesto_acepta_imagenes_por_multipart(servidor):
    _, _, cuerpo = _get(servidor + "/manifest.webmanifest")
    st = json.loads(cuerpo)["share_target"]
    assert st["enctype"] == "multipart/form-data"
    assert st["params"]["files"][0]["name"] == "archivo"


def test_compartir_texto_por_multipart_tambien_funciona(servidor):
    cuerpo, tipo = _multipart({"text": TEXTO}, None)
    _, html = _post(servidor + "/compartir", cuerpo, tipo)
    dato = re.search(r'type="application/json">(.*?)</script>', html).group(1)
    assert json.loads(dato) == {"origen": "texto", "texto": TEXTO}


def test_compartir_captura_llega_con_el_resultado_y_traza_tipo_imagen(servidor):
    cuerpo, tipo = _multipart({"text": ""}, PNG)
    with patch("app.entradas.texto_de_archivo", return_value=_extraido()) as leer, \
         patch("app.agente.analizar", return_value=ROJO) as analizar, \
         patch("app.trazas.registrar") as registrar:
        _, html = _post(servidor + "/compartir", cuerpo, tipo)
    leer.assert_called_once_with(PNG)
    analizar.assert_called_once_with(TEXTO)
    assert registrar.call_args.kwargs["tipo_entrada"] == "imagen"
    resultado_registrado = registrar.call_args.args[0]
    assert resultado_registrado.tokens_in >= 900, "el costo de leer la imagen entra en la traza"
    dato = json.loads(re.search(r'type="application/json">(.*?)</script>', html).group(1))
    assert dato["origen"] == "imagen"
    assert dato["resultado"]["semaforo"] == "rojo"
    assert dato["resultado"]["leido"] == TEXTO


def test_api_analizar_archivo_con_captura(servidor):
    cuerpo, tipo = _multipart({}, PNG)
    with patch("app.entradas.texto_de_archivo", return_value=_extraido()), \
         patch("app.agente.analizar", return_value=ROJO), patch("app.trazas.registrar"):
        estado, respuesta_json = _post(servidor + "/api/analizar_archivo", cuerpo, tipo)
    datos = json.loads(respuesta_json)
    assert estado == 200
    assert datos["lineas"][0] == ORDENES["rojo"]
    assert datos["leido"] == TEXTO


def test_api_imagen_sin_texto_pide_otra_sin_llamar_al_agente(servidor):
    from app.entradas import EntradaInvalida
    cuerpo, tipo = _multipart({}, PNG)
    with patch("app.entradas.texto_de_archivo", side_effect=EntradaInvalida("No pude leer texto en esa imagen.")), \
         patch("app.agente.analizar") as analizar:
        _, respuesta_json = _post(servidor + "/api/analizar_archivo", cuerpo, tipo)
    analizar.assert_not_called()
    datos = json.loads(respuesta_json)
    assert datos["semaforo"] == "error"
    assert "No pude leer texto" in datos["lineas"][0]


def test_api_imagen_sin_archivo(servidor):
    cuerpo, tipo = _multipart({"text": "hola"}, None)
    estado, _ = _post(servidor + "/api/analizar_archivo", cuerpo, tipo)
    assert estado == 400


def test_api_imagen_demasiado_grande(servidor):
    cuerpo, tipo = _multipart({}, PNG + b"\x00" * (compartir.MAX_CUERPO_ARCHIVO + 10))
    with patch("app.entradas.texto_de_archivo") as leer:
        estado, _ = _post(servidor + "/api/analizar_archivo", cuerpo, tipo)
    assert estado == 413
    leer.assert_not_called()


# ── D12: notas de voz ─────────────────────────────────────────────────────────

OGG = b"OggS" + b"\x00" * 300


def test_compartir_nota_de_voz_llega_con_el_resultado_y_traza_tipo_audio(servidor):
    from app.entradas import TextoExtraido
    extraido = TextoExtraido(texto=TEXTO, tokens_in=0, tokens_out=0, latencia_ms=900, tipo="audio")
    cuerpo, tipo = _multipart({}, OGG, nombre_archivo="PTT-20261030.opus", tipo="audio/ogg")
    with patch("app.entradas.texto_de_archivo", return_value=extraido) as leer, \
         patch("app.agente.analizar", return_value=ROJO), \
         patch("app.trazas.registrar") as registrar:
        _, html = _post(servidor + "/compartir", cuerpo, tipo)
    leer.assert_called_once_with(OGG)
    assert registrar.call_args.kwargs["tipo_entrada"] == "audio"
    dato = json.loads(re.search(r'type="application/json">(.*?)</script>', html).group(1))
    assert dato["origen"] == "audio"
    assert dato["resultado"]["tipo"] == "audio"
    assert dato["resultado"]["leido"] == TEXTO


def test_manifiesto_acepta_notas_de_voz(servidor):
    _, _, cuerpo = _get(servidor + "/manifest.webmanifest")
    aceptados = json.loads(cuerpo)["share_target"]["params"]["files"][0]["accept"]
    assert "audio/ogg" in aceptados and ".opus" in aceptados


def test_api_devuelve_la_orden_primero_y_guarda_traza(servidor):
    with patch("app.agente.analizar", return_value=ROJO) as analizar, \
         patch("app.trazas.registrar") as registrar:
        estado, cuerpo = _api(servidor, TEXTO)
    datos = json.loads(cuerpo)
    assert estado == 200
    analizar.assert_called_once_with(TEXTO)
    registrar.assert_called_once()
    assert datos["semaforo"] == "rojo"
    assert datos["lineas"][0] == ORDENES["rojo"]
    assert "01 8000 9 12345" in datos["lineas"][-1]
    assert datos["trucos"][0]["evidencia"] == "Bancolombia: actualice"


def test_api_texto_vacio_no_llama_al_agente(servidor):
    with patch("app.agente.analizar") as analizar:
        _, cuerpo = _api(servidor, "   ")
    analizar.assert_not_called()
    assert json.loads(cuerpo)["semaforo"] == "vacio"


def test_api_error_del_agente_sin_detalle_tecnico(servidor):
    with patch("app.agente.analizar", return_value=ResultadoAgente(ok=False, error="timeout")), \
         patch("app.trazas.registrar"):
        _, cuerpo = _api(servidor, TEXTO)
    datos = json.loads(cuerpo)
    assert datos["semaforo"] == "error"
    assert "Traceback" not in cuerpo


def test_api_rechaza_mensajes_enormes(servidor):
    with patch("app.agente.analizar") as analizar:
        estado, _ = _api(servidor, "x" * 20_000)
    assert estado == 413
    analizar.assert_not_called()


def test_api_limita_analisis_por_minuto(servidor):
    with patch("app.agente.analizar", return_value=ROJO) as analizar, patch("app.trazas.registrar"):
        estados = [_api(servidor, TEXTO)[0] for _ in range(compartir.MAX_ANALISIS_POR_MINUTO + 1)]
    assert analizar.call_count == compartir.MAX_ANALISIS_POR_MINUTO
    assert estados[-1] == 429


def test_parametros_en_la_url_se_registran_sin_su_valor(servidor, capsys):
    _get(servidor + "/?" + urllib.parse.urlencode({"text": TEXTO, "title": "x"}))
    salida = capsys.readouterr().out
    assert "parámetros: text,title" in salida
    assert "bancolombia-actualizacion" not in salida


def test_el_texto_nunca_aparece_en_la_consola(servidor, capsys):
    with patch("app.agente.analizar", return_value=ROJO), patch("app.trazas.registrar"):
        _api(servidor, TEXTO)
        cuerpo = urllib.parse.urlencode({"text": TEXTO}).encode()
        _post(servidor + "/compartir", cuerpo, "application/x-www-form-urlencoded")
    salida = capsys.readouterr().out
    assert "bancolombia-actualizacion" not in salida
    assert "rojo" in salida
