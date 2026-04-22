@echo off
title VDesk Manager - Quick Start
cd /d "%~dp0"

echo ============================================
echo   VDesk Manager - Quick Start
echo ============================================
echo.

:: 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found!
    echo.
    echo Please install Python 3.10+ from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

python --version

:: 安装依赖
echo.
echo Checking dependencies...
pip install pyvda pystray Pillow --quiet 2>nul

echo.
echo Starting VDesk Manager...
echo (Close this window or press Ctrl+C to exit)
echo.

python main.py %*

pause
