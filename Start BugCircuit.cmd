@echo off
setlocal
cd /d "%~dp0"
title BugCircuit - Local Web Dashboard
set "PYTHON=py -3"
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
  set "PYTHON=python"
  python --version >nul 2>&1
  if errorlevel 1 goto MissingPython
)
if not exist ".venv\Scripts\python.exe" (
  echo [BugCircuit] Preparing Python environment on this laptop...
  %PYTHON% -m venv .venv
  if errorlevel 1 goto SetupFailed
)
if not exist ".venv\bugcircuit-web-v0.4.ready" (
  echo [BugCircuit] Installing dependencies on the first launch...
  ".venv\Scripts\python.exe" -m pip install -e .
  if errorlevel 1 goto SetupFailed
  type nul > ".venv\bugcircuit-web-v0.4.ready"
)
echo.
echo  BugCircuit local dashboard: http://127.0.0.1:8765
 echo  Safe GitHub updates check every 5 minutes. Keep this window open.
echo.
".venv\Scripts\python.exe" -m bugcircuit.updater --open
if errorlevel 1 (
  echo.
  echo [BugCircuit] Server could not start. Port 8765 might be in use.
  pause
)
exit /b 0
:MissingPython
echo.
echo Python 3.10+ is required only once. Install Python from https://www.python.org/downloads/windows/
echo Select "Add Python to PATH" during setup and double-click this file again.
pause
exit /b 1
:SetupFailed
echo.
echo [BugCircuit] Initial setup failed. Check your network and Python installation.
pause
exit /b 1
