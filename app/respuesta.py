"""Convierte el resultado del agente en el mensaje que ve la persona (bot de Telegram).

Todo texto que venga del mensaje analizado o del modelo se escapa: es contenido no confiable
y Telegram lo interpretaría como formato HTML.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from html import escape

from app.contrato import ResultadoAgente
from app.db import _clave_entidad

LIMITE_TELEGRAM = 4000  # Telegram admite 4096 caracteres por mensaje

AVISO_VERDE = "No encontramos señales, pero si dudas, llama tú a la línea oficial."

MENSAJES_ERROR = {
    "timeout":             "El análisis tardó más de lo permitido. Inténtalo de nuevo.",
    "iteraciones":         "El agente llegó a su límite de pasos sin terminar el análisis.",
    "presupuesto_agotado": "El análisis superó el presupuesto de tokens. Prueba con un mensaje más corto.",
    "contrato_invalido":   "El modelo no respondió en el formato esperado. Inténtalo de nuevo.",
}

# D19: la primera línea la decide el código según el color, igual que el semáforo.
ORDENES = {
    "rojo":     "🔴 NO pagues ni abras enlaces. Parece una estafa.",
    "amarillo": "🟡 Espera: no pude confirmar que sea real.",
    "verde":    "🟢 No vimos señales de estafa.",
}

_LINEAS = (
    re.compile(r"01\s?8000[\d\s]{5,12}\d"),             # líneas nacionales gratuitas
    re.compile(r"[Ll]ínea (?:de emergencia )?(\d{3})\b"),  # 123 de la Policía
)


def linea_oficial(canales: str) -> str | None:
    """Saca la línea telefónica nacional del texto de canales verificados (nunca del modelo)."""
    for patron in _LINEAS:
        m = patron.search(canales or "")
        if m:
            return " ".join((m.group(1) if m.groups() else m.group(0)).split())
    return None


def _canal_verificado(r: ResultadoAgente, semaforo: str) -> dict | None:
    """Canal oficial a recomendar. En rojo/amarillo solo si el mensaje dice venir de esa entidad:
    en 'mándame plata al Nequi' Nequi es el destino, no quien escribe, y llamarlo no ayuda."""
    suplantada = _clave_entidad(r.contrato.entidad_suplantada or "") if r.contrato else ""
    for h in r.herramientas:
        res = h.resultado if isinstance(h.resultado, dict) else {}
        if h.nombre != "canal_oficial" or not res.get("encontrada"):
            continue
        if semaforo == "verde" or (suplantada and _clave_entidad(res.get("entidad", "")) in suplantada):
            return res
    return None


def _entidad_de_enlace_oficial(r: ResultadoAgente) -> str | None:
    """Dueño de los enlaces del mensaje si TODOS están en la tabla de dominios oficiales."""
    if not r.contrato or not r.contrato.enlaces:
        return None
    revisados = [h.resultado for h in r.herramientas
                 if h.nombre == "revisar_enlace" and isinstance(h.resultado, dict)]
    if len(revisados) < len(r.contrato.enlaces) or not all(x.get("es_oficial") for x in revisados):
        return None
    return revisados[0].get("entidad") or None


def _despejado(r: ResultadoAgente, semaforo: str) -> bool:
    """Verde aunque el modelo vio tácticas: las reglas comprobaron que el enlace es oficial."""
    return bool(semaforo == "verde" and r.contrato and r.contrato.tacticas and _entidad_de_enlace_oficial(r))


_NOMBRES_TACTICAS = {t["id"]: t["nombre"] for t in json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "tacticas.json").read_text(encoding="utf-8"))}


def _dudas(r: ResultadoAgente, maximo: int = 3) -> list[str]:
    """Lo que dejó el mensaje en amarillo, en palabras simples y sacado de datos, no del modelo."""
    c = r.contrato
    dudas: list[str] = []
    if c and "transferencia" in c.pide:
        dudas.append("te piden pagar o transferir dinero")
    oficial = _entidad_de_enlace_oficial(r)
    for h in r.herramientas:
        res = h.resultado if isinstance(h.resultado, dict) else {}
        if h.nombre != "revisar_enlace" or res.get("es_oficial") or not res.get("dominio"):
            continue
        if res.get("imita_a"):
            dudas.append(f"el enlace {res['dominio']} se parece al de {res['imita_a']}, pero no es el suyo")
        elif res.get("es_acortador"):
            dudas.append(f"el enlace {res['dominio']} esconde a dónde lleva")
        else:
            dudas.append(f"el enlace {res['dominio']} no es de ninguna entidad que yo pueda comprobar")
    for t in (c.tacticas if c else []):
        if t.id == "enlace_disfrazado" and (oficial or any("enlace" in d for d in dudas)):
            continue
        dudas.append(f"se parece al truco «{_NOMBRES_TACTICAS.get(t.id, t.id).lower()}»")
    return dudas[:maximo]


def _oficial_que_cobra(r: ResultadoAgente, semaforo: str) -> str | None:
    """Amarillo con enlace oficial: el cobro puede ser real, pero se revisa en la app, no en el mensaje.
    Devuelve la entidad para que la explicación no acuse de 'inventar' algo que el dato no muestra."""
    return _entidad_de_enlace_oficial(r) if semaforo == "amarillo" else None


def para_llamar(r: ResultadoAgente, semaforo: str) -> dict | None:
    """B3: la línea oficial para el botón "Llamar". Sale de la tabla verificada, nunca del modelo,
    y solo cuando el resumen ya la recomienda (misma regla que `_canal_verificado`)."""
    if semaforo not in ORDENES or r.contrato is None:
        return None
    canal = _canal_verificado(r, semaforo)
    numero = linea_oficial(canal.get("canales", "")) if canal else None
    if not numero:
        return None
    return {"entidad": canal.get("entidad", ""), "numero": numero, "marcar": re.sub(r"\D", "", numero)}


def resumen(r: ResultadoAgente, semaforo: str) -> list[str]:
    """Las tres líneas para una persona mayor: qué hacer, por qué y a quién llamar. Texto plano."""
    lineas = [ORDENES[semaforo]]
    c = r.contrato
    if _despejado(r, semaforo):
        # Las reglas despejaron lo que el modelo sospechaba: su explicación diría lo contrario.
        lineas.append(f"El enlace es de {_entidad_de_enlace_oficial(r)} (dominio oficial comprobado) y el mensaje no te pide "
                      "claves, códigos ni pagos.")
    elif entidad_cobra := _oficial_que_cobra(r, semaforo):
        lineas.append(f"El enlace sí es de {entidad_cobra} (dominio oficial comprobado), pero te piden pagar o "
                      f"entregar algo. Si el cobro es real, también aparece en la app de {entidad_cobra}: "
                      "revísalo ahí y no desde el mensaje.")
    elif semaforo == "amarillo" and (dudas := _dudas(r)):
        # Amarillo = duda, no condena: se dice qué hizo dudar, sin el "te inventan…" del modelo.
        lineas.append("No tengo pruebas de que sea estafa, pero tampoco de que sea real. Me hizo dudar: "
                      + "; ".join(dudas) + ".")
    elif c and c.explicacion:
        lineas.append(c.explicacion)

    canal = _canal_verificado(r, semaforo)
    if canal:
        entidad = canal.get("entidad", "")
        numero = linea_oficial(canal.get("canales", ""))
        if semaforo == "verde":
            lineas.append(f"👉 Si dudas, llama tú a {entidad}: {numero}" if numero else f"👉 {AVISO_VERDE}")
        elif numero:
            lineas.append(f"👉 Llama tú a {entidad}: {numero}. No uses los números del mensaje.")
        else:
            lineas.append(f"👉 No uses los números ni enlaces del mensaje: entra tú mismo a la app o la página oficial de {entidad}.")
    elif semaforo == "verde":
        lineas.append(f"👉 {AVISO_VERDE}")
    elif c and c.que_hacer:
        lineas.append(f"👉 {c.que_hacer}")
    else:
        lineas.append("👉 No respondas ni pagues. Si dudas, pregúntale a alguien de confianza.")
    return lineas


def que_revise(r: ResultadoAgente) -> list[str]:
    """Qué consultó el agente, en texto plano. Quien lo muestre debe escaparlo."""
    lineas = []
    for h in r.herramientas:
        res = h.resultado if isinstance(h.resultado, dict) else {}
        if h.nombre == "revisar_enlace":
            if res.get("imita_a"):
                lineas.append(f"el enlace {res.get('dominio', '')} imita a {res['imita_a']}")
            elif res.get("es_acortador"):
                lineas.append(f"el enlace {res.get('dominio', '')} es acortado y oculta el destino")
            elif res.get("es_oficial"):
                lineas.append(f"el enlace {res.get('dominio', '')} es oficial")
        elif h.nombre == "buscar_numero" and "reportes" in res:
            lineas.append(f"el número {res.get('numero', '')} tiene {res['reportes']} reporte(s)")
        elif h.nombre == "canal_oficial":
            if res.get("encontrada"):
                lineas.append(f"cómo contacta de verdad {res.get('entidad', '')}")
            else:
                lineas.append(f"no pude verificar el canal oficial de {h.parametros.get('entidad', '')}")
    return lineas


def para_web(r: ResultadoAgente, semaforo: str) -> dict:
    """Resultado para la página de compartir, como datos. La página lo pinta con textContent."""
    datos = _para_web(r, semaforo)
    if r.proveedor_usado:   # D17: deja ver en la demo con qué IA salió cada respuesta
        datos["analizado_con"] = " · ".join(x for x in (r.proveedor_usado, r.modelo_usado) if x)
    return datos


def _para_web(r: ResultadoAgente, semaforo: str) -> dict:
    if semaforo == "error" or r.contrato is None:
        if r.error == "contrato_invalido" and r.texto_plano:
            # Sección 11: texto plano con aviso. Sin semáforo, porque no hay señales verificadas.
            lineas = ["⚠️ No pude verificar este análisis: la IA no respondió en el formato esperado.",
                      f"Esto fue lo que dijo, sin revisar: «{r.texto_plano}»",
                      f"👉 {AVISO_VERDE}"]
        else:
            lineas = [MENSAJES_ERROR.get(r.error or "", r.detalle or "No pude revisar el mensaje. Inténtalo de nuevo.")]
        return {"semaforo": "error", "lineas": lineas, "reintentar": r.error == "timeout", "avisos": r.avisos}
    if semaforo == "rechazo":
        return {"semaforo": "rechazo",
                "lineas": ["Solo reviso mensajes sospechosos de WhatsApp o SMS.",
                           "Comparte o pega el mensaje que te llegó y te digo si parece estafa."],
                "avisos": r.avisos}
    c = r.contrato
    lineas = resumen(r, semaforo)
    despejado = _despejado(r, semaforo)  # el consejo y los trucos del modelo contradirían el verde
    return {
        "semaforo": semaforo,
        "lineas": lineas,
        "ademas": c.que_hacer if c.que_hacer and c.que_hacer not in lineas[-1] and not despejado else None,
        "trucos": [] if despejado else
                  [{"nombre": t.id.replace("_", " ").capitalize(), "evidencia": t.evidencia} for t in c.tacticas
                   if not (t.id == "enlace_disfrazado" and _entidad_de_enlace_oficial(r))],
        "revise": que_revise(r),
        "truncado": r.truncado,
        "avisos": r.avisos,
        "llamar": para_llamar(r, semaforo),
    }


def para_telegram(r: ResultadoAgente, semaforo: str) -> str:
    """Mensaje en HTML de Telegram para el resultado de un análisis."""
    if semaforo == "error" or r.contrato is None:
        texto = MENSAJES_ERROR.get(r.error or "", r.detalle or "No pude analizar el mensaje.")
        return f"⚠️ {escape(texto)}"

    c = r.contrato
    if semaforo == "rechazo":
        return ("⚪ Solo reviso mensajes sospechosos de WhatsApp o SMS.\n"
                "Reenvíame el mensaje que te llegó y te digo si parece estafa.")

    orden, *resto = resumen(r, semaforo)
    accion = resto[-1]
    explicacion = resto[:-1]
    partes = ["\n".join([f"<b>{escape(orden)}</b>", *map(escape, explicacion)]), f"<b>{escape(accion)}</b>"]
    despejado = _despejado(r, semaforo)
    if c.que_hacer and c.que_hacer not in accion and not despejado:
        partes.append(f"✅ <b>Además:</b> {escape(c.que_hacer)}")
    if c.tacticas and not despejado:
        trucos = "\n".join(
            f"• {escape(t.id.replace('_', ' ').capitalize())}: <i>«{escape(t.evidencia)}»</i>" for t in c.tacticas
        )
        partes.append(f"🎭 <b>El truco:</b>\n{trucos}")
    revise = que_revise(r)
    if revise:
        partes.append("🔎 <b>Revisé:</b> " + escape("; ".join(revise)) + ".")
    if r.truncado:
        partes.append("<i>El mensaje era muy largo: revisé solo el comienzo.</i>")

    # Si no cabe, se quitan secciones completas desde el final: cortar a mitad de texto
    # podría partir una etiqueta HTML y Telegram rechazaría todo el mensaje.
    while len("\n\n".join(partes)) > LIMITE_TELEGRAM and len(partes) > 1:
        partes.pop()
    return "\n\n".join(partes)
