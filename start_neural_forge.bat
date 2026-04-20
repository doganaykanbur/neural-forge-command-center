@echo off
TITLE Neural Forge — Master Control
echo ======================================================
echo   NEURAL FORGE — STARTING SYSTEM (Phase 12)
echo ======================================================

:: 1. Start Backend
echo [*] Launching Backend...
start "Neural Forge - Backend" cmd /k "cd backend && python main.py"

:: 2. Start Frontend (Admin Panel)
echo [*] Launching Frontend...
start "Neural Forge - Frontend" cmd /k "cd admin-panel && npm run dev"

:: 3. Start Node Agent
echo [*] Launching Node Agent...
start "Neural Forge - Node Agent" cmd /k "cd node_agent && python agent.py"

echo.
echo [✓] All components are launching in separate windows.
echo [i] Command Center: http://localhost:3000
echo [i] Backend       : http://localhost:8000
echo ======================================================
pause
