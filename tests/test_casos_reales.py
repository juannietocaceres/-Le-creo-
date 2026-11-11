"""C5: el validador no deja entrar datos reales y el archivo del repo pasa."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validar_casos_reales import ARCHIVO, _dominios_oficiales, main, problemas_de  # noqa: E402

BASE = {"id": "r50", "tipo": "texto", "es_estafa": True, "recolectado_por": "Angela", "fecha": "2026-11-10",
        "como_se_supo": "El banco confirmó por la app que no lo envió", "anonimizado": True}


def _problemas(entrada: str) -> list[str]:
    return problemas_de({**BASE, "entrada": entrada}, _dominios_oficiales())


def test_archivo_del_repo_pasa():
    assert main(ARCHIVO) == 0


def test_telefono_ficticio_y_montos_pasan():
    assert _problemas("Llama al +57 300 000 0099. Te llegaron $1.200.000 y 150000.00 COP") == []


def test_telefono_real_no_pasa():
    assert any("321 456 7890" in p for p in _problemas("Llama al 321 456 7890"))


def test_numero_de_guia_real_no_pasa_y_relleno_si():
    assert _problemas("Guía 7004512398")
    assert _problemas("Guía 1234567890") == []


def test_correo_personal_no_pasa_y_oficial_si():
    assert _problemas("Escribe a juan.perez@gmail.com")
    assert _problemas("Reporta a correosospechoso@bancolombia.com.co") == []
