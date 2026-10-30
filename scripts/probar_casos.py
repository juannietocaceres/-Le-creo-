"""D10: corre los primeros N casos de eval/casos.jsonl de punta a punta.

Uso:  python scripts\\probar_casos.py 5 [segundos_de_pausa]
Solo imprime semáforo obtenido vs esperado y deja la traza; las métricas son D15.
La pausa sirve con Groq gratis: 8.000 tokens/minuto alcanzan para ~1 análisis por minuto.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import agente, reglas, trazas

CASOS = Path(__file__).parent.parent / "eval" / "casos.jsonl"


def main(n: int, pausa: float = 0) -> int:
    casos = [json.loads(l) for l in CASOS.read_text(encoding="utf-8").splitlines() if l.strip()][:n]
    fallidos = 0
    for i, caso in enumerate(casos):
        if i and pausa:
            time.sleep(pausa)
        r = agente.analizar(caso["entrada"])
        if r.ok and r.contrato is not None:
            semaforo, senales = reglas.calcular_semaforo(r.contrato, r.herramientas)
        else:
            semaforo, senales = "error", []
        trazas.registrar(r, semaforo, senales)

        esperado = caso["esperado"]["semaforo"]
        coincide = semaforo == esperado
        fallidos += not coincide
        herramientas = ", ".join(h.nombre for h in r.herramientas) or "ninguna"
        detalle = f" ({r.error}: {r.detalle})" if r.error else ""
        print(f"{caso['id']}  {'OK ' if coincide else 'NO '} obtenido={semaforo:<8} esperado={esperado:<8} "
              f"herramientas=[{herramientas}] {r.latencia_ms} ms{detalle}")
    print(f"\n{len(casos) - fallidos}/{len(casos)} coinciden con el esperado.")
    return 0


if __name__ == "__main__":
    sys.exit(main(
        int(sys.argv[1]) if len(sys.argv) > 1 else 5,
        float(sys.argv[2]) if len(sys.argv) > 2 else 0,
    ))
