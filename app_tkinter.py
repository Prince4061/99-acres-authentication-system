import os
import sys
import threading
import queue
import time
import subprocess
import urllib.request
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from playwright.sync_api import sync_playwright

# Imports for Auto Scrapers
try:
    from extract_buy_data import extract_buy_properties
    from extract_data import extract_properties as extract_rent_properties
except ImportError as e:
    print(f"Warning: Missing property auto-scraper module: {e}")

# Imports for Owner Scrapers (Aliased to avoid conflict)
try:
    from extract_buy_owner_details import extract_basic_details as extract_buy_basic_details, extract_phone_number as extract_buy_phone_number
    from extract_owner_details import extract_basic_details as extract_rent_basic_details, extract_phone_number as extract_rent_phone_number
except ImportError as e:
    print(f"Warning: Missing owner details scraper module: {e}")


# Google Sheets Verification Configuration
# Change this default URL or create a "sheet_url.txt" file in the app directory to update the link
DEFAULT_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTun7cSJ2eXkom_W1RPvTIIJ4kKIlmG1t5UFt9KEgk4_tqu68N-J2-k03lK052Gdxw2A8wmN3_q4b-p/pub?output=csv"


def get_sheet_url():
    url_file = "sheet_url.txt"
    if not os.path.exists(url_file):
        try:
            with open(url_file, "w") as f:
                f.write(DEFAULT_SHEET_CSV_URL)
        except:
            pass
        return DEFAULT_SHEET_CSV_URL
    try:
        with open(url_file, "r") as f:
            val = f.read().strip()
            return val if val else DEFAULT_SHEET_CSV_URL
    except:
        return DEFAULT_SHEET_CSV_URL

def check_google_sheet_pin(entered_pin):
    if not entered_pin.strip():
        return False, "PIN cannot be empty."
    import urllib.request
    url = get_sheet_url()
    
    if "YOUR_GOOGLE_SHEET_ID_HERE" in url:
        return False, "Please configure your Google Sheet link in 'sheet_url.txt'."
        
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            content = response.read().decode('utf-8')
            pins = []
            for line in content.splitlines():
                if line.strip():
                    col1 = line.split(',')[0].strip().replace('"', '').strip()
                    pins.append(col1)
            if entered_pin.strip() in pins:
                return True, "Success"
            else:
                return False, "Incorrect PIN! Access Denied."
    except Exception as e:
        return False, f"Internet/Link Error: {str(e)}"


class RedirectText:
    def __init__(self, text_ctrl):
        self.text_ctrl = text_ctrl
    def write(self, string):
        self.text_ctrl.insert(tk.END, string)
        self.text_ctrl.see(tk.END)
    def flush(self):
        pass


class UnifiedScraperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GharLeads Verified Owner Panel")
        self.geometry("950x800")
        
        # Withdraw the main window until login is verified
        self.withdraw()
        
        self.login_verified = False
        self.show_login_dialog()
        
        # Style
        self.style = ttk.Style(self)
        try:
            self.style.theme_use('clam')
        except:
            pass
        self.style.configure("TFrame", background="#F4F6F9")
        self.style.configure("TLabel", background="#F4F6F9", font=("Arial", 11))
        self.style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        self.style.configure("Status.TLabel", font=("Arial", 10, "italic"), foreground="gray")
        self.style.configure("TButton", font=("Arial", 10))
        self.configure(bg="#F4F6F9")
        
        # State Variables
        self.buy_state = self._init_state()
        self.rent_state = self._init_state()
        
        self.buy_queue = queue.Queue()
        self.rent_queue = queue.Queue()
        self.checking_status = True
        
        # Setup GUI
        self.setup_global_controls()
        
        # Main Tabview for Buy vs Rent
        self.main_notebook = ttk.Notebook(self)
        self.main_notebook.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        self.buy_tab = ttk.Frame(self.main_notebook)
        self.rent_tab = ttk.Frame(self.main_notebook)
        
        self.main_notebook.add(self.buy_tab, text="BUY Properties")
        self.main_notebook.add(self.rent_tab, text="RENT Properties")
        
        self.setup_buy_section()
        self.setup_rent_section()
        
        # Loop for queue updates
        self.after(1000, self.update_ui_state)

    def show_login_dialog(self):
        login_win = tk.Toplevel(self)
        login_win.title("GharLeads Authorization")
        login_win.geometry("380x220")
        login_win.resizable(False, False)
        login_win.configure(bg="#F4F6F9")
        
        # Keep login window on top and focus it
        login_win.grab_set()
        login_win.focus_force()
        
        # Center the window
        login_win.update_idletasks()
        width = login_win.winfo_width()
        height = login_win.winfo_height()
        x = (login_win.winfo_screenwidth() // 2) - (width // 2)
        y = (login_win.winfo_screenheight() // 2) - (height // 2)
        login_win.geometry(f'+{x}+{y}')
        
        # Title Label
        tk.Label(login_win, text="GharLeads Verified Panel", font=("Arial", 12, "bold"), fg="#2C3E50", bg="#F4F6F9").pack(pady=15)
        tk.Label(login_win, text="Enter authorized PIN to unlock software:", font=("Arial", 10), fg="#555", bg="#F4F6F9").pack(pady=2)
        
        pin_var = tk.StringVar()
        pin_entry = tk.Entry(login_win, textvariable=pin_var, show="*", font=("Arial", 12), width=18, justify="center")
        pin_entry.pack(pady=8)
        pin_entry.focus()
        
        status_lbl = tk.Label(login_win, text="", fg="#C0392B", bg="#F4F6F9", font=("Arial", 9, "bold"), wraplength=340)
        status_lbl.pack(pady=2)
        
        def verify_action(event=None):
            pin = pin_var.get().strip()
            if not pin:
                status_lbl.config(text="Please enter a PIN.")
                return
            
            status_lbl.config(text="Connecting to security server...", fg="#2980B9")
            login_win.update()
            
            # Run the verification
            success, msg = check_google_sheet_pin(pin)
            if success:
                self.login_verified = True
                login_win.destroy()
            else:
                status_lbl.config(text=msg, fg="#C0392B")
                pin_entry.delete(0, tk.END)
                
        pin_entry.bind("<Return>", verify_action)
        
        btn = tk.Button(login_win, text="Verify & Unlock", command=verify_action, bg="#27AE60", fg="white", font=("Arial", 10, "bold"), width=15, relief=tk.RAISED)
        btn.pack(pady=10)
        
        def on_close():
            self.destroy()
            sys.exit(0)
            
        login_win.protocol("WM_DELETE_WINDOW", on_close)
        
        # Wait until login window is closed or destroyed
        self.wait_window(login_win)
        
        if not self.login_verified:
            self.destroy()
            sys.exit(0)
        else:
            self.deiconify() # Reveal main window

    def _init_state(self):
        return {
            "status": "Idle",
            "file_path": "",
            "output_name": "",
            "rows": [],
            "current_index": -1,
            "total": 0,
            "current_url": "",
            "worker_status": "Idle",
            "db_widgets": {}  # Store references to specific tab widgets
        }

    def setup_global_controls(self):
        # Frame at the bottom for Chrome Launch / Status
        self.footer = tk.Frame(self, bg="#E8EEF2", height=50)
        self.footer.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        btn_frame = tk.Frame(self.footer, bg="#E8EEF2")
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        self.chrome_btn = tk.Button(btn_frame, text="🚀 Launch Secure Chrome", bg="#F39C12", fg="white", font=("Arial", 11, "bold"), command=self.launch_chrome, relief=tk.RAISED)
        self.chrome_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.ip_btn = tk.Button(btn_frame, text="Rotate IP (Secure Network) >", bg="#3498DB", fg="white", font=("Arial", 11, "bold"), command=self.change_ip, relief=tk.RAISED)
        self.ip_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.global_status = tk.Label(self.footer, text="✔ Verified Owner Status: Active", fg="#27AE60", bg="#E8EEF2", font=("Arial", 11, "bold"))
        self.global_status.pack(side=tk.RIGHT, padx=20, pady=10)

    def launch_chrome(self):
        """Kills old chrome and starts debug chrome"""
        self.global_status.config(text="Killing old Chrome & Starting New...")
        def run():
            os.system('taskkill /F /IM chrome.exe /T 2>nul')
            time.sleep(1)
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            user_data_dir = os.path.join(os.getcwd(), "chrome_debug_profile")
            cmd = [
                chrome_path,
                "--remote-debugging-port=9222",
                f"--user-data-dir={user_data_dir}",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-popup-blocking",
                "--start-maximized"
            ]
            try:
                subprocess.Popen(cmd, shell=False)
                self.global_status.config(text="Chrome is running in Debug Mode.")
            except Exception as e:
                self.global_status.config(text=f"Failed to launch Chrome: {e}")
        threading.Thread(target=run, daemon=True).start()


    def change_ip(self):
        self.ip_btn.config(state=tk.DISABLED, text="Changing...")
        def run():
            warp_cli = r"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe"
            if not os.path.exists(warp_cli):
                self.global_status.config(text="Cloudflare WARP not found.")
                self.ip_btn.config(state=tk.NORMAL, text="Rotate IP (WARP)")
                return
            try:
                subprocess.run([warp_cli, 'tos', 'accept'], capture_output=True, timeout=5)
                subprocess.run([warp_cli, 'disconnect'], capture_output=True, timeout=10)
                time.sleep(2)
                subprocess.run([warp_cli, 'connect'], capture_output=True, timeout=10)
                time.sleep(4)
                new_ip = urllib.request.urlopen('https://api.ipify.org', timeout=8).read().decode()
                self.global_status.config(text=f"IP Changed: {new_ip}")
            except Exception as e:
                self.global_status.config(text=f"IP Error: {e}")
            self.ip_btn.config(state=tk.NORMAL, text="Rotate IP (WARP)")
        threading.Thread(target=run, daemon=True).start()

    # ==========================
    # UI SETUP: BUY SECTION
    # ==========================
    def setup_buy_section(self):
        sub_notebook = ttk.Notebook(self.buy_tab)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tab_buy_auto = ttk.Frame(sub_notebook)
        tab_buy_owner = ttk.Frame(sub_notebook)
        
        sub_notebook.add(tab_buy_auto, text="Lead Finder")
        sub_notebook.add(tab_buy_owner, text="Owner Contact Extractor")
        
        # 1. AUTO BUY
        title1 = ttk.Label(tab_buy_auto, text="Find 'Buy' Property Links", style="Header.TLabel")
        title1.pack(pady=10)
        self.loc_buy_entry = ttk.Entry(tab_buy_auto, width=40, font=("Arial", 12))
        self.loc_buy_entry.insert(0, "Location Name (e.g. Thane)...")
        self.loc_buy_entry.bind('<FocusIn>', lambda e: self.loc_buy_entry.delete(0, tk.END) if 'Location' in self.loc_buy_entry.get() else None)
        self.loc_buy_entry.pack(pady=10)
        
        self.start_buy_prop_btn = tk.Button(tab_buy_auto, text="Auto Property Finder >", bg="#3498DB", fg="white", font=("Arial", 11, "bold"), command=self.start_buy_auto_scraper, relief=tk.RAISED)
        self.start_buy_prop_btn.pack(pady=5)
        self.buy_console = tk.Text(tab_buy_auto, width=90, height=15, bg="black", fg="#00FF00", font=("Consolas", 10))
        self.buy_console.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        # 2. BUY OWNER
        self._setup_owner_gui(tab_buy_owner, "buy", self.buy_state, self.buy_queue)

    # ==========================
    # UI SETUP: RENT SECTION
    # ==========================
    def setup_rent_section(self):
        sub_notebook = ttk.Notebook(self.rent_tab)
        sub_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tab_rent_auto = ttk.Frame(sub_notebook)
        tab_rent_owner = ttk.Frame(sub_notebook)
        
        sub_notebook.add(tab_rent_auto, text="Lead Finder")
        sub_notebook.add(tab_rent_owner, text="Owner Contact Extractor")
        
        # 1. AUTO RENT
        title1 = ttk.Label(tab_rent_auto, text="Find 'Rent' Property Links", style="Header.TLabel")
        title1.pack(pady=10)
        self.loc_rent_entry = ttk.Entry(tab_rent_auto, width=40, font=("Arial", 12))
        self.loc_rent_entry.insert(0, "Location Name (e.g. Bandra)...")
        self.loc_rent_entry.bind('<FocusIn>', lambda e: self.loc_rent_entry.delete(0, tk.END) if 'Location' in self.loc_rent_entry.get() else None)
        self.loc_rent_entry.pack(pady=10)
        
        self.start_rent_prop_btn = tk.Button(tab_rent_auto, text="Auto Property Finder >", bg="#3498DB", fg="white", font=("Arial", 11, "bold"), command=self.start_rent_auto_scraper, relief=tk.RAISED)
        self.start_rent_prop_btn.pack(pady=5)
        self.rent_console = tk.Text(tab_rent_auto, width=90, height=15, bg="black", fg="#00FF00", font=("Consolas", 10))
        self.rent_console.pack(pady=10, fill=tk.BOTH, expand=True, padx=10)
        
        # 2. RENT OWNER
        self._setup_owner_gui(tab_rent_owner, "rent", self.rent_state, self.rent_queue)

    def _setup_owner_gui(self, parent_frame, mode, state_obj, cmd_q):
        # Top panel: Load File & Connect
        top_frame = ttk.Frame(parent_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_lbl = ttk.Label(top_frame, text="▶ Auto Property Finder", font=("Arial", 12, "bold"), foreground="#3498DB")
        title_lbl.pack(side=tk.LEFT, padx=10, pady=5)
        
        load_btn = tk.Button(top_frame, text="Upload Excel >", width=15, bg="#3498DB", fg="white", font=("Arial", 10, "bold"), command=lambda: self.load_excel(mode, state_obj))
        load_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        conn_btn = tk.Button(top_frame, text="Connect System", width=18, bg="#BDC3C7", font=("Arial", 10, "bold"), command=lambda: self.connect_playwright(mode, state_obj, cmd_q))
        conn_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        state_obj["db_widgets"]["conn_btn"] = conn_btn
        
        # Navigation
        nav_frame = tk.Frame(parent_frame, bg="#E8EEF2", bd=1, relief=tk.RIDGE)
        nav_frame.pack(fill=tk.X, padx=10, pady=10)
        
        row_lbl = tk.Label(nav_frame, text="Row: 0 / 0", font=("Arial", 12, "bold"), bg="#E8EEF2", fg="#333333")
        row_lbl.pack(side=tk.TOP, pady=5)
        state_obj["db_widgets"]["row_lbl"] = row_lbl

        ctrl_frame = tk.Frame(nav_frame, bg="#E8EEF2")
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        
        prev_btn = tk.Button(ctrl_frame, text="< Previous", width=12, bg="#3498DB", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED, command=lambda: self.navigate_row(-1, state_obj, cmd_q))
        prev_btn.pack(side=tk.LEFT, padx=5, pady=5)
        state_obj["db_widgets"]["prev_btn"] = prev_btn
        
        next_btn = tk.Button(ctrl_frame, text="Next >", width=12, bg="#3498DB", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED, command=lambda: self.navigate_row(1, state_obj, cmd_q))
        next_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        state_obj["db_widgets"]["next_btn"] = next_btn
        
        # Data Display
        data_frame = tk.Frame(parent_frame, bg="white", highlightbackground="#D5DBDB", highlightthickness=1)
        data_frame.pack(fill=tk.X, padx=10, pady=5)
        
        contact_alert = tk.Label(data_frame, text="⚠ Owner Contact: Pending...", bg="#EAECEE", fg="#7F8C8D", font=("Arial", 12, "bold"), anchor=tk.W)
        contact_alert.pack(fill=tk.X, padx=10, pady=10)
        state_obj["db_widgets"]["contact_alert"] = contact_alert
        
        lbl_url = tk.Label(data_frame, text="URL: -", fg="#7F8C8D", bg="white", font=("Arial", 10), wraplength=850, justify=tk.LEFT, anchor=tk.W)
        lbl_url.pack(anchor=tk.W, fill=tk.X, padx=10, pady=2)
        state_obj["db_widgets"]["lbl_url"] = lbl_url
        
        lbl_price = tk.Label(data_frame, text="Price: - | Configuration: -", font=("Arial", 11), fg="#2C3E50", bg="white", anchor=tk.W)
        lbl_price.pack(anchor=tk.W, fill=tk.X, padx=10, pady=5)
        state_obj["db_widgets"]["lbl_price"] = lbl_price
        
        lbl_owner = tk.Label(data_frame, text="Owner: -", font=("Arial", 11, "bold"), fg="#2C3E50", bg="white", anchor=tk.W)
        lbl_owner.pack(anchor=tk.W, fill=tk.X, padx=10, pady=5)
        state_obj["db_widgets"]["lbl_owner"] = lbl_owner

        lbl_phone = tk.Label(data_frame, text="Phone: -", font=("Arial", 14, "bold"), fg="#27AE60", bg="white", anchor=tk.W)
        lbl_phone.pack(anchor=tk.W, fill=tk.X, padx=10, pady=5)
        state_obj["db_widgets"]["lbl_phone"] = lbl_phone
        
        # Action Buttons
        bot_frame = ttk.Frame(parent_frame)
        bot_frame.pack(fill=tk.X, padx=10, pady=10)
        
        btn_det = tk.Button(bot_frame, text="🔍 Fetch Property Details", height=2, bg="#3498DB", fg="white", font=("Arial", 11, "bold"), state=tk.DISABLED, command=lambda: self.extract_details(state_obj, cmd_q))
        btn_det.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        state_obj["db_widgets"]["ext_det_btn"] = btn_det
        
        btn_num = tk.Button(bot_frame, text="📞 Get Owner Phone Number", height=2, bg="#27AE60", fg="white", font=("Arial", 11, "bold"), state=tk.DISABLED, command=lambda: self.extract_num(state_obj, cmd_q))
        btn_num.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5)
        state_obj["db_widgets"]["ext_num_btn"] = btn_num

    # ==========================
    # LOGIC: AUTO SCRAPERS
    # ==========================
    def start_buy_auto_scraper(self):
        loc = self.loc_buy_entry.get().strip()
        if not loc or "Location" in loc:
            messagebox.showerror("Error", "Please enter a location!")
            return
        
        self.start_buy_prop_btn.config(state=tk.DISABLED, text="Processing...")
        self.buy_console.insert(tk.END, f"\n[System] Starting auto-property finder 'Buy' for '{loc}'...\n")
        
        def run_script():
            old_stdout = sys.stdout
            sys.stdout = RedirectText(self.buy_console)
            try:
                out = extract_buy_properties(loc)
                self.buy_console.insert(tk.END, f"\n[System] Done! File saved: {out}\n")
            except Exception as e:
                self.buy_console.insert(tk.END, f"\n[Error] {str(e)}\n")
            finally:
                sys.stdout = old_stdout
                self.start_buy_prop_btn.config(state=tk.NORMAL, text="Start Buy Scraping")
                
        threading.Thread(target=run_script, daemon=True).start()

    def start_rent_auto_scraper(self):
        loc = self.loc_rent_entry.get().strip()
        if not loc or "Location" in loc:
            messagebox.showerror("Error", "Please enter a location!")
            return
        
        self.start_rent_prop_btn.config(state=tk.DISABLED, text="Processing...")
        self.rent_console.insert(tk.END, f"\n[System] Starting auto-property finder 'Rent' for '{loc}'...\n")
        
        def run_script():
            old_stdout = sys.stdout
            sys.stdout = RedirectText(self.rent_console)
            try:
                out = extract_rent_properties(loc)
                self.rent_console.insert(tk.END, f"\n[System] Done! File saved: {out}\n")
            except Exception as e:
                self.rent_console.insert(tk.END, f"\n[Error] {str(e)}\n")
            finally:
                sys.stdout = old_stdout
                self.start_rent_prop_btn.config(state=tk.NORMAL, text="Start Rent Scraping")
                
        threading.Thread(target=run_script, daemon=True).start()

    # ==========================
    # LOGIC: OWNER SCRAPERS
    # ==========================
    def load_excel(self, mode, state_obj):
        file_path = filedialog.askopenfilename(title=f"Select Extracted Excel ({mode})", filetypes=[("Excel Files", "*.xlsx")])
        if not file_path: return
        
        try:
            df = pd.read_excel(file_path)
            
            # Detect URL columns
            url_col_candidates = ['Property URL', 'Number', 'Owner Name']
            url_col = next((col for col in url_col_candidates if col in df.columns), None)
            
            if not url_col:
                messagebox.showerror("Error", "Missing recognizable URL column.")
                return
                
            # Define new columns specific to Buy vs Rent
            if mode == "buy":
                new_cols = [
                    "Phone Number", "Owner Name", "Area", "Configuration", 
                    "Price", "Address", "Floor Number", "Highlights", 
                    "Property Age", "Furnishing", "Facing", "Overlooking", 
                    "Possession in", "Position", "Properties Listed", "Localities"
                ]
            else:
                new_cols = [
                    "Owner Name", "Phone Number", "Configuration", "Rent", 
                    "Area", "Address", "Furnishing", "Available For", 
                    "Available From", "Posted By", "Properties Listed", "Localities"
                ]
                
            for col in new_cols:
                if col not in df.columns: df[col] = "Not Found"
            
            df = df.fillna("N/A")
            
            state_obj["file_path"] = file_path
            state_obj["output_name"] = file_path.replace(".xlsx", "_Updated.xlsx")
            state_obj["rows"] = df.to_dict('records')
            state_obj["total"] = len(state_obj["rows"])
            state_obj["current_index"] = -1
            state_obj["status"] = "File loaded. Please connect to browser!"
            
            widgets = state_obj["db_widgets"]
            widgets["row_lbl"].config(text=f"Row: 0 / {state_obj['total']}")
            
        except Exception as e:
            messagebox.showerror("Error Loading Excel", str(e))

    def connect_playwright(self, mode, state_obj, cmd_q):
        if state_obj["worker_status"] == "Connected": return
        state_obj["db_widgets"]["conn_btn"].config(state=tk.DISABLED, text="Connecting...")
        
        def worker():
            with sync_playwright() as p:
                try:
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    context = browser.contexts[0]
                    context.add_init_script('''
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    ''')
                    page = context.new_page()
                    state_obj["worker_status"] = "Connected"
                    state_obj["status"] = "Connected to Browser. Ready to navigate."
                except Exception as e:
                    state_obj["worker_status"] = "Error"
                    state_obj["status"] = f"Connection failed: {e}"
                    return
                
                # Worker Loop
                while self.checking_status:
                    if not cmd_q.empty():
                        cmd = cmd_q.get()
                        action = cmd.get("action")
                        idx = cmd.get("index")
                        
                        if action == "navigate":
                            if 0 <= idx < len(state_obj["rows"]):
                                row = state_obj["rows"][idx]
                                url = row.get("Property URL", row.get("Number", row.get("Owner Name", "")))
                                state_obj["current_index"] = idx
                                state_obj["current_url"] = url
                                state_obj["status"] = f"[{mode.upper()}] Navigating to row {idx+1}..."
                                try:
                                    if page.is_closed(): page = context.new_page()
                                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                                    time.sleep(2)
                                    state_obj["status"] = f"[{mode.upper()}] Ready for extraction (Row {idx+1})"
                                except Exception as e:
                                    state_obj["status"] = f"Nav error: {e}"
                                    
                        elif action == "extract_details":
                            state_obj["status"] = f"[{mode.upper()}] Extracting info..."
                            try:
                                if mode == "buy":
                                    data = extract_buy_basic_details(page)
                                else:
                                    data = extract_rent_basic_details(page)
                                    
                                for k, v in data.items(): state_obj["rows"][idx][k] = v
                                pd.DataFrame(state_obj["rows"]).to_excel(state_obj["output_name"], index=False)
                                state_obj["status"] = f"[{mode.upper()}] Basic extraction OK!"
                            except Exception as e:
                                state_obj["status"] = f"[{mode.upper()}] Extract Error: {e}"
                                
                        elif action == "extract_number":
                            state_obj["status"] = f"[{mode.upper()}] Extracting phone..."
                            try:
                                if mode == "buy":
                                    data = extract_buy_phone_number(page)
                                else:
                                    data = extract_rent_phone_number(page)
                                    
                                num = data.get("Number", "Failed")
                                url_col = 'Property URL' if 'Property URL' in state_obj["rows"][idx] else 'Number'
                                
                                if num != "Extraction Failed":
                                    state_obj["rows"][idx][url_col] = num
                                    state_obj["rows"][idx]["Phone Number"] = num
                                    state_obj["status"] = f"[{mode.upper()}] Number Found: {num}"
                                else:
                                    state_obj["rows"][idx]["Phone Number"] = "Not Found"
                                    state_obj["status"] = f"[{mode.upper()}] Number NOT Found."
                                pd.DataFrame(state_obj["rows"]).to_excel(state_obj["output_name"], index=False)
                            except Exception as e:
                                state_obj["status"] = f"[{mode.upper()}] Extract Error: {e}"
                        cmd_q.task_done()
                    time.sleep(0.5)
        
        threading.Thread(target=worker, daemon=True).start()

    def navigate_row(self, direction, state_obj, cmd_q):
        new_idx = state_obj["current_index"] + direction
        if 0 <= new_idx < state_obj["total"]:
            cmd_q.put({"action": "navigate", "index": new_idx})

    def extract_details(self, state_obj, cmd_q):
        if state_obj["current_index"] >= 0:
            cmd_q.put({"action": "extract_details", "index": state_obj["current_index"]})

    def extract_num(self, state_obj, cmd_q):
        if state_obj["current_index"] >= 0:
            cmd_q.put({"action": "extract_number", "index": state_obj["current_index"]})

    def update_ui_state(self):
        # Update Buy State UI
        self._update_tab_state(self.buy_state)
        # Update Rent State UI
        self._update_tab_state(self.rent_state)
        
        # Display latest status from active tab in global footer
        try:
            active_tab_id = self.main_notebook.select()
            active_tab_name = self.main_notebook.tab(active_tab_id, "text")
        except:
            active_tab_name = "Buy"
            
        if "Buy" in active_tab_name:
            st = self.buy_state["status"]
            if self.buy_state["worker_status"] == 'Connected':
                 self.buy_state["db_widgets"]["conn_btn"].config(text="Connected!")
        else:
            st = self.rent_state["status"]
            if self.rent_state["worker_status"] == 'Connected':
                 self.rent_state["db_widgets"]["conn_btn"].config(text="Connected!")
                
        self.global_status.config(text=st)
        
        if self.checking_status:
            self.after(1000, self.update_ui_state)

    def _update_tab_state(self, st):
        has_file = st["total"] > 0
        is_conn = st["worker_status"] == "Connected"
        w = st["db_widgets"]
        
        if not w: return
        
        w["ext_det_btn"].config(state=tk.NORMAL if is_conn and st["current_index"] >= 0 else tk.DISABLED)
        w["ext_num_btn"].config(state=tk.NORMAL if is_conn and st["current_index"] >= 0 else tk.DISABLED)
        
        w["prev_btn"].config(state=tk.NORMAL if (has_file and is_conn and st["current_index"] > 0) else tk.DISABLED)
        w["next_btn"].config(state=tk.NORMAL if (has_file and is_conn and st["current_index"] < st["total"] - 1) else tk.DISABLED)
            
        if st["current_index"] >= 0:
            idx = st["current_index"]
            row = st["rows"][idx]
            w["row_lbl"].config(text=f"Row: {idx + 1} / {st['total']}")
            
            url_val = str(st.get('current_url', ''))
            short_url = url_val.split('?')[0].split('/')[-1] if '/' in url_val else url_val
            w["lbl_url"].config(text=f"{short_url}")
            
            phone = str(row.get('Phone Number', row.get('Number', '-')))
            w["lbl_phone"].config(text=f"Phone: {phone}")
            w["lbl_owner"].config(text=f"Owner: {row.get('Owner Name', '-')}")
            w["lbl_price"].config(text=f"Price: {row.get('Price', row.get('Rent', '-'))} | Configuration: {row.get('Configuration', '-')}")
            
            if phone in ["-", "Not Found", "Extraction Failed", "N/A"]:
                w["contact_alert"].config(text="⚠ Owner Contact: Not Available", bg="#FADBD8", fg="#C0392B")
            else:
                w["contact_alert"].config(text="✔ Owner Contact: Available", bg="#D5F5E3", fg="#27AE60")
if __name__ == "__main__":
    app = UnifiedScraperApp()
    app.mainloop()
