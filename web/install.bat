@echo off
echo ========================================
echo  DouyinStream Pro Web - Installer
echo ========================================
echo.

REM Check if venv exists
if exist venv\ (
    echo Virtual environment already exists.
    echo To reinstall, delete the venv folder first.
    goto :activate
)

echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    echo Make sure Python 3.8+ is installed.
    pause
    exit /b 1
)

:activate
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Installation Complete!
echo ========================================
echo.
echo To start the server:
echo   Double-click start.bat
echo.
pause
