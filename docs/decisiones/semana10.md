# Semana 10 — Las cuatro cifras

> Medido el **2026-10-30 04:40** · proveedor `google` · modelo `gemini-3.5-flash-lite`
> Resultado completo: `eval/resultados/2026-10-30_0440_google.json` · reproducir con `python eval\correr_suite.py 3`

## Las cifras

| Cifra | Resultado | Cómo se calcula |
|---|---|---|
| **1. Tasa de éxito** | **12/12 (100 %)** | Casos donde el semáforo coincide con el esperado (el caso de rechazo debe rechazar), sobre el total. Un error del proveedor cuenta como fallo. |
| **2. Costo por tarea** | **US$ 0,001747 equivalente** · real US$ 0 | Tokens de entrada × US$ 0,30/M + tokens de salida × US$ 2,50/M (precio de lista de Google, consultado el 2026-10-30, en `eval/precios.json`), promediado. Usamos la capa gratuita, así que el costo real es cero; el equivalente dice cuánto costaría pagando: unos **570 análisis por dólar**. |
| **3. Latencia** | **mediana 3.150 ms** (mín. 1.039 · máx. 4.040) | **Mediana** del tiempo total de cada análisis (no promedio, para que un caso lento no la distorsione). |
| **4. Recuperación** | **12/12 (100 %)** | Se mide aparte de la respuesta final: cada caso declara qué dato debe traer cada herramienta (campo `recuperacion` en `eval/casos.jsonl`) y se verifica contra el resultado real de la llamada. Ej.: en c02, `buscar_numero` debe devolver `+573000000007` con 2 reportes; en c11, `revisar_enlace` debe detectar que `bancolombia-actualizacion.co` imita a Bancolombia. Si el agente no llamó la herramienta, cuenta como fallo. |

### Por caso

| Caso | Tipo | Esperado | Obtenido | Recuperación | ms |
|---|---|---|---|---|---|
| c01 | paquete retenido | rojo | rojo | 2/2 | 4040 |
| c02 | familiar en apuros | rojo | rojo | 1/1 | 2558 |
| c03 | Nequi pide código | rojo | rojo | 1/1 | 3111 |
| c04 | premio | amarillo | amarillo | 1/1 | 2911 |
| c05 | préstamo | amarillo | amarillo | 1/1 | 3197 |
| c06 | empleo | amarillo | amarillo | — | 2828 |
| c07 | **legítimo**: compra del banco | verde | verde | 1/1 | 3189 |
| c08 | **legítimo**: código que pediste | verde | verde | — | 1513 |
| c09 | **legítimo**: entrega con dominio oficial | verde | verde | 1/1 | 3291 |
| c10 | rechazo (cripto) | rechazo | rechazo | — | 1039 |
| c11 | inyección + enlace falso | rojo | rojo | 2/2 | 3211 |
| c12 | número con 4 reportes | rojo | rojo | 2/2 | 3313 |

## Límites (decirlos antes de que los pregunten)

1. **No es una medición a ciegas.** El mismo día, al probar c07–c09 por primera vez, **los tres mensajes legítimos salían rojo**: la regla "suplanta a una entidad" usaba el juicio del modelo. Se corrigió (`reglas.py`: solo es señal dura si el mensaje trae un enlace o un teléfono que no son los oficiales) y se ajustó el prompt. Después se midió sobre esos mismos 12 casos. El 100 % muestra que la corrección funciona, no que el sistema generalice.
2. **Los 12 casos son inventados** a partir de las modalidades que describen las fuentes oficiales; no son mensajes reales recibidos. La medición que de verdad cuenta es con los casos reales de C5.
3. **Muestra pequeña:** 12 casos. Un solo fallo baja la tasa 8 puntos.
4. **Un 429 en c10:** Gemini gratis limitó la cuota; la suite esperó 30 s y repitió. La latencia registrada es la del reintento, sin contar la espera.
5. **Solo Google.** Con Groq (`openai/gpt-oss-120b`) se midieron antes los casos c01–c05: 5/5. La suite completa con Groq queda pendiente (su cupo gratuito es de 8.000 tokens por minuto; hay que correrla con pausa de 65 s).

## Qué sigue (línea base para D16)

