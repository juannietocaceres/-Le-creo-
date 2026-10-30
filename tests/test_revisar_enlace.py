"""Tests de revisar_enlace — solo reglas, sin LLM. Docker debe estar corriendo."""
from __future__ import annotations

import pytest

from app.herramientas import revisar_enlace, _extraer_dominio, _levenshtein

pytestmark = pytest.mark.usefixtures("requiere_db")


# ── Extracción de dominio ─────────────────────────────────────────────────────

def test_extrae_dominio_con_https():
    assert _extraer_dominio("https://bancolombia-seguro.co/pagar") == "bancolombia-seguro.co"


def test_extrae_dominio_con_http():
    assert _extraer_dominio("http://bit.ly/abc123") == "bit.ly"


def test_extrae_dominio_sin_protocolo():
    assert _extraer_dominio("bancolombia.com") == "bancolombia.com"


def test_extrae_dominio_elimina_www():
    assert _extraer_dominio("https://www.bancolombia.com/home") == "bancolombia.com"


# ── Levenshtein ───────────────────────────────────────────────────────────────

def test_levenshtein_identico():
    assert _levenshtein("bancolombia", "bancolombia") == 0


def test_levenshtein_un_cambio():
    assert _levenshtein("bancolombla", "bancolombia") == 1


def test_levenshtein_distinto():
    assert _levenshtein("nequi", "davivienda") > 2


# ── Criterios D5 (los que pide el criterio sí/no) ────────────────────────────

def test_imitacion_bancolombia():
    """bancolombia-seguro.co debe detectarse como imitación de Bancolombia."""
    r = revisar_enlace("https://bancolombia-seguro.co/actualizar")
    assert r["sospechoso"] is True
    assert r["imita_a"] == "Bancolombia"
    assert r["es_oficial"] is False


def test_acortador_bitly():
    """bit.ly/x debe detectarse como acortador."""
    r = revisar_enlace("http://bit.ly/abc123")
    assert r["es_acortador"] is True
    assert r["sospechoso"] is True


# ── Casos adicionales ─────────────────────────────────────────────────────────

def test_dominio_oficial_no_sospechoso():
    r = revisar_enlace("https://bancolombia.com/login")
    assert r["es_oficial"] is True
    assert r["sospechoso"] is False
    assert r["imita_a"] is None


def test_acortador_tinyurl():
    r = revisar_enlace("https://tinyurl.com/xyz")
    assert r["es_acortador"] is True


def test_punycode_sospechoso():
    r = revisar_enlace("https://xn--bancolmbia-r6a.com")
    assert r["sospechoso"] is True
    assert "punycode" in r["motivo"].lower()


def test_url_limpia_no_sospechosa():
    r = revisar_enlace("https://ejemplo-no-conocido.io/page")
    assert r["sospechoso"] is False
    assert r["imita_a"] is None
    assert r["es_acortador"] is False


def test_imitacion_nequi():
    r = revisar_enlace("http://nequi-soporte.com/verificar")
    assert r["sospechoso"] is True
    assert r["imita_a"] == "Nequi"


# ── Correcciones 2026-10-17 ───────────────────────────────────────────────────

def test_subdominio_oficial_no_es_imitacion():
    r = revisar_enlace("https://sucursal.bancolombia.com/personas")
    assert r["es_oficial"] is True
    assert r["sospechoso"] is False


def test_bancol_co_es_oficial():
    """Bancolombia dice que sus SMS legítimos traen enlaces que empiezan por bancol.co."""
    r = revisar_enlace("https://bancol.co/abc")
    assert r["es_oficial"] is True
    assert r["sospechoso"] is False


def test_arroba_oculta_el_destino_real():
    r = revisar_enlace("https://bancolombia.com@sitio-falso.co/login")
    assert r["dominio"] == "sitio-falso.co"
    assert r["es_oficial"] is False
    assert r["sospechoso"] is True


def test_dominio_falso_que_termina_parecido_no_es_oficial():
    r = revisar_enlace("https://bancolombia.com.pagos-seguros.co")
    assert r["es_oficial"] is False
    assert r["imita_a"] == "Bancolombia"


def test_marca_corta_no_da_falso_positivo():
    """'meridian' contiene 'dian' pero no imita a la DIAN."""
    r = revisar_enlace("https://meridian.com")
    assert r["imita_a"] is None


def test_marca_corta_al_inicio_si_es_imitacion():
    assert revisar_enlace("https://dian-pagos.co")["imita_a"] == "DIAN"


def test_distancia_no_aplica_a_nombres_cortos():
    """'bbc' está a distancia 2 de 'bbva' pero no es una imitación."""
    assert revisar_enlace("https://bbc.com")["imita_a"] is None


def test_typosquatting_una_letra():
    assert revisar_enlace("https://nequl.com.co")["imita_a"] == "Nequi"


def test_puerto_se_ignora():
    assert _extraer_dominio("http://bit.ly:8080/x") == "bit.ly"
