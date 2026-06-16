@echo off
echo ============================================================
echo     99Acres Universal Scraper - EXE Builder
echo     Buy + Rent Properties in ONE App
echo ============================================================
echo.

SET VENV="%~dp0venv\Scripts"
SET PYINSTALLER="%~dp0venv\Scripts\pyinstaller.exe"
SET DIST_DIR="%~dp0dist\99Acres_Universal_Scraper"

echo [Step 1] Installing / Updating required packages...
%VENV%\python.exe -m pip install --quiet customtkinter pyinstaller pandas openpyxl playwright
echo Done.
echo.

echo [Step 2] Installing Playwright browsers (Chromium)...
%VENV%\python.exe -m playwright install chromium
echo Done.
echo.

echo [Step 3] Compiling EXE...
%PYINSTALLER% --noconfirm --onedir ^
    --hidden-import customtkinter ^
    --hidden-import playwright ^
    --hidden-import playwright.sync_api ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --hidden-import extract_buy_data ^
    --hidden-import extract_data ^
    --hidden-import extract_buy_owner_details ^
    --hidden-import extract_owner_details ^
    --name 99Acres_Universal_Scraper --windowed "%~dp0app_unified.py"
echo Done.
echo.

echo [Step 4] Copying Python scraper modules into dist folder...
copy /Y "%~dp0extract_buy_data.py" %DIST_DIR%\
copy /Y "%~dp0extract_data.py" %DIST_DIR%\
copy /Y "%~dp0extract_buy_owner_details.py" %DIST_DIR%\
copy /Y "%~dp0extract_owner_details.py" %DIST_DIR%\
echo Done.
echo.

echo ============================================================
echo  BUILD COMPLETE!
echo  Your EXE is ready at:
echo  dist\99Acres_Universal_Scraper\99Acres_Universal_Scraper.exe
echo ============================================================
pause
