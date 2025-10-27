@echo off
setlocal enabledelayedexpansion

rem Change to project directory (folder of this .bat)
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

rem Print current directory for debugging (useful for scheduled tasks)
echo [%date% %time%] Running from: %PROJECT_DIR% >> logs\cron_windows.out

rem Ensure logs directory exists
if not exist "logs" mkdir "logs"

rem Prune old per-run logs older than 14 days (ignore errors if any)
forfiles /p "logs" /m "cron_processor_*.log" /d -14 /c "cmd /c del /q @path" >nul 2>&1

rem Choose Python: prefer venv, fall back to system python on PATH
set "PYTHON_EXE=venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

rem Print Python exe path for debugging
echo [%date% %time%] Using Python: %PYTHON_EXE% >> logs\cron_windows.out

rem Append output to a rolling log file
set "LOG_FILE=logs\cron_windows.out"
"%PYTHON_EXE%" "cron_processor.py" >> "%LOG_FILE" 2>>&1

exit /b %ERRORLEVEL%


