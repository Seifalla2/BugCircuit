@echo off
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if not exist "%STARTUP%" (
 echo Windows Startup folder is not available.
 pause
 exit /b 1
)
(
 echo @echo off
 echo call "%~dp0Start BugCircuit.cmd"
) > "%STARTUP%\BugCircuit.cmd"
echo.
echo BugCircuit will start automatically when you sign in to Windows.
echo The dashboard address is http://127.0.0.1:8765/
pause
