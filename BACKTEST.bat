@echo off
chcp 65001 >nul

rem ===========================================================================
rem  HALOL CRYPTO SAVDO — BACKTEST. Ikki marta bosing, tamom.
rem
rem  BU FAYL ATAYLAB KICHIK va u boshqa O'ZGARMAYDI.
rem
rem  Sabab: Windows `.bat` faylni qator-qator DISKDAN o'qiydi. `git pull`
rem  ishlayotgan faylning o'zini almashtirsa, cmd qolgan qismini
rem  noto'g'ri joydan o'qib, tushunarsiz xato beradi.
rem
rem  Shuning uchun butun mantiq `scripts\backtest_win.bat` da: u pull
rem  TUGAGANDAN keyin chaqiriladi, ya'ni doim yangi holida o'qiladi.
rem  Kelajakdagi o'zgarishlar o'sha faylga kiradi, bu yerga emas.
rem ===========================================================================

cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
    echo  [OGOHLANTIRISH] Git topilmadi — kod yangilanmadi.
) else (
    echo  Kod yangilanmoqda...
    git pull
)
echo.

call "%~dp0scripts\backtest_win.bat" %1
pause
