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


# ── Suplantación: comparación de contactos, no juicio del modelo ─────────────

_BANCOLOMBIA = _h("canal_oficial", {"encontrada": True, "entidad": "Bancolombia",
                                    "canales": "resto del país 01 8000 9 12345; enlaces bancol.co"})


def test_aviso_legitimo_del_banco_sin_contacto_es_verde():
    """c07: 'Bancolombia le informa compra…' sin enlace ni teléfono. Antes salía rojo."""
    contrato = ContratoSalida(entidad_suplantada="Bancolombia")
    assert calcular_semaforo(contrato, [_BANCOLOMBIA])[0] == "verde"


def test_aviso_con_dominio_oficial_es_verde():
    """c09: Inter Rapidísimo con interrapidisimo.com. Antes salía rojo."""
    canal = _h("canal_oficial", {"encontrada": True, "entidad": "Inter Rapidísimo", "canales": "interrapidisimo.com"})
    enlace = _h("revisar_enlace", {"dominio": "interrapidisimo.com", "es_oficial": True, "imita_a": None,
                                   "es_acortador": False})
    contrato = ContratoSalida(entidad_suplantada="Inter Rapidísimo")
    assert calcular_semaforo(contrato, [canal, enlace])[0] == "verde"


def test_entidad_con_telefono_que_no_es_el_oficial_es_rojo():
    """c12: 'Davivienda… comuníquese al 300 000 0002'."""
    contrato = ContratoSalida(entidad_suplantada="Bancolombia", telefonos=["300 000 0002"])
    semaforo, senales = calcular_semaforo(contrato, [_BANCOLOMBIA])
    assert semaforo == "rojo"
    assert any("no es el oficial" in s for s in senales)


def test_entidad_con_su_linea_oficial_no_es_senal():
    contrato = ContratoSalida(entidad_suplantada="Bancolombia", telefonos=["01 8000 9 12345"])
    assert calcular_semaforo(contrato, [_BANCOLOMBIA])[0] == "verde"


def test_entidad_con_enlace_acortado_es_rojo():
    """c01: 'Servientrega… bit.ly/…': el acortador no es el dominio oficial."""
    canal = _h("canal_oficial", {"encontrada": True, "entidad": "Servientrega", "canales": "servientrega.com"})
    enlace = _h("revisar_enlace", {"dominio": "bit.ly", "es_oficial": False, "imita_a": None, "es_acortador": True})
    contrato = ContratoSalida(entidad_suplantada="Servientrega")
    assert calcular_semaforo(contrato, [canal, enlace])[0] == "rojo"
