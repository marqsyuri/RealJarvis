@echo off
REM Inicia o Jarvis Worker SEM janela de console (evita Windows Narrator / Cortana)
REM Logs em: jarvis.log (mesma pasta)

cd /d "%~dp0"
start "" pythonw.exe main.py
echo [Jarvis] Iniciado em background. Logs em: %~dp0jarvis.log
timeout /t 2 >nul
