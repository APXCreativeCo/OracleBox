# OracleBox Deployment Script
# Deploys oraclebox.py to Raspberry Pi and restarts service

param(
    [string]$PiHost = "192.168.1.74",
    [string]$PiUser = "dylan",
    [string]$RemotePath = "/home/dylan/oraclebox/oraclebox.py"
)

Write-Host ">>> Deploying OracleBox to Raspberry Pi..." -ForegroundColor Cyan
Write-Host ""

# Check if file exists
if (-not (Test-Path "oraclebox.py")) {
    Write-Host "[ERROR] oraclebox.py not found in current directory" -ForegroundColor Red
    exit 1
}

Write-Host "[*] Copying oraclebox.py to Pi..." -ForegroundColor Yellow
scp oraclebox.py "${PiUser}@${PiHost}:${RemotePath}"

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] File copied successfully" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "[*] Restarting OracleBox service..." -ForegroundColor Yellow
    ssh "${PiUser}@${PiHost}" "sudo systemctl restart oraclebox.service"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Service restarted successfully" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "[*] Checking service status..." -ForegroundColor Yellow
        ssh "${PiUser}@${PiHost}" "sudo systemctl status oraclebox.service --no-pager -n 20"
    } else {
        Write-Host "[ERROR] Failed to restart service" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[ERROR] Failed to copy file" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ">>> Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "   1. Verify announcements exist: ssh ${PiUser}@${PiHost} 'ls -lh /home/dylan/oraclebox/announcements/'"
Write-Host "   2. Test connection from Android app"
Write-Host "   3. Check logs: ssh ${PiUser}@${PiHost} 'sudo journalctl -u oraclebox.service -f'"
