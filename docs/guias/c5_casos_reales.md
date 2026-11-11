# Guía C5: recoger mensajes reales

**Para:** Diego, Anderson y Angela  ·  **Meta:** 30 mensajes reales  ·  **Entrega:** una semana antes de M3 (semana 14)

## Por qué lo hacemos

Nuestra suite da 100 %, pero 12 de sus 14 casos los inventamos nosotros. Así no prueba nada.

El 6 de noviembre bastaron dos mensajes reales de Diego para encontrar fallas:

- **Un giro de Western Union:** salió 🟡 y además acusaba ("te inventan una transferencia").
- **Un cobro de DiDi:** salió 🟡 con la misma acusación.

Ya está corregido, pero la lección es clara: la cifra que vale para M3 sale de mensajes que de verdad llegaron.

## Qué buscamos

Mensajes de WhatsApp o SMS que te hayan llegado a ti o a tu familia en los últimos meses.

| Tipo | Cuántos (entre los 3) | Ejemplos |
|---|---|---|
| **Estafas** | al menos 12 | premio falso, "mamá cambié de número", paquete retenido, multa, préstamo fácil, falso banco |
| **Legítimos** | al menos 12 | avisos del banco, códigos de verificación, cobros de servicios, giros, domicilios, citas médicas, envíos |
| **Libres** | hasta completar 30 | lo que encuentres, de cualquier tipo |

> **Los legítimos importan tanto como las estafas.** Si la app le dice "estafa" a un mensaje real del banco, la persona mayor deja de creerle.

**Toma todos, no solo los interesantes.** Revisa tus chats de las últimas semanas y saca *todos* los mensajes de empresas o desconocidos. Si eliges solo los que crees que la app acierta, la cifra queda inflada.

**Reparto:** 10 cada uno, al menos 4 estafas y 4 legítimos por persona.

## Regla de oro: si no sabes si era estafa, no lo incluyas

Para cada mensaje solo anotamos **si era estafa o no**. Nada más: no adivines qué color debería salir. La suite se encarga de eso.

Solo vale lo que sabes con certeza, y en `como_se_supo` escribes cómo lo sabes:

- ✅ "El banco confirmó en la app que no lo envió."
- ✅ "Esperaba ese giro y el dinero llegó."
- ✅ "El número decía ser mi hija y ella estaba al lado."
- ✅ "El cobro aparece en la app oficial."
- ❌ "Me pareció raro." Es una opinión, no un dato: no lo incluyas.
- ❌ "Lo pasé por ¿Le creo? y salió rojo." No sirve: no puedes medir la app con la propia app.

## Antes de entregar: anonimizar (obligatorio)

Ningún dato de una persona real entra al repositorio: ni el tuyo, ni el de tu familia, ni el del estafador.

| Dato | Cómo queda | Ejemplo antes → después |
|---|---|---|
| Teléfonos | `+57 300 000 0001` a `+57 300 000 0099` | 321 456 7890 → +57 300 000 0012 |
| Nombres de personas | otro nombre común | "Hola Doña Rosa" → "Hola Doña Carmen" |
| Códigos (MTCN, guía, cuenta, cédula, referencia) | `1234567890` (los dígitos que hagan falta) | MTCN 3892681298 → MTCN 1234567890 |
| Correos personales | `nombre@ejemplo.com` | juan.perez@gmail.com → juan@ejemplo.com |
| Enlaces | **el dominio se deja igual**, se cambia el código final | go.wu.com/e/dWqNvwoQQ7b → go.wu.com/e/AbCdEf123 |
| Montos, fechas, nombres de empresas | **no se cambian** | $3.500, Bancolombia, DiDi |

**El dominio del enlace no se toca:** es justo lo que la app revisa. El código del final sí se cambia, porque a veces identifica a la persona.

**Audios y fotos:** escribe el texto que dicen. No subas el audio ni la imagen.

## Cómo entregar

1. Cada mensaje es **una línea** en `eval/casos_reales.jsonl`, con este formato:

```json
{"id": "r03", "tipo": "texto", "entrada": "TEXTO DEL MENSAJE YA ANONIMIZADO", "es_estafa": true, "como_se_supo": "Cómo sabes que era (o no) estafa", "recolectado_por": "Angela", "fecha": "2026-11-12", "anonimizado": true}
```

   | Campo | Qué poner |
   |---|---|
   | `id` | el siguiente libre. Rangos: Diego `r01`–`r20`, Anderson `r21`–`r40`, Angela `r41`–`r60` |
   | `es_estafa` | `true` o `false`, sin comillas |
   | `recolectado_por` | `Diego`, `Anderson` o `Angela` |
   | `fecha` | el día en que llegó el mensaje |

2. Revisa el archivo:

```bash
python scripts/validar_casos_reales.py
```

   El validador rechaza teléfonos reales, códigos que parecen reales, correos personales y campos vacíos. Tiene dos límites, y esas dos cosas las revisas tú:

   - **Nombres propios:** no los puede detectar.
   - **Enlaces:** te los muestra con "revisa a mano" para que confirmes que cambiaste el código final.

3. Cuando diga `✓ listo para subir`, súbelo a GitHub o pásale el archivo a Diego por chat privado. Nunca lo pegues en el grupo **sin anonimizar**.

## Qué medimos con esto

```bash
python eval/correr_suite.py 4 --casos eval/casos_reales.jsonl --repeticiones 3 --etiqueta c5_real
```

La suite imprime cuatro números y estos son los que van en la presentación de M3:

| Número | Qué significa | Qué queremos |
|---|---|---|
| **Estafas con alerta** | estafas que salieron 🔴 o 🟡 | todas |
| **Estafas en verde** | estafas que la app dejó pasar: **el error más grave** | 0 |
| **Legítimos en rojo** | mensajes reales tratados de estafa: la persona deja de confiar | 0 |
| **Legítimos en amarillo** | "no pude confirmar": aceptable, pero hay que bajarlo | pocos |

Cada error que aparezca es una tarea concreta:

- una empresa que falta en `data/semillas/canales_oficiales.csv`;
- una regla de `app/reglas.py`;
- una descripción del prompt.

Se arregla, se vuelve a medir y se anota en `docs/decisiones.md` con el antes y el después.

## Ya van 2

`r01` (giro de Western Union) y `r02` (cobro de DiDi), los dos de Diego y legítimos. Primera medición (`c5_inicio`, 2026-11-10):

- r01 salió 🟢.
- r02 salió 🟡. Es correcto, porque pide pagar, y la respuesta manda a revisar el cobro en la app.
