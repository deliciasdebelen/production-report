#!/bin/bash
# Instala Node.js via NVM (sin sudo) y luego OpenClaw
set -e

echo "============================================"
echo "  Instalando NVM + Node.js 22 + OpenClaw"
echo "============================================"

# --- NVM ---
echo ""
echo "[1/4] Instalando NVM..."
export NVM_DIR="$HOME/.nvm"
if [ -d "$NVM_DIR" ]; then
    echo "  NVM ya existe"
else
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    echo "  ✅ NVM instalado"
fi

# Cargar NVM en sesión actual
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# --- Node.js 22 ---
echo ""
echo "[2/4] Instalando Node.js 22 via NVM..."
nvm install 22
nvm use 22
nvm alias default 22
echo "  ✅ Node.js: $(node --version)"
echo "  ✅ npm: $(npm --version)"

# Agregar NVM al .bashrc si no existe
if ! grep -q 'NVM_DIR' ~/.bashrc; then
    cat >> ~/.bashrc << 'NVMEOF'

# NVM - Node Version Manager
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
NVMEOF
    echo "  ✅ NVM agregado a .bashrc"
fi

# --- OpenClaw ---
echo ""
echo "[3/4] Instalando OpenClaw via npm..."
npm install -g openclaw 2>&1 | tail -5
echo "  ✅ OpenClaw instalado"

# --- Verificar ---
echo ""
echo "[4/4] Verificación final..."
echo "  Node.js: $(node --version)"
echo "  npm: $(npm --version)"
openclaw --version 2>/dev/null && echo "  ✅ OpenClaw OK" || echo "  ⚠️  OpenClaw: verificar con: openclaw --version"

echo ""
echo "=== Servicios Docker activos ==="
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"

echo ""
echo "============================================"
echo "  ✅ INSTALACIÓN COMPLETADA"
echo ""
echo "  Para configurar OpenClaw, haz SSH al servidor:"
echo "  ssh administrador@192.168.1.193"
echo "  Y ejecuta: openclaw onboard --install-daemon"
echo "============================================"
