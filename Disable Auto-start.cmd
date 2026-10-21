@echo off
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\BugCircuit.cmd" del "%STARTUP%\BugCircuit.cmd"
echo BugCircuit Windows auto-start has been disabled.
pause
