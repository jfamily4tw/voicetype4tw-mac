@echo off
setlocal
title Starting VoiceType4TW...
chcp 65001 >nul

set "BASE_DIR=%~dp0"

rem Priority 1: Embedded Python with packages installed
if exist "%BASE_DIR%.runtime\python.exe" (
    "%BASE_DIR%.runtime\python.exe" -c "import PyQt6" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHONW=%BASE_DIR%.runtime\pythonw.exe"
        goto LAUNCH_APP
    )
)

rem Priority 2: venv
if exist "%BASE_DIR%venv\Scripts\pythonw.exe" (
    set "PYTHONW=%BASE_DIR%venv\Scripts\pythonw.exe"
    goto LAUNCH_APP
)

rem Nothing ready — run setup
echo [INFO] Python environment not ready. Starting setup...
call "%BASE_DIR%setup_win.bat"

rem Re-check after setup
if exist "%BASE_DIR%.runtime\python.exe" (
    "%BASE_DIR%.runtime\python.exe" -c "import PyQt6" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHONW=%BASE_DIR%.runtime\pythonw.exe"
        goto LAUNCH_APP
    )
)
if exist "%BASE_DIR%venv\Scripts\pythonw.exe" (
    set "PYTHONW=%BASE_DIR%venv\Scripts\pythonw.exe"
    goto LAUNCH_APP
)

echo [ERROR] Setup failed or was cancelled.
pause
exit /b

:LAUNCH_APP
echo [INFO] Launching VoiceType4TW...
cd /d "%BASE_DIR%"
set "PYTHONPATH=%BASE_DIR%"
start "" "%PYTHONW%" main.py
exit
