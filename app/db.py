"""Conexión a Postgres. Las herramientas del agente solo hacen SELECT.

Las únicas escrituras (al final) son las que la persona aprueba con un clic (D14); el agente
no tiene forma de llamarlas.
"""
from __future__ import annotations

import unicodedata
from contextlib import contextmanager
from typing import Any

import psycopg

from app.config import DATABASE_URL


@contextmanager
def conexion():
    # Si Postgres no responde, falla en segundos en vez de consumir el timeout del análisis.
    with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
        yield conn


def buscar_numero(numero: str) -> dict[str, Any]:
    """Devuelve reportes del número. Si no existe, reportes=0."""
    with conexion() as conn:
        fila = conn.execute(
            "SELECT reportes, ultimo_reporte FROM numeros_reportados WHERE numero = %s",
            (numero,),
        ).fetchone()

    if fila is None:
        return {
            "numero": numero,
            "reportes": 0,
            "peligroso": False,
            "ultimo_reporte": None,
            "nota": "Sin reportes no significa seguro.",
        }
    return {
        "numero": numero,
        "reportes": fila[0],
        "peligroso": fila[0] >= 3,
        "ultimo_reporte": str(fila[1]) if fila[1] else None,
    }


def dominios_oficiales() -> list[tuple[str, str]]:
    """Devuelve todos los dominios oficiales como lista de (dominio, entidad)."""
    with conexion() as conn:
        filas = conn.execute("SELECT dominio, entidad FROM dominios_oficiales").fetchall()
    return [(f[0], f[1]) for f in filas]


def es_acortador(dominio: str) -> bool:
    """True si el dominio está en la tabla de acortadores."""
    with conexion() as conn:
        fila = conn.execute(
            "SELECT 1 FROM acortadores WHERE dominio = %s", (dominio,)
        ).fetchone()
    return fila is not None


def _clave_entidad(texto: str) -> str:
    """'Inter Rapidísimo' → 'interrapidisimo'; ignora tildes, mayúsculas y signos."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c for c in sin_tildes.lower() if c.isalnum())


def canal_oficial(entidad: str) -> dict[str, Any]:
    """Devuelve canales oficiales de la entidad.

    Coincidencia exacta normalizada; si no hay, la entidad de la tabla más larga
    contenida en el nombre recibido (ej. 'Bancolombia S.A.' → Bancolombia).
    """
    with conexion() as conn:
        filas = conn.execute(
            """SELECT entidad, sector, canales, nunca_pide, fuente_url, verificado_en
               FROM canales_oficiales"""
        ).fetchall()

    buscada = _clave_entidad(entidad)
    fila = next((f for f in filas if _clave_entidad(f[0]) == buscada), None)
    if fila is None and buscada:
        contenidas = [f for f in filas if _clave_entidad(f[0]) and _clave_entidad(f[0]) in buscada]
        fila = max(contenidas, key=lambda f: len(_clave_entidad(f[0])), default=None)

    if fila is None:
        return {"encontrada": False, "entidad": entidad}
    return {
        "encontrada": True,
        "entidad":       fila[0],
        "sector":        fila[1],
        "canales":       fila[2],
        "nunca_pide":    fila[3],
        "fuente_url":    fila[4],
        "verificado_en": str(fila[5]),
    }


# ── Escrituras aprobadas por la persona (D14) ─────────────────────────────────

def registrar_reporte(numero: str) -> int:
    """Suma un reporte aprobado al número y devuelve el total."""
    with conexion() as conn:
        fila = conn.execute(
            """INSERT INTO numeros_reportados (numero, reportes, ultimo_reporte, origen)
               VALUES (%s, 1, CURRENT_DATE, 'usuario')
               ON CONFLICT (numero) DO UPDATE
                 SET reportes = numeros_reportados.reportes + 1, ultimo_reporte = CURRENT_DATE
               RETURNING reportes""",
            (numero,),
        ).fetchone()
        conn.commit()
    return fila[0]


def guardar_feedback(analisis_id: int, usuario_dice: str) -> None:
    """'era_estafa' | 'no_era_estafa' para un análisis ya registrado."""
    with conexion() as conn:
        conn.execute(
            "INSERT INTO feedback (analisis_id, usuario_dice) VALUES (%s, %s)",
            (analisis_id, usuario_dice),
        )
        conn.commit()
