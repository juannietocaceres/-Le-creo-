# Guía C8 — Prueba con un adulto mayor real

> **Para qué:** responder con evidencia a la crítica del profe ("para una persona mayor es complejo revisar desde otra app").
> **Criterio de C8:** ¿la tabla "Qué tuvimos que explicar / Qué cambiamos" está llena en `docs/decisiones/semana09.md`?
> **Duración:** unos 30 minutos por persona. **Personas:** al menos 1; idealmente 2 o 3.

---

## 1. Quién participa

| Rol | Quién | Qué hace |
|---|---|---|
| **Participante** | Un adulto mayor (60+) que use WhatsApp, que **no sea del equipo** y que no haya visto la app. Lo ideal es que no sea muy hábil con el celular. | Usa la app. |
| **Guía** | Una persona del equipo | Lee las tareas en voz alta, tal como están escritas. **No ayuda** salvo con las pistas de la sección 5. |
| **Observador** | Otra persona del equipo | Anota en la hoja (sección 8) y toma el tiempo. No habla. |

Si solo hay una persona del equipo, puede hacer de guía y grabar solo el **audio** de la sesión para anotar después, con permiso.

## 2. Antes de la sesión (el día anterior)

**Consentimiento.** Explícale a la persona en palabras simples: "Estamos probando una app para estudiantes. No es un examen para ti: si algo es difícil, la culpa es de la app. No vamos a usar tus mensajes reales ni guardar nada tuyo." Pide permiso de forma verbal y anota que lo dio. Si no quiere seguir en cualquier momento, se para.

**Celular.** Usa **el celular de la persona**, porque así la prueba es real. Un familiar o alguien del equipo instala la app **antes** de la sesión, que es lo que haría el familiar que cuida en la vida real:
1. En el PC: `powershell -ExecutionPolicy Bypass -File scripts\demo.ps1` y copiar la dirección del celular.
2. En el celular de la persona: Chrome → esa dirección → ⋮ → **Instalar app**.
3. Comprobar que **¿Le creo?** aparece en WhatsApp → nota de voz → Compartir.
4. Anotar **cuánto tardó la instalación y qué hubo que hacer**: también es un dato.

> ⚠️ El PC debe quedar encendido durante toda la prueba. Si se reinicia, la dirección cambia y hay que reinstalar.

**Mensajes de prueba (todos ficticios).** El equipo se los envía por WhatsApp al participante **el mismo día, antes de empezar**, desde un celular del equipo:

| # | Qué se envía | Basado en | Resultado esperado |
|---|---|---|---|
| A | **Nota de voz** grabada por alguien del equipo: *"Mami, este es mi número nuevo, se me dañó el celular. Necesito que me hagas una transferencia urgente por Nequi, hoy mismo, porfa."* | c02 | 🔴 |
| B | **Imagen** `eval/archivos/c11_captura_sintetica.png` (pantallazo de un SMS falso de Bancolombia) | c11 | 🔴 |
| C | **Texto:** `Nequi: detectamos un ingreso inusual a tu cuenta. Para no bloquearla responde con el código de 6 dígitos que te llegó por SMS.` | c03 | 🔴 |
| D | **Texto legítimo:** copiar el campo `entrada` de **c07** en `eval/casos.jsonl` (aviso real de compra del banco) | c07 | 🟢 |

Nunca uses mensajes reales de la persona ni números reales: todos los números deben ser +5730000000XX.

## 3. Al empezar (2 min)

Lee esto en voz alta:

> "Te van a llegar mensajes raros, como los que le llegan a mucha gente. En tu celular hay una app que se llama **¿Le creo?**, que te dice si un mensaje es una estafa. Te voy a pedir unas cosas y tú haces lo que harías normalmente. Si no sabes cómo, dímelo en voz alta: eso nos ayuda. Yo no te voy a decir cómo hacerlo."

Lo único que se le enseña es **un solo gesto**, una vez, como lo haría el familiar:

> "Cuando te llegue algo raro, déjalo presionado, toca **Compartir** y escoge **¿Le creo?**."

No se le muestra cómo hacerlo con el dedo; solo se dice.

## 4. Las tareas

Lee cada tarea **tal cual**. Toma el tiempo desde que terminas de leerla hasta que la persona ve el resultado.

| Tarea | Lo que dice el guía | Qué se observa |
|---|---|---|
| **T1 — Nota de voz** | "Te llegó una nota de voz de alguien que dice ser tu hijo. Revísala con ¿Le creo?" | ¿Encuentra *Compartir*? ¿Encuentra *¿Le creo?* en la lista? |
| **T2 — Pantallazo** | "Te llegó esta imagen de tu banco. Revísala con ¿Le creo?" | Igual que T1, ahora con imagen. |
| **T3 — Texto** | "Te llegó este mensaje de Nequi. Revísalo con ¿Le creo?" | **Aquí *Compartir* no existe para texto.** ¿Qué intenta? ¿Llega sola a Copiar → abrir la app → *Pegar y revisar*? |
| **T4 — Mensaje real** | "Y este otro del banco, revísalo también." | ¿Entiende que 🟢 significa que no hay señales, sin creer que la app "aprobó" el mensaje? |

