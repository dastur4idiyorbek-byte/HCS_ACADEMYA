@echo off
rem ===========================================================================
rem  Backtestning HAQIQIY ishi — `BACKTEST.bat` shu faylni chaqiradi.
rem
rem  NEGA ALOHIDA FAYL: `BACKTEST.bat` `git pull` qiladi va o'sha pull
rem  ishlayotgan faylni almashtirib yuborishi mumkin. Bu fayl esa pull
rem  TUGAGANDAN keyin ochiladi — ya'ni doim yangi holida o'qiladi.
rem
rem  NEGA `zanjir_alternativ`: jonli sikl aynan shu zanjirni yuritadi
rem  (`zanjir_yur_alternativ`). Boshqa skript o'lchansa, o'lchov jonli
rem  tizimga tegishli bo'lmasdi.
rem ===========================================================================

cd /d "%~dp0.."

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
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo  Muhit qurilmoqda ^(bir marta, 2-5 daqiqa^)...
    python -m venv .venv
    if errorlevel 1 (
        echo  [XATO] Muhit qurilmadi.
        exit /b 1
    )
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo  [XATO] Kutubxonalar o'rnatilmadi.
        exit /b 1
    )
    echo  Muhit tayyor.
    echo.
) else (
    rem Muhit bor, lekin kutubxonalar ESKIRGAN bo'lishi mumkin: kod
    rem yangilanganda `requirements.txt` ham o'zgargan bo'lishi mumkin.
    rem O'zgarish bo'lmasa bu tekshiruv bir necha soniya oladi.
    echo  Kutubxonalar tekshirilmoqda...
    .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
    echo.
)

set DAYS=%1
if "%DAYS%"=="" set DAYS=730

rem 12 coinlik to'plam — oldingi o'lchovlar shu hajmda yuritilgan.
rem O'zgartirilsa, natijani eskisi bilan solishtirib bo'lmaydi.
set COINLAR=BTC,ETH,SOL,ADA,AVAX,LINK,DOT,ATOM,LTC,NEAR,ETC,FIL

echo  Backtest boshlandi: %DAYS% kun, 12 coin.
echo  Birinchi marta ma'lumot yuklanadi — 10-20 daqiqa ketishi mumkin.
echo  Bu oynani YOPMANG.
echo.

.venv\Scripts\python.exe -m scripts.zanjir_alternativ --days %DAYS% --symbols %COINLAR% > natija.txt 2>&1

echo.
if exist "natija.txt" (
    type natija.txt
    echo.
    echo  ================================================
    echo   TAYYOR. Natija: natija.txt
    echo   Shu faylni Claude'ga tashlang.
    echo  ================================================
) else (
    echo  [XATO] Natija fayli yaratilmadi.
)
