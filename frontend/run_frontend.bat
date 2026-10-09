@echo off
chcp 65001 >nul
title QLVB - Frontend React [Port 5173]
echo ===============================================================================
echo        QLVB FRONTEND SERVER - REACT VITE (PORT 5173)
echo        URL: http://localhost:5173/
echo ===============================================================================
echo.
call npm.cmd run dev
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Frontend da bi dung hoac xay ra loi!
    pause
)
