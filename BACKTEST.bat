@echo off
chcp 65001 >nul
setlocal

rem ===========================================================================
rem  HALOL CRYPTO SAVDO — backtest (Windows, terminalsiz)
rem
rem  Bu fayl ustiga IKKI MARTA BOSING. Boshqa hech narsa yozish shart emas.
rem  U o'zi muhit quradi, kutubxonalarni o'rnatadi va backtestni ishga
rem  tushiradi. Natija `natija.txt` fayliga yoziladi.
rem
rem  PowerShell'ning `activate` ni bloklashi (ijro siyosati) shu yerda
rem  chetlab o'tilgan: Python to'g'ridan-to'g'ri chaqiriladi.
rem ===========================================================================

cd /d "%~dp0"

echo.
echo  ================================================
echo   HALOL CRYPTO SAVDO — BACKTEST
echo  ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo  [XATO] Python topilmadi.
    echo.
    echo  https://www.python.org/downloads/ dan Python 3.11 ni o'rnating.
    echo  O'rnatishda "Add python.exe to PATH" katagini BELGILANG.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo  Muhit qurilmoqda ^(bir marta, 2-5 daqiqa^)...
    python -m venv .venv
    if errorlevel 1 (
        echo  [XATO] Muhit qurilmadi.
        pause
        exit /b 1
    )
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo  [XATO] Kutubxonalar o'rnatilmadi.
        pause
        exit /b 1
    )
    echo  Muhit tayyor.
    echo.
)

set DAYS=%1
if "%DAYS%"=="" set DAYS=730

echo  Backtest boshlandi: %DAYS% kun.
echo  Birinchi marta ma'lumot yuklanadi — 10-20 daqiqa ketishi mumkin.
echo  Bu oynani YOPMANG.
echo.

.venv\Scripts\python.exe -m scripts.backtest --compare --days %DAYS% --output natija.txt

echo.
if exist "natija.txt" (
    echo  ================================================
    echo   TAYYOR. Natija: natija.txt
    echo   Shu faylni Claude'ga tashlang.
    echo  ================================================
) else (
    echo  [XATO] Natija fayli yaratilmadi — yuqoridagi xabarni o'qing.
)
echo.
pause
