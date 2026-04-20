@echo off
setlocal
:: Neural Forge Node.js Worker Launcher

echo [🚀] NEURAL FORGE | NODE.JS CORE WORKER LAUNCHER
echo [INFO] Preparing Environment...

:: Diagnostic: Check Node.js
node -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [❌] ERROR: Node.js is not installed or not in PATH.
    echo [i] Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

:: Diagnostic: Check NPM
npm -v >nul 2>&1
if %errorlevel% neq 0 (
    echo [❌] ERROR: NPM is not installed or not in PATH.
    pause
    exit /b 1
)

cd neural-forge-core || (
    echo [❌] ERROR: Could not find 'neural-forge-core' directory.
    pause
    exit /b 1
)

:: Check if node_modules exists, if not run npm install
if not exist "node_modules\" (
    echo [INFO] First time setup: Installing dependencies...
    call npm install || (
        echo [❌] ERROR: 'npm install' failed.
        pause
        exit /b 1
    )
)

:: Set environment variables
set NERVE_CENTER_URL=http://localhost:8001
set OLLAMA_MODEL=mistral:latest

echo [INFO] Starting Node.js Worker...
node index.js || (
    echo [❌] ERROR: Worker crashed or failed to start.
    pause
    exit /b 1
)

pause
