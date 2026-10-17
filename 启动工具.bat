@echo off
chcp 65001 >nul
cd /d "%~dp0"
title mrptool

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   [ERROR] Python not found.
  echo.
  echo   Please install Python 3.8 or newer first:
  echo     https://www.python.org/downloads/
  echo   During install, CHECK the box "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0"

python -m mrptool.interactive
if errorlevel 1 (
  echo.
  echo   [ERROR] mrptool exited abnormally.
  echo.
  pause
)
