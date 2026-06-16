@echo off
echo ============================================================
echo   Starting 99Acres Scraper Studio...
echo ============================================================

cd /d "%~dp0"

IF EXIST "dist\99Acres_Universal_Scraper\99Acres_Universal_Scraper.exe" (
    echo Launching the application...
    start "" "dist\99Acres_Universal_Scraper\99Acres_Universal_Scraper.exe"
) ELSE (
    echo Error: The executable couldn't be found. 
    echo Please run Build_EXE.bat first to compile the application.
    pause
)
