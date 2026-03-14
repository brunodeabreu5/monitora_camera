@echo off
setlocal
cd /d "%~dp0"

set "APP_VERSION=4.2.0"
set "APP_EXE=HikvisionRadarProV42.exe"
set "NO_PAUSE=1"
set "SKIP_PIP_INSTALL=1"

call build_hikvision_pro_v42_windows.bat
if errorlevel 1 exit /b 1

if not exist local_update mkdir local_update
copy /Y "dist\%APP_EXE%" "local_update\%APP_EXE%" >nul
if errorlevel 1 exit /b 1

(
echo {
echo   "version": "%APP_VERSION%",
echo   "exe_path": "%APP_EXE%"
echo }
) > "local_update\update_manifest.json"

echo.
echo Pacote de update local pronto em:
echo %cd%\local_update\%APP_EXE%
echo %cd%\local_update\update_manifest.json
echo.
echo Configure no app:
echo update_manifest_url=%cd%\local_update\update_manifest.json
if not "%NO_PAUSE%"=="1" pause
