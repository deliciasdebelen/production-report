param(
    [string]$Server = "192.168.1.79",
    [string]$User = "administrador",
    [string]$Pass = "GRW7czL3*"
)

Write-Host "Archiving local app directory..."
if (Test-Path "$env:TEMP\deploy_sync_79.tar.gz") { Remove-Item "$env:TEMP\deploy_sync_79.tar.gz" }
tar -czf "$env:TEMP\deploy_sync_79.tar.gz" app

Write-Host "Copying tar to server..."
scp "$env:TEMP\deploy_sync_79.tar.gz" "${User}@${Server}:/tmp/deploy_sync_79.tar.gz"

Write-Host "Extracting on server and restarting web container..."
ssh -t "${User}@${Server}" "echo '${Pass}' | sudo -S tar -xzf /tmp/deploy_sync_79.tar.gz -C /home/administrador/apps/production-report/ && echo '${Pass}' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml restart web"

Write-Host "Done deploying code."
