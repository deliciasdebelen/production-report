# Force Deploy Script
# Zips the current directory and sends it to the server directly
# Requires 7z or tar. We will use tar (built-in In Windows 10+ and Linux)

$ServerUser = "administrador"
$ServerIP = "192.168.1.79"
$ServerPath = "~/apps/production-report"

Write-Host "--- FORCE DEPLOYMENT ---"

# 1. Create Archive (excluding venv, .git, __pycache__)
Write-Host "Creating archive..."
tar -cvf deploy_package.tar --exclude=venv --exclude=.git --exclude=__pycache__ --exclude=*.pyc --exclude=deploy_package.tar .

# 2. Upload to Server
Write-Host "Uploading to server $ServerIP..."
# Using scp. If ssh works, scp usually works.
scp deploy_package.tar ${ServerUser}@${ServerIP}:~/apps/production-report/deploy_package.tar

# 3. Extract and Restart on Server
Write-Host "Extracting and Restarting on Server..."
ssh ${ServerUser}@${ServerIP} "cd $ServerPath && tar -xvf deploy_package.tar && docker-compose down && docker-compose build && docker-compose up -d && rm deploy_package.tar"

# 4. Clean up local
Remove-Item deploy_package.tar

Write-Host "--- DEPLOYMENT COMPLETE ---"
