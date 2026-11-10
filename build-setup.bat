@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
cd /d "%~dp0"

title AeroVantage Setup

echo.
echo  ========================================
echo   AeroVantage — Logolu EXE + Setup
echo  ========================================
echo.

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
    echo [HATA] Python bulunamadi.
    pause
    exit /b 1
)

echo [1/4] Marka ikonlari hazirlaniyor...
%PY% scripts\prepare_brand_icons.py
if errorlevel 1 (
    echo [HATA] Ikon hazirligi basarisiz.
    pause
    exit /b 1
)

echo [2/4] AeroVantage.exe derleniyor (PyInstaller)...
%PY% scripts\build_exe.py
if errorlevel 1 (
    echo [HATA] EXE derlemesi basarisiz.
    pause
    exit /b 1
)

if not exist "AeroVantage.exe" (
    echo [!] AeroVantage.exe olusmadi — mock derleme olabilir.
    echo     pip install pyinstaller sonra tekrar: build-setup.bat
)

echo [3/4] Masaustu / Baslat menusu kisayollari...
%PY% scripts\create_shortcuts.py

echo [4/4] Inno Setup (opsiyonel)...
set "ISCC="
where iscc >nul 2>&1 && set "ISCC=iscc"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo [i] ISCC yok — sessiz kurulum deneniyor (winget/choco)...
    where winget >nul 2>&1 && (
        winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements --silent
    )
    where choco >nul 2>&1 && if not exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        choco install innosetup -y
    )
    where iscc >nul 2>&1 && set "ISCC=iscc"
    if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
    if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)

set "SETUP_OK=0"
if defined ISCC (
    if exist "AeroVantage.exe" if exist "AeroVantage.ico" (
        echo ISCC bulundu — Setup installer uretiliyor...
        "%ISCC%" "installer\aerovantage.iss"
        if errorlevel 1 (
            echo [!] Inno Setup derlemesi basarisiz — portable fallback.
        ) else (
            echo [OK] Setup: dist\setup\
            set "SETUP_OK=1"
        )
    )
)

if "%SETUP_OK%"=="0" (
    echo [i] Inno Setup yok/basarisiz — portable paket + AeroVantage-Setup.bat
    call AeroVantage-Setup.bat /nopause
)

echo.
echo  ========================================
echo   Tamam
echo  ========================================
echo   EXE     : AeroVantage.exe
echo   Ikon    : AeroVantage.ico
echo   LNK     : AeroVantage.lnk  (repo kok, logolu)
echo   Tray    : AeroVantage-Tray.bat  (EXE varsa onu kullanir)
echo   Kisayol : Masaustu / Baslat menusu
echo   Setup   : dist\setup\  (Inno veya Portable zip)
echo.
echo   Baslatmak icin AeroVantage.exe, AeroVantage.lnk veya masaustu kisayoluna cift tiklayin.
echo.
pause
exit /b 0
