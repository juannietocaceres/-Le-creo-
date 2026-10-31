# Decisión: público objetivo y canal de entrada

> Fecha: 2026-10-29 · Estado: aceptada por el equipo · Cambia las decisiones 1 (canal) y el público de la spec
> **Revisión 2026-10-30: Telegram se descarta.** Ver "Revisión: de Telegram a Compartir desde WhatsApp" al final. El público objetivo se mantiene.

## Contexto

En la presentación de avance, la retroalimentación fue sobre el público objetivo: es poco realista que una persona mayor abra una aplicación web, pegue el mensaje y lea el resultado. Justo ese grupo es uno de los más expuestos a estafas como "mami, este es mi número nuevo".

La spec original asumía que quien duda de un mensaje es también quien usa la app.

## Decisión

1. **Usuario principal: el familiar que cuida** (hijo, hija, nieto). Es quien instala y configura, y le enseña a la persona mayor **un solo gesto**: "si dudas de un mensaje, reenvíaselo a ¿Le creo?".
2. **Canal nuevo: bot de Telegram.** La persona reenvía el mensaje sospechoso al contacto "¿Le creo?" y recibe la respuesta en el mismo chat. No tiene que abrir ninguna app ni copiar y pegar.
3. **La web se mantiene** para la demo, para quien sí la sepa usar y para ver la traza completa ("qué revisé").
4. **El agente no cambia.** El bot es otra puerta de entrada que llama a la misma `agente.analizar()`. Las reglas, las herramientas, los límites y la traza son los mismos.

## Por qué Telegram y no WhatsApp

| | Telegram | WhatsApp |
|---|---|---|
| Costo | $0, sin tarjeta | API de Meta: número verificado, aprobación y posible costo por conversación |
| Tiempo para tenerlo | minutos (BotFather) | semanas de aprobación |
| Dónde están los mayores | pocos lo usan | casi todos |

Telegram permite construir y validar la idea **dentro del curso y a costo cero**. WhatsApp queda como el siguiente paso natural, con su costo y su proceso explicados. El agente ya está separado del canal, así que cambiar de canal es cambiar la "puerta", no el sistema.

**Costo de esta decisión:** el familiar tiene que instalar Telegram en el celular de la persona mayor. Lo asumimos porque el familiar ya es quien la ayuda con el celular.

## Qué se descarta

- **Llamadas telefónicas (IVR):** tienen costo por minuto.
- **App móvil nativa:** sigue fuera de alcance.
- **Responder con nota de voz:** sería ideal para los mayores, pero los modelos de voz gratuitos disponibles en Groq (Orpheus) no hablan español. Queda como idea a futuro.

## Qué cambia en el plan

- **D18 (nuevo):** bot de Telegram con solo texto.
- **D19 (nuevo):** respuesta en formato corto para la persona mayor: primero una orden clara y luego la línea oficial.
- **D11 y D12 (captura y audio) suben de prioridad:** a los mayores las estafas les llegan como pantallazo y nota de voz.
- **C8 (prueba del compañero):** la persona externa será un adulto mayor real.

## Reglas duras que siguen intactas

- El bot **no guarda** el texto reenviado ni lo escribe en registros (regla 3).
- El bot **no abre** los enlaces (regla 1).
- El bot responde solo a quien le escribe; no envía nada a terceros. Avisar a un familiar es el modo familia, con aprobación (regla 4, Momento 3).

---

## Revisión 2026-10-30: de Telegram a "Compartir desde WhatsApp"

### Qué pasó
Al crear el bot, Telegram pidió para **registrar una cuenta nueva en Colombia** un "One-time SMS Fee": verificar el número por SMS cuesta una semana de Telegram Premium ($5.000 COP). Lo vimos en la app el 2026-10-30.

Eso rompe dos cosas:
1. **El costo cero del curso** (regla: solo capas gratuitas sin tarjeta).
2. **El argumento del público:** la persona mayor, o su familiar, tendría que pagar para usar la herramienta. Es justo la barrera que queríamos quitar.

El bot (`ui/bot_telegram.py`, D18) queda en el repositorio como evidencia del intento, con sus pruebas, pero **no es el canal del producto**.

