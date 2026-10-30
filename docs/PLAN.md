# Plan — ¿Le creo?

> Derivado de `PROYECTO_LE_CREO.md` sección 15.  
> Regla: una tarea a la vez, verificar criterio antes de pasar a la siguiente.

---

## FASE 1 — "El núcleo con texto" · Corte: sábado 17 oct 2026

**Terminada cuando:** pego un mensaje de texto en la web, el agente usa al menos una herramienta, sale semáforo + tácticas + qué hacer + "qué revisé", queda traza JSONL, y las semillas del compañero están cargadas en Postgres.

**NO entra en Fase 1:** imágenes, audio, aprobación real, errores forzados, suite completa, métricas, feedback del usuario, modo familia.

| ID | Tarea | Dueño | Depende de | Criterio (sí/no) | Horas est. | Estado |
|---|---|---|---|---|---|---|
| **D1** ⭐ | Estructura del repo, `CLAUDE.md`, `docker-compose.yml`, `.env.example`, `requirements.txt` | Diego | — | ¿`docker compose up -d` levanta Postgres y conecta? | 1 | ✅ |
| D2 | `db/01_esquema.sql` — 6 tablas | Diego | D1 | ¿`\dt` muestra las 6 tablas? | 1 | ✅ |
| D3 | `proveedor.py`: función `responder()` con Google y Groq por `.env` | Diego | D1 | ¿Cambiando `PROVEEDOR` en `.env` la misma prueba responde con ambos? | 2 | ✅ 2026-10-17: mismos 5 casos → Google (gemini-3.5-flash-lite) 5/5 y Groq (openai/gpt-oss-120b) 5/5, con el catálogo de tácticas inyectado en formato compacto (máx. 6.118 tokens por análisis, bajo el cupo de 8.000/min de Groq) |
| D4 | `buscar_numero` y `canal_oficial` + tests | Diego | D2 | ¿Los tests con datos de semilla pasan? | 2 | ✅ |
| D5 | `revisar_enlace` (solo reglas, sin LLM) + tests | Diego | D2 | ¿`bancolombia-seguro.co` → imita Bancolombia y `bit.ly/x` → acortador? | 2 | ✅ |
| D6 | `agente.py`: loop ReAct, contrato pydantic, límites (iteraciones, timeout, presupuesto; aprobación como stub) | Diego | D3, D4, D5 | ¿Con `MAX_ITER=1` se detiene y lo dice? | 3 | ✅ (con LLM simulado) |
| D7 | `reglas.py` + 6 tests (rojo ×2, amarillo ×2, verde ×1, rechazo ×1) | Diego | D6 | ¿Pasan los 6 tests? | 1 | ✅ |
| D8 | `trazas.py` (JSONL + fila en `analisis`) | Diego | D6 | ¿Cada análisis deja traza con herramientas, orden, parámetros, tokens y latencia? | 1 | ✅ |
| D9 | UI Streamlit mínima (texto) | Diego | D7, D8 | ¿Pego texto y veo semáforo, tácticas, qué hacer y "qué revisé"? | 2 | ✅ 2026-10-17 con gemini-3.5-flash-lite: caso c11 (inyección) → 🔴, tácticas, qué hacer y expander con 2 herramientas |
| D10 | Integrar archivos del compañero: `cargar_semillas.py` y correr 5 casos | Diego | D9, C1–C5 | ¿Las semillas cargan sin error y los 5 casos corren de punta a punta? | 1 | ✅ 2026-10-17: semillas cargan; 5/5 casos con el semáforo esperado (`scripts\probar_casos.py 5`) |
| C1–C6 | Ver `TAREAS_COMPANERO.md` | Claude (por Anderson) | — | Ver su archivo | ~7 | ✅ borrador; Diego revisa C5 |

**Si no alcanza el tiempo:** D9 puede salir como script de consola; la UI pasa al inicio de la Fase 2. Se recorta alcance, nunca verificación.

---

## FASE 2 — "Usable y medida" · Hasta Momento 2 (semana 11)

> Reordenada el 2026-10-29 tras la retroalimentación sobre público objetivo y otra vez el 2026-10-30 al descartar Telegram (`decisiones/publico_y_canal.md`). Orden: D19 → D20 → D11 → D12 → resto.

