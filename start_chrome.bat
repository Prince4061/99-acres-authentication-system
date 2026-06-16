@echo off
echo ========================================================
echo FORCE CLOSING all hidden Chrome windows...
echo ========================================================
taskkill /F /IM chrome.exe /T
timeout /t 2 /nobreak > nul

echo Starting Google Chrome in Stealth Debugging Mode...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%CD%\chrome_debug_profile" ^
  --disable-blink-features=AutomationControlled ^
  --disable-infobars ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-popup-blocking ^
  --start-maximized

echo Chrome started in stealth mode!
echo You can now run the Python script.
pause
