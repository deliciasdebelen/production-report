param(
    [string]$Server = "192.168.1.193",
    [string]$User = "administrador",
    [string]$Pass = "GRW7czL3*",
    [string]$RemoteDir = "~/production-report"
)

$SSHTarget = "${User}@${Server}"
$tarFile = "$env:TEMP\app_sync_193.tar.gz"

Write-Host "Creating remote tar..."
# plink or ssh
ssh -o StrictHostKeyChecking=no "$SSHTarget" "cd ~/production-report && tar -czf app_sync_193.tar.gz app"

Write-Host "Downloading tar..."
scp -o StrictHostKeyChecking=no "${SSHTarget}:~/production-report/app_sync_193.tar.gz" $tarFile

Write-Host "Extracting locally..."
cd c:\Users\ovargas\Projects\production-report
if (Test-Path "app_sync_193.tar.gz") { Remove-Item "app_sync_193.tar.gz" }
Copy-Item $tarFile -Destination .
tar -xf app_sync_193.tar.gz

Write-Host "Done!"
