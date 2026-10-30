# ¿Le creo? — CLAUDE.md

## Resumen
Agente web que analiza mensajes sospechosos de WhatsApp/SMS y da una segunda opinión **antes de pagar**. Responde con semáforo (🔴/🟡/🟢), táctica de manipulación detectada, qué hacer y qué revisó. No detecta fraudes bancarios post-transacción; actúa en la conversación, antes de que la víctima autorice nada.

## Stack
| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.11+ |
| UI | Streamlit |
| Base de datos | PostgreSQL 16 en Docker |
| LLM (plan A) | Google AI Studio (gratis, sin tarjeta) |
| LLM (plan B) | Groq |
| LLM (plan C) | OpenRouter |
| Cliente LLM | SDK `openai` con `base_url` configurable |
| Validación | `pydantic` |
| Pruebas | `pytest` |

## Comandos
Repo en `C:\Users\juand\Electiva\le-creo`. Postgres expuesto en **5433** (el 5432 lo ocupa un Postgres local).

```powershell
# Entorno (versiones fijadas en requirements.txt)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Base de datos (cargar_semillas es idempotente: reemplaza las semillas)
docker compose up -d
python scripts\cargar_semillas.py

# App
streamlit run ui\app_streamlit.py

# Tests (necesitan Postgres arriba con semillas cargadas)
pytest tests\ -q

# D10: correr N casos de eval/casos.jsonl de punta a punta (necesita API key)
python scripts\probar_casos.py 5
```

Errores forzados (D13, solo para demo y pruebas): `FORZAR_ERROR=429 | timeout | invalida` en `.env` o como variable de entorno. El 429 pasa al proveedor de `PROVEEDOR_RESPALDO`. Dejarlo vacío en uso normal: las trazas lo marcan en el campo `forzado`.

## Reglas duras (sección 14 del documento maestro)
1. El agente **nunca** abre ni visita un enlace. Solo analiza el texto de la URL.
2. El semáforo lo decide `reglas.py`, **nunca** el LLM directamente.
3. **Nunca** se guarda el texto original del mensaje del usuario.
4. Toda acción hacia afuera (reportar número, avisar familiar) **exige** aprobación explícita del usuario (botón en el código).
5. El proveedor LLM solo se llama desde `app/proveedor.py`. Ningún otro módulo importa el SDK directamente.
6. Ningún nombre de modelo ni llave API en el código: todo en `.env`.
7. Las semillas solo usan **números ficticios** (formato `+5730000000XX`). Nunca números reales de personas.
