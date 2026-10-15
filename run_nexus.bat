@echo off
title Nexus Streamlit (Sovereign Study & Exam Platform)
echo ========================================================
echo   Nexus Streamlit - Sovereign Study & Exam Platform
echo   Powered by Nexus SQLite Engine + Parallel PDF Workers
echo ========================================================
cd /d "%~dp0"
..\pw-client\venv\Scripts\streamlit.exe run app.py --server.port 8503
pause
