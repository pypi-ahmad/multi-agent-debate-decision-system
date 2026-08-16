@echo off
setlocal
cd /d "%~dp0"

echo === Multi-Agent Debate Decision System ===

where uv >nul 2>&1
if errorlevel 1 (
    echo uv not found, installing it now...
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo Installing/updating dependencies...
uv sync
if errorlevel 1 (
    echo.
    echo Dependency install failed. See errors above.
    pause
    exit /b 1
)
echo Optional RAG embeddings: ollama pull nomic-embed-text
if not exist "data\lancedb" mkdir data\lancedb

if not exist ".env" (
    if exist ".env.example" (
        echo No .env found - copying .env.example as a starting point.
        copy /y ".env.example" ".env" >nul
        echo Edit .env with API keys if you are not using Ollama only.
    )
)

if not exist "data\debates" mkdir data\debates

echo Starting the app at http://localhost:8522 ...
uv run streamlit run app.py

pause
