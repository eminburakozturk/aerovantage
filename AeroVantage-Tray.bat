@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"

title AeroVantage

if exist "AeroVantage.ico" (
    rem .bat dosyasi ikon tutamaz — logolu baslatma: AeroVantage.exe / AeroVantage.lnk / masaustu kisayolu
)

if /I "%~1"=="/reset" goto :RESET
if /I "%~1"=="reset" goto :RESET
goto :NORMAL

:RESET
echo [!] Zorla sifirlama: tray + 8000/3000 portlari temizleniyor...
if exist "launcher\.tray.lock" del /f /q "launcher\.tray.lock" >nul 2>&1
if exist ".aero.pid" del /f /q ".aero.pid" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /PID %%a /F /T >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /PID %%a /F /T >nul 2>&1
taskkill /IM pythonw.exe /F >nul 2>&1
taskkill /IM AeroVantage.exe /F >nul 2>&1
echo [OK] Temizlik bitti. Tray yeniden baslatiliyor...
echo.

:NORMAL
if exist "AeroVantage.exe" (
    echo AeroVantage.exe baslatiliyor...
    start "" "AeroVantage.exe"
    exit /b 0
)

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
    echo [HATA] Python bulunamadi. Once install.bat calistirin.
    pause
    exit /b 1
)

if not exist "scripts\aero.py" (
    echo [HATA] scripts\aero.py bulunamadi.
    pause
    exit /b 1
)

if not exist "launcher\app.py" (
    echo [HATA] launcher\app.py bulunamadi.
    pause
    exit /b 1
)

rem --- Tray zaten aciksa: PID canli mi? ---
set "TRAY_LOCK=%~dp0launcher\.tray.lock"
set "TRAY_ALIVE=0"
if exist "%TRAY_LOCK%" (
    set /p TRAY_PID=<"%TRAY_LOCK%"
    if defined TRAY_PID (
        tasklist /FI "PID eq %TRAY_PID%" 2>nul | find /I "%TRAY_PID%" >nul 2>&1
        if not errorlevel 1 set "TRAY_ALIVE=1"
    )
    if "%TRAY_ALIVE%"=="1" (
        rem Servis ayaktaysa sadece pano; degilse zombie tray — sifirla
        powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { $false }" 2>nul | find "True" >nul
        if not errorlevel 1 (
            echo [OK] Tray zaten acik — pano aciliyor...
            start "" "http://127.0.0.1:3000"
            exit /b 0
        )
        echo [!] Tray kilitli ama sunucu yok — zorla sifirlaniyor...
        taskkill /PID %TRAY_PID% /F /T >nul 2>&1
        del /f /q "%TRAY_LOCK%" >nul 2>&1
        for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /PID %%a /F /T >nul 2>&1
        for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":3000" ^| findstr "LISTENING"') do taskkill /PID %%a /F /T >nul 2>&1
    ) else (
        del /f /q "%TRAY_LOCK%" >nul 2>&1
    )
)

rem --- Eksik bagimlilik varsa hizli kurulum ---
%PY% -c "import pystray, fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [!] Bagimliliklar eksik — hizli kurulum yapiliyor...
    %PY% scripts\aero.py install --quick
    if errorlevel 1 (
        echo [HATA] Kurulum basarisiz. install.bat calistirin.
        pause
        exit /b 1
    )
)

echo AeroVantage System Tray starting...
echo Runs in the background. Right-click the tray icon ^> Stop and Exit
echo If stuck: AeroVantage-Tray.bat /reset

%PY% scripts\launch_tray.py
if errorlevel 1 (
    echo [ERROR] Tray failed to start. Check launcher\logs\aero.log
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul
exit /b 0
