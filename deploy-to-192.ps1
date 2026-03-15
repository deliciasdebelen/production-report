# ============================================================================
# deploy-to-192.ps1
# Script de despliegue completo al servidor 192.168.1.193
# Migra el proyecto, configura Docker, instala Node.js + OpenClaw
# ============================================================================

param(
    [string]$Server = "192.168.1.193",
    [string]$User = "administrador",
    [string]$Pass = "GRW7czL3*",
    [string]$RemoteDir = "~/production-report",
    [switch]$SkipTransfer,
    [switch]$SkipDocker,
    [switch]$InstallOpenClaw,
    [switch]$All
)

$ErrorActionPreference = "Stop"
$SSHTarget = "${User}@${Server}"

# --- Helper: ejecutar comando SSH con contraseña via plink (PuTTY) o ssh
function Invoke-SSH {
    param([string]$Command, [string]$Description = "")
    if ($Description) { Write-Host "`n[SSH] $Description" -ForegroundColor Cyan }
    
    # Intentar con plink si está disponible
    $plinkPath = (Get-Command plink -ErrorAction SilentlyContinue)?.Source
    if ($plinkPath) {
        echo $Pass | plink -ssh -pw $Pass -batch "$SSHTarget" $Command
    }
    else {
        # Usar ssh con variable de entorno SSHPASS si está en WSL, o Posh-SSH
        Write-Host "  Ejecutando: $Command" -ForegroundColor DarkGray
        $result = ssh -o StrictHostKeyChecking=no -o BatchMode=no "$SSHTarget" $Command
        return $result
    }
}

Write-Host @"
╔══════════════════════════════════════════════════════════╗
║         DEPLOY → $Server           ║
║         production-report + OpenClaw AI                 ║
╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green

# ─────────────────────────────────────────────────────────
# PASO 1: Setup SSH Key (una sola vez para evitar contraseñas)
# ─────────────────────────────────────────────────────────
Write-Host "`n[1/6] Configurando SSH Key..." -ForegroundColor Yellow

$sshDir = "$env:USERPROFILE\.ssh"
$keyFile = "$sshDir\id_rsa_prodserver"

if (-not (Test-Path $keyFile)) {
    Write-Host "  Generando nueva clave SSH RSA..." -ForegroundColor DarkGray
    ssh-keygen -t rsa -b 4096 -f $keyFile -N "" -C "antigravity-prodserver" | Out-Null
    Write-Host "  ✅ Clave generada: $keyFile" -ForegroundColor Green
}
else {
    Write-Host "  ✅ Clave SSH ya existe: $keyFile" -ForegroundColor Green
}

# Copiar clave pública al servidor
$pubKey = Get-Content "$keyFile.pub"
Write-Host "  Copiando clave pública al servidor..." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  EJECUTA este comando manualmente para copiar la clave SSH:" -ForegroundColor Magenta
Write-Host "  ssh-copy-id -i $keyFile.pub -o StrictHostKeyChecking=no ${SSHTarget}" -ForegroundColor White
Write-Host ""
Write-Host "  O pega esto en el servidor:" -ForegroundColor Magenta
Write-Host "  echo '$pubKey' >> ~/.ssh/authorized_keys" -ForegroundColor White

# ─────────────────────────────────────────────────────────
# PASO 2: Transferir el proyecto (rsync/scp)
# ─────────────────────────────────────────────────────────
if (-not $SkipTransfer -or $All) {
    Write-Host "`n[2/6] Transfiriendo proyecto al servidor..." -ForegroundColor Yellow
    
    $localDir = $PSScriptRoot
    
    # Crear .rsyncignore temporal
    $rsyncIgnore = @"
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.git/
.pytest_cache/
*.db.bak*
app_backup_*/
*.tar.gz
deploy.log
debug_output.txt
full_log.txt
temp_schema.txt
"@
    $rsyncIgnore | Out-File -FilePath "$localDir\.rsyncignore" -Encoding utf8 -Force

    Write-Host "  Usando scp para transferir proyecto..." -ForegroundColor DarkGray
    
    # Crear tar del proyecto (excluyendo archivos innecesarios)
    $tarFile = "$env:TEMP\production-report-deploy.tar.gz"
    Write-Host "  Creando paquete de deploy..." -ForegroundColor DarkGray
    
    Push-Location $localDir
    git archive --format=tar.gz HEAD -o $tarFile
    Pop-Location
    
    Write-Host "  ✅ Paquete creado: $tarFile ($([math]::Round((Get-Item $tarFile).Length / 1MB, 2)) MB)" -ForegroundColor Green
    Write-Host "  Transfiriendo al servidor..." -ForegroundColor DarkGray
    scp -o StrictHostKeyChecking=no $tarFile "${SSHTarget}:/home/${User}/production-report.tar.gz"
    Write-Host "  ✅ Transferencia completada" -ForegroundColor Green
}

