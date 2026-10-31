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

**Cambiar de proveedor en plena demo (D17):** con la app corriendo, cambia `PROVEEDOR=google` por `PROVEEDOR=groq` en `.env` y guarda. El siguiente análisis ya usa Groq, sin reiniciar nada. En "Ver por qué" aparece "Analizado con groq · …" y la traza registra el proveedor.

## Compartir desde WhatsApp (para personas mayores)

Página instalable: en Android, la persona deja presionado el mensaje sospechoso en WhatsApp → ⋮ → **Compartir** → **¿Le creo?** y ve la respuesta en grande. También acepta **pantallazos y notas de voz**: compartidos desde WhatsApp o con el botón "📷 🎙️ Revisar captura o audio". Las notas de voz se transcriben con Whisper en Groq (`MODELO_TRANSCRIPCION` en `.env`). En iPhone se usa "Pegar y revisar" o el botón. **Ojo:** WhatsApp en Android solo deja *compartir* notas de voz, fotos y documentos; un mensaje de **texto** se copia y se revisa con "Pegar y revisar". Si se cambia el manifiesto, hay que reinstalar la app en el celular.

```powershell
.\.venv\Scripts\python.exe ui\compartir.py          # http://localhost:8600
```

Para instalarla en un celular hace falta HTTPS. Para la demo sirve un túnel gratuito de Cloudflare (la dirección cambia cada vez que se abre):

```powershell
cloudflared tunnel --url http://localhost:8600
```

En el celular: abre la dirección `https://…trycloudflare.com` en Chrome → ⋮ → **Instalar app**.

El texto compartido llega por POST (nunca en la URL), no se guarda y se muestra como texto plano. Hay un límite de 5 análisis por minuto.

> El bot de Telegram (`ui/bot_telegram.py`) se descartó el 2026-10-30: en Colombia crear una cuenta de Telegram cuesta $5.000. Ver `docs/decisiones/publico_y_canal.md`.

## Tests

```powershell
pytest tests\ -v
```
