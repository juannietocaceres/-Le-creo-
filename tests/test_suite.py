"""D15: cálculo de las cuatro cifras, sin llamar al modelo."""
from __future__ import annotations

from eval.correr_suite import calcular_cifras, cargar_casos, evaluar_caso, recuperacion_cumplida
from app.contrato import LlamadaHerramienta, ResultadoAgente

PRECIOS = {"modelo-x": {"entrada_usd_por_millon": 0.30, "salida_usd_por_millon": 2.50}}


def _resultado(herramientas=(), latencia=1000, tin=3000, tout=400, error=None):
    return ResultadoAgente(ok=error is None, error=error, latencia_ms=latencia, tokens_in=tin, tokens_out=tout,
                           herramientas=list(herramientas))


def _numero(numero, reportes):
    return LlamadaHerramienta(nombre="buscar_numero", parametros={"numero": numero}, latencia_ms=1,
                              resultado={"numero": numero, "reportes": reportes, "peligroso": reportes >= 3})


def test_recuperacion_cumplida_si_la_herramienta_trajo_el_dato():
    esperada = {"herramienta": "buscar_numero", "debe": {"numero": "+573000000007", "reportes": 2}}
    assert recuperacion_cumplida(esperada, _resultado([_numero("+573000000007", 2)]))


def test_recuperacion_falla_si_trajo_otro_dato_o_no_llamo():
    esperada = {"herramienta": "buscar_numero", "debe": {"numero": "+573000000007", "reportes": 2}}
    assert not recuperacion_cumplida(esperada, _resultado([_numero("+573000000001", 5)]))
    assert not recuperacion_cumplida(esperada, _resultado([]))


def test_las_cuatro_cifras():
    caso_ok = {"id": "a", "esperado": {"semaforo": "rojo"},
               "recuperacion": [{"herramienta": "buscar_numero", "debe": {"numero": "+573000000007"}}]}
    caso_no = {"id": "b", "esperado": {"semaforo": "verde"}, "recuperacion": []}
    caso_err = {"id": "c", "esperado": {"semaforo": "rojo"}, "recuperacion": []}
    registros = [
        evaluar_caso(caso_ok, _resultado([_numero("+573000000007", 2)], latencia=1000), "rojo"),
        evaluar_caso(caso_no, _resultado(latencia=3000), "rojo"),
        evaluar_caso(caso_err, _resultado(latencia=2000, error="timeout"), "error"),
    ]
    c = calcular_cifras(registros, "modelo-x", PRECIOS)
    assert c["tasa_exito"] == {"aciertos": 1, "total": 3, "porcentaje": 33.3}
    assert c["latencia"]["mediana_ms"] == 2000, "mediana, no promedio"
    assert c["recuperacion"] == {"cumplidas": 1, "esperadas": 1, "porcentaje": 100.0}
    # 3000 tokens × 0,30 + 400 × 2,50 por millón = 0,0009 + 0,001 = 0,0019
    assert c["costo_por_tarea"]["promedio_usd"] == 0.0019
    assert c["costo_por_tarea"]["costo_real_usd"] == 0.0


def test_llamadas_de_mas_son_las_herramientas_que_el_caso_no_necesitaba():
    caso = {"id": "c02", "esperado": {"semaforo": "rojo"},
            "recuperacion": [{"herramienta": "buscar_numero", "debe": {"numero": "+573000000007"}}]}
    canal = LlamadaHerramienta(nombre="canal_oficial", parametros={"entidad": "Nequi"}, latencia_ms=1,
                               resultado={"encontrada": True})
    r = evaluar_caso(caso, _resultado([_numero("+573000000007", 2), canal]), "rojo")
    assert r["llamadas_de_mas"] == ["canal_oficial"]
    c = calcular_cifras([r], "modelo-x", PRECIOS)
    assert c["herramientas"] == {"llamadas_por_caso": 2.0, "de_mas": 1, "de_mas_porcentaje": 50.0}


def test_modelo_sin_precio_no_inventa_costo():
    registros = [evaluar_caso({"id": "a", "esperado": {"semaforo": "verde"}}, _resultado(), "verde")]
    assert calcular_cifras(registros, "modelo-sin-precio", PRECIOS)["costo_por_tarea"] is None


def test_casos_traen_recuperacion_con_herramientas_validas():
    validas = {"buscar_numero", "canal_oficial", "revisar_enlace"}
    casos = cargar_casos()
    for c in casos:
        assert "recuperacion" in c, c["id"]
        assert all(e["herramienta"] in validas and e["debe"] for e in c["recuperacion"]), c["id"]
    assert sum(len(c["recuperacion"]) for c in casos) >= 10
