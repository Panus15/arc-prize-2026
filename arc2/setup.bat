@echo off
REM First-time setup for the ARC-AGI-2 workspace (Windows).
REM   1. fetch the dataset repo as a shallow external checkout
REM   2. create .venv and install requirements.txt
REM   3. verify all 1120 public tasks parse
REM Safe to re-run: an existing checkout is updated, an existing venv is reused.
setlocal
cd /d "%~dp0"

set "DATASET_URL=https://github.com/arcprize/ARC-AGI-2.git"
set "DATASET_DIR=ARC-AGI-2"
if "%PYTHON%"=="" set "PYTHON=python"

echo.
echo ==^> Dataset
if exist "%DATASET_DIR%\.git" (
    echo     %DATASET_DIR% already present - pulling latest
    git -C "%DATASET_DIR%" pull --ff-only --depth 1 origin HEAD || goto fail
) else (
    git clone --depth 1 "%DATASET_URL%" "%DATASET_DIR%" || goto fail
)

echo.
echo ==^> Virtual environment
if not exist ".venv" (
    "%PYTHON%" -m venv .venv || goto nopy
)
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet || goto fail
".venv\Scripts\pip.exe" install -r requirements.txt || goto fail

echo.
echo ==^> Verifying dataset
".venv\Scripts\python.exe" -m arc verify || goto fail

echo.
echo Setup complete. Activate the environment with:
echo.
echo     .venv\Scripts\activate
echo.
echo Then try:
echo.
echo     python -m arc stats
echo     python -m arc show 007bbfb7
echo     pytest
echo.
goto end

:nopy
echo [ERROR] Could not run "%PYTHON%" -m venv.
echo Install Python 3.11+ and make sure it is on PATH, or set PYTHON to its full path:
echo     set "PYTHON=C:\path\to\python.exe" ^&^& setup.bat
goto end

:fail
echo.
echo [ERROR] Setup failed - see the messages above.

:end
endlocal
pause
