@echo off
setlocal
cd /d "%~dp0"

if not defined QUESTIONNAIRE_CONDA_ENV set "QUESTIONNAIRE_CONDA_ENV=database"
if not defined MONGODB_URI set "MONGODB_URI=mongodb://127.0.0.1:27018/?replicaSet=surveyRS"
if not defined MONGODB_DATABASE set "MONGODB_DATABASE=questionnaire"
if not defined PUBLIC_BASE_URL set "PUBLIC_BASE_URL=http://127.0.0.1:8000"

where conda >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot find conda. Initialize Conda in Windows PATH, then try again.
    pause
    exit /b 1
)

call conda run -n "%QUESTIONNAIRE_CONDA_ENV%" python -c "import fastapi, uvicorn, pymongo" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Required Python packages are missing from Conda environment "%QUESTIONNAIRE_CONDA_ENV%".
    echo Run this command from the project directory:
    echo conda run -n "%QUESTIONNAIRE_CONDA_ENV%" python -m pip install -r requirements.txt
    pause
    exit /b 1
)

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/ui/' -TimeoutSec 2; if ($r.StatusCode -eq 200 -and $r.Content.Contains('/ui-assets/app.js')) { exit 0 }; exit 1 } catch { exit 1 }" >nul 2>nul
if not errorlevel 1 (
    echo [INFO] The questionnaire server is already running on port 8000.
    start "" "http://127.0.0.1:8000/ui/"
    exit /b 0
)

echo Starting questionnaire system from:
echo %CD%
echo Database: %MONGODB_DATABASE%
echo URL: %PUBLIC_BASE_URL%
echo.
echo Ensure the MongoDB replica set is running before startup.
echo Press Ctrl+C in this window to stop the server.
echo.

call conda run -n "%QUESTIONNAIRE_CONDA_ENV%" --no-capture-output python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 (
    echo.
    echo [ERROR] Startup failed. Check the Conda environment, dependencies, and MongoDB connection.
    pause
)

endlocal
