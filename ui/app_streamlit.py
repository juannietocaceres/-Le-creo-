"""UI principal de ¿Le creo? — Streamlit."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from app import agente, config, reglas, respuesta, trazas
from app.contrato import ContratoSalida, ResultadoAgente

_MARKDOWN = re.compile(r"([\\`*_\[\]()#<>|~!])")


def _md(texto: str) -> str:
    """Escapa markdown: el texto viene del mensaje o del modelo y no puede crear enlaces ni formato."""
    return _MARKDOWN.sub(r"\\\1", texto)

st.set_page_config(page_title="¿Le creo?", page_icon="🔍", layout="centered")

_SEMAFORO_UI = {
    "rojo":     ("🔴", "error",   "Parece estafa"),
    "amarillo": ("🟡", "warning", "Tiene señales sospechosas"),
    "verde":    ("🟢", "success", "No encontramos señales"),
    "rechazo":  ("⚪", "info",    "Esto está fuera de lo que reviso"),
}
_PIDE = {
    "clave": "🔑 Clave", "codigo": "📟 Código de verificación", "transferencia": "💸 Transferencia",
    "datos_personales": "🪪 Datos personales", "clic": "🔗 Clic en enlace",
}


def _metricas(r: ResultadoAgente) -> str:
    return (
        f"Proveedor **{r.proveedor_usado}** · modelo **{r.modelo_usado or '—'}** · "
        f"{r.iteraciones} iter · {r.tokens_in + r.tokens_out} tokens · {r.latencia_ms} ms"
    )


def _mostrar_que_reviso(r: ResultadoAgente, senales: list[str]) -> None:
    for aviso in r.avisos:
        st.caption(f"ℹ️ {_md(aviso)}")
    with st.expander("🔎 Ver qué hizo el agente"):
        st.caption(_metricas(r))
        if not r.herramientas:
            st.caption("No llamó ninguna herramienta en este análisis.")
        for i, h in enumerate(r.herramientas, 1):
            st.markdown(f"**{i}. `{h.nombre}`** · {h.latencia_ms} ms")
            col_p, col_r = st.columns(2)
            with col_p:
                st.caption("Parámetros")
                st.json(h.parametros, expanded=False)
            with col_r:
                st.caption("Resultado")
                st.json(h.resultado, expanded=False)
        if senales:
            st.caption("**Señales que usó la regla del semáforo (reglas.py):**")
            for s in senales:
                st.markdown(f"- {s}")


def _mostrar_error(r: ResultadoAgente) -> None:
    st.error(f"⚠️ {respuesta.MENSAJES_ERROR.get(r.error or '', r.detalle or 'No pudimos analizar el mensaje.')}")
    if r.error == "contrato_invalido" and r.texto_plano:
        st.warning("No pudimos verificar este análisis. Esto fue lo que dijo la IA, **sin revisar**:")
        st.text(r.texto_plano)
        st.info(f"💡 {respuesta.AVISO_VERDE}")
    if r.error == "timeout":
        st.button("Reintentar", on_click=lambda: st.session_state.update(reintentar=True))
    _mostrar_que_reviso(r, [])


def _mostrar_resultado(contrato: ContratoSalida, semaforo: str, senales: list[str], r: ResultadoAgente) -> None:
    emoji, tipo, titulo = _SEMAFORO_UI[semaforo]
    if semaforo != "rechazo":
        titulo = _md(respuesta.ORDENES[semaforo].split(" ", 1)[1])
    getattr(st, tipo)(f"## {emoji} {titulo}")

    if semaforo == "rechazo":
        st.write(
            "Esta app revisa mensajes sospechosos de WhatsApp o SMS antes de que pagues o hagas clic. "
            "No da consejos de inversión, legales ni de otro tipo."
        )
        return

    # D19: primero lo que una persona mayor necesita, grande y en tres líneas.
    _, *resto = respuesta.resumen(r, semaforo)
    accion, explicacion = resto[-1], resto[:-1]
    for linea in explicacion:
        st.markdown(f"#### {_md(linea)}")
    st.info(f"### {_md(accion)}")
    if r.truncado:
        st.caption(f"El mensaje era muy largo: se analizaron los primeros {agente.MAX_TEXTO} caracteres.")

    st.divider()
    if contrato.tacticas:
        st.markdown("#### 🎭 El truco que usa")
        for t in contrato.tacticas:
            st.markdown(f"- **{_md(t.id.replace('_', ' ').capitalize())}** — «{_md(t.evidencia)}»")
    if contrato.entidad_suplantada:
        st.markdown(f"🏦 Dice venir de: **{_md(contrato.entidad_suplantada)}**")
    for h in r.herramientas:
        if h.nombre == "canal_oficial" and isinstance(h.resultado, dict) and not h.resultado.get("encontrada"):
            st.caption(f"No pudimos verificar el canal oficial de «{_md(str(h.parametros.get('entidad', '')))}»: no está en nuestra tabla.")
    if contrato.pide:
        st.markdown("**Te pide:** " + " · ".join(_PIDE.get(p, _md(p)) for p in contrato.pide))
    if contrato.que_hacer and contrato.que_hacer not in accion:
        st.markdown(f"✅ **Además:** {_md(contrato.que_hacer)}")

    _mostrar_que_reviso(r, senales)


# ── Página ────────────────────────────────────────────────────────────────────

st.title("🔍 ¿Le creo?")
st.caption("Una segunda opinión antes de pagar. Pega el mensaje que te llegó y te digo si parece estafa, qué truco usa y qué hacer.")

config.recargar_si_cambio()   # D17: el proveedor se cambia en el .env sin reiniciar
try:
    config.modelo()
    modelo_ok = True
except ValueError:
    modelo_ok = False
    st.warning(f"⚙️ Falta configurar `MODELO_{config.PROVEEDOR.upper()}` y su API key en `.env`.")

texto = st.text_area(
    "Mensaje sospechoso",
    placeholder='Pega aquí el mensaje de WhatsApp o SMS.\n\nEjemplo: "Servientrega: su paquete está retenido. Pague $3.500 aquí: bit.ly/xxxx"',
    height=160,
    label_visibility="collapsed",
)
col_btn, col_info = st.columns([1, 3])
with col_btn:
    analizar = st.button("Analizar", type="primary", disabled=not modelo_ok, use_container_width=True)
with col_info:
    st.caption(f"Proveedor: **{config.PROVEEDOR}** · máx. {config.MAX_ITER} pasos · {config.TIMEOUT_S} s")
st.caption("No guardamos el texto de tu mensaje: solo el resultado y lo que hizo el agente.")

if analizar or st.session_state.pop("reintentar", False):
    if not texto.strip():
        st.warning("Pega un mensaje antes de analizar.")
        st.stop()

    with st.spinner("Revisando el mensaje…"):
        resultado = agente.analizar(texto)

    if resultado.ok and resultado.contrato is not None:
        semaforo, senales = reglas.calcular_semaforo(resultado.contrato, resultado.herramientas)
    else:
        semaforo, senales = "error", []

    try:
        trazas.registrar(resultado, semaforo, senales)
    except Exception:
        st.caption("⚠️ No se pudo guardar la traza de este análisis (¿Postgres está arriba?).")

    st.divider()
    if semaforo == "error":
        _mostrar_error(resultado)
    else:
        _mostrar_resultado(resultado.contrato, semaforo, senales, resultado)