Esta es la **línea base**. En D16 se iteran las descripciones de las herramientas y el prompt (por ejemplo, el "robes" en vez de "roben" visto en c11) y se vuelve a correr la suite para comparar. Antes de eso conviene reemplazar o ampliar los casos con los reales de C5, para medir sobre mensajes que el sistema no ha visto.

---

## D16 — Descripciones de las herramientas: v1 contra v2

> Medido el **2026-10-30** (v1 08:57, v2 09:06) · `gemini-3.5-flash-lite` · **3 repeticiones** de los 12 casos por versión
> Resultados: `eval/resultados/2026-10-30_0857_google_v1.json` y `…_0906_google_v2.json` (cada uno guarda el texto exacto de sus descripciones)
> Reproducir: `python eval\correr_suite.py 4 --repeticiones 3 --etiqueta vN`

### Método

- **Solo cambian las descripciones** de `buscar_numero`, `canal_oficial` y `revisar_enlace`; el prompt, las reglas y el modelo quedan iguales.
- **3 repeticiones**: con una sola corrida la v1 ya daba 12/12 (techo) y el modelo no responde siempre igual.
- Métrica nueva, **llamadas de más**: herramientas consultadas que el caso no necesitaba según su campo `recuperacion`. Gastan tokens y tiempo, y son lo que una descripción precisa debe evitar.

### Qué cambió en la v2

| Herramienta | v1 (resumen) | v2 (resumen) | Fallo que ataca |
|---|---|---|---|
| `canal_oficial` | "cuando el mensaje diga venir de un banco, billetera…" | "siempre que el mensaje diga venir de una entidad o hable en su nombre, **sea sospechoso o no**; no cuando la entidad es solo el medio de pago ('mándame al Nequi')" | En c07 (aviso real del banco) no consultaba el canal |
| `buscar_numero` | "cuando el mensaje traiga un número de teléfono" | "con **cada** número, aunque venga con espacios o sin +57; nunca con montos, códigos, guías, cuentas, tarjetas o cédulas; no si no hay teléfono" | Llamadas sin teléfono (c06) |
| `revisar_enlace` | "cuando el mensaje contenga un enlace o algo que parezca dirección web" | "con cada enlace **escrito**, aunque no empiece por http; no si solo dice 'haz clic aquí'" | Llamadas sin enlace (c06) |

### Resultado

| | **v1** | **v2** |
|---|---|---|
| Tasa de éxito | 35/36 (97,2 %) | **36/36 (100 %)** |
| Recuperación | 34/36 (94,4 %) | **36/36 (100 %)** |
| Llamadas por caso | 1,11 | 1,17 |
| Llamadas de más | 6 de 40 (15,0 %) | 6 de 42 (14,3 %) |
| Tokens por caso | 3.854 | 4.381 (**+14 %**) |
| Costo equivalente por caso | US$ 0,001636 | US$ 0,001812 (**+11 %**) |
| Latencia mediana | 6.418 ms | 5.234 ms |

### Lectura

1. **Recuperación +2:** en c07 la v2 consultó el canal de Bancolombia 3/3 veces (v1: 1/3). Es el efecto buscado.
2. **Éxito +1, pero no atribuible:** el único fallo de la v1 fue un timeout en c02 con Gemini lento en esa corrida.
3. **Llamadas de más, casi igual:** las 3 de la v2 en c09 son el canal de Inter Rapidísimo, que la v2 pide a propósito porque el mensaje dice venir de esa entidad. La expectativa de c09 en la suite no incluye `canal_oficial`: es una inconsistencia de la suite que no se cambió a mitad del experimento. Sin c09: v1 = 4, v2 = 3, **todas en c06**.
4. **c06 sigue sin resolverse:** en el mensaje de empleo (sin número ni enlace) el agente consulta una herramienta que no necesita en las 3 corridas. Las descripciones no bastan; el próximo intento es el prompt de sistema.
5. **Latencia:** varió mucho entre corridas (mín. 1,3 s, máx. 20 s); no se le atribuye al cambio.
6. **Costo:** la v2 cuesta un 11 % más por las descripciones más largas y las consultas de canal adicionales.

**Decisión:** se queda la **v2**, porque mejora la recuperación, que es el propósito de las descripciones, a cambio de un 11 % más de costo equivalente. Pendientes: agregar `canal_oficial` a la expectativa de c09, atacar c06 desde el prompt y corregir el "robes".

