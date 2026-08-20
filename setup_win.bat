@echo off
setlocal
title VoiceType4TW Environment Setup
chcp 65001 >nul

echo ========================================================
echo   VoiceType4TW Environment Setup
echo ========================================================

rem 1. Detect Python source
set PY_CMD=
set IS_EMBEDDED=0

if exist "%~dp0.runtime\python.exe" (
    set "PY_CMD=%~dp0.runtime\python.exe"
    set IS_EMBEDDED=1
    echo [INFO] Using embedded Python runtime.
    goto BOOTSTRAP_PIP
)

rem Try the Python Launcher with a supported version (3.10 - 3.14)
rem 3.12 first (matches the shipped portable runtime), then newer, then older.
where py >nul 2>&1
if errorlevel 1 goto TRY_PYTHON_CMD
py -3.12 -c "pass" >nul 2>&1
if not errorlevel 1 ( set "PY_CMD=py -3.12" & echo [INFO] Using Python 3.12 via Launcher. & goto CHECK_DONE )
py -3.13 -c "pass" >nul 2>&1
if not errorlevel 1 ( set "PY_CMD=py -3.13" & echo [INFO] Using Python 3.13 via Launcher. & goto CHECK_DONE )
py -3.14 -c "pass" >nul 2>&1
if not errorlevel 1 ( set "PY_CMD=py -3.14" & echo [INFO] Using Python 3.14 via Launcher. & goto CHECK_DONE )
py -3.11 -c "pass" >nul 2>&1
if not errorlevel 1 ( set "PY_CMD=py -3.11" & echo [INFO] Using Python 3.11 via Launcher. & goto CHECK_DONE )
py -3.10 -c "pass" >nul 2>&1
if not errorlevel 1 ( set "PY_CMD=py -3.10" & echo [INFO] Using Python 3.10 via Launcher. & goto CHECK_DONE )
echo [WARN] Python Launcher found, but no supported version (3.10-3.14) installed.

:TRY_PYTHON_CMD
rem Verify "python" is real (not the Microsoft Store alias) and a supported version
where python >nul 2>&1
if errorlevel 1 goto NO_PYTHON
python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>&1
if not errorlevel 1 ( set "PY_CMD=python" & echo [INFO] Detected compatible python command. & goto CHECK_DONE )
echo [WARN] "python" command is missing or not a supported version (3.10-3.14).
goto NO_PYTHON

:BOOTSTRAP_PIP
rem Embedded Python: ensure pip is available (ensurepip or existing pip)
"%~dp0.runtime\python.exe" -m pip --version >nul 2>&1
if not errorlevel 1 goto CHECK_DONE
echo [INFO] Bootstrapping pip for embedded Python...
"%~dp0.runtime\python.exe" -m ensurepip --upgrade
if errorlevel 1 (
    echo [ERROR] Failed to bootstrap pip for embedded Python.
    pause
    exit /b
)
goto CHECK_DONE

:NO_PYTHON
echo [INFO] Python not found. Attempting to download Portable Python...
powershell -ExecutionPolicy Bypass -File "%~dp0tools\get_portable_python.ps1"
if exist "%~dp0.runtime\python.exe" (
    set "PY_CMD=%~dp0.runtime\python.exe"
    set IS_EMBEDDED=1
    goto BOOTSTRAP_PIP
)
echo [INFO] Attempting to install via winget...
winget --version >nul 2>&1
if errorlevel 1 goto WINGET_NOT_FOUND
echo [INFO] Installing Python 3.12 via winget...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto WINGET_FAIL
echo [SUCCESS] Python installed. Please restart this script.
pause
exit /b

:WINGET_FAIL
echo [ERROR] Automatic installation failed.
pause & exit /b

:WINGET_NOT_FOUND
echo [ERROR] Python and winget not found.
echo [ACTION] Please download Python 3.12 from https://www.python.org/
pause & exit /b

:CHECK_DONE
rem 2. Run environment diagnostics
set "PYTHONPATH=%~dp0"
echo [INFO] Running environment diagnostics...
%PY_CMD% "%~dp0tools\doctor.py"
if errorlevel 1 goto DOCTOR_FAIL

rem 3. Install dependencies
if "%IS_EMBEDDED%"=="1" goto INSTALL_EMBEDDED

