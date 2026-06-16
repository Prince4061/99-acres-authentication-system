@echo off
echo ========================================================
echo Starting 99acres Scraper Application...
echo ========================================================
echo.

echo [1/3] FORCE CLOSING existing Chrome sessions...
taskkill /F /IM chrome.exe /T 2>nul
timeout /t 2 /nobreak > nul
echo.

echo [2/3] Starting Chrome Browser in automation mode...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%CD%\chrome_debug_profile"
timeout /t 3 /nobreak > nul
echo.

echo [3/3] Starting Local Web Server...
echo The Scraper Website should open automatically shortly.
echo.

:: Start the Flask app quietly in the background
start /B "" "%~dp0venv\Scripts\python.exe" "%~dp0app.py" 

:: Wait a little bit for the server to spin up
timeout /t 3 /nobreak > nul

:: Open the user's default browser to the web app
start http://127.0.0.1:5000/

echo ========================================================
echo Everything is running! 
echo DO NOT CLOSE THIS BLACK WINDOW until you are completely 
echo done scraping. Closing this will stop the server.
echo.
echo Press any key to stop the server and exit...
echo ========================================================
pause > nul

:: When user presses a key, kill the Python process (the flask app)
taskkill /F /IM python.exe /T 2>nul
exit
