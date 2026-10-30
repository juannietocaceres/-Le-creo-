"""Carga las semillas de data/semillas/*.csv en Postgres.

Idempotente: reemplaza las tablas de consulta y los números de origen
'semilla_ficticia'; conserva los reportes hechos por usuarios.
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg

from app.config import DATABASE_URL

SEMILLAS = Path(__file__).parent.parent / "data" / "semillas"

ENCABEZADOS = {
    "canales_oficiales.csv":  ["entidad", "sector", "canales", "nunca_pide", "fuente_url", "verificado_en"],
    "dominios_oficiales.csv": ["dominio", "entidad"],
    "acortadores.csv":        ["dominio"],
    "numeros_ficticios.csv":  ["numero", "reportes", "ultimo_reporte", "origen"],
}
SECTORES = {"banco", "billetera", "mensajeria", "gobierno", "otro"}
NUMERO_FICTICIO = re.compile(r"^\+5730000000\d{2}$")


class SemillaInvalida(ValueError):
    pass


def leer(nombre: str) -> list[dict[str, str]]:
    ruta = SEMILLAS / nombre
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        if lector.fieldnames != ENCABEZADOS[nombre]:
            raise SemillaInvalida(f"{nombre}: encabezados {lector.fieldnames}, se esperaba {ENCABEZADOS[nombre]}")
        filas = [{k: (v or "").strip() for k, v in fila.items()} for fila in lector]
    if not filas:
        raise SemillaInvalida(f"{nombre}: no tiene filas")
    return filas


def validar(datos: dict[str, list[dict[str, str]]]) -> None:
    for i, f in enumerate(datos["canales_oficiales.csv"], 2):
        if f["sector"] not in SECTORES:
            raise SemillaInvalida(f"canales_oficiales.csv línea {i}: sector '{f['sector']}' no válido")
        if not f["entidad"] or not f["fuente_url"].startswith("https://"):
            raise SemillaInvalida(f"canales_oficiales.csv línea {i}: falta entidad o fuente_url https")
        date.fromisoformat(f["verificado_en"])

    for i, f in enumerate(datos["dominios_oficiales.csv"], 2):
        if f["dominio"].startswith(("http", "www.")):
            raise SemillaInvalida(f"dominios_oficiales.csv línea {i}: el dominio va sin https:// ni www.")

    for i, f in enumerate(datos["numeros_ficticios.csv"], 2):
        if not NUMERO_FICTICIO.match(f["numero"]):
            raise SemillaInvalida(f"numeros_ficticios.csv línea {i}: '{f['numero']}' no es un número ficticio +5730000000XX")
        if f["origen"] != "semilla_ficticia":
            raise SemillaInvalida(f"numeros_ficticios.csv línea {i}: origen debe ser semilla_ficticia")
        int(f["reportes"])
        date.fromisoformat(f["ultimo_reporte"])


def cargar(conn: psycopg.Connection, datos: dict[str, list[dict[str, str]]]) -> dict[str, int]:
    with conn.transaction():
        conn.execute("TRUNCATE canales_oficiales, dominios_oficiales, acortadores RESTART IDENTITY")
        conn.execute("DELETE FROM numeros_reportados WHERE origen = 'semilla_ficticia'")

        for f in datos["canales_oficiales.csv"]:
            conn.execute(
                """INSERT INTO canales_oficiales (entidad, sector, canales, nunca_pide, fuente_url, verificado_en)
                   VALUES (%(entidad)s, %(sector)s, %(canales)s, %(nunca_pide)s, %(fuente_url)s, %(verificado_en)s)""",
                f,
            )
        for f in datos["dominios_oficiales.csv"]:
            conn.execute(
                "INSERT INTO dominios_oficiales (dominio, entidad) VALUES (%(dominio)s, %(entidad)s)",
                {"dominio": f["dominio"].lower(), "entidad": f["entidad"]},
            )
        for f in datos["acortadores.csv"]:
            conn.execute("INSERT INTO acortadores (dominio) VALUES (%s)", (f["dominio"].lower(),))
        for f in datos["numeros_ficticios.csv"]:
            conn.execute(
                """INSERT INTO numeros_reportados (numero, reportes, ultimo_reporte, origen)
                   VALUES (%(numero)s, %(reportes)s, %(ultimo_reporte)s, %(origen)s)
                   ON CONFLICT (numero) DO NOTHING""",
                f,
            )
    return {nombre: len(filas) for nombre, filas in datos.items()}


if __name__ == "__main__":
    try:
        datos = {nombre: leer(nombre) for nombre in ENCABEZADOS}
        validar(datos)
    except (SemillaInvalida, ValueError, FileNotFoundError) as exc:
        print(f"ERROR en semillas: {exc}")
        sys.exit(1)

    with psycopg.connect(DATABASE_URL) as conn:
        conteo = cargar(conn, datos)
    for nombre, n in conteo.items():
        print(f"  {nombre:<24} {n:>3} filas")
    print("Semillas cargadas OK.")
