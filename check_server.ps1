$ServerUser = "administrador"
$ServerIP = "192.168.1.79"

Write-Host "Checking SSH connection..."
ssh ${ServerUser}@${ServerIP} "echo 'SSH SUCCESS'; ls -la; mkdir -p ~/apps/production-report"