**Después de cada resultado**, pregunta sin señalar la pantalla:
1. "¿Qué te dijo la app?" → anota si lo dice con sus palabras.
2. "¿Qué harías ahora?" → ¿coincide con lo que dice la app (no pagar, llamar al número de siempre…)?

## 5. Si se queda bloqueada: pistas por niveles

Espera **60 segundos** sin intervenir. Después da la pista del nivel siguiente y **anota cuál diste**:

| Nivel | Pista |
|---|---|
| 1 | "¿Qué harías si quisieras mandárselo a alguien?" |
| 2 | "Prueba dejando el dedo presionado sobre el mensaje." |
| 3 | Se le señala el botón en la pantalla, sin tocarlo. |
| 4 | El guía lo hace y se anota **"no lo logró"**. |

Para T3, la pista de nivel 2 es: "Prueba copiándolo y abriendo la app."

## 6. Al final (5 min)

1. "Del 1 al 5, ¿qué tan fácil fue?" (1 = muy difícil).
2. "¿Lo usarías tú sola, sin que nadie te ayude?" ¿Por qué?
3. "¿Qué fue lo más confuso?"
4. "Si te llega un mensaje así mañana, ¿qué harías?"
5. "¿Le entendiste a la letra? ¿Era suficientemente grande?"

Agradece y, si la persona quiere, desinstala la app.

## 7. Qué medir

| Medida | Cómo |
|---|---|
| **Logró sola** | Sí si llegó al resultado sin pistas o solo con la de nivel 1. |
| **Tiempo** | Segundos desde que se lee la tarea hasta que ve el resultado. |
| **Pistas** | Nivel máximo usado y lo que dijo el guía, palabra por palabra. |
| **Entendió el resultado** | Repite la orden con sus palabras (sí / a medias / no). |
| **Actuaría bien** | Lo que dice que haría coincide con la app (sí / no). |
| **Semáforo correcto** | El color coincide con el esperado (tabla de la sección 2). |

Comprobar después de la sesión en el registro del servidor (`%TEMP%\lecreo-compartir.log`): T1 y T2 deben aparecer como `POST /compartir` y T3 y T4 como `POST /api/analizar`. Así se sabe por qué camino entró cada uno, sin depender de la memoria.

## 8. Hoja de registro (copiar una por participante)

```
Participante: P__   Edad: __   Fecha: ________   Celular: ________
Consentimiento verbal: sí / no      Guía: ______   Observador: ______
Instalación hecha por: ______   Tiempo de instalación: ___ min   Problemas: ______________

| Tarea | Logró sola | Tiempo (s) | Pista máx. | Qué se le dijo | Entendió | Actuaría bien | Semáforo |
|-------|-----------|-----------|-----------|----------------|----------|---------------|----------|
| T1 audio   |  |  |  |  |  |  |  |
| T2 imagen  |  |  |  |  |  |  |  |
| T3 texto   |  |  |  |  |  |  |  |
| T4 legítimo|  |  |  |  |  |  |  |

Facilidad (1–5): __   ¿La usaría sola?: ______________
Lo más confuso: ____________________________________________
Frases textuales que dijo: __________________________________
```

## 9. Después: llenar `semana09.md`

1. En **"Qué tuvimos que explicar"**: cada pista de nivel 2 o más, con la tarea. Ej.: *"T3: no encontró cómo revisar un texto; hubo que decirle que lo copiara (nivel 2)."*
2. En **"Qué cambiamos"**: el cambio concreto que se hizo en la app por esa causa, o *"pendiente: …"* si no se alcanzó. Ej.: *"La página muestra 'Copia el mensaje y toca aquí' en grande cuando se abre sola."*
3. Agregar debajo un resumen con las cifras: tareas logradas solas (x/4 por persona), tiempo mediano por tarea y facilidad promedio.
4. Si algo salió mal, **se anota igual**. Un resultado malo con evidencia sirve más que uno bueno sin ella.

## Qué esperamos encontrar (para comparar después, no para guiar la prueba)

- T1 y T2 deberían ser las más fáciles: el gesto es igual al de reenviar.
- **T3 es el punto débil conocido:** WhatsApp en Android no permite compartir texto (ver `decisiones/publico_y_canal.md`). Si casi nadie lo logra sin ayuda, es la prioridad siguiente.
- En T4 hay que vigilar que 🟢 no se entienda como "es seguro, paga". La app dice "No vimos señales de estafa", no "es seguro".
