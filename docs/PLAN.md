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
| **D20** ⭐ | "Compartir con ¿Le creo?" desde WhatsApp: página instalable (PWA con `share_target`) que muestra la respuesta de D19 | Diego | ¿En un Android, compartiendo desde WhatsApp un mensaje de la suite, veo el semáforo esperado con la orden primero, con traza y sin que el texto viaje en la URL? — ⚠️ 2026-10-30: `ui/compartir.py` + `ui/web/` hechos, 16 tests (suite 132/132). En navegador con Gemini real, un POST a /compartir con c02 mostró 🔴 y "Llama al número de toda la vida de tu hijo"; la URL queda en `/` y el registro no guarda el texto. **Avance 2026-10-30 con túnel de Cloudflare:** Chrome de escritorio ofrece "Instalar" (el service worker sí funciona en Chrome normal); en un Android la app se instaló y **aparece en el menú Compartir de WhatsApp**; los análisis desde PC y celular llegaron por `/api/analizar` en rojo y el registro no guardó el texto. **Falta:** ver en el registro del servidor un `POST /compartir` (huella de compartir desde WhatsApp). La persona dijo que el texto llegó escrito, pero el servidor no registró ese envío y una prueba de control con un mensaje nuevo no llegó. Un `POST /compartir` simulado **a través del túnel** sí llegó, se registró sin el texto y la página mostró "📤 Recibido desde WhatsApp" + 🔴 con Gemini. **✅ Cerrada 2026-10-31 en un Android real (Xiaomi):** una nota de voz compartida desde WhatsApp (→ Compartir → ¿Le creo?) abrió la app y el servidor registró `POST /compartir` → audio → 🔴, con traza #508 (`tipo_entrada=audio`, sin texto). El pantallazo muestra "📤 Nota de voz recibida desde WhatsApp" y la orden primero (`docs/evidencia/d20_android_nota_de_voz.jpg`). **Hallazgo:** WhatsApp en Android no permite compartir mensajes de **texto**, solo audios, fotos y documentos; para texto el camino es Copiar → "Pegar y revisar" (probado: 🔴). Para que la app apareciera en el menú hubo que aceptar `audio/*` e `image/*` en el manifiesto. Detalle en `decisiones/publico_y_canal.md` |
| D19 | Respuesta corta para persona mayor: orden clara primero + línea oficial de la entidad (web y bot) | Diego | ¿En los 5 casos la primera línea dice qué hacer y, si hay entidad conocida, trae su línea oficial? — ✅ 2026-10-29 con Gemini: c01–c05 + c11 → 6/6 con la orden primero; c11 trae la línea de Bancolombia (01 8000 9 12345) desde la tabla verificada; c02 ya no remite a Nequi sino a "llamar al número de siempre de tu hijo". Pendiente para D16: en c11 el modelo escribió "robes" en vez de "roben". **Corrección 2026-10-30:** al probar los legítimos (c07–c09) los tres salían rojo: el cambio de prompt de D19 volvió `entidad_suplantada` "quien dice escribir", y `reglas.py` lo tomaba como señal dura. Ahora "dice ser la entidad" solo es señal dura si el mensaje trae un enlace o un teléfono que no son los oficiales (comparación de datos, no juicio del modelo); el prompt aclara que avisar no es pedir. Suite completa con Gemini: **12/12** (c12 se repitió tras un 429) |
| D11 | Entrada por captura (imagen al modelo multimodal), compartida desde WhatsApp o subida en la página | Diego | ¿Una captura da el mismo semáforo que su texto? — ✅ 2026-10-30 con Gemini: 5/5 capturas sintéticas estilo WhatsApp (c01, c03, c07, c11, c12 en `eval/archivos/`) dan el mismo semáforo que su texto, con lectura exacta palabra por palabra; la trampa de c11 dentro de la imagen se ignoró. Traza con `tipo_entrada=imagen` y tokens de la lectura incluidos. Latencia 5–10 s (dos pasos). Faltan capturas reales (C7) |
| D12 | Entrada por audio (Whisper en Groq), compartida desde WhatsApp o subida en la página | Diego | ¿Un audio de prueba se transcribe y se analiza? — ✅ 2026-10-30: 3/3 audios sintéticos (voz Sabina de Windows, en `eval/archivos/`): c02 → 🔴, c07 → 🟢, silencio → pide otro audio sin inventar. Traza con `tipo_entrada=audio`. **Límite:** Whisper oyó "Neki" y "30000000007" (un cero de más): un número dictado puede transcribirse mal y entonces `buscar_numero` no lo encuentra. Faltan audios reales (C7) y probar el compartir de una nota de voz real desde WhatsApp |
| D13 | Los 3 errores forzados (`FORZAR_ERROR`) | Diego | ¿Los tres se demuestran sin stack trace? — ✅ 2026-10-30 con APIs reales sobre c03: 429 → esperas 1-2-4 s y respondió Groq (10,9 s); timeout → corte a 20,0 s con Reintentar; inválida → reintento y 🔴 correcto (9,3 s). Ningún stack trace. Documentado en `decisiones/semana09.md` |
| D14 | `reportar_numero` con aprobación real + tabla `feedback` | Diego | ¿Sin clic no se escribe nada en la base? — ✅ 2026-10-30 con Gemini y Postgres reales (c02): analizar dejó la base igual (2 reportes, 0 feedback); reportar sin permiso → 403; con el clic "Sí, reportar" → 3 reportes y el número pasa a peligroso; repetir el clic → 403; "¿Me equivoqué?" → 1 fila en `feedback`. La supervisión está en el código: `app/aprobacion.py` (permiso firmado, de un solo uso, 30 min) y `ui/compartir.py::_reportar`. La IA solo recibe el stub de `reportar_numero`. Datos de prueba restaurados después |
| D15 | `correr_suite.py` + las 4 cifras con fecha en `semana10.md` | Diego | ¿El script imprime las 4 cifras y las guarda con fecha? — ✅ 2026-10-30 04:40 con Gemini: éxito 12/12, costo equivalente US$ 0,001747, latencia mediana 3.150 ms, recuperación 12/12. Guardado en `eval/resultados/` y `docs/decisiones/semana10.md` (con sus límites: medido en la misma suite que se corrigió) |
| D16 | Iterar descripciones de herramientas y medir antes/después | Diego | ¿Hay 2 versiones con su tasa de éxito? — ✅ 2026-10-30, 3 repeticiones × 12 casos cada una: v1 éxito 97,2 % / recuperación 94,4 %; v2 éxito 100 % / recuperación 100 % (+11 % de costo). Se queda la v2. **Cierre 2026-10-31 (prompt v3→v5):** c09 ahora espera `canal_oficial`; c06 llamaba `buscar_numero` con "$300.000" y `canal_oficial` con "agencia de marketing". Con el prompt v5: éxito 36/36, recuperación 39/39, **0 llamadas de más** (v2: 3) y 0 "robes" en 36 explicaciones. La v3 y la v4 empeoraron c09 (respondía "oficial" sin consultar) y se documentan como intento fallido. Detalle en `decisiones/semana10.md` |
| D17 | Demo: cambio de proveedor en vivo | Diego | ¿Se cambia el proveedor durante la demo sin tocar código? — ✅ 2026-10-30 con APIs reales: el mismo servidor (`ui/compartir.py`, PID 30000 sin reiniciar) analizó c03 con `PROVEEDOR=google` → 🔴 «Analizado con google · gemini-3.5-flash-lite» (11,8 s); se editó solo esa línea del `.env` a `groq` → 🔴 «groq · openai/gpt-oss-120b» (7,7 s); de vuelta a `google` → 🔴 google (11,7 s). Las trazas registran los tres proveedores. Cómo: `config.recargar_si_cambio()` relee el `.env` antes de cada análisis solo si cambió su fecha de modificación (6 tests). La página muestra con qué IA salió cada respuesta en "Ver por qué"; Streamlit ya lo mostraba |
| C7–C10 | Ver `TAREAS_COMPANERO.md` (Fase 2). En C8 la persona externa es un adulto mayor real, usando "Compartir desde WhatsApp" (guía en `docs/guias/c8_prueba_adulto_mayor.md`) | Anderson / Angela | Ver su archivo |

