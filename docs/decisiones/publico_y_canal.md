# Decisión: público objetivo y canal de entrada

> Fecha: 2026-10-29 · Estado: aceptada por el equipo · Cambia las decisiones 1 (canal) y el público de la spec

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
