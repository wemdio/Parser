@echo off
chcp 65001 >nul
echo ================================================
echo STOPPING OLD BACKEND...
echo ================================================

REM Kill any Python processes on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)

timeout /t 2 >nul

echo.
echo ================================================
echo STARTING NEW BACKEND...
echo ================================================
echo.

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python run_backend.py

pause

