#!/bin/bash
FILAGENT_DIR="/Users/felixlefebvre/FilAgent"
source "${FILAGENT_DIR}/venv/bin/activate"

# Arrêter serveurs existants
pkill -f "uvicorn runtime.server" 2>/dev/null
pkill -f "gradio" 2>/dev/null
sleep 2

# Démarrer FastAPI
echo "🚀 Démarrage serveur FastAPI..."
cd "${FILAGENT_DIR}"
nohup python -m uvicorn runtime.server:app --host 0.0.0.0 --port 8000 > logs/fastapi.log 2>&1 &
echo $! > pids/fastapi.pid

# Attendre démarrage
sleep 3

# Démarrer Gradio
echo "🚀 Démarrage interface Gradio..."
nohup python gradio_app.py > logs/gradio.log 2>&1 &
echo $! > pids/gradio.pid

echo "✅ Serveurs démarrés!"
echo "📡 API: http://localhost:8000"
echo "🎨 Interface: http://localhost:7860"
echo "📚 Docs: http://localhost:8000/docs"
