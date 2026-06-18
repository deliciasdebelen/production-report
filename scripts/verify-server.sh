#!/bin/bash
echo "=== VERIFICACIÓN FINAL DEL SERVIDOR 192.168.1.193 ==="
echo ""
echo "--- Contenedores Docker ---"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

echo ""
echo "--- App Web (puerto 8000) ---"
curl -s -o /dev/null -w "http://localhost:8000 -> HTTP %{http_code}\n" http://localhost:8000/login

echo ""
echo "--- OpenClaw ---"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
openclaw --version 2>/dev/null && echo "✅ OpenClaw OK" || echo "⚠️  Revisar PATH"

echo ""
echo "--- Node.js ---"
node --version && echo "✅ Node OK" || echo "⚠️  Revisar NVM"

echo ""
echo "--- Proyecto ---"
ls ~/production-report/ | head -15
echo ""
echo "--- stitch_sync.py ---"
ls -lh ~/production-report/stitch_sync.py

echo ""
echo "--- Disco ---"
df -h / | tail -1

echo ""
echo "=== TODO LISTO ==="
