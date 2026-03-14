@echo off
setlocal
cd /d "%~dp0"

set "APP_VERSION=4.2.0"
set "APP_EXE=HikvisionRadarProV42.exe"
set "APP_PUBLISHER=Hikvision Radar Pro"
set "GITHUB_RELEASE_TAG=v%APP_VERSION%"
set "GITHUB_RELEASE_BASE_URL=https://github.com/SEU_USUARIO/SEU_REPOSITORIO/releases/download/%GITHUB_RELEASE_TAG%"
set "NO_PAUSE=1"
if /i "%SKIP_PIP_INSTALL%"=="1" echo SKIP_PIP_INSTALL=1

call build_hikvision_pro_v42_windows.bat
if errorlevel 1 exit /b 1

if not exist "%cd%\dist\%APP_EXE%" (
    echo Executavel nao encontrado em dist\%APP_EXE%.
    exit /b 1
)

set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_EXE%" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_EXE%" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not exist "%ISCC_EXE%" (
    echo Inno Setup 6 nao foi encontrado.
    echo Instale o Inno Setup e tente novamente.
    exit /b 1
)

if not exist release mkdir release

"%ISCC_EXE%" ^
  /DMyAppVersion=%APP_VERSION% ^
  /DMyAppExeName=%APP_EXE% ^
  /DMyAppPublisher="%APP_PUBLISHER%" ^
  /DMyAppSourceDir="%cd%\dist" ^
  /DMyOutputDir="%cd%\release" ^
  "%cd%\installer\hikvision_radar_pro.iss"

if errorlevel 1 exit /b 1

(
echo {
echo   "version": "%APP_VERSION%",
echo   "installer_url": "%GITHUB_RELEASE_BASE_URL%/HikvisionRadarPro-%APP_VERSION%-setup.exe",
echo   "release_notes_url": "https://github.com/SEU_USUARIO/SEU_REPOSITORIO/releases/tag/%GITHUB_RELEASE_TAG%"
echo }
) > "%cd%\release\update_manifest.json"

echo.
echo Release pronto em:
echo %cd%\release\HikvisionRadarPro-%APP_VERSION%-setup.exe
echo %cd%\release\update_manifest.json
echo.
echo Antes de publicar, ajuste GITHUB_RELEASE_BASE_URL neste arquivo.
if not "%NO_PAUSE%"=="1" pause
