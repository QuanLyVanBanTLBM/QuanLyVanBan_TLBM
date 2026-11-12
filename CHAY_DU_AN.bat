@echo off
setlocal
chcp 65001 >nul
title KHOI DONG DU AN QUAN LY VAN BAN VA TAI LIEU MAT - NHOM 2

echo ===============================================================================
echo        HE THONG QUAN LY VAN BAN VA TAI LIEU MAT - NHOM 2
echo ===============================================================================
echo.

:: 1. Kiem tra Python
echo [1/3] Kiem tra Python...
set "PY_EXE=python"
if exist "%~dp0backend\.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0backend\.venv\Scripts\python.exe"
) else (
    py -3.11 --version >nul 2>nul
    if not errorlevel 1 (
        set "PY_EXE=py -3.11"
    ) else (
        python --version >nul 2>nul
        if errorlevel 1 (
            echo [LOI] Khong tim thay Python trong bien moi truong PATH!
            pause
            exit /b 1
        )
    )
)

:: 2. Kiem tra Node.js / pnpm
echo [2/3] Kiem tra Node.js va pnpm...
node --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Node.js trong bien moi truong PATH!
    pause
    exit /b 1
)

:: 3. Khoi dong PostgreSQL, Backend va Frontend
echo [3/3] Dang khoi dong PostgreSQL, Backend va Frontend tren PostgreSQL local...
echo.

netstat -ano | findstr ":55432 " | findstr "LISTENING" >nul 2>nul
if %errorlevel% neq 0 (
    echo   * Dang bat PostgreSQL local port 55432...
    start /b "" "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "%~dp0data\pgdata" -l "%~dp0data\pgdata\logfile.log" -o "-p 55432" start >nul 2>nul
    timeout /t 2 /nobreak >nul 2>nul
)

echo   * Dang bat Backend Django tai http://127.0.0.1:8000 ...
pushd "%~dp0backend"
start "QLVB - Backend [Django :8000]" cmd /k "chcp 65001 >nul & title QLVB - Backend [Django :8000] & call ""%PY_EXE%"" manage.py runserver 127.0.0.1:8000"
popd

echo   * Dang bat Frontend React tai http://localhost:5173 ...
pushd "%~dp0frontend"
start "QLVB - Frontend [React :5173]" cmd /k "chcp 65001 >nul & title QLVB - Frontend [React :5173] & call pnpm dev"
popd

echo.
echo Dang cho Backend va Frontend khoi dong san sang [khoang 5 giay]...
timeout /t 5 /nobreak >nul 2>nul || ping -n 6 127.0.0.1 >nul

echo Dang mo giao dien he thong tren trinh duyet...
start http://localhost:5173

cls
echo ===============================================================================
echo        HE THONG QUAN LY VAN BAN VA TAI LIEU - NHOM 2
echo ===============================================================================
echo.
echo   [TRANG THAI] He thong dang chay truc tiep tren PostgreSQL Windows (Sieu nhe):
echo.
echo   + Frontend [Giao dien React]:     http://localhost:5173
echo   + Backend API [Django REST]:      http://127.0.0.1:8000/
echo   + Trang quan tri Django Admin:    http://127.0.0.1:8000/admin/
echo   + Co so du lieu:                  PostgreSQL Windows (Database: qlvb_dev)
echo.
echo   -----------------------------------------------------------------------------
echo   [TAI KHOAN DANG NHAP THU NGHIEM (NHOM 7)]:
echo   + Quan tri vien [Admin]:          admin             /  Admin@123
echo   + Truong Phong CNTT:              truongphong_cntt  /  Admin@123
echo   + Van Thu Luu Tru:                vanthu_cntt       /  Admin@123
echo   + Chuyen Vien CNTT:               chuyenvien_cntt   /  Admin@123
echo   -----------------------------------------------------------------------------
echo.
echo   [UU DIEM]:
echo   - Khong can mo Docker Desktop (tiet kiem 100%% RAM va CPU cho may).
echo   - De dung he thong, chi can click dup file: DUNG_DU_AN.bat
echo ===============================================================================
echo.
pause
