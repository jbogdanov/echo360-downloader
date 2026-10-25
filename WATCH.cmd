@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Run SETUP.cmd first.
  pause
  exit /b 1
)
if "%~1"=="" (
  "%~dp0.venv\Scripts\python.exe" -u "%~dp0echo360_tool.py" watch
) else (
  "%~dp0.venv\Scripts\python.exe" -u "%~dp0echo360_tool.py" watch "%~1"
)
pause
