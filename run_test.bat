@echo off
setlocal
title Flash npmBuilder v1.02 - Test Runner
echo ====================================================
echo        Flash npmBuilder v1.02 - Test Launcher
echo        Developed by: Tech Realtime ^& SaQuiz Perks
echo        Conceived by: Mr. Saqlain
echo ====================================================
echo.

:: Try py -3.12, py, or python
py -3.12 -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py -3.12
    goto run
)

py -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py
    goto run
)

python -c "import sys" >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto run
)

echo [ERROR] Python not found! Please install Python 3.10+ from python.org
pause
exit /b 1

:run
echo Starting Flash npmBuilder using: %PY_CMD%
%PY_CMD% "%~dp0app.py"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%
    pause
)
endlocal
