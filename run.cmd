@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Multi-Agent Debate Decision System ===

if not exist "pyproject.toml" (
    echo This folder is not the repo root. Clone the project, then double-click run.cmd there.
    pause
    exit /b 1
)
if not exist "uv.lock" (
    echo uv.lock is missing. Re-clone https://github.com/pypi-ahmad/multi-agent-debate-decision-system
    pause
    exit /b 1
)
if not exist "app.py" (
    echo app.py is missing. Re-clone the repository.
    pause
    exit /b 1
)

call :ensure_uv
if errorlevel 1 (
    pause
    exit /b 1
)

rem Official uv project env: .venv at the workspace root.
set "VENV=%CD%\.venv"
set "UV_PROJECT_ENVIRONMENT=%VENV%"

if not exist "%VENV%\Scripts\python.exe" (
    echo First-time setup: creating project-root .venv with uv...
    uv python install
    if errorlevel 1 (
        echo Python install failed. See errors above.
        pause
        exit /b 1
    )
    uv venv "%VENV%" --allow-existing
    if errorlevel 1 (
        echo uv venv failed. See errors above.
        pause
        exit /b 1
    )
)

if not exist "%VENV%\Scripts\streamlit.exe" (
    echo Installing project dependencies into .venv...
    uv sync --project "%CD%"
    if errorlevel 1 (
        echo Dependency install failed. See errors above.
        pause
        exit /b 1
    )
    if not exist "%VENV%\Scripts\streamlit.exe" (
        echo Setup finished but Streamlit is still missing from .venv.
        pause
        exit /b 1
    )
    echo First-time setup done. Environment: %VENV%
) else (
    echo Using existing project venv: %VENV%
)

if not exist ".env" (
    if exist ".env.example" (
        echo No .env found - copying .env.example as a starting point.
        copy /y ".env.example" ".env" >nul
        echo Edit .env with API keys if you are not using Ollama only. OS env vars still win.
    )
)

if not exist "data\debates" mkdir data\debates
if not exist "data\lancedb" mkdir data\lancedb

echo Activating .venv and starting http://localhost:8522 ...
call "%VENV%\Scripts\activate.bat"
if errorlevel 1 (
    echo Could not activate .venv. Falling back to venv Scripts on PATH.
    set "PATH=%VENV%\Scripts;%PATH%"
)

streamlit run app.py
if errorlevel 1 (
    echo.
    echo App exited with an error.
)

pause
exit /b %ERRORLEVEL%

:ensure_uv
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>&1
if not errorlevel 1 exit /b 0
if exist "%USERPROFILE%\.local\bin\uv.exe" exit /b 0
if exist "%USERPROFILE%\.cargo\bin\uv.exe" exit /b 0

echo uv not found. Installing with the official standalone installer...
powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if errorlevel 1 (
    echo uv install failed. Install from https://docs.astral.sh/uv/getting-started/installation/ then re-run.
    exit /b 1
)

set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
where uv >nul 2>&1
if not errorlevel 1 exit /b 0
if exist "%USERPROFILE%\.local\bin\uv.exe" exit /b 0

echo uv installed but not on PATH. Open a new terminal, or add %%USERPROFILE%%\.local\bin to PATH.
exit /b 1
