param(
    [string]$Server = "192.168.1.193",
    [string]$User = "administrador",
    [string]$Pass = "GRW7czL3*"
)

Write-Host "Copying docker-compose.yml to server..."
scp docker-compose.yml "${User}@${Server}:/home/administrador/production-report/docker-compose.yml"

Write-Host "Restarting web container..."
ssh -t "${User}@${Server}" "echo '${Pass}' | sudo -S docker compose -f /home/administrador/production-report/docker-compose.yml up -d web"

Write-Host "Done deploying fix."
