#!/bin/bash
# install-ollama.sh
# Instala Ollama y descarga modelos LLM en el servidor
# Servidor: 98GB RAM — puede correr modelos 70B sin GPU

set -e

echo "╔══════════════════════════════════════════════════════╗"
echo "║         Instalando Ollama + Modelos LLM              ║"
echo "║         Servidor: 192.168.1.193 (98GB RAM)           ║"
echo "╚══════════════════════════════════════════════════════╝"

# ─────────────────────────────────────────────────────────
# 1. INSTALAR OLLAMA
# ─────────────────────────────────────────────────────────
echo ""
echo "[1/5] Instalando Ollama..."

if command -v ollama &>/dev/null; then
    echo "  Ollama ya instalado: $(ollama --version)"
else
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "  ✅ Ollama instalado: $(ollama --version)"
fi

# ─────────────────────────────────────────────────────────
# 2. CONFIGURAR OLLAMA COMO SERVICIO
# ─────────────────────────────────────────────────────────
echo ""
echo "[2/5] Configurando Ollama como servicio systemd..."

# Crear archivo de servicio para usuario (sin sudo para systemd --user)
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/ollama.service << 'SVCEOF'
[Unit]
Description=Ollama LLM Server
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
SVCEOF

systemctl --user daemon-reload
systemctl --user enable ollama 2>/dev/null || true
systemctl --user start ollama 2>/dev/null || true
echo "  ✅ Servicio Ollama configurado"

# Arrancar Ollama en background si el servicio no funciona
if ! pgrep -x "ollama" > /dev/null; then
    echo "  Iniciando Ollama en background..."
    OLLAMA_HOST=0.0.0.0:11434 nohup ollama serve > ~/ollama.log 2>&1 &
    sleep 5
    echo "  ✅ Ollama arrancado en background"
fi

# ─────────────────────────────────────────────────────────
# 3. VERIFICAR QUE OLLAMA ESTÁ CORRIENDO
# ─────────────────────────────────────────────────────────
echo ""
echo "[3/5] Verificando Ollama..."
sleep 3
if curl -s http://localhost:11434/api/version &>/dev/null; then
    echo "  ✅ Ollama API respondiendo en :11434"
    curl -s http://localhost:11434/api/version
else
    echo "  ⚠️  Ollama iniciando... (puede tomar unos segundos)"
    OLLAMA_HOST=0.0.0.0:11434 nohup ollama serve > ~/ollama.log 2>&1 &
    sleep 8
    curl -s http://localhost:11434/api/version && echo "  ✅ OK"
fi

# ─────────────────────────────────────────────────────────
# 4. DESCARGAR MODELOS
# ─────────────────────────────────────────────────────────
echo ""
echo "[4/5] Descargando modelos LLM..."
echo "  RAM disponible: $(free -h | awk '/^Mem:/{print $7}') libre"
echo ""

# Modelo rápido para pruebas y tareas simples (3.8GB)
echo "  → Descargando llama3.2:3b (rápido, 3.8GB)..."
ollama pull llama3.2:3b
echo "  ✅ llama3.2:3b listo"

# Modelo potente para tareas complejas (necesita ~40GB RAM)
echo ""
echo "  → Descargando llama3.3:70b (potente, ~40GB) — esto toma varios minutos..."
ollama pull llama3.3:70b
echo "  ✅ llama3.3:70b listo"

# ─────────────────────────────────────────────────────────
# 5. CONFIGURAR OPENCLAW CON OLLAMA
# ─────────────────────────────────────────────────────────
echo ""
echo "[5/5] Configurando OpenClaw para usar Ollama..."

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Configurar openclaw para usar Ollama como backend
openclaw config set provider ollama 2>/dev/null || true
openclaw config set baseUrl http://localhost:11434 2>/dev/null || true
openclaw config set model llama3.3:70b 2>/dev/null || true
echo "  ✅ OpenClaw configurado con Ollama + llama3.3:70b"

echo ""
echo "=== Modelos disponibles ==="
ollama list

echo ""
echo "=== Servicios activos ==="
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✅ OLLAMA + IA LOCAL COMPLETAMENTE INSTALADO         ║"
echo "║                                                      ║"
echo "║  API Ollama:  http://192.168.1.193:11434             ║"
echo "║  Modelo 3B:   llama3.2:3b  (rápido)                  ║"
echo "║  Modelo 70B:  llama3.3:70b (potente)                 ║"
echo "║                                                      ║"
echo "║  Para chatear en terminal:                           ║"
echo "║    ollama run llama3.3:70b                           ║"
echo "╚══════════════════════════════════════════════════════╝"
