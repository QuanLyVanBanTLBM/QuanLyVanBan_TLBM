# ===============================================================================
#        HE THONG QUAN LY VAN BAN VA TAI LIEU MAT - NHOM 2
# ===============================================================================

$projectRoot = $PSScriptRoot

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "       HE THONG QUAN LY VAN BAN VA TAI LIEU MAT - NHOM 2" -ForegroundColor Yellow
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Kiem tra Python
Write-Host "[1/3] Kiem tra Python..." -ForegroundColor Gray
$pythonExe = if (Test-Path "$projectRoot\backend\.venv\Scripts\python.exe") {
    "$projectRoot\backend\.venv\Scripts\python.exe"
} else {
    $pyCheck = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCheck) { "py -3.11" } else { "python" }
}

# 2. Kiem tra npm / pnpm
Write-Host "[2/3] Kiem tra Node / pnpm..." -ForegroundColor Gray
$nodeCheck = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCheck) {
    Write-Host "[LOI] Khong tim thay Node.js trong bien moi truong PATH!" -ForegroundColor Red
    Pause
    exit 1
}

# 3. Khoi dong PostgreSQL, Backend va Frontend
Write-Host "[3/3] Dang khoi dong PostgreSQL, Backend va Frontend tren PostgreSQL local..." -ForegroundColor Green

$portCheck = netstat -ano | Select-String ":55432 " | Select-String "LISTENING"
if (-not $portCheck) {
    Write-Host "  * Dang bat PostgreSQL local port 55432..." -ForegroundColor Cyan
    Start-Process "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -ArgumentList "-D", "`"$projectRoot\data\pgdata`"", "-l", "`"$projectRoot\data\pgdata\logfile.log`"", "-o", "-p 55432", "start" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

Write-Host "  * Dang bat Backend Django tai http://127.0.0.1:8000 ..." -ForegroundColor Cyan
Start-Process cmd.exe -ArgumentList "/k", "chcp 65001 >nul & cd /d `"$projectRoot\backend`" & `"$pythonExe`" manage.py runserver 127.0.0.1:8000"

Write-Host "  * Dang bat Frontend React tai http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process cmd.exe -ArgumentList "/k", "chcp 65001 >nul & cd /d `"$projectRoot\frontend`" & pnpm dev"

Write-Host ""
Write-Host "Dang cho Backend va Frontend khoi dong san sang (khoang 5 giay)..." -ForegroundColor Gray
Start-Sleep -Seconds 5

Start-Process "http://localhost:5173"

Clear-Host
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "       HE THONG QUAN LY VAN BAN VA TAI LIEU - NHOM 2" -ForegroundColor Yellow
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  [TRANG THAI] He thong dang chay truc tiep tren PostgreSQL Windows (Sieu nhe):" -ForegroundColor Green
Write-Host ""
Write-Host "  + Frontend [Giao dien React]:     http://localhost:5173" -ForegroundColor White
Write-Host "  + Backend API [Django REST]:      http://127.0.0.1:8000/" -ForegroundColor White
Write-Host "  + Trang quan tri Django Admin:    http://127.0.0.1:8000/admin/" -ForegroundColor White
Write-Host "  + Co so du lieu:                  PostgreSQL Windows (Database: qlvb_dev)" -ForegroundColor White
Write-Host ""
Write-Host "  -----------------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  [TAI KHOAN DANG NHAP THU NGHIEM (NHOM 7)]:" -ForegroundColor Yellow
Write-Host "  + Quan tri vien [Admin]:          admin             /  Admin@123" -ForegroundColor White
Write-Host "  + Truong Phong CNTT:              truongphong_cntt  /  Admin@123" -ForegroundColor White
Write-Host "  + Van Thu Luu Tru:                vanthu_cntt       /  Admin@123" -ForegroundColor White
Write-Host "  + Chuyen Vien CNTT:               chuyenvien_cntt   /  Admin@123" -ForegroundColor White
Write-Host "  -----------------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  [UU DIEM]:" -ForegroundColor Cyan
Write-Host "  - Khong can mo Docker Desktop (tiet kiem 100% RAM va CPU cho may)." -ForegroundColor Gray
Write-Host "  - De dung he thong, chay file DUNG_DU_AN.bat" -ForegroundColor Gray
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
Pause
