# GharLeads Verified Owner Panel & Scraper Studio

A powerful real estate scraper and lead finder studio for **99Acres.com** (Buy & Rent sections), secured with an **Online Google Sheets Security PIN Lock System**.

---

## 🔒 Google Sheets Security Lock System

This application includes a remote license lock screen on startup to restrict unauthorized access. It fetches authorized PINs from a published Google Sheet CSV link in real-time.

### How it works:
1. **Startup Check**: On launch, the main application window is hidden. A security dialog box pops up asking for an authorization PIN.
2. **Real-time Verification**: The software downloads the CSV list of valid PINs from a configured Google Sheet.
3. **Access Control**: If the entered PIN matches a record in the sheet, the application unlocks. If incorrect or offline, access is denied.
4. **Internet Dependency**: Active internet is required. Going offline blocks the software to prevent security bypasses.

### How to set up your Google Sheet authorization:
1. Create a new Google Sheet.
2. Put all allowed PINs in **Column A** (one PIN per row). You can refer to [keys.csv](./keys.csv) for sample keys.
3. Go to **File** -> **Share** -> **Publish to web**.
4. Set the link options to publish **Entire Document** (or specific tab) as **Comma-separated values (.csv)**.
5. Click **Publish** and copy the link.
6. Open your application folder and edit the file [sheet_url.txt](./sheet_url.txt). Paste your Google Sheet CSV URL there.
7. You can now add, edit, or delete PINs directly from the Google Sheets app on your phone or PC, and it will take effect instantly!

---

## 🚀 Getting Started

### Prerequisites:
- **Python 3.x**
- **Google Chrome** installed in the default location.
- **Playwright** browsers installed.

### Installation:
Initialize dependencies using the setup batch script:
```powershell
# Run the setup script to install dependencies
.\Install_Setup.bat
```

### Running the Apps:
You can run the applications using the virtual environment interpreter:

1. **Classic Tkinter Version** (GharLeads Verified Owner Panel):
   ```powershell
   venv\Scripts\python.exe app_tkinter.py
   ```
2. **Modern CustomTkinter Version** (99Acres Universal Scraper Studio):
   ```powershell
   venv\Scripts\python.exe app_unified.py
   ```

---

## ⚙️ How Chrome Automation Bypasses Bot Detectors

To bypass Cloudflare and 99Acres bot mitigations:
1. The app connects to a running Google Chrome instance via **Chrome DevTools Protocol (CDP)** on port `9222`.
2. To start Chrome in debug mode, run the shortcut:
   ```powershell
   .\start_chrome.bat
   ```
   This opens Chrome with `--remote-debugging-port=9222` and a dedicated user data profile, which makes automation behave exactly like a real user.

---

## 🛠️ Rebuilding/Compiling the Executable (`.exe`)

If you change the Python code and want to generate new `.exe` binaries:

- **Rebuild GharLeads Owner Panel**:
  ```powershell
  venv\Scripts\pyinstaller --noconfirm GharLeads_Owner_Panel.spec
  ```
- **Rebuild Portable Scrapper**:
  Run the batch script:
  ```powershell
  .\Build_Portable_EXE.bat
  ```

*Note: After building the executable, make sure to copy your scraper helper scripts (`extract_buy_data.py`, `extract_data.py`, etc.) and `sheet_url.txt` into the corresponding `dist` folder.*
