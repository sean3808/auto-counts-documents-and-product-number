@echo off
REM ============================================
REM  run.bat - Launcher for run.ps1
REM  Double-click to execute the document processor
REM ============================================

cd /d "%~dp0"

REM Execute run.ps1 with PowerShell 7 (pwsh)
REM -NoProfile: Skip loading profile for faster startup
REM -ExecutionPolicy Bypass: Allow script execution
REM -File: Run the script file

pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" all

REM If pwsh is not available, try Windows PowerShell
if errorlevel 9009 (
    echo [Warning] PowerShell 7 not found, trying Windows PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" all
)

REM Keep window open to see results
echo.
echo Press any key to close...
pause >nul
