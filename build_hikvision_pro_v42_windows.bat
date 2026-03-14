@echo off
setlocal
cd /d "%~dp0"

if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    set "PY_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
    goto found_python
)

where python >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=python
    goto found_python
)

where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py
    goto found_python
)

echo Python nao foi encontrado no PATH.
echo Instale o Python e marque "Add Python to PATH".
pause
exit /b 1

:found_python
echo Usando: %PY_CMD%
%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto pip_failed

%PY_CMD% -m pip install -r requirements_hikvision_pro_v4.txt
if errorlevel 1 goto pip_failed

if exist build rmdir /s /q build
if exist build goto clean_failed

if exist dist rmdir /s /q dist
if exist dist goto clean_failed

%PY_CMD% -m PyInstaller --noconfirm --onefile --windowed --name HikvisionRadarProV42 hikvision_pro_v42_app.py
if errorlevel 1 goto build_failed

if not exist dist\HikvisionRadarProV42.exe goto build_failed

echo.
echo Pronto. O executavel esta em:
echo %cd%\dist\HikvisionRadarProV42.exe
pause
exit /b 0

:pip_failed
echo.
echo Falha ao instalar ou atualizar dependencias.
pause
exit /b 1

:clean_failed
echo.
echo Falha ao limpar as pastas build/dist.
pause
exit /b 1

:build_failed
echo.
echo Falha ao gerar o executavel com PyInstaller.
pause
exit /b 1
