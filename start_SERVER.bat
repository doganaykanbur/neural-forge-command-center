@echo off
TITLE Neural Forge — SERVER CONTROL
echo ======================================================
echo   NEURAL FORGE — STARTING SERVER (Phase 15)
echo ======================================================

:: 1. Start Backend
echo [*] Launching Backend...
cd backend
start "Neural Forge - Backend" cmd /k "python main.py"
cd ..

:: Wait 3 seconds for Uvicorn to bind to port 8000
echo [*] Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

:: 2. Start Frontend (Admin Panel)
echo [*] Launching Admin Dashboard...
cd admin-panel
start "Neural Forge - Frontend" cmd /k "npm run dev"
cd ..

echo.
echo [✓] SERVER STARTED!
echo [i] Admin UI: http://localhost:3000
echo [i] Backend : http://localhost:8000
echo ======================================================
pause