| ID | Tarea | Dueño | Criterio (sí/no) |
|---|---|---|---|
| ~~D18~~ | ~~Bot de Telegram~~ | Diego | **Descartada el 2026-10-30:** en Colombia crear una cuenta de Telegram cuesta $5.000 (rompe el costo cero y le pone una barrera a la persona mayor). El código y sus 15 tests quedan como evidencia del intento. |
| **D20** ⭐ | "Compartir con ¿Le creo?" desde WhatsApp: página instalable (PWA con `share_target`) que muestra la respuesta de D19 | Diego | ¿En un Android, compartiendo desde WhatsApp un mensaje de la suite, veo el semáforo esperado con la orden primero, con traza y sin que el texto viaje en la URL? — ⚠️ 2026-10-30: `ui/compartir.py` + `ui/web/` hechos, 16 tests (suite 132/132). En navegador con Gemini real, un POST a /compartir con c02 mostró 🔴 y "Llama al número de toda la vida de tu hijo"; la URL queda en `/` y el registro no guarda el texto. **Avance 2026-10-30 con túnel de Cloudflare:** Chrome de escritorio ofrece "Instalar" (el service worker sí funciona en Chrome normal); en un Android la app se instaló y **aparece en el menú Compartir de WhatsApp**; los análisis desde PC y celular llegaron por `/api/analizar` en rojo y el registro no guardó el texto. **Falta:** ver en el registro del servidor un `POST /compartir` (huella de compartir desde WhatsApp). La persona dijo que el texto llegó escrito, pero el servidor no registró ese envío y una prueba de control con un mensaje nuevo no llegó. Un `POST /compartir` simulado **a través del túnel** sí llegó, se registró sin el texto y la página mostró "📤 Recibido desde WhatsApp" + 🔴 con Gemini. **Estado: parcial.** Para cerrarlo: un pantallazo del Android junto con el `POST /compartir` correspondiente en el registro |
| D19 | Respuesta corta para persona mayor: orden clara primero + línea oficial de la entidad (web y bot) | Diego | ¿En los 5 casos la primera línea dice qué hacer y, si hay entidad conocida, trae su línea oficial? — ✅ 2026-10-29 con Gemini: c01–c05 + c11 → 6/6 con la orden primero; c11 trae la línea de Bancolombia (01 8000 9 12345) desde la tabla verificada; c02 ya no remite a Nequi sino a "llamar al número de siempre de tu hijo". Pendiente para D16: en c11 el modelo escribió "robes" en vez de "roben". **Corrección 2026-10-30:** al probar los legítimos (c07–c09) los tres salían rojo: el cambio de prompt de D19 volvió `entidad_suplantada` "quien dice escribir", y `reglas.py` lo tomaba como señal dura. Ahora "dice ser la entidad" solo es señal dura si el mensaje trae un enlace o un teléfono que no son los oficiales (comparación de datos, no juicio del modelo); el prompt aclara que avisar no es pedir. Suite completa con Gemini: **12/12** (c12 se repitió tras un 429) |
| D11 | Entrada por captura (imagen al modelo multimodal), compartida desde WhatsApp o subida en la página | Diego | ¿Una captura da el mismo semáforo que su texto? — ✅ 2026-10-30 con Gemini: 5/5 capturas sintéticas estilo WhatsApp (c01, c03, c07, c11, c12 en `eval/archivos/`) dan el mismo semáforo que su texto, con lectura exacta palabra por palabra; la trampa de c11 dentro de la imagen se ignoró. Traza con `tipo_entrada=imagen` y tokens de la lectura incluidos. Latencia 5–10 s (dos pasos). Faltan capturas reales (C7) |
| D12 | Entrada por audio (Whisper en Groq), también nota de voz reenviada al bot | Diego | ¿Un audio de prueba se transcribe y se analiza? |
| D13 | Los 3 errores forzados (`FORZAR_ERROR`) | Diego | ¿Los tres se demuestran sin stack trace? |
| D14 | `reportar_numero` con aprobación real + tabla `feedback` | Diego | ¿Sin clic no se escribe nada en la base? |
| D15 | `correr_suite.py` + las 4 cifras con fecha en `semana10.md` | Diego | ¿El script imprime las 4 cifras y las guarda con fecha? — ✅ 2026-10-30 04:40 con Gemini: éxito 12/12, costo equivalente US$ 0,001747, latencia mediana 3.150 ms, recuperación 12/12. Guardado en `eval/resultados/` y `docs/decisiones/semana10.md` (con sus límites: medido en la misma suite que se corrigió) |
| D16 | Iterar descripciones de herramientas y medir antes/después | Diego | ¿Hay 2 versiones con su tasa de éxito? |
| D17 | Demo: cambio de proveedor en vivo | Diego | ¿Se cambia el proveedor durante la demo sin tocar código? |
| C7–C10 | Ver `TAREAS_COMPANERO.md` (Fase 2). En C8 la persona externa es un adulto mayor real, usando el bot | Anderson / Angela | Ver su archivo |

---

## FASE 3 — Momento 3 (semanas 12–14)

Prueba de inyección documentada · modelo de amenazas · hardening con antes/después · ficha de gobernanza · modo familia (`avisar_familiar` con aprobación) · respuesta a auditoría cruzada · cifras finales contra línea base.

---

## Fuera de este ciclo

- Integración directa con WhatsApp / SMS / Telegram
- App móvil nativa
- Modo familia (pasa a Fase 3 / Momento 3)