# ─────────────────────────────────────────────────────────
# PASO 3: Configurar y levantar Docker en el servidor
# ─────────────────────────────────────────────────────────
Write-Host "`n[3/6] Configurando Docker en el servidor..." -ForegroundColor Yellow

$dockerSetupScript = @'
set -e
echo "=== Preparando directorio del proyecto ==="
mkdir -p ~/production-report
cd ~/production-report

if [ -f ~/production-report.tar.gz ]; then
    echo "Extrayendo proyecto..."
    tar -xzf ~/production-report.tar.gz -C ~/production-report/
    rm ~/production-report.tar.gz
    echo "✅ Proyecto extraído"
fi

echo "=== Configurando .env ==="
if [ ! -f ~/production-report/.env ]; then
    cat > ~/production-report/.env << 'ENVEOF'
DATABASE_URL=postgresql://app_user:production_password@db:5432/production_db
SECRET_KEY=prod_secret_$(openssl rand -hex 32)
HOST=0.0.0.0
PORT=8000
PYTHONUNBUFFERED=1
OPENSSL_CONF=/etc/ssl/openssl.cnf
ENVEOF
    echo "✅ .env creado"
else
    echo "✅ .env ya existe (no se sobrescribe)"
fi

echo "=== Estado de Docker ==="
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
echo "✅ Servidor preparado"
'@

ssh -o StrictHostKeyChecking=no "${SSHTarget}" $dockerSetupScript

# ─────────────────────────────────────────────────────────
# PASO 4: Levantar Docker Compose
# ─────────────────────────────────────────────────────────
if (-not $SkipDocker -or $All) {
    Write-Host "`n[4/6] Levantando contenedores Docker..." -ForegroundColor Yellow
    
    $dockerComposeScript = @'
cd ~/production-report
echo "=== Levantando servicios ==="
docker compose down --remove-orphans 2>/dev/null || true
docker compose pull 2>/dev/null || true
docker compose up -d --build
echo "=== Esperando que los servicios estén listos ==="
sleep 15
docker compose ps
echo ""
echo "=== Verificando salud de la app ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}" http://localhost:8000/login || echo "App aún iniciando..."
'@
    
    ssh -o StrictHostKeyChecking=no "${SSHTarget}" $dockerComposeScript
}

# ─────────────────────────────────────────────────────────
# PASO 5: Instalar Node.js y OpenClaw
# ─────────────────────────────────────────────────────────
if ($InstallOpenClaw -or $All) {
    Write-Host "`n[5/6] Instalando Node.js 22 y OpenClaw..." -ForegroundColor Yellow
    
    $nodeInstallScript = @'
set -e
echo "=== Instalando Node.js 22 ==="
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version
npm --version
echo "✅ Node.js instalado"

echo "=== Instalando OpenClaw ==="
curl -fsSL https://openclaw.ai/install.sh | bash
echo "✅ OpenClaw instalado"

echo "=== Versión OpenClaw ==="
openclaw --version || true
'@
    
    ssh -o StrictHostKeyChecking=no "${SSHTarget}" $nodeInstallScript
}

# ─────────────────────────────────────────────────────────
# PASO 6: Resumen final
# ─────────────────────────────────────────────────────────
Write-Host "`n[6/6] Verificación final..." -ForegroundColor Yellow

$verifyScript = @'
echo "=== ESTADO FINAL DEL SERVIDOR ==="
echo ""
echo "--- Contenedores Docker ---"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
echo ""
echo "--- App Web ---"
curl -s -o /dev/null -w "App en :8000 -> HTTP %{http_code}\n" http://localhost:8000/login 2>/dev/null || echo "App no disponible aún"
echo ""
echo "--- Disco ---"
df -h / | tail -1
echo ""
echo "--- Node.js ---"
node --version 2>/dev/null || echo "Node no instalado (ejecutar con -InstallOpenClaw)"
echo ""
echo "--- OpenClaw ---"
openclaw --version 2>/dev/null || echo "OpenClaw no instalado (ejecutar con -InstallOpenClaw)"
echo ""
echo "✅ Deploy completado"
'@

ssh -o StrictHostKeyChecking=no "${SSHTarget}" $verifyScript

Write-Host @"

╔══════════════════════════════════════════════════════════╗
║  ✅ DEPLOY COMPLETADO                                     ║
║                                                          ║
║  App Web:     http://192.168.1.193:8000                  ║
║  OpenClaw UI: http://192.168.1.193:18789                 ║
║  VNC:         http://192.168.1.193:6080                  ║
║                                                          ║
║  Próximos pasos:                                         ║
║  1. Configurar OpenClaw: ssh + openclaw onboard          ║
║  2. Configurar Stitch Import API                         ║
╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
