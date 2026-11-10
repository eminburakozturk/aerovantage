@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"

title AeroVantage Install

echo.
echo  ========================================
echo   AeroVantage - Kurulum
echo  ========================================
echo.

rem --- Python: py -3.12 ^> py -3 ^> python ---
set "PY="
for %%P in (py -3.12 py -3 python) do (
    if not defined PY (
        %%P --version >nul 2>&1 && set "PY=%%P"
    )
)

if not defined PY (
    echo [HATA] Python bulunamadi.
    echo        Python 3.12+ kurun: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo [OK] %%v

%PY% -c "import sys; raise SystemExit(0 if sys.version_info>=(3,12) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python 3.12 veya uzeri gerekli.
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [HATA] Node.js bulunamadi.
    echo        Node.js LTS kurun: https://nodejs.org/
    pause
    exit /b 1
)

for /f "delims=" %%v in ('node --version 2^>^&1') do echo [OK] Node %%v

if not exist "requirements.txt" (
    echo [HATA] requirements.txt bulunamadi. Proje kok dizininde calistirin.
    pause
    exit /b 1
)

rem --- Hizli kurulum: bagimliliklar zaten varsa --quick ---
set "INSTALL_ARGS="
if "%~1"=="--full" goto :run_install
if "%~1"=="--quick" (
    set "INSTALL_ARGS=--quick"
    goto :run_install
)

%PY% -c "import fastapi,uvicorn" >nul 2>&1
if errorlevel 1 goto :run_install
if not exist "frontend\node_modules\next\dist\bin\next" goto :run_install

echo [OK] Mevcut bagimliliklar algilandi — hizli kurulum
set "INSTALL_ARGS=--quick"

:run_install
echo.
echo Bagimliliklar kuruluyor...
echo.

%PY% scripts\aero.py install %INSTALL_ARGS%
if errorlevel 1 (
    echo.
    echo [HATA] Kurulum basarisiz.
    echo        Tam yeniden kurulum icin: install.bat --full
    pause
    exit /b 1
)

echo.
echo  ========================================
echo   Kurulum tamamlandi.
echo   Baslatmak icin: AeroVantage-Tray.bat
echo  ========================================
echo.
pause
exit /b 0
