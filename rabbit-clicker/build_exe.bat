@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
python -m PyInstaller --clean --noconfirm rabbit_clicker.spec
echo.
if exist "dist\兔子点击器.exe" (
    copy /Y "dist\兔子点击器.exe" "兔子点击器.exe" >nul
    echo Build complete: dist\兔子点击器.exe
    echo Root copy ready: 兔子点击器.exe
) else (
    echo Build failed.
)
pause
