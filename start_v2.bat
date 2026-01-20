@echo off
REM DouyinStream Pro v2 - Start Script
REM Starts both backend and frontend servers

echo ================================
echo   DouyinStream Pro v2
echo ================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

REM Create data directory
if not exist "backend\data" mkdir "backend\data"

REM Check/install backend dependencies
echo [1/3] Checking backend dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing backend dependencies...
    pip install -r backend\requirements.txt
)

REM Start backend server
echo [2/3] Starting backend server on http://127.0.0.1:8000...
start "DouyinStream Backend" cmd /c "cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Serve frontend
echo [3/3] Starting frontend on http://127.0.0.1:3000...
start "DouyinStream Frontend" cmd /c "cd frontend && python -m http.server 3000"

echo.
echo ================================
echo   DouyinStream Pro v2 Running!
echo ================================
echo.
echo   Frontend: http://127.0.0.1:3000
echo   Backend:  http://127.0.0.1:8000
echo   API Docs: http://127.0.0.1:8000/docs
echo.
echo Press any key to stop all servers...
pause >nul

REM Kill the servers
taskkill /FI "WindowTitle eq DouyinStream*" /F >nul 2>&1

echo Servers stopped.
