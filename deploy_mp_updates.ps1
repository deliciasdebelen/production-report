$Server = "192.168.1.193"
$User = "administrador"
$Pass = "GRW7czL3*"
$SSHTarget = "${User}@${Server}"

Write-Host "=== Deploy: MP vs Compras + Telegram Admin ===" -ForegroundColor Cyan

# ── Paso 1: Transferir el tar ─────────────────────────────────
Write-Host "[1/4] Transfiriendo archivos..." -ForegroundColor Yellow
scp -o StrictHostKeyChecking=no "update_mp_telegram.tar.gz" "${SSHTarget}:/home/${User}/update_mp_telegram.tar.gz"
Write-Host "OK." -ForegroundColor Green

# ── Paso 2: Extraer en el servidor ────────────────────────────
Write-Host "[2/4] Extrayendo archivos en el servidor..." -ForegroundColor Yellow
$extractCmd = "cd /home/administrador/production-report && tar -xzf /home/administrador/update_mp_telegram.tar.gz && echo 'EXTRACT_OK' && ls app/services/mp_alert_service.py app/routers/compras_mp.py app/routers/telegram_admin.py"
ssh -o StrictHostKeyChecking=no "$SSHTarget" $extractCmd
Write-Host "OK." -ForegroundColor Green

# ── Paso 3: Ejecutar migración ────────────────────────────────
Write-Host "[3/4] Ejecutando migracion de base de datos..." -ForegroundColor Yellow
$migrateCmd = "cd /home/administrador/production-report && source .venv/bin/activate 2>/dev/null; set -a && source .env && set +a && python migrate_telegram_subscribers.py"
ssh -o StrictHostKeyChecking=no "$SSHTarget" $migrateCmd
Write-Host "OK." -ForegroundColor Green

# ── Paso 4: Reiniciar el servicio ─────────────────────────────
Write-Host "[4/4] Reiniciando servicio..." -ForegroundColor Yellow
$restartCmd = "docker restart `$(docker ps -qf name=production) 2>/dev/null || sudo systemctl restart production-report 2>/dev/null || echo 'Reiniciar manualmente'; sleep 3; curl -s -o /dev/null -w 'HTTP Status: %{http_code}' http://localhost:8000/login"
ssh -o StrictHostKeyChecking=no "$SSHTarget" $restartCmd
Write-Host ""
Write-Host "=== Deploy completado ===" -ForegroundColor Green
Write-Host "  http://192.168.1.193:8000/compras-mp" -ForegroundColor White
Write-Host "  http://192.168.1.193:8000/telegram-admin" -ForegroundColor White
