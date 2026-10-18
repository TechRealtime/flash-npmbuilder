@echo off
setlocal enabledelayedexpansion
title Flash npmBuilder v1.02 - Portable Exe Builder
echo ====================================================
echo      Flash npmBuilder v1.02 - Executable Builder
echo      Developed by: Tech Realtime ^& SaQuiz Perks
echo      Conceived by: Mr. Saqlain
echo ====================================================
echo.

:: Detect Python environment
py -3.12 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py -3.12
    goto check_tools
)

py -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py
    goto check_tools
)

python -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto check_tools
)

echo [ERROR] Python was not detected on this system.
pause
exit /b 1

:check_tools
echo [+] Using Python: %PY_CMD%

echo [+] Cleaning previous build artifacts...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"

echo [+] Checking dependencies...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install pyinstaller send2trash

echo.
echo [+] Compiling Flash-npmBuilder.exe (Portable Standalone Single-File EXE)...
cd /d "%~dp0"

%PY_CMD% -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "Flash-npmBuilder" ^
    --icon "icon.ico" ^
    --add-data "assets;assets" ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    --hidden-import "send2trash" ^
    --hidden-import "urllib.request" ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --clean ^
    "app.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed! Check errors above.
    pause
    exit /b %errorlevel%
)

echo.
echo [+] Cleaning intermediate build folder so only dist remains...
if exist "build" rd /s /q "build"

if exist "dist\Flash-npmBuilder.exe" (
    echo.
    echo ======================================================================
    echo   [SUCCESS] Standalone Portable Exe Generated:
    echo   dist\Flash-npmBuilder.exe
    echo ======================================================================
    echo.
    echo Note: Always run the executable directly from the 'dist' folder!
    echo Do NOT run from the internal 'build' temporary folder.
)

pause
endlocal
