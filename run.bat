@echo off
REM Inicia o Jarvis Worker SEM janela de console (evita Windows Narrator / Cortana)
REM Logs em: jarvis.log (mesma pasta)

cd /d "%~dp0"

REM Localizar pythonw.exe no mesmo diretorio do python.exe ativo
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i & goto :found
:found
set PYTHONW_PATH=%PYTHON_PATH:python.exe=pythonw.exe%

if exist "%PYTHONW_PATH%" (
    start "" "%PYTHONW_PATH%" main.py
    echo [Jarvis] Iniciado sem console. Logs em: %~dp0jarvis.log
) else (
    echo [Jarvis] pythonw nao encontrado, usando python normal...
    start "" python main.py
)

timeout /t 2 >nul
