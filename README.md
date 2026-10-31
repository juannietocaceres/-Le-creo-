# ¿Le creo?

**Una segunda opinión antes de pagar.** Una persona recibe un mensaje sospechoso por WhatsApp o SMS. Lo comparte o lo pega en ¿Le creo? y un agente de IA le responde con un **semáforo** 🔴 🟡 🟢, el **truco** que usan, **qué hacer** y **qué revisó** para decirlo. Acepta texto, pantallazos y notas de voz.

Equipo: Diego, Anderson y Angela · Ingeniería de Aplicaciones con IA · UCC 2026-2

> 📄 **Decisiones técnicas, datos y línea base:** [`docs/decisiones.md`](docs/decisiones.md)
> 🎤 **Guion de la demo:** [`docs/guion_demo.md`](docs/guion_demo.md)

---

## 1. Requisitos

| Qué | Versión | Para qué |
|---|---|---|
| **Python** | 3.11 o superior | La app y el agente |
| **Docker** con Compose v2 | Docker Desktop 4.x / Docker 24+ | PostgreSQL 16 (se levanta solo) |
| **Llave de Google AI Studio** | gratis, sin tarjeta: https://aistudio.google.com/apikey | El modelo principal |
| Llave de Groq *(opcional)* | gratis, sin tarjeta: https://console.groq.com/keys | Notas de voz (Whisper) y respaldo si Google responde 429 |
| `cloudflared` *(opcional)* | cualquiera | Solo para abrir la app desde un celular |

Probado en Windows 11 con PowerShell 5.1, Python 3.11 y Docker 29.

## 2. Arranque en un comando

**1. Credenciales.** Copia la plantilla y llena las llaves:

```powershell
copy .env.example .env
```

Variables mínimas en `.env`:

```
PROVEEDOR=google
GOOGLE_API_KEY=tu_llave
MODELO_GOOGLE=gemini-3.5-flash-lite
```

Para notas de voz y respaldo, agrega también `GROQ_API_KEY`, `MODELO_GROQ=openai/gpt-oss-120b` y `MODELO_TRANSCRIPCION=whisper-large-v3-turbo`. Todas las variables están explicadas en `.env.example`. **Nunca subas el `.env`**: está en `.gitignore`.

**2. Levantar todo.** Instala dependencias, levanta Postgres, carga las semillas y abre las dos apps.

Windows:
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Linux / macOS / Git Bash:
```bash
./run.sh
```

**3. Abrir:**

| Dirección | Qué es |
|---|---|
| http://localhost:8600 | **La app**: lo que ve la persona. Pegar, subir un pantallazo o un audio. |
| http://localhost:8501 | **Streamlit con trazas**: la misma revisión, mostrando qué herramientas pidió el agente, sus resultados, tokens y latencia. |

En Windows, `run.ps1` también abre un túnel HTTPS y muestra la dirección para el celular. Usa `-SinTunel` para no abrirlo.

**Apagar:** `.\run.ps1 -Detener` (Windows) o `./run.sh detener`. Postgres sigue en Docker; `docker compose down` lo apaga.

Si algo falla, la causa más común es que Docker Desktop no esté abierto. Ábrelo, espera a que diga *Engine running* y vuelve a correr el comando.

## 3. Qué modelo usamos y por qué

| Uso | Proveedor | Modelo | Razón |
|---|---|---|---|
| Agente | Google AI Studio | `gemini-3.5-flash-lite` | Gratis sin tarjeta, **mediana 2,2 s** en la suite, tool calling estable y multimodal (lee pantallazos). |
| Respaldo ante 429 | Groq | `openai/gpt-oss-120b` | Gratis y rápido; 5/5 en los casos c01–c05. |
| Notas de voz | Groq | `whisper-large-v3-turbo` | Transcripción en español sin costo. |

