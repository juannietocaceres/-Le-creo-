"""Convierte el resultado del agente en el mensaje que ve la persona (bot de Telegram).

Todo texto que venga del mensaje analizado o del modelo se escapa: es contenido no confiable
y Telegram lo interpretaría como formato HTML.
"""
from __future__ import annotations

import re
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
    "amarillo": "🟡 Espera antes de pagar o responder: tiene señales sospechosas.",
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


def resumen(r: ResultadoAgente, semaforo: str) -> list[str]:
    """Las tres líneas para una persona mayor: qué hacer, por qué y a quién llamar. Texto plano."""
    lineas = [ORDENES[semaforo]]
    c = r.contrato
    if c and c.explicacion:
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
    if semaforo == "error" or r.contrato is None:
        return {"semaforo": "error",
                "lineas": [MENSAJES_ERROR.get(r.error or "", r.detalle or "No pude revisar el mensaje. Inténtalo de nuevo.")]}
    if semaforo == "rechazo":
        return {"semaforo": "rechazo",
                "lineas": ["Solo reviso mensajes sospechosos de WhatsApp o SMS.",
                           "Comparte o pega el mensaje que te llegó y te digo si parece estafa."]}
    c = r.contrato
    lineas = resumen(r, semaforo)
    return {
        "semaforo": semaforo,
        "lineas": lineas,
        "ademas": c.que_hacer if c.que_hacer and c.que_hacer not in lineas[-1] else None,
        "trucos": [{"nombre": t.id.replace("_", " ").capitalize(), "evidencia": t.evidencia} for t in c.tacticas],
        "revise": que_revise(r),
        "truncado": r.truncado,
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
    if c.que_hacer and c.que_hacer not in accion:
        partes.append(f"✅ <b>Además:</b> {escape(c.que_hacer)}")
    if c.tacticas:
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
