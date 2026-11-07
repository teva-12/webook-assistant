@echo off
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo Python virtual environment not found. Run setup first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m app.telegram_bot
if errorlevel 1 pause