- Solo `app/proveedor.py` habla con la API (SDK compatible con OpenAI y `base_url` por proveedor).
- **Cambio de proveedor en vivo:** con la app corriendo, cambia `PROVEEDOR=google` por `PROVEEDOR=groq` en `.env` y guarda. El siguiente análisis ya usa Groq, sin reiniciar. En "Ver por qué" aparece "Analizado con groq · …".
- Costo real: **US$ 0**. Costo equivalente pagando: unos **US$ 0,0018** por análisis.

Detalle y alternativas descartadas: `docs/decisiones.md`, secciones 3 y 4.

## 4. Cómo funciona (en corto)

1. Si es imagen o audio, primero se convierte a texto (modelo multimodal o Whisper).
2. El **agente** (`app/agente.py`) decide qué consultar con tres herramientas propias: `buscar_numero` y `canal_oficial` (Postgres) y `revisar_enlace` (reglas de cadena, **nunca abre el enlace**). Devuelve un contrato JSON validado con pydantic.
3. **`app/reglas.py` decide el semáforo**, no la IA.
4. `app/respuesta.py` arma la respuesta: primero una orden fija por color, luego la explicación y la línea oficial verificada.
5. `app/trazas.py` guarda la traza (JSONL + tabla `analisis`) **sin el texto del mensaje**.

**Límites del agente:** 5 iteraciones, 20 s en total, 8.000 tokens y aprobación por clic para cualquier escritura en la base. Todos se configuran en `.env`.

## 5. Probar los fallos (sin tocar código)

En `.env`, `FORZAR_ERROR=` acepta:

| Valor | Qué se ve |
|---|---|
| `429` | Espera 1, 2 y 4 s, responde Groq y lo avisa en pantalla |
| `timeout` | Corta a los 20 s y ofrece "Reintentar" |
| `invalida` | Reintenta; si sigue mal, muestra el texto sin semáforo y avisa |

Se aplica al guardar el `.env`, sin reiniciar. Déjalo vacío para el uso normal.

## 6. Medición

```powershell
.\.venv\Scripts\python.exe eval\correr_suite.py 4 --repeticiones 3
```

Corre los 12 casos de `eval/casos.jsonl` e imprime y guarda en `eval/resultados/` las cuatro cifras: éxito, costo, **latencia mediana** y recuperación. Resultado del 2026-10-31: **36/36**, US$ 0,0018 equiv., mediana 2.224 ms, recuperación 39/39.

## 7. Usarla desde el celular (Android)

1. Corre `run.ps1` (abre el túnel) y en el celular abre en **Chrome** la dirección `https://…trycloudflare.com` que muestra.
2. ⋮ → **Instalar app**.
3. En WhatsApp: deja presionada una **nota de voz o foto** → Compartir → **¿Le creo?**.
   WhatsApp en Android no deja compartir mensajes de **texto**: para esos, Copiar → abrir ¿Le creo? → **Pegar y revisar**.

La dirección del túnel cambia cada vez; si cambia, hay que reinstalar la app. El contenido compartido llega por POST (nunca en la URL), no se guarda, y hay un límite de 5 análisis por minuto.

## 8. Estructura

```
app/            agente, proveedor, herramientas, reglas, respuesta, trazas, aprobación, entradas
app/prompts/    prompt de sistema
ui/             compartir.py + web/ (la app instalable) y app_streamlit.py (trazas)
db/             esquema SQL (6 tablas, se crea solo al levantar Docker)
data/           catálogo de tácticas y semillas (CSV con fuentes oficiales; números ficticios)
eval/           casos dorados, script de la suite, precios y resultados con fecha
docs/           decisiones.md, guion de la demo, spec, plan, guías y evidencia
scripts/        carga de semillas, prueba de casos y demo.ps1
tests/          212 pruebas (pytest)
run.ps1 / run.sh  arranque en un comando
```

## 9. Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Las pruebas de base de datos se saltan solas si Postgres no está arriba.
