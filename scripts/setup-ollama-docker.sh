#!/bin/bash
# setup-ollama-docker.sh
# Levanta Ollama + Open WebUI via Docker Compose (sin sudo)

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║    Ollama LLM via Docker + Open WebUI                ║"
echo "╚══════════════════════════════════════════════════════╝"

# Crear directorio de trabajo
mkdir -p ~/ai-stack
cp ~/docker-compose.ollama.yml ~/ai-stack/docker-compose.yml
cd ~/ai-stack

echo ""
echo "[1/4] Levantando contenedores Ollama + Open WebUI..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose pull
docker compose up -d
echo "  ✅ Contenedores iniciados"

echo ""
echo "[2/4] Esperando que Ollama esté listo..."
for i in {1..20}; do
    if curl -s http://localhost:11434/api/version &>/dev/null; then
        echo "  ✅ Ollama API lista en :11434"
        break
    fi
    echo "  ... esperando ($i/20)"
    sleep 5
done

echo ""
echo "[3/4] Descargando modelo rápido: llama3.2:3b (~2GB)"
docker exec ollama ollama pull llama3.2:3b
echo "  ✅ llama3.2:3b descargado"

echo ""
echo "[4/4] Iniciando descarga del modelo potente: llama3.3:70b (~40GB)"
echo "  ⚠️  Este proceso toma varios minutos según el ancho de banda"
echo "  Lanzando en background para no bloquear la sesión..."
nohup docker exec ollama ollama pull llama3.3:70b > ~/ollama-70b-download.log 2>&1 &
PULL_PID=$!
echo "  PID del proceso de descarga: $PULL_PID"
echo "  Para monitorear: tail -f ~/ollama-70b-download.log"

echo ""
echo "=== Test rápido con llama3.2:3b ==="
RESPONSE=$(curl -s http://localhost:11434/api/generate \
    -d '{"model":"llama3.2:3b","prompt":"Di hola en español en máximo 10 palabras","stream":false}' \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','sin respuesta'))" 2>/dev/null)
echo "  Respuesta IA: $RESPONSE"

echo ""
echo "=== Configurando OpenClaw con Ollama ==="
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Configurar openclaw para usar Ollama local
if command -v openclaw &>/dev/null; then
    openclaw config set provider ollama 2>/dev/null && echo "  ✅ provider=ollama" || echo "  ⚠️ config provider (manual)"
    openclaw config set baseUrl http://localhost:11434 2>/dev/null && echo "  ✅ baseUrl=11434" || echo "  ⚠️ config baseUrl (manual)"
    openclaw config set model llama3.3:70b 2>/dev/null && echo "  ✅ model=llama3.3:70b" || echo "  ⚠️ config model (manual)"
else
    echo "  ⚠️  OpenClaw no en PATH — ejecutar: openclaw config set provider ollama"
fi

echo ""
echo "=== Estado de todos los servicios ==="
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ STACK DE IA COMPLETO                              ║"
echo "║                                                      ║"
echo "║  🤖 Ollama API:    http://192.168.1.193:11434        ║"
echo "║  💬 Open WebUI:    http://192.168.1.193:3000         ║"
echo "║  🌐 App:           http://192.168.1.193:8000         ║"
echo "║  🖥️  VNC:           http://192.168.1.193:6080         ║"
echo "║                                                      ║"
echo "║  Modelos listos:  llama3.2:3b                        ║"
echo "║  Descargando:     llama3.3:70b (background)          ║"
echo "║    monitor: tail -f ~/ollama-70b-download.log        ║"
echo "╚══════════════════════════════════════════════════════╝"
