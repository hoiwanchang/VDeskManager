@echo off
title VDesk Manager - Virtual Desktop Manager
cd /d "%~dp0"

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: 检查并安装依赖
pip show pyvda >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

:: 启动
echo Starting VDesk Manager...
python main.py --no-hotkeys %*
