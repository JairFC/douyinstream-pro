@echo off
REM ===============================================
REM DouyinStream Pro - Ejecutar
REM ===============================================

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    python main.py
) else (
    echo Ejecutando sin entorno virtual...
    python main.py
)
