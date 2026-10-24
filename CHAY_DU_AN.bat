@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title HE THONG QUAN LY VAN BAN VA TAI LIEU (QLVB&TL)

:MENU
cls
echo ===============================================================================
echo        HE THONG QUAN LY VAN BAN VA TAI LIEU (QLVB&TL) - LOP CD25CT_CLC
echo ===============================================================================
echo.
echo   [1] KHOI DONG DU AN   (Bat Backend Django :8000 + Frontend React :5173)
echo   [2] DUNG DU AN        (Tat toan bo tien trinh dang chay tren port 8000 va 5173)
echo   [3] KHOI DONG LAI     (Restart: Tat cac tien trinh cu va khoi dong lai moi)
echo   [0] THOAT
echo.
echo ===============================================================================
set "CHOICE=1"
set /p "CHOICE= Nhap lua chon cua ban [Mac dinh: 1]: "

if "%CHOICE%"=="1" goto START_PROJECT
if "%CHOICE%"=="2" goto STOP_PROJECT
if "%CHOICE%"=="3" goto RESTART_PROJECT
if "%CHOICE%"=="0" goto EXIT_SCRIPT

echo.
echo [!] Lua chon khong hop le, vui long thu lai.
timeout /t 2 >nul
goto MENU


:STOP_SERVICES
echo.
echo [*] Dang tim va tat tien trinh tren cong 8000 (Backend Django)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":8000 " ^| findstr "LISTENING"') do (
    echo     - Dung tien trinh PID: %%a
    taskkill /F /PID %%a >nul 2>nul
)

echo [*] Dang tim va tat tien trinh tren cong 5173 (Frontend React)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":5173 " ^| findstr "LISTENING"') do (
    echo     - Dung tien trinh PID: %%a
    taskkill /F /PID %%a >nul 2>nul
)
exit /b 0


:STOP_PROJECT
call :STOP_SERVICES
echo.
echo ===============================================================================
echo [THANH CONG] Da tat sach cac dich vu Backend va Frontend!
echo ===============================================================================
echo.
pause
goto MENU


:RESTART_PROJECT
call :STOP_SERVICES
timeout /t 2 >nul
goto START_PROJECT


:START_PROJECT
cls
echo ===============================================================================
echo        DANG KHOI DONG HE THONG QUAN LY VAN BAN VA TAI LIEU (QLVB&TL)
echo ===============================================================================
echo.

:: 1. Kiem tra Python
echo [1/3] Kiem tra Python...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python trong bien moi truong PATH!
    pause
    goto MENU
)

:: 2. Kiem tra Node.js
echo [2/3] Kiem tra Node.js...
node --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Node.js trong bien moi truong PATH!
    pause
    goto MENU
)

:: 3. Giai phong port cu neu dang bi chiem
call :STOP_SERVICES

:: 4. Khoi dong Backend va Frontend
echo.
echo [3/3] Dang khoi dong Backend va Frontend...
echo   * Dang bat Backend Django tai http://127.0.0.1:8000 ...
pushd "%~dp0backend"
if exist ".venv\Scripts\activate.bat" (
    start "QLVB - Backend [Django :8000]" cmd /k "chcp 65001 >nul & title QLVB - Backend [Django :8000] & call .venv\Scripts\activate.bat & python manage.py runserver 127.0.0.1:8000"
) else if exist "venv\Scripts\activate.bat" (
    start "QLVB - Backend [Django :8000]" cmd /k "chcp 65001 >nul & title QLVB - Backend [Django :8000] & call venv\Scripts\activate.bat & python manage.py runserver 127.0.0.1:8000"
) else (
    start "QLVB - Backend [Django :8000]" cmd /k "chcp 65001 >nul & title QLVB - Backend [Django :8000] & python manage.py runserver 127.0.0.1:8000"
)
popd

echo   * Dang bat Frontend React tai http://localhost:5173 ...
pushd "%~dp0frontend"
where pnpm >nul 2>nul
if %errorlevel% equ 0 (
    start "QLVB - Frontend [React :5173]" cmd /k "chcp 65001 >nul & title QLVB - Frontend [React :5173] & call pnpm dev"
) else (
    start "QLVB - Frontend [React :5173]" cmd /k "chcp 65001 >nul & title QLVB - Frontend [React :5173] & call npm run dev"
)
popd

echo.
echo Dang cho Backend va Frontend khoi dong san sang (khoang 5 giay)...
timeout /t 5 /nobreak >nul 2>nul || ping -n 6 127.0.0.1 >nul

echo Dang mo giao dien he thong tren trinh duyet...
start http://localhost:5173

cls
echo ===============================================================================
echo        HE THONG QUAN LY VAN BAN VA TAI LIEU (QLVB&TL) DANG HOAT DONG
echo ===============================================================================
echo.
echo   [DUONG DAN TRUY CAP]:
echo   + Frontend (Giao dien React):     http://localhost:5173
echo   + Backend API (Django REST):      http://127.0.0.1:8000/
echo   + Trang quan tri Django Admin:    http://127.0.0.1:8000/admin/
echo.
echo   -----------------------------------------------------------------------------
echo   [TAI KHOAN DANG NHAP THU NGHIEM (CHUNG MAT KHAU: @django_CD25CT_CLC)]:
echo   + Quan tri vien [Admin]:          admin
echo   + Truong Phong:                   truongphong   (Co 5 ho so cho ky tren Dashboard)
echo   + Giam Doc:                       giamdoc       (Co 6 ho so cho ky tren Dashboard)
echo   + Chuyen Vien:                    chuyenvien
echo   + Van Thu:                        vanthu
echo   -----------------------------------------------------------------------------
echo.
echo   [HUONG DAN DUNG HE THONG]:
echo   - De dung he thong, chay lai file nay va chon phim [2] DUNG DU AN.
echo   - Hoac dong truc tiep 2 cua so CMD (Backend & Frontend) dang chay.
echo ===============================================================================
echo.
pause
goto MENU

:EXIT_SCRIPT
exit /b 0
