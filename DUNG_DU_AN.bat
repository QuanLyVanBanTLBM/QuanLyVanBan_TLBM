@echo off
chcp 65001 >nul
title DUNG DU AN QUAN LY VAN BAN VA TAI LIEU MAT

echo ===============================================================================
echo        DUNG CAC DICH VU CUA DU AN QUAN LY VAN BAN - NHOM 2
echo ===============================================================================
echo.

echo Dang tim va tat tien trinh tren cong 8000 (Backend Django)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":8000 " ^| findstr "LISTENING"') do (
    echo - Dang dung PID: %%a
    taskkill /F /PID %%a >nul 2>nul
)

echo Dang tim va tat tien trinh tren cong 5173 (Frontend React)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":5173 " ^| findstr "LISTENING"') do (
    echo - Dang dung PID: %%a
    taskkill /F /PID %%a >nul 2>nul
)

echo Dang dung PostgreSQL local port 55432...
"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "%~dp0data\pgdata" stop >nul 2>nul

echo.
echo ===============================================================================
echo [THANH CONG] Da tat cac tien trinh Backend va Frontend!
echo ===============================================================================
echo.
pause
