@echo off
setlocal
title VoiceType4TW Environment Setup

echo ========================================================
echo   VoiceType4TW Environment Setup (venv mode)
echo ========================================================

rem 1. Check if Python is installed
set PY_CMD=

where py >nul 2>&1
if not errorlevel 1 goto FOUND_PY
where python >nul 2>&1
if not errorlevel 1 goto FOUND_PYTHON
goto NO_PYTHON

:FOUND_PY
set PY_CMD=py -3.12
echo [INFO] Detected Python Launcher (py).
goto CHECK_DONE

:FOUND_PYTHON
set PY_CMD=python
echo [INFO] Detected python command.
goto CHECK_DONE

:NO_PYTHON
echo [INFO] Python not found. Attempting to install via winget...
winget --version >nul 2>&1
if errorlevel 1 goto WINGET_NOT_FOUND

echo [INFO] Installing Python 3.12 via winget...
winget install -e --id Python.Python.3.12 --scope machine --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto WINGET_FAIL
echo [SUCCESS] Python installed. Please restart this script.
pause
exit /b

:WINGET_FAIL
echo [ERROR] Automatic installation failed.
pause
exit /b

:WINGET_NOT_FOUND
echo [ERROR] Python and winget not found.
echo [ACTION] Please download and install Python 3.12 from https://www.python.org/
pause
exit /b

:CHECK_DONE
rem 1.5 Run environment diagnostics
echo [INFO] Running environment diagnostics...
%PY_CMD% "%~dp0tools\doctor.py"
if errorlevel 1 goto DOCTOR_FAIL

rem 2. Create Virtual Environment (venv)
if exist "%~dp0venv\Scripts\python.exe" goto INSTALL_REQ
echo [INFO] Creating virtual environment (venv)...
%PY_CMD% -m venv venv
if errorlevel 1 goto VENV_FAIL
goto INSTALL_REQ

:DOCTOR_FAIL
echo [ERROR] Environment diagnostics failed.
echo [ACTION] Please check diagnostic_report.txt for details.
pause
exit /b

:VENV_FAIL
echo [ERROR] Failed to create virtual environment.
pause
exit /b

:INSTALL_REQ
rem 3. Install requirements
echo [INFO] Upgrading pip...
"%~dp0venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto REQ_FAIL
echo [INFO] Installing dependencies (this may take a few minutes)...
"%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements-win.txt"
if errorlevel 1 goto REQ_FAIL

rem 4. Pre-download STT Models
echo [INFO] Pre-downloading STT Models (this will save time during first run)...
echo [INFO] This might take a while depending on your internet speed.
"%~dp0venv\Scripts\python.exe" "%~dp0tools\download_models.py" medium
if errorlevel 1 echo [WARNING] Model download skipped or failed. You can still download it inside the app.

rem 5. Create Desktop Shortcut
echo [INFO] Creating Desktop Shortcut...
powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"

echo ========================================================
echo   Environment Setup Complete!
echo   You can now launch the app via run_voicetype.bat
echo   or the Desktop shortcut.
echo ========================================================
pause
exit /b

:REQ_FAIL
echo [ERROR] Dependency installation failed.
pause
exit /b
