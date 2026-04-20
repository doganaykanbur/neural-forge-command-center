@echo off
title Neural Forge Presentation Mode
echo ==========================================
echo    NEURAL FORGE - COMMAND CENTER DEMO
echo ==========================================
echo [*] Initializing Presentation Environment...
echo [*] Checking local Python environment...

python -m pip install fastapi uvicorn pydantic >nul 2>&1

echo [*] Starting Mock Orchestrator Backend (Port 8001)...
start "Neural Forge Backend" /B python demo_server.py

echo [*] Waiting for backend to stabilize...
timeout /t 3 /nobreak >nul

echo [*] Launching High-Fidelity UI...
start index.html

echo.
echo [SUCCESS] Presentation system is online.
echo [INFO] Close this window to keep the backend running, 
echo        or press any key to exit.
echo ==========================================
pause
