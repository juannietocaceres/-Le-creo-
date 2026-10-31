#!/usr/bin/env bash
# ¿Le creo? — arranque en un solo comando (Linux / macOS / Git Bash)
#   ./run.sh           → instala lo que falte, levanta Postgres, carga semillas y abre las dos apps
#   ./run.sh detener   → apaga las apps (Postgres sigue en Docker)
set -euo pipefail
cd "$(dirname "$0")"

if [ -d .venv/Scripts ]; then BIN=.venv/Scripts; else BIN=.venv/bin; fi

if [ "${1:-}" = "detener" ]; then
  pkill -f "ui/compartir.py" 2>/dev/null || true
  pkill -f "app_streamlit.py" 2>/dev/null || true
  echo "✓ Apps detenidas (Postgres sigue en Docker)"; exit 0
fi

PY=$(command -v python3.11 || command -v python3 || command -v python) || { echo "✗ Falta Python 3.11+"; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || { echo "✗ Se necesita Python 3.11 o superior"; exit 1; }
echo "✓ $("$PY" --version)"

[ -x "$BIN/python" ] || [ -x "$BIN/python.exe" ] || "$PY" -m venv .venv
if [ -d .venv/Scripts ]; then BIN=.venv/Scripts; else BIN=.venv/bin; fi
"$BIN/python" -m pip install --disable-pip-version-check -q -r requirements.txt
echo "✓ Dependencias instaladas"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "✗ Creé .env desde .env.example. Llena GOOGLE_API_KEY y MODELO_GOOGLE (y GROQ_* para audio y respaldo) y vuelve a correr."
  exit 1
fi

docker compose up -d
for _ in $(seq 1 30); do docker exec lecreo-db pg_isready -U lecreo >/dev/null 2>&1 && break; sleep 2; done
"$BIN/python" scripts/cargar_semillas.py
echo "✓ Postgres listo y semillas cargadas"

mkdir -p trazas
nohup "$BIN/python" -u ui/compartir.py > trazas/compartir.log 2>&1 &
nohup "$BIN/streamlit" run ui/app_streamlit.py --server.headless true --server.port 8501 > trazas/streamlit.log 2>&1 &
sleep 5
echo
echo "¿Le creo? listo:"
echo "  App (lo que ve la persona):  http://localhost:8600"
echo "  Streamlit con trazas:        http://localhost:8501"
echo "  Registro del servidor:       trazas/compartir.log (nunca guarda el texto de los mensajes)"
echo "  Para apagar:                 ./run.sh detener"
