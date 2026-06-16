@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo Starting 99Acres Buy Properties Owner Extractor...
python app_buy_owner.py
pause
