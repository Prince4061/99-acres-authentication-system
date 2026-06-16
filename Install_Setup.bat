@echo off
title 99acres Scraper Builder
echo ========================================================
echo 99acres Scraper - One Click Setup and Installation
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not added to PATH!
    echo Please install Python from python.org and ensure "Add Python to PATH" is checked during installation.
    pause
    exit /b
)

echo [1/4] Checking Virtual Environment...
IF NOT EXIST "venv\Scripts\python.exe" (
    echo Creating virtual environment (venv)...
    python -m venv venv
) ELSE (
    echo Virtual environment already exists, skipping creation.
)

echo.
echo [2/4] Activating Virtual Environment and Upgrading PIP...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo.
echo [3/4] Installing Required Dependencies...
pip install -r requirements.txt

echo.
echo [4/4] Installing Playwright Browsers...
playwright install chromium

echo.
echo ========================================================
echo INSTALLATION COMPLETE!
echo.
echo You can now close this window and double click on:
echo - Run_Scraper.bat (for the main data scraper)
echo - Run_Owner_Scraper.bat (for the owner details scraper)
echo ========================================================
pause
