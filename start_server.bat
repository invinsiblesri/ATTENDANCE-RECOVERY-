@echo off
title AttendAI Agentic Server
echo ========================================================
echo   AttendAI - 100%% Agentic AI Attendance Recovery System
echo   Starting server at http://localhost:8000 ...
echo ========================================================
cd /d "%~dp0"

IF EXIST ".\.venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe run.py
) ELSE (
    python run.py
)

pause
