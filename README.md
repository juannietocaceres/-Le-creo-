# ¿Le creo?

Segunda opinión antes de pagar. Pega el mensaje sospechoso y el agente te dice si parece estafa, qué truco usa y qué hacer.

## Requisitos
- Python 3.11+
- Docker Desktop

## Levantar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Editar .env: PROVEEDOR, su API key y el nombre vigente del modelo (MODELO_GOOGLE, etc.)
docker compose up -d          # Postgres queda en el puerto 5433
python scripts\cargar_semillas.py
streamlit run ui\app_streamlit.py
```

## Bot de Telegram (reenviar mensajes)

Pensado para personas mayores: el familiar lo configura y la persona solo reenvía el mensaje sospechoso al bot.

1. En Telegram, busca **@BotFather**, escríbele `/newbot` y elige un nombre y un usuario que termine en `bot`.
2. Copia el token que te da (se ve como `1234567890:AAH…`) y pégalo en `.env` después de `TELEGRAM_BOT_TOKEN=`. Guarda.
3. Con Docker y Postgres arriba, arranca el bot:

```powershell
.\.venv\Scripts\python.exe ui\bot_telegram.py
```

4. En Telegram, abre tu bot, escribe `/start` y reenvíale cualquier mensaje sospechoso.

El bot solo responde en chats privados, no guarda el texto de los mensajes y permite 3 análisis por minuto por persona.

## Tests

```powershell
pytest tests\ -v
```
