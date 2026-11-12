@echo off
chcp 65001 >nul
title QLVB - Backend Django [Port 8000]
echo ===============================================================================
echo        QLVB BACKEND SERVER - DJANGO REST API (PORT 8000)
echo        URL: http://127.0.0.1:8000/
echo        Admin: http://127.0.0.1:8000/admin/
echo ===============================================================================
echo.
python manage.py runserver 127.0.0.1:8000
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Backend da bi dung hoac xay ra loi!
    pause
)