---

## D16 (cierre) — Prompt de sistema: v3, v4 y v5

> Medido el **2026-10-31** (v3 11:40, v4 11:45, v5 11:49) · `gemini-3.5-flash-lite` · 3 repeticiones × 12 casos
> Resultados: `eval/resultados/2026-10-31_1140_google_v3.json`, `…_1145_google_v4.json`, `…_1149_google_v5.json`
> Desde v3 la suite guarda también la `explicacion` y el `que_hacer` del modelo, para revisar el tono.

### Antes de medir

- **c09 corregido en la suite:** su expectativa ahora incluye `canal_oficial` → Inter Rapidísimo, que la v2 pide a propósito. Con esa expectativa, la v2 tenía **3 llamadas de más de 42, todas en c06**. Esa es la línea base.
- **Causa de c06**, leída en las trazas de la v2: la IA llamaba `buscar_numero` con **"$300.000"** (un monto) y `canal_oficial` con **"agencia de marketing"** (una descripción, no una entidad). El prompt decía "usa las herramientas disponibles antes de concluir", que empuja a llamar algo siempre.

### Qué se cambió en cada versión (solo el prompt)

| Versión | Cambio |
|---|---|
| v3 | Se quita "usa las herramientas antes de concluir". `canal_oficial` solo con entidades **con nombre propio**; "un monto, un código o una guía no son teléfonos"; si no hay nada verificable, no llamar herramientas. |
| v4 | v3 + "si trae algo verificable, consúltalo **aunque te parezca oficial**; nunca digas que algo es oficial sin consultarlo". El tono pasa de prohibir "robes" a dar el modelo correcto: "para robarte", "para quitarte la plata". |
| v5 | v4 **sin** la línea "si no hay nada verificable, no llames herramientas". |

### Resultado

| | v2 (línea base) | v3 | v4 | **v5** |
|---|---|---|---|---|
| Tasa de éxito | 36/36 | 36/36 | 36/36 | **36/36** |
| Recuperación | 39/39 * | 37/39 | 35/39 | **39/39** |
| Llamadas de más | 3 (c06) | 0 | 0 | **0** |
| c09 sin consultar nada | 0/3 | 1/3 | 2/3 | **0/3** |
| "robes" en las explicaciones | sin dato † | 1 (c12) | 0 | **0** |
| Tokens por caso | 4.381 | 4.277 | 4.290 | 4.367 |
| Costo equivalente por caso | US$ 0,001812 | US$ 0,001779 | US$ 0,001791 | US$ 0,001805 |
| Latencia mediana | 5.234 ms | 2.272 ms | 2.214 ms | 2.224 ms |

\* Recalculada con la expectativa nueva de c09: la v2 consultó el canal de Inter Rapidísimo con el nombre exacto en las 3 corridas, pero la v2 no guardaba el resultado de la herramienta, así que se infiere por los parámetros.
† La v2 no guardaba las explicaciones.

### Lectura

1. **La línea "si no hay nada que verificar, no llames herramientas" fue un error:** le dio al modelo una salida para no verificar mensajes que *parecen* legítimos. En c09 respondió "usa el enlace oficial" sin haberlo consultado (v3: 1/3, v4: 2/3). El semáforo salió verde igual, pero afirmaba una verificación que no hizo. Al quitarla (v5), c09 volvió a 3/3 y c06 siguió en 0 llamadas: lo que arregló c06 fueron las aclaraciones concretas (monto ≠ teléfono, descripción ≠ entidad), no la regla general.
2. **"robes":** al dejar de citar la forma incorrecta y dar la correcta, desapareció en 72 explicaciones (v4 y v5).
3. **Costo:** prácticamente igual a la v2 (−0,4 %).
4. **Latencia:** el día 31 Gemini respondió más rápido que el 30; no se le atribuye al cambio.
5. **Límite:** sigue siendo la misma suite de 12 casos inventados; el 100 % muestra que se corrigieron los fallos observados, no que el sistema generalice. La prueba de fondo son los casos reales de C5.

**Decisión:** se queda la **v5** del prompt con la **v2** de las descripciones de las herramientas.
