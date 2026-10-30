"""Registro de trazas: JSONL en disco + fila en tabla analisis."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

from app.config import DATABASE_URL
from app.contrato import ResultadoAgente

_TRAZAS_DIR = Path(__file__).parent.parent / "trazas"
_MAX_RESULTADO = 500  # chars para resumir resultados de herramientas en la traza


def registrar(
    resultado: ResultadoAgente,
    semaforo: str,
    senales: list[str],
    tipo_entrada: str = "texto",
) -> int:
    """Escribe la traza JSONL y la fila en analisis. Devuelve el id de la fila."""
    fila_id = _insertar_analisis(resultado, semaforo, senales, tipo_entrada)
    _escribir_jsonl(resultado, semaforo, senales, tipo_entrada, fila_id)
    return fila_id


# ── JSONL ─────────────────────────────────────────────────────────────────────

def _escribir_jsonl(
    resultado: ResultadoAgente,
    semaforo: str,
    senales: list[str],
    tipo_entrada: str,
    fila_id: int,
) -> None:
    _TRAZAS_DIR.mkdir(parents=True, exist_ok=True)
    archivo = _TRAZAS_DIR / f"{date.today().isoformat()}.jsonl"

    herramientas_log = [
        {
            "orden":            i + 1,
            "nombre":           h.nombre,
            "parametros":       h.parametros,
            "resultado_resumido": _resumir(h.resultado),
            "latencia_ms":      h.latencia_ms,
        }
        for i, h in enumerate(resultado.herramientas)
    ]

    linea: dict[str, Any] = {
        "id":           str(uuid.uuid4()),
        "analisis_id":  fila_id,
        "fecha":        datetime.now(timezone.utc).isoformat(),
        "tipo_entrada": tipo_entrada,
        "proveedor":    resultado.proveedor_usado,
        "modelo":       resultado.modelo_usado,
        "herramientas": herramientas_log,
        "iteraciones":  resultado.iteraciones,
        "tokens_in":    resultado.tokens_in,
        "tokens_out":   resultado.tokens_out,
        "latencia_ms":  resultado.latencia_ms,
        "semaforo":     semaforo,
        "senales":      senales,
        "ok":           resultado.ok,
        "error":        resultado.error,
    }

    with archivo.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")


# ── Base de datos ─────────────────────────────────────────────────────────────

def _insertar_analisis(
    resultado: ResultadoAgente,
    semaforo: str,
    senales: list[str],
    tipo_entrada: str,
) -> int:
    senales_json = json.dumps(senales, ensure_ascii=False)
    with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
        fila = conn.execute(
            """INSERT INTO analisis
                 (tipo_entrada, semaforo, senales, proveedor, modelo,
                  tokens_in, tokens_out, latencia_ms, iteraciones, ok)
               VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (
                tipo_entrada,
                semaforo,
                senales_json,
                resultado.proveedor_usado,
                resultado.modelo_usado,
                resultado.tokens_in,
                resultado.tokens_out,
                resultado.latencia_ms,
                resultado.iteraciones,
                resultado.ok,
            ),
        ).fetchone()
        conn.commit()
    return fila[0]  # type: ignore[index]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resumir(obj: Any) -> str:
    texto = json.dumps(obj, ensure_ascii=False) if not isinstance(obj, str) else obj
    if len(texto) > _MAX_RESULTADO:
        return texto[:_MAX_RESULTADO] + "…"
    return texto
