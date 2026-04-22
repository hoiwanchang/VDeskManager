@echo off
title Building VDesk Manager
cd /d "%~dp0"

:: 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: 检查依赖
pip install -r requirements.txt

echo.
echo ============================================
echo   Building VDesk Manager...
echo ============================================
echo.

pyinstaller --noconfirm --onefile --noconsole ^
    --name "VDeskManager" ^
    --add-data "src;src" ^
    --hidden-import pyvda ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    main.py

echo.
if exist "dist\VDeskManager.exe" (
    echo [SUCCESS] Built: dist\VDeskManager.exe
    echo.
    echo You can now copy VDeskManager.exe to any location and run it.
) else (
    echo [FAILED] Build failed. Check the output above.
)
echo.
pause
