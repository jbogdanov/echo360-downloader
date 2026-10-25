@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Drag your batch JSON file onto this launcher, or use START.cmd option 4.
  pause
  exit /b 1
)
if not exist "%~dp0.venv\Scripts\python.exe" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
"%~dp0.venv\Scripts\python.exe" -u "%~dp0echo360_tool.py" batch "%~1" --background --watch
pause
