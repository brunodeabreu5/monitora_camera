@echo off
REM Hikvision Radar Pro V4.2 Launcher
echo Starting Hikvision Radar Pro V4.2...
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Error running application!
    pause
)
