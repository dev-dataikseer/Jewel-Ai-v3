@echo off
setlocal EnableDelayedExpansion

echo ==========================================================
echo        JEWEL AI - AI JEWELRY STUDIO
echo ==========================================================
echo.

set "ROOT=%~dp0.."
set "API=%ROOT%\backend"
set "WEB=%ROOT%\frontend"

REM --- Python check ---
set "PYTHON_CMD=python"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=py -3"
    !PYTHON_CMD! --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed or not available via python/py launcher. Install Python 3.12+ from python.org
        pause
        exit /b 1
    )
)

REM --- Node check ---
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed. Install from nodejs.org
    pause
    exit /b 1
)

echo [1/5] Python virtual environment...
set "VENV=%API%\.venv"
if not exist "%VENV%\Scripts\python.exe" (
    echo       Creating virtual environment...
    %PYTHON_CMD% -m venv "%VENV%"
) else (
    echo       Virtual environment found.
)
call "%VENV%\Scripts\activate.bat"

echo [2/5] Installing API dependencies...
set "REQ_STAMP=%VENV%\requirements.installed"
if exist "%REQ_STAMP%" (
    fc /B "%API%\requirements.txt" "%REQ_STAMP%" >nul 2>&1
    if errorlevel 1 (
        "%VENV%\Scripts\python.exe" -m pip install -r "%API%\requirements.txt" -q
        copy /Y "%API%\requirements.txt" "%REQ_STAMP%" >nul
    ) else (
        echo       API dependencies OK.
    )
) else (
    "%VENV%\Scripts\python.exe" -m pip install -r "%API%\requirements.txt" -q
    copy /Y "%API%\requirements.txt" "%REQ_STAMP%" >nul
)

if not exist "%API%\.env" (
    echo [3/5] Creating backend\.env for local SQLite...
    copy /Y "%API%\.env.local.example" "%API%\.env" >nul
) else (
    echo [3/5] backend\.env found.
)

echo [4/5] Installing web dependencies...
if not exist "%WEB%\node_modules\" (
    pushd "%WEB%"
    call npm install --silent
    popd
) else (
    echo       Web dependencies OK.
)

echo [5/5] Starting servers...
echo.
echo   API:  http://127.0.0.1:8000
echo   App:  http://localhost:5173
echo   Admin: admin@jewelai.com / changeme
echo   User:  studio@jewelai.com / studio123
echo.
echo   Close the API and Web windows to stop.
echo ==========================================================
echo.

set "PYTHONPATH=%API%"
set "DATABASE_URL=sqlite:///./jewel.db"
set "ADMIN_EMAIL=admin@jewelai.com"
set "ADMIN_PASSWORD=changeme"
set "API_PUBLIC_URL=http://127.0.0.1:8000"

REM Load FAL_ADMIN_KEY from backend\.env into this process (pydantic also reads .env;
REM explicit set helps when a parent shell polluted env vars).
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b "FAL_ADMIN_KEY=" "%API%\.env"`) do (
  set "FAL_ADMIN_KEY=%%B"
)

start "Jewel AI - API" cmd /k "cd /d "%API%" && set PYTHONPATH=. && set DATABASE_URL=sqlite:///./jewel.db && set ADMIN_EMAIL=admin@jewelai.com && set ADMIN_PASSWORD=changeme && set API_PUBLIC_URL=http://127.0.0.1:8000 && if defined FAL_ADMIN_KEY set FAL_ADMIN_KEY=!FAL_ADMIN_KEY! && "%VENV%\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

start "Jewel AI - Web" cmd /k "cd /d "%WEB%" && npm run dev"

timeout /t 4 /nobreak >nul
start "" "http://localhost:5173"

echo Done. Browser should open shortly.
