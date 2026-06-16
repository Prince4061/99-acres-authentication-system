@echo off
echo ============================================================
echo   99Acres Universal Scraper - PORTABLE EXE Builder
echo   (Tkinter Edition)
echo ============================================================
echo.

SET VENV="%~dp0venv\Scripts"
SET PYINSTALLER="%~dp0venv\Scripts\pyinstaller.exe"

echo [Step 1] Verifying dependencies...
%VENV%\python.exe -m pip install --quiet pyinstaller pandas openpyxl playwright
echo Done.
echo.

echo [Step 2] Compiling ONE-FILE EXE...
%VENV%\python.exe -m PyInstaller --noconfirm --onefile ^
    --hidden-import customtkinter ^
    --hidden-import playwright ^
    --hidden-import playwright.sync_api ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --hidden-import extract_buy_data ^
    --hidden-import extract_data ^
    --hidden-import extract_buy_owner_details ^
    --hidden-import extract_owner_details ^
    --name "Property Scrapper" --windowed "%~dp0app_tkinter.py"
echo Done.
echo.

echo ============================================================
echo  PORTABLE BUILD COMPLETE!
echo  Your standalone EXE is ready at:
echo  dist\Property Scrapper.exe
echo ============================================================
pause
