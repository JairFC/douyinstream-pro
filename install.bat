@echo off
REM ===============================================
REM DouyinStream Pro - Instalador Portable
REM Solo ejecuta este archivo y todo se configura
REM ===============================================

echo.
echo  ____                   _       ____  _                            
echo ^|  _ \  ___  _   _ _   _(_)_ __ / ___^|^| ^|_ _ __ ___  __ _ _ __ ___  
echo ^| ^| ^| ^|/ _ \^| ^| ^| ^| ^| ^| ^| ^| '_ \\___ \^| __^| '__/ _ \/ _` ^| '_ ` _ \ 
echo ^| ^|_^| ^| (_) ^| ^|_^| ^| ^|_^| ^| ^| ^| ^| ^|___) ^| ^|_^| ^| ^|  __/ (_^| ^| ^| ^| ^| ^| ^|
echo ^|____/ \___/ \__,_^|\__, ^|_^|_^| ^|_^|____/ \__^|_^|  \___^|\__,_^|_^| ^|_^| ^|_^|
echo                    ^|___/                                   Pro
echo.
echo ===============================================
echo   INSTALADOR AUTOMATICO
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo Por favor instala Python 3.10+ desde:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Marca la opcion "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version

REM Check if VLC is installed
if exist "C:\Program Files\VideoLAN\VLC\vlc.exe" (
    echo [OK] VLC encontrado en Program Files
) else if exist "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" (
    echo [OK] VLC encontrado en Program Files x86
) else (
    echo [ADVERTENCIA] VLC no encontrado.
    echo.
    echo Para el reproductor integrado, instala VLC desde:
    echo   https://www.videolan.org/vlc/
    echo.
    echo Puedes continuar sin VLC, pero el player no funcionara.
    echo.
)

echo.
echo ===============================================
echo   INSTALANDO DEPENDENCIAS...
echo ===============================================
echo.

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activate and install
call venv\Scripts\activate.bat

echo Instalando paquetes...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de dependencias.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo   INSTALACION COMPLETA!
echo ===============================================
echo.
echo Para iniciar la aplicacion:
echo   - Doble clic en "run.bat"
echo   - O ejecuta: python main.py
echo.
echo.

REM Create run.bat
echo @echo off > run.bat
echo call venv\Scripts\activate.bat >> run.bat
echo python main.py >> run.bat

echo Archivo run.bat creado.
echo.

REM Ask to run now
set /p runNow="Iniciar DouyinStream Pro ahora? (S/n): "
if /i "%runNow%" neq "n" (
    echo.
    echo Iniciando...
    python main.py
)

pause
