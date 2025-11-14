#!/bin/bash

# Script pour arrêter proprement tous les services FilAgent

echo "🛑 Arrêt des services FilAgent..."

# Arrêter via PIDs si disponibles
if [ -f "/Users/felixlefebvre/FilAgent/pids/fastapi.pid" ]; then
    kill $(cat /Users/felixlefebvre/FilAgent/pids/fastapi.pid) 2>/dev/null
    rm /Users/felixlefebvre/FilAgent/pids/fastapi.pid
    echo "✅ API FastAPI arrêtée"
fi

if [ -f "/Users/felixlefebvre/FilAgent/pids/gradio.pid" ]; then
    kill $(cat /Users/felixlefebvre/FilAgent/pids/gradio.pid) 2>/dev/null
    rm /Users/felixlefebvre/FilAgent/pids/gradio.pid
    echo "✅ Interface Gradio arrêtée"
fi

# Arrêter par nom de processus (backup)
pkill -f "uvicorn runtime.server" 2>/dev/null
pkill -f "gradio_app.py" 2>/dev/null
pkill -f "python.*filagent" 2>/dev/null

echo "✅ Tous les services FilAgent sont arrêtés"
