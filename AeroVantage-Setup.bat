@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"

title AeroVantage Setup (portable)

echo.
echo  ========================================
echo   AeroVantage — Portable Setup
echo  ========================================
echo.

if not exist "AeroVantage.exe" (
    echo [HATA] AeroVantage.exe bulunamadi.
    echo        Once: python scripts\prepare_brand_icons.py
    echo              python scripts\build_exe.py
    echo        veya: build-setup.bat
    pause
    exit /b 1
)

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"

echo [1/2] Masaustu / Baslat menusu kisayollari...
if defined PY (
    %PY% scripts\create_shortcuts.py
) else (
    echo [!] Python yok — kisayol atlandi. EXE yine de kullanilabilir.
)

echo [2/2] Portable paket (opsiyonel zip)...
if not exist "dist\setup" mkdir "dist\setup"
set "PORTABLE=dist\setup\AeroVantage-Portable"
if exist "%PORTABLE%" rmdir /s /q "%PORTABLE%"
mkdir "%PORTABLE%"
copy /Y "AeroVantage.exe" "%PORTABLE%\" >nul
if exist "AeroVantage.ico" copy /Y "AeroVantage.ico" "%PORTABLE%\" >nul
if exist "AeroVantage.lnk" copy /Y "AeroVantage.lnk" "%PORTABLE%\" >nul
if exist "AeroVantage-Tray.bat" copy /Y "AeroVantage-Tray.bat" "%PORTABLE%\" >nul
if exist "AeroVantage-Install.lnk" copy /Y "AeroVantage-Install.lnk" "%PORTABLE%\" >nul
(
    echo AeroVantage Portable
    echo ====================
    echo.
    echo Logolu baslatma ^(oncelik sirasi^):
    echo   1. AeroVantage.exe  — gomulu logo + system tray
    echo   2. AeroVantage.lnk  — Explorer'da logo ^(EXE hedef^)
    echo   3. AeroVantage-Tray.bat — EXE varsa onu acar ^(bat ikon tutamaz^)
    echo.
    echo Not: Backend/frontend icin Python + Node bagimliliklari gerekir.
    echo      Ilk kurulumda install.bat veya: python scripts\aero.py install --quick
    echo.
    echo Tam Windows Setup installer icin Inno Setup + build-setup.bat kullanin.
) > "%PORTABLE%\README.txt"

powershell -NoProfile -Command "Compress-Archive -Path '%PORTABLE%\*' -DestinationPath 'dist\setup\AeroVantage-Portable.zip' -Force" 2>nul
if exist "dist\setup\AeroVantage-Portable.zip" (
    echo [OK] Zip: dist\setup\AeroVantage-Portable.zip
) else (
    echo [OK] Klasor: %PORTABLE%
)

echo.
echo  ========================================
echo   Hazir
echo  ========================================
echo   EXE     : AeroVantage.exe
echo   Ikon    : AeroVantage.ico
echo   Baslat  : AeroVantage.exe veya masaustu kisayolu
echo   Tray bat: AeroVantage-Tray.bat
echo.
if /I not "%~1"=="/nopause" pause
exit /b 0
