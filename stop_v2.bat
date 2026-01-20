@echo off
REM DouyinStream Pro v2 - Stop Script
REM Stops all running servers

echo Stopping DouyinStream Pro v2 servers...

REM Kill by window title
taskkill /FI "WindowTitle eq DouyinStream*" /F >nul 2>&1

REM Kill Python processes on our ports
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo Done. All servers stopped.
pause
