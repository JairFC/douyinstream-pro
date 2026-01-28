@echo off
cd /d "%~dp0"

REM Check venv exists
if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found!
    echo Run install.bat first.
    pause
    exit /b 1
)

echo Starting DouyinStream Pro Web...
echo.

REM Activate venv
call venv\Scripts\activate.bat

REM Start backend in new window
echo Starting Backend API on http://127.0.0.1:8000
start "Backend API" cmd /k "cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting Frontend on http://127.0.0.1:3000
start "Frontend" cmd /k "cd frontend && python -m http.server 3000"

echo.
echo ========================================
echo  Servers Running!
echo ========================================
echo  Frontend: http://127.0.0.1:3000
echo  Backend:  http://127.0.0.1:8000
echo  API Docs: http://127.0.0.1:8000/docs
echo ========================================
echo.
echo Press any key to open browser...
pause >nul
start http://127.0.0.1:3000
