@echo off
REM Nerve Center URL ayarla
set NERVE_CENTER_URL=http://localhost:8001

REM Python agent başlat
python node_agent/agent.py

pause