@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Toonflow-app\scripts\start-timesfm-dashboard.ps1"

if errorlevel 1 (
  echo.
  echo Startup failed. See:
  echo C:\Users\84922\Desktop\codeX\Toonflow-app\logs\timesfm-dashboard-startup.err.log
  pause
)

exit /b %ERRORLEVEL%
