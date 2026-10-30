# Semana 9 — App usable

> Actualizado 2026-10-30. Las secciones marcadas **Pendiente** dependen del equipo.

## Dónde vive el agente

- **Para la persona:** una página instalable (`ui/compartir.py` + `ui/web/`) a la que se comparte el mensaje, su captura o la nota de voz desde WhatsApp en Android. Ver `decisiones/publico_y_canal.md`.
- **Para la demo y la auditoría:** la app de Streamlit (`ui/app_streamlit.py`), con "Ver qué hizo el agente".
- **El agente es uno solo** (`app/agente.py`): las dos interfaces lo llaman igual. El proveedor de IA se elige en `.env`.

## Manejo de errores (D13): los tres casos, forzados

Se fuerzan con `FORZAR_ERROR` en `.env` (o como variable de entorno). Demostrados el **2026-10-30** con Gemini y Groq reales sobre el caso c03; **ninguno mostró un stack trace**.

| Situación | Qué hace la app | Cómo se fuerza | Resultado de la demostración |
|---|---|---|---|
| **429 / cuota agotada** | Reintenta con espera creciente (1 s, 2 s, 4 s) y pasa al **proveedor de respaldo** (`PROVEEDOR_RESPALDO`, Groq). Muestra el aviso. Los pasos siguientes del mismo análisis van directo al respaldo. | `FORZAR_ERROR=429` (simula el 429 solo en el principal) | 🔴 correcto, respondió **groq**, aviso visible · 10,9 s |
| **Timeout** | Corta al llegar a los 20 s del análisis y ofrece **🔄 Reintentar** (en la página y en Streamlit). | `FORZAR_ERROR=timeout` (consume el tiempo que quedaba) | "El análisis tardó más de lo permitido" + botón Reintentar · 20,0 s |
| **Salida que no cumple el contrato** | Valida con pydantic, hace **1 reintento** devolviéndole el error al modelo y, si vuelve a fallar, muestra **texto plano con aviso** ("sin revisar") y sin semáforo. | `FORZAR_ERROR=invalida` (la primera respuesta final llega como texto libre) | Se pidió de nuevo y salió 🔴 correcto, con aviso · 9,3 s. El caso de doble fallo (texto plano) está cubierto por pruebas automáticas. |

Cada traza guarda `forzado` (qué error se forzó) y `avisos`, para no mezclar estas pruebas con errores reales al medir cifras.

**Detalle técnico que encontramos:** al pasar de Gemini a Groq a mitad de una conversación hay que quitar la "firma de pensamiento" que Gemini pone en las llamadas a herramientas (`extra_content`); Groq no la conoce.

## Costo

En capa gratuita el costo real es **US$ 0**. El costo equivalente medido en la semana 10 es **US$ 0,001747 por análisis** con `gemini-3.5-flash-lite` (ver `semana10.md`). Las capturas y los audios cuestan más: la lectura de la imagen suma unos 1.000 tokens.

## Prueba del compañero (C8) — Pendiente

Una persona de otro equipo (idealmente un adulto mayor) usa la app sin explicación. Se anota todo lo que hubo que explicarle y qué se cambió.

| Qué tuvimos que explicar | Qué cambiamos |
|---|---|
| *(pendiente)* | *(pendiente)* |
