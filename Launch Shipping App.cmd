@echo off
cd /d "%~dp0"

echo Starting Shipping App...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Logistics-App.ps1"

if errorlevel 1 (
    echo.
    echo The Shipping App failed to start.
    pause
)
