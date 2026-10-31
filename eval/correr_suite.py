"""D15: corre eval/casos.jsonl y calcula las cuatro cifras (sección 12 del documento maestro).

Uso:  python eval\\correr_suite.py [segundos_entre_casos]

  1. Tasa de éxito    → casos con el semáforo esperado (el rechazo debe rechazar) / total
  2. Costo por tarea  → tokens × precio de lista (eval/precios.json), promedio. En capa gratuita
                        el costo real es 0: se reporta el costo EQUIVALENTE.
  3. Latencia         → mediana (no promedio) del tiempo total por análisis
  4. Recuperación     → ¿la herramienta trajo el dato correcto? Se mide aparte de la respuesta final,
                        contra el campo "recuperacion" de cada caso.

Guarda el resultado con fecha en eval/resultados/ y deja la traza de cada análisis.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))

from app import agente, config, herramientas, reglas, trazas
from app.contrato import ResultadoAgente

CASOS = RAIZ / "eval" / "casos.jsonl"
PRECIOS = RAIZ / "eval" / "precios.json"
RESULTADOS = RAIZ / "eval" / "resultados"
ESPERA_TRAS_429 = 30


def cargar_casos() -> list[dict[str, Any]]:
    return [json.loads(l) for l in CASOS.read_text(encoding="utf-8").splitlines() if l.strip()]


def recuperacion_cumplida(esperada: dict[str, Any], resultado: ResultadoAgente) -> bool:
    """Alguna llamada a esa herramienta devolvió todos los campos esperados."""
    for h in resultado.herramientas:
        res = h.resultado if isinstance(h.resultado, dict) else {}
        if h.nombre == esperada["herramienta"] and all(res.get(k) == v for k, v in esperada["debe"].items()):
            return True
    return False


def evaluar_caso(caso: dict[str, Any], resultado: ResultadoAgente, semaforo: str) -> dict[str, Any]:
    esperado = caso["esperado"]["semaforo"]
    recuperacion = [{"esperada": e, "cumplida": recuperacion_cumplida(e, resultado)} for e in caso.get("recuperacion", [])]
    necesarias = {e["herramienta"] for e in caso.get("recuperacion", [])}
    return {
        "id": caso["id"],
        "esperado": esperado,
        "obtenido": semaforo,
        "acierto": semaforo == esperado,
        "error": resultado.error,
        "latencia_ms": resultado.latencia_ms,
        "tokens_in": resultado.tokens_in,
        "tokens_out": resultado.tokens_out,
        "iteraciones": resultado.iteraciones,
        "herramientas": [{"nombre": h.nombre, "parametros": h.parametros} for h in resultado.herramientas],
        "recuperacion": recuperacion,
        # D16: herramientas consultadas que el caso no necesitaba (gastan tokens y tiempo)
        "llamadas_de_mas": [h.nombre for h in resultado.herramientas if h.nombre not in necesarias],
        # Lo que escribió el modelo (los casos son ficticios), para revisar el tono: p. ej. "robes" por "roben"
        "explicacion": resultado.contrato.explicacion if resultado.contrato else None,
        "que_hacer": resultado.contrato.que_hacer if resultado.contrato else None,
    }


def calcular_cifras(registros: list[dict[str, Any]], modelo: str, precios: dict[str, Any]) -> dict[str, Any]:
    total = len(registros)
    aciertos = sum(r["acierto"] for r in registros)
    esperadas = [x for r in registros for x in r["recuperacion"]]
    cumplidas = sum(x["cumplida"] for x in esperadas)
    llamadas = sum(len(r["herramientas"]) for r in registros)
    de_mas = sum(len(r.get("llamadas_de_mas", [])) for r in registros)

    precio = precios.get(modelo)
    costo = None
    if precio:
        por_caso = [
            r["tokens_in"] * precio["entrada_usd_por_millon"] / 1e6 + r["tokens_out"] * precio["salida_usd_por_millon"] / 1e6
            for r in registros
        ]
        costo = {
            "promedio_usd": round(statistics.mean(por_caso), 6),
            "total_usd": round(sum(por_caso), 6),
            "costo_real_usd": 0.0,
            "precio_usado": precio,
        }

    return {
        "tasa_exito": {"aciertos": aciertos, "total": total, "porcentaje": round(100 * aciertos / total, 1) if total else 0.0},
        "costo_por_tarea": costo,
        "latencia": {
            "mediana_ms": int(statistics.median(r["latencia_ms"] for r in registros)) if total else 0,
            "min_ms": min((r["latencia_ms"] for r in registros), default=0),
            "max_ms": max((r["latencia_ms"] for r in registros), default=0),
        },
        "recuperacion": {
            "cumplidas": cumplidas,
            "esperadas": len(esperadas),
            "porcentaje": round(100 * cumplidas / len(esperadas), 1) if esperadas else 0.0,
        },
        "herramientas": {
            "llamadas_por_caso": round(llamadas / total, 2) if total else 0.0,
            "de_mas": de_mas,
            "de_mas_porcentaje": round(100 * de_mas / llamadas, 1) if llamadas else 0.0,
        },
        "tokens_por_caso": round(statistics.mean(r["tokens_in"] + r["tokens_out"] for r in registros)) if total else 0,
    }


def analizar_con_reintento(texto: str) -> ResultadoAgente:
    resultado = agente.analizar(texto)
    if resultado.error == "proveedor" and "429" in (resultado.detalle or ""):
        print(f"    429 del proveedor: espero {ESPERA_TRAS_429} s y reintento una vez")
        time.sleep(ESPERA_TRAS_429)
        resultado = agente.analizar(texto)
    return resultado


def main(pausa: float = 3, repeticiones: int = 1, etiqueta: str = "") -> int:
    casos = cargar_casos()
    precios = json.loads(PRECIOS.read_text(encoding="utf-8"))
    modelo = config.modelo()
    inicio = datetime.now()
    print(f"Suite: {len(casos)} casos × {repeticiones} · {config.PROVEEDOR} / {modelo} · "
          f"{etiqueta or 'sin etiqueta'} · {inicio:%Y-%m-%d %H:%M}\n")

    registros = []
    for rep in range(1, repeticiones + 1):
        for i, caso in enumerate(casos):
            if (i or rep > 1) and pausa:
                time.sleep(pausa)
            resultado = analizar_con_reintento(caso["entrada"])
            if resultado.ok and resultado.contrato is not None:
                semaforo, senales = reglas.calcular_semaforo(resultado.contrato, resultado.herramientas)
            else:
                semaforo, senales = "error", []
            trazas.registrar(resultado, semaforo, senales)
            r = {**evaluar_caso(caso, resultado, semaforo), "repeticion": rep}
            registros.append(r)
            rec = "".join("✓" if x["cumplida"] else "✗" for x in r["recuperacion"]) or "—"
            de_mas = f" de más: {','.join(r['llamadas_de_mas'])}" if r["llamadas_de_mas"] else ""
            print(f"  [{rep}] {r['id']}  {'OK' if r['acierto'] else 'NO'}  obtenido={semaforo:<8} esperado={r['esperado']:<8} "
                  f"recuperación={rec:<3} {r['latencia_ms']:>5} ms{de_mas}"
                  + (f"  ({resultado.error}: {resultado.detalle})" if resultado.error else ""))

    cifras = calcular_cifras(registros, modelo, precios)
    salida = {
        "fecha": inicio.isoformat(timespec="seconds"),
        "etiqueta": etiqueta,
        "proveedor": config.PROVEEDOR,
        "modelo": modelo,
        "casos": len(casos),
        "repeticiones": repeticiones,
        # El texto exacto de las descripciones usadas: cada resultado es reproducible y comparable (D16).
        "descripciones": {e["function"]["name"]: e["function"]["description"] for e in herramientas.ESQUEMAS},
        "cifras": cifras,
        "registros": registros,
    }
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    sufijo = f"_{etiqueta}" if etiqueta else ""
    archivo = RESULTADOS / f"{inicio:%Y-%m-%d_%H%M}_{config.PROVEEDOR}{sufijo}.json"
    archivo.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

    c = cifras
    print(f"\n── Las 4 cifras · {inicio:%Y-%m-%d %H:%M} · {modelo} ──")
    print(f"  1. Tasa de éxito:  {c['tasa_exito']['aciertos']}/{c['tasa_exito']['total']} ({c['tasa_exito']['porcentaje']} %)")
    if c["costo_por_tarea"]:
        print(f"  2. Costo por tarea: US$ {c['costo_por_tarea']['promedio_usd']:.6f} equivalente (real: US$ 0, capa gratuita)")
    else:
        print(f"  2. Costo por tarea: sin precio de lista para {modelo} en eval/precios.json")
    print(f"  3. Latencia:       mediana {c['latencia']['mediana_ms']} ms (mín {c['latencia']['min_ms']}, máx {c['latencia']['max_ms']})")
    print(f"  4. Recuperación:   {c['recuperacion']['cumplidas']}/{c['recuperacion']['esperadas']} ({c['recuperacion']['porcentaje']} %)")
    h = c["herramientas"]
    print(f"  Herramientas:      {h['llamadas_por_caso']} llamadas por caso · {h['de_mas']} de más ({h['de_mas_porcentaje']} %) "
          f"· {c['tokens_por_caso']} tokens por caso")
    print(f"\nGuardado en {archivo.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Suite de evaluación de ¿Le creo? (D15, D16)")
    parser.add_argument("pausa", nargs="?", type=float, default=3, help="segundos entre casos")
    parser.add_argument("--repeticiones", type=int, default=1, help="veces que se corre la suite completa")
    parser.add_argument("--etiqueta", default="", help="nombre de la versión que se mide (p. ej. v1)")
    args = parser.parse_args()
    sys.exit(main(args.pausa, args.repeticiones, args.etiqueta))