### Nueva decisión
**"Compartir con ¿Le creo?" desde WhatsApp (Android).** La persona deja presionado el mensaje sospechoso en WhatsApp → ⋮ → **Compartir** → elige **¿Le creo?** Se abre nuestra página con el texto ya cargado y le muestra la respuesta corta de D19.

- Técnicamente es una **web instalable (PWA)** con `share_target` en su manifiesto: Android la muestra en el menú Compartir como si fuera una app.
- El familiar la instala **una sola vez** (Chrome → "Agregar a pantalla de inicio").
- Verificado en un Android del equipo (2026-10-30): al dejar presionado un mensaje de texto en WhatsApp → ⋮ aparece "Compartir" y abre la lista de apps.

| | Compartir (elegido) | Telegram (descartado) | WhatsApp Cloud API (descartado) |
|---|---|---|---|
| Costo | $0, sin cuentas | $5.000 por cuenta nueva en Colombia | $0 en pruebas, pero solo con números registrados a mano |
| Gesto de la persona mayor | Compartir desde WhatsApp, donde le llega la estafa | Reenviar a otra app que debe instalar | Reenviar a un contacto |
| Fragilidad | Baja | Baja | Alta: el token de prueba vence en menos de 24 h y necesita un webhook público |
| iPhone | ❌ no (iOS no permite `share_target` en webs) | ✅ | ✅ |

**Costo de esta decisión:** no funciona en iPhone. En iPhone el gesto es copiar el mensaje y pegarlo en la página, que tiene un botón grande de "Pegar y revisar".

### Privacidad
El texto compartido llega por **POST**, nunca en la URL, así que no queda en el historial del navegador ni en los registros del servidor (regla 3).

## Prueba real en Android (2026-10-31)

Probado en un Xiaomi (HyperOS) con WhatsApp, usando la app instalada desde Chrome por el túnel de Cloudflare.

### Lo que funcionó
- **Nota de voz:** WhatsApp → mantener presionada → Compartir → **¿Le creo?** abre la app directamente. El servidor registró `POST /compartir` (el audio va en el cuerpo, no en la URL), Whisper transcribió y el resultado fue **🔴** con "📤 Nota de voz recibida desde WhatsApp" y la orden primero (traza #508, `tipo_entrada=audio`, sin el texto). Pantallazo: `docs/evidencia/d20_android_nota_de_voz.jpg`.
- **Mensaje de texto:** Copiar → abrir ¿Le creo? → "Pegar y revisar" → 🔴.

### Lo que encontramos
1. **WhatsApp en Android no ofrece "Compartir" para mensajes de texto**, solo para notas de voz, fotos y documentos. El menú ⋮ de un texto trae Copiar, Fijar, Meta AI, Traducir y Reportar. Para texto el camino es de dos gestos: copiar y pegar. Esto explica por qué en las pruebas del 30 de octubre "el texto llegaba escrito" pero el servidor nunca vio un `POST /compartir`.
2. **La app no aparecía en el menú Compartir** aunque estaba instalada como app (WebAPK, "Versión: 1"). La causa era la lista de tipos del manifiesto: WhatsApp puede etiquetar la nota de voz como `audio/ogg; codecs=opus` y Android oculta la app si el tipo no coincide. Se cambió a `image/*` y `audio/*`. El servidor sigue validando el formato real por su contenido. Hay que **reinstalar** la app para que Android lea el manifiesto nuevo.
3. El primer envío falló en el paso de Gemini (no en Whisper), al parecer por una falla transitoria. Ahora el registro del servidor anota el código y el mensaje del proveedor cuando un análisis falla, sin el texto.

### Qué cambia para el público objetivo
- Para la persona mayor, el gesto que más se parece a lo que ya hace ("reenviárselo al nieto") existe **para audios y pantallazos**. Para los textos son dos gestos (Copiar → Pegar y revisar).
- La instalación la hace un familiar, una vez. Eso refuerza la decisión de que el usuario real es la pareja persona mayor + familiar que cuida.
- La prueba con un adulto mayor real (C8) debe medir los dos caminos por separado: compartir una nota de voz o un pantallazo, y copiar y pegar un texto.
