"""C5: revisa eval/casos_reales.jsonl antes de subirlo. Ningún dato real de una persona entra al repo.

Uso:  python scripts/validar_casos_reales.py [archivo]
Sale con código 1 si algo falla y dice qué línea arreglar.

Qué revisa:
  - Campos obligatorios y valores permitidos.
  - Teléfonos: solo los ficticios +5730000000XX (regla 7 del proyecto).
  - Otras cifras largas (MTCN, guías, cuentas, cédulas): solo de relleno, como 1234567890 o 0000000.
  - Correos: solo @ejemplo.com o de un dominio oficial de la tabla.
No puede ver nombres propios ni rutas de enlaces: esos los muestra para que una persona los revise.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "eval" / "casos_reales.jsonl"
EQUIPO = {"Diego", "Anderson", "Angela"}
CAMPOS = {"id", "tipo", "entrada", "es_estafa", "como_se_supo", "recolectado_por", "fecha", "anonimizado"}
TELEFONO_FICTICIO = re.compile(r"^(57)?30000000\d\d$")
RELLENO = ("1234567890" * 3, "0" * 30)
ES_MONTO = re.compile(r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d+[.,]\d{2}")


def _dominios_oficiales() -> set[str]:
    with open(RAIZ / "data" / "semillas" / "dominios_oficiales.csv", encoding="utf-8") as f:
        return {fila["dominio"] for fila in csv.DictReader(f)}


def problemas_de(caso: dict, oficiales: set[str]) -> list[str]:
    malos: list[str] = []
    faltan = CAMPOS - caso.keys()
    if faltan:
        malos.append(f"faltan campos: {', '.join(sorted(faltan))}")
    if not re.fullmatch(r"r\d{2,3}", str(caso.get("id", ""))):
        malos.append("id debe ser r01, r02…")
    if caso.get("tipo") not in {"texto"}:
        malos.append("tipo debe ser 'texto' (los audios y fotos se transcriben)")
    if not isinstance(caso.get("es_estafa"), bool):
        malos.append("es_estafa debe ser true o false (si no estás seguro, no incluyas el mensaje)")
    if len(str(caso.get("como_se_supo", ""))) < 15:
        malos.append("como_se_supo: explica cómo sabes si era estafa (p. ej. 'el banco confirmó por la app')")
    if caso.get("recolectado_por") not in EQUIPO:
        malos.append(f"recolectado_por debe ser uno de {sorted(EQUIPO)}")
    if caso.get("anonimizado") is not True:
        malos.append("anonimizado debe ser true: cambia nombres, números y enlaces antes de entregar")

    texto = str(caso.get("entrada", ""))
    for bloque in re.findall(r"\+?\d[\d .\-]{5,}\d", texto):
        cifras = re.sub(r"\D", "", bloque)
        if len(cifras) < 7 or ES_MONTO.fullmatch(bloque.strip()):
            continue  # los montos ($1.200.000, 150000.00) no identifican a nadie
        if TELEFONO_FICTICIO.match(cifras):
            continue
        if any(r.startswith(cifras) for r in RELLENO):
            continue
        malos.append(f"cifra que parece real: «{bloque.strip()}» → usa +57 300 000 00XX o 1234567890")
    for correo in re.findall(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", texto):
        dominio = correo.lower()
        if dominio != "ejemplo.com" and not any(dominio == d or dominio.endswith("." + d) for d in oficiales):
            malos.append(f"correo con dominio {dominio}: cámbialo a algo@ejemplo.com")
    return malos


def para_revisar_a_mano(caso: dict) -> list[str]:
    texto = str(caso.get("entrada", ""))
    enlaces = re.findall(r"(?:https?://)?[\w-]+(?:\.[\w-]+)+/\S+", texto)
    return [f"ruta de enlace (¿cambiaste el código final?): {e}" for e in enlaces]


def main(ruta: Path = ARCHIVO) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    oficiales = _dominios_oficiales()
    lineas = [l for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids: set[str] = set()
    errores = 0
    for n, linea in enumerate(lineas, 1):
        try:
            caso = json.loads(linea)
        except json.JSONDecodeError as exc:
            print(f"línea {n}: no es JSON válido ({exc.msg})")
            errores += 1
            continue
        malos = problemas_de(caso, oficiales)
        if caso.get("id") in ids:
            malos.append(f"id repetido: {caso.get('id')}")
        ids.add(caso.get("id"))
        for m in malos:
            print(f"línea {n} ({caso.get('id', '?')}): ✗ {m}")
        for m in para_revisar_a_mano(caso):
            print(f"línea {n} ({caso.get('id', '?')}): revisa a mano · {m}")
        errores += len(malos)
    estafas = sum(1 for l in lineas if '"es_estafa": true' in l)
    print(f"\n{len(lineas)} casos ({estafas} estafas, {len(lineas) - estafas} legítimos) · "
          + ("✓ listo para subir" if not errores else f"✗ {errores} cosas por arreglar"))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ARCHIVO))
