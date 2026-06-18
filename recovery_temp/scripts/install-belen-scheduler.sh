#!/bin/bash
# install-belen-scheduler.sh
# Instala el scheduler de BELÉN como servicio del sistema
# Ejecutar en el servidor: bash install-belen-scheduler.sh

set -e
SCHEDULER_DIR="/home/administrador/belen-scheduler"
SERVICE_NAME="belen-scheduler"

echo "======================================"
echo "  BELÉN Scheduler — Instalación"
echo "======================================"

# 1. Crear directorio de trabajo
mkdir -p "$SCHEDULER_DIR"
cp ~/belen_scheduler.py "$SCHEDULER_DIR/scheduler.py"

# 2. Instalar dependencias Python en entorno virtual
python3 -m venv "$SCHEDULER_DIR/venv"
"$SCHEDULER_DIR/venv/bin/pip" install --upgrade pip
"$SCHEDULER_DIR/venv/bin/pip" install \
    apscheduler \
    python-telegram-bot \
    sqlalchemy \
    psycopg2-binary \
    requests \
    python-dotenv

# 3. Crear archivo .env si no existe
if [ ! -f "$SCHEDULER_DIR/.env" ]; then
    cat > "$SCHEDULER_DIR/.env" << 'ENV'
# BELÉN Scheduler — Configuración
# ¡COMPLETA ESTOS VALORES!

# Telegram Bot (crear en @BotFather)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Ollama — modelo de BELÉN
OLLAMA_URL=http://localhost:11434
BELEN_MODEL=belen_fast

# Base de datos del production-report
DATABASE_URL=postgresql://prod_user:prod_password@localhost:5434/production_db
ENV
    echo ""
    echo "⚠️  Edita el archivo .env antes de iniciar el servicio:"
    echo "    nano $SCHEDULER_DIR/.env"
fi

# 4. Crear servicio systemd (o script de inicio si no hay systemd)
if command -v systemctl &> /dev/null; then
    # Usando systemd
    cat > /tmp/belen-scheduler.service << SERVICE
[Unit]
Description=BELÉN Scheduler — Tareas automáticas de inventario y producción
After=network.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=administrador
WorkingDirectory=$SCHEDULER_DIR
EnvironmentFile=$SCHEDULER_DIR/.env
ExecStart=$SCHEDULER_DIR/venv/bin/python $SCHEDULER_DIR/scheduler.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

    sudo cp /tmp/belen-scheduler.service /etc/systemd/system/
    sudo systemctl daemon-reload
    echo "✅ Servicio systemd creado: $SERVICE_NAME"
    echo ""
    echo "Comandos útiles:"
    echo "  sudo systemctl start $SERVICE_NAME    ← iniciar"
    echo "  sudo systemctl enable $SERVICE_NAME   ← iniciar al arranque"
    echo "  sudo systemctl status $SERVICE_NAME   ← ver estado"
    echo "  sudo journalctl -u $SERVICE_NAME -f   ← ver logs en tiempo real"
else
    # Sin systemd (ej. Docker container) — usar nohup
    cat > "$SCHEDULER_DIR/start.sh" << 'STARTSH'
#!/bin/bash
source "$(dirname "$0")/venv/bin/activate"
cd "$(dirname "$0")"
python scheduler.py >> belen_scheduler.log 2>&1 &
echo "BELÉN Scheduler iniciado. PID: $!"
STARTSH
    chmod +x "$SCHEDULER_DIR/start.sh"
    echo "✅ Script de inicio creado: $SCHEDULER_DIR/start.sh"
fi

echo ""
echo "======================================"
echo "  Instalación completada 🎉"
echo "======================================"
echo ""
echo "PRÓXIMOS PASOS:"
echo "1. Editar configuración: nano $SCHEDULER_DIR/.env"
echo "2. Crear bot en Telegram: hablar con @BotFather → /newbot"
echo "3. Obtener chat ID: hablar con @userinfobot"
echo "4. Probar una tarea:"
echo "   cd $SCHEDULER_DIR && venv/bin/python scheduler.py --test stock"
echo "5. Si todo funciona, iniciar el servicio:"
echo "   sudo systemctl enable --now belen-scheduler"