---

## FASE 3 — "Responder por lo construido" · Momento 3 (semanas 12–14)

> Planeada el 2026-10-31 a partir de la rúbrica del Momento 3 (https://ingenieria-aplicaciones-ia.netlify.app/momento3_rubrica).
> Pesa **40 %** y es la única entrega que puede **subir** los criterios de los Momentos 1 y 2.
> Dos frentes: **A** = lo que exige la rúbrica (sin esto se pierden puntos) y **B** = lo que hace que el producto no se sienta básico. Las mismas reglas: costo cero, una tarea a la vez, criterio sí/no con evidencia.

**Terminada cuando:** alguien ajeno al equipo usa la app en vivo sin explicación, existen `docs/seguridad.md`, `docs/gobernanza.md` y `docs/respuesta_auditoria.md` verificables en el código, y las cuatro cifras finales están comparadas contra la línea base en `docs/decisiones.md`.

### A. Obligatorio por la rúbrica

| ID | Tarea | Dueño | Criterio (sí/no) | Estado |
|---|---|---|---|---|
| **S1** ⭐ | Ataque propio: 10–15 inyecciones contra el agente (en texto, **dentro de un pantallazo**, **dicha en una nota de voz**, trucos Unicode, intentar cerrar `</mensaje>` o romper el JSON), corridas con traza | Por asignar | ¿Cada ataque está en `docs/seguridad.md` con su traza, si funcionó o no, y qué se cambió después? | Pendiente |
| S2 | Modelo de amenazas concreto: la tríada evaluada sobre ¿Le creo? y qué pata cerramos y por qué | Por asignar | ¿`docs/seguridad.md` nombra los activos, entradas y salidas reales del sistema y la decisión tomada? | Pendiente |
| S3 | Hardening con antes y después: permisos mínimos del usuario de Postgres, límite de peticiones, validación de archivos, CSP, permisos de un solo uso | Por asignar | ¿Cada medida tiene su prueba y una medición antes/después? | Pendiente |
| G1 | Ficha de gobernanza: las cinco preguntas respondidas con lo que el sistema hace **de verdad** | Por asignar | ¿Cada respuesta enlaza la línea de código que la demuestra (p. ej. `app/aprobacion.py` para la supervisión humana)? | Pendiente |
| G2 | Respuesta a la auditoría cruzada | Por asignar | ¿Cada hallazgo de `docs/respuesta_auditoria.md` tiene respuesta argumentada ("lo arreglamos" con commit, o "lo asumimos y por qué")? | Espera el reporte del otro equipo |
| C8 | Prueba con un adulto mayor real (guía: `docs/guias/c8_prueba_adulto_mayor.md`), **después** de B1 | Anderson / Angela | ¿La tabla "Qué tuvimos que explicar / Qué cambiamos" de `semana09.md` está llena? | Pendiente |
| C5 | Casos reales: reemplazar o ampliar los 12 casos inventados con mensajes reales anonimizados | Anderson | ¿`eval/casos.jsonl` tiene casos reales verificados a mano, con números ficticios? | Pendiente |
| M1 | Cifras finales con los casos reales, comparadas contra la línea base de la semana 10 | Por asignar | ¿`docs/decisiones.md` muestra las cuatro cifras finales al lado de la línea base, con fecha y qué cambió y por qué? | Pendiente |
| M2 | Pendientes de medición: suite completa con Groq (pausa de 65 s) y probar un modelo más barato | Por asignar | ¿Hay un resultado guardado en `eval/resultados/` para cada uno? | Pendiente |

### B. Producto: que no se sienta básico

| ID | Tarea | Dueño | Criterio (sí/no) | Estado |
|---|---|---|---|---|
| **B1** ⭐ | Rediseño visual de la app: identidad de marca, semáforo que se "enciende", mensajes mientras analiza ("Revisando el número…", "Mirando el enlace…"), íconos por táctica, modo oscuro; sin perder letra grande ni contraste | Por asignar | ¿Hay capturas antes/después y las pruebas de la UI siguen pasando? | Pendiente |
| B2 | 🔊 Leer la respuesta en voz alta (síntesis de voz del navegador, sin costo) | Por asignar | ¿Un botón "Escuchar" lee la orden y el paso en español en un Android real? | Pendiente |
| B3 | 📞 Botón "Llamar a la línea oficial" (`tel:` con el número verificado de la base) | Por asignar | ¿En el celular abre el marcador con la línea oficial correcta, y solo aparece si el número viene de la tabla verificada? | Pendiente |
| B4 | 👨‍👩‍👧 Modo familia: con 🔴, "¿Avisarle a tu hijo?" abre WhatsApp con el aviso ya escrito (`wa.me`), y la persona toca Enviar | Por asignar | ¿Nada se envía sin el toque de la persona, y el aviso **no incluye** el texto del mensaje original? | Pendiente |
| B5 | 🌐 Link fijo: publicar en una capa gratuita **sin tarjeta** para no reinstalar cada vez | Por asignar | ¿Se verificó que el servicio es gratis sin tarjeta y la app instalada sigue funcionando al día siguiente? | Por verificar (si no hay opción sin tarjeta, se descarta y se documenta) |
| B6 | 📊 Panel para la familia: números más reportados de la semana y estafas frenadas, con datos agregados | Por asignar | ¿Muestra solo agregados de la base, sin ningún texto de mensajes? | Pendiente |

### Orden propuesto

1. **Semana 12:** B1 + B2 + B3. Es lo que más cambia la impresión, y C8 debe hacerse con la versión nueva.
2. **Semanas 12–13:** S1 → S2 → S3 y B4. B4 suma también a gobernanza, porque el toque de la persona **es** la supervisión humana.
3. **Semanas 13–14:** G1, C8, C5 → M1, G2 (cuando llegue la auditoría), M2 y B5/B6 si queda tiempo.

**Preguntas que hay que poder responder en la semana 14** (de la rúbrica): que alguien del público la use sin explicación · ¿es lo que declaramos en la spec? · el ataque que probamos y qué pasó · qué pata de la tríada cerramos · la línea donde el sistema exige la supervisión humana · si causa un daño hoy, ¿qué hacemos? · cifras contra la semana 10 · la traza de un caso que falla · qué haríamos distinto desde la semana 1.

---

## Fuera de este ciclo

- Integración directa con WhatsApp / SMS / Telegram
- App móvil nativa
- Modo familia (pasa a Fase 3 / Momento 3)