rem --- System Python: use venv ---
if exist "%~dp0venv\Scripts\python.exe" goto INSTALL_REQ_VENV
echo [INFO] Creating virtual environment...
%PY_CMD% -m venv venv
if errorlevel 1 goto VENV_FAIL

:INSTALL_REQ_VENV
echo [INFO] Upgrading pip...
"%~dp0venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto REQ_FAIL
echo [INFO] Installing dependencies (this may take a few minutes)...
"%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements-win.txt"
if errorlevel 1 goto REQ_FAIL
set "RUN_PY=%~dp0venv\Scripts\python.exe"
goto INSTALL_CUDA

rem --- Embedded Python: install directly, no venv needed ---
:INSTALL_EMBEDDED
set "RUN_PY=%~dp0.runtime\python.exe"
rem Skip pip install if PyQt6 already bundled
"%~dp0.runtime\python.exe" -c "import PyQt6" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Dependencies already bundled. Skipping pip install.
    goto DOWNLOAD_MODELS
)
echo [INFO] Installing dependencies into embedded runtime (this may take a few minutes)...
"%~dp0.runtime\python.exe" -m pip install --upgrade pip
"%~dp0.runtime\python.exe" -m pip install -r "%~dp0requirements-win.txt"
if errorlevel 1 goto REQ_FAIL

:INSTALL_CUDA
rem 3b. Install CUDA libraries only when an NVIDIA GPU is present.
rem Without a GPU the app runs Whisper on CPU and these ~800MB wheels are wasted.
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [INFO] No NVIDIA GPU detected. Skipping CUDA libraries - CPU mode will be used.
    goto DOWNLOAD_MODELS
)
echo [INFO] NVIDIA GPU detected. Installing CUDA acceleration libraries...
"%RUN_PY%" -m pip install -r "%~dp0requirements-cuda-win.txt"
if errorlevel 1 echo [WARNING] CUDA library install failed. The app will fall back to CPU mode.

:DOWNLOAD_MODELS
rem 4. Install STT Model (bundled or download)
set "MODEL_DEST=%APPDATA%\VoiceType4TW\whisper_models\models--Systran--faster-whisper-medium"
set "MODEL_BUNDLE=%~dp0bundled_models\models--Systran--faster-whisper-medium"

if exist "%MODEL_DEST%\snapshots" (
    echo [INFO] Whisper medium model already installed. Skipping.
) else if exist "%MODEL_BUNDLE%" (
    echo [INFO] Installing bundled Whisper medium model...
    robocopy "%MODEL_BUNDLE%" "%MODEL_DEST%" /E /NFL /NDL /NJH /NJS /nc /ns /np
    echo [INFO] Model installed successfully.
) else (
    echo [INFO] Downloading Whisper medium model ^(this may take a while^)...
    "%RUN_PY%" "%~dp0tools\download_models.py" medium
    if errorlevel 1 echo [WARNING] Model download failed. You can download it inside the app.
)

rem 5. Build the native launcher EXE (replaces BAT entry point, immune to cmd encoding issues)
set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
    echo [WARN] .NET csc.exe not found. Shortcut will use run_voicetype.bat instead.
    goto CREATE_SHORTCUT
)
echo [INFO] Building launcher EXE...
"%CSC%" /nologo /target:winexe /out:"%~dp0VoiceType4TW.exe" /win32icon:"%~dp0assets\icon.ico" /r:System.Windows.Forms.dll "%~dp0tools\launcher.cs"
if errorlevel 1 echo [WARN] Launcher build failed. Shortcut will use run_voicetype.bat instead.

:CREATE_SHORTCUT
rem 6. Create Desktop Shortcut
echo [INFO] Creating Desktop Shortcut...
powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"

echo ========================================================
echo   Setup Complete!
echo   Launch the app via run_voicetype.bat or Desktop shortcut.
echo ========================================================
pause
exit /b

:DOCTOR_FAIL
echo [ERROR] Environment diagnostics failed.
echo [ACTION] Please check diagnostic_report.txt for details.
pause & exit /b

:VENV_FAIL
echo [ERROR] Failed to create virtual environment.
pause & exit /b

:REQ_FAIL
echo [ERROR] Dependency installation failed.
pause & exit /b
