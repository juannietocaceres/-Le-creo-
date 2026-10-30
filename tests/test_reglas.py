"""6 tests de reglas.py: rojo ×2, amarillo ×2, verde ×1, rechazo ×1."""
from __future__ import annotations

from app.contrato import ContratoSalida, LlamadaHerramienta, Tactica
from app.reglas import calcular_semaforo


def _h(nombre: str, resultado: dict) -> LlamadaHerramienta:
    return LlamadaHerramienta(nombre=nombre, parametros={}, resultado=resultado, latencia_ms=0)


# ── RECHAZO ───────────────────────────────────────────────────────────────────

def test_rechazo_fuera_de_alcance():
    contrato = ContratoSalida(fuera_de_alcance=True)
    semaforo, senales = calcular_semaforo(contrato, [])
    assert semaforo == "rechazo"
    assert "fuera_de_alcance" in senales


# ── ROJO ──────────────────────────────────────────────────────────────────────

def test_rojo_enlace_imita_dominio_oficial():
    """Señal dura: revisar_enlace detectó imitación."""
    contrato = ContratoSalida(
        tacticas=[Tactica(id="enlace_disfrazado", evidencia="bancolombia-seguro.co")],
    )
    herramientas = [
        _h("revisar_enlace", {"dominio": "bancolombia-seguro.co", "imita_a": "Bancolombia",
                              "es_acortador": False, "sospechoso": True, "motivo": "contiene marca"}),
    ]
    semaforo, senales = calcular_semaforo(contrato, herramientas)
    assert semaforo == "rojo"
    assert any("Bancolombia" in s for s in senales)


def test_rojo_dos_tacticas_fuertes():
    """Señal dura: 2 tácticas fuertes (urgencia + pide_credenciales)."""
    contrato = ContratoSalida(
        tacticas=[
            Tactica(id="urgencia",          evidencia="su cuenta será bloqueada hoy"),
            Tactica(id="pide_credenciales", evidencia="comparta el código que le llegó"),
        ],
        pide=["codigo"],
    )
    semaforo, senales = calcular_semaforo(contrato, [])
    assert semaforo == "rojo"
    assert any("tácticas fuertes" in s for s in senales)


# ── AMARILLO ──────────────────────────────────────────────────────────────────

def test_amarillo_una_sola_tactica_fuerte():
    """Señal blanda: una sola táctica fuerte sin otras señales duras."""
    contrato = ContratoSalida(
        tacticas=[Tactica(id="urgencia", evidencia="responda antes de las 5 pm")],
    )
    semaforo, senales = calcular_semaforo(contrato, [])
    assert semaforo == "amarillo"
    assert any("urgencia" in s for s in senales)


def test_amarillo_acortador_sin_imitacion():
    """Señal blanda: acortador que no imita ningún dominio oficial."""
    contrato = ContratoSalida()
    herramientas = [
        _h("revisar_enlace", {"dominio": "bit.ly", "imita_a": None,
                              "es_acortador": True, "sospechoso": True, "motivo": "acortador"}),
    ]
    semaforo, senales = calcular_semaforo(contrato, herramientas)
    assert semaforo == "amarillo"
    assert any("acortador" in s for s in senales)


# ── VERDE ─────────────────────────────────────────────────────────────────────

def test_verde_sin_senales():
    """Sin tácticas, sin herramientas con señales → verde."""
    contrato = ContratoSalida()
    semaforo, senales = calcular_semaforo(contrato, [])
    assert semaforo == "verde"
    assert senales == []
