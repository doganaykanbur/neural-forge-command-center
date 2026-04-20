@echo off
:: Eğer yönetici izni vs. yüzünden kapanıyorsa bunu engeller
setlocal enabledelayedexpansion

title NEURAL FORGE | EMERGENCY LAUNCHER
echo [🎨] NEURAL FORGE | ADMIN PANEL
echo -----------------------------------------

:: Mevcut konumu zorla sabitle
pushd "%~dp0"

echo [1] Checking Directory...
if not exist "admin-panel" (
    echo [❌] Klasor bulunamadi! Yol: %cd%
    pause
    exit
)

cd admin-panel

echo [2] Checking Node...
call node -v || (echo [❌] Node hatasi! && pause && exit)

echo [3] Launching NEXT.JS (Zorlanmis Mod)...
echo -----------------------------------------

:: 'call' komutunu 'npm' ile kullanırken bazen Windows hata verir. 
:: Bu yüzden doğrudan npm.cmd'yi çağırıyoruz.
cmd /c npm.cmd run dev

if %errorlevel% neq 0 (
    echo.
    echo [❌] Bir seyler ters gitti! Hata kodu: %errorlevel%
    pause
)

echo [ℹ️] Pencere kapanmasin diye bekliyorum...
pause
cmd /k