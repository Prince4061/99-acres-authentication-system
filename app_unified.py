import os
import sys
import threading
import queue
import time
import subprocess
import urllib.request
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox
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


class RedirectText:
    def __init__(self, text_ctrl):
        self.text_ctrl = text_ctrl
    def write(self, string):
        self.text_ctrl.insert("end", string)
        self.text_ctrl.see("end")
    def flush(self):
        pass

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

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


class UnifiedScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("99Acres Universal Scraper Studio - Buy & Rent")
        self.geometry("950x800")
        
        # Withdraw the main window until login is verified
        self.withdraw()
        
        self.login_verified = False
        self.show_login_dialog()
        
        # State Variables
        self.buy_state = self._init_state()
        self.rent_state = self._init_state()
        
        self.buy_queue = queue.Queue()
        self.rent_queue = queue.Queue()
        self.checking_status = True
        
        # Setup GUI
        self.setup_global_controls()
        
        # Main Tabview for Buy vs Rent
        self.main_tabview = ctk.CTkTabview(self, width=900, height=650)
        self.main_tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.buy_tab = self.main_tabview.add("BUY Properties")
        self.rent_tab = self.main_tabview.add("RENT Properties")
        
        self.setup_buy_section()
        self.setup_rent_section()
        
        # Loop for queue updates
        self.after(1000, self.update_ui_state)

    def show_login_dialog(self):
        login_win = ctk.CTkToplevel(self)
        login_win.title("GharLeads Authorization")
        login_win.geometry("380x245")
        login_win.resizable(False, False)
        
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
        title_lbl = ctk.CTkLabel(login_win, text="GharLeads Verified Panel", font=("Arial", 16, "bold"), text_color=["#2C3E50", "#ECF0F1"])
        title_lbl.pack(pady=15)
        
        desc_lbl = ctk.CTkLabel(login_win, text="Enter authorized PIN to unlock software:", font=("Arial", 12))
        desc_lbl.pack(pady=2)
        
        pin_var = tk.StringVar()
        pin_entry = ctk.CTkEntry(login_win, textvariable=pin_var, show="*", font=("Arial", 14), width=180, justify="center")
        pin_entry.pack(pady=10)
        pin_entry.focus()
        
        status_lbl = ctk.CTkLabel(login_win, text="", text_color="#E74C3C", font=("Arial", 11, "bold"), wraplength=340)
        status_lbl.pack(pady=2)
        
        def verify_action(event=None):
            pin = pin_var.get().strip()
            if not pin:
                status_lbl.configure(text="Please enter a PIN.")
                return
            
            status_lbl.configure(text="Connecting to security server...", text_color="#3498DB")
            login_win.update()
            
            # Run the verification
            success, msg = check_google_sheet_pin(pin)
            if success:
                self.login_verified = True
                login_win.destroy()
            else:
                status_lbl.configure(text=msg, text_color="#E74C3C")
                pin_entry.delete(0, tk.END)
                
        pin_entry.bind("<Return>", verify_action)
        
        btn = ctk.CTkButton(login_win, text="Verify & Unlock", command=verify_action, font=("Arial", 12, "bold"), width=150, height=35, fg_color="#2ECC71", hover_color="#27AE60")
        btn.pack(pady=15)
        
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
        self.footer = ctk.CTkFrame(self, height=45)
        self.footer.pack(side="bottom", fill="x", padx=20, pady=10)
        
        btn_frame = ctk.CTkFrame(self.footer, fg_color="transparent")
        btn_frame.pack(side="left", fill="y", padx=10)
        
        self.chrome_btn = ctk.CTkButton(btn_frame, text="🚀 Launch Base Chrome", fg_color="#F39C12", hover_color="#D68910", text_color="white", command=self.launch_chrome)
        self.chrome_btn.pack(side="left", padx=5, pady=5)
        
        self.ip_btn = ctk.CTkButton(btn_frame, text="Rotate IP (WARP)", fg_color="#E74C3C", hover_color="#C0392B", command=self.change_ip)
        self.ip_btn.pack(side="left", padx=5, pady=5)
        
        self.global_status = ctk.CTkLabel(self.footer, text="System: Ready", text_color="gray", font=("Arial", 12))
        self.global_status.pack(side="right", padx=20, pady=10)

    def launch_chrome(self):
        """Kills old chrome and starts debug chrome"""
        self.global_status.configure(text="Killing old Chrome & Starting New...")
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
                self.global_status.configure(text="Chrome is running in Debug Mode.")
            except Exception as e:
                self.global_status.configure(text=f"Failed to launch Chrome: {e}")
        threading.Thread(target=run, daemon=True).start()


    def change_ip(self):
        self.ip_btn.configure(state="disabled", text="Changing...")
        def run():
            warp_cli = r"C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe"
            if not os.path.exists(warp_cli):
                self.global_status.configure(text="Cloudflare WARP not found.")
                self.ip_btn.configure(state="normal", text="Rotate IP (WARP)")
                return
            try:
                subprocess.run([warp_cli, 'tos', 'accept'], capture_output=True, timeout=5)
                subprocess.run([warp_cli, 'disconnect'], capture_output=True, timeout=10)
                time.sleep(2)
                subprocess.run([warp_cli, 'connect'], capture_output=True, timeout=10)
                time.sleep(4)
                new_ip = urllib.request.urlopen('https://api.ipify.org', timeout=8).read().decode()
                self.global_status.configure(text=f"IP Changed: {new_ip}")
            except Exception as e:
                self.global_status.configure(text=f"IP Error: {e}")
            self.ip_btn.configure(state="normal", text="Rotate IP (WARP)")
        threading.Thread(target=run, daemon=True).start()

    # ==========================
    # UI SETUP: BUY SECTION
    # ==========================
    def setup_buy_section(self):
        sub_tabview = ctk.CTkTabview(self.buy_tab)
        sub_tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        tab_buy_auto = sub_tabview.add("1. Auto Buy Properties")
        tab_buy_owner = sub_tabview.add("2. Buy Owner Scraper")
        
        # 1. AUTO BUY
        title1 = ctk.CTkLabel(tab_buy_auto, text="Scrape 'Buy' Property Links", font=("Arial", 18, "bold"))
        title1.pack(pady=10)
        self.loc_buy_entry = ctk.CTkEntry(tab_buy_auto, placeholder_text="Location Name (e.g. Thane)...", width=300, height=35)
        self.loc_buy_entry.pack(pady=10)
        self.start_buy_prop_btn = ctk.CTkButton(tab_buy_auto, text="Start Buy Scraping", font=("Arial", 12, "bold"), command=self.start_buy_auto_scraper)
        self.start_buy_prop_btn.pack(pady=5)
        self.buy_console = ctk.CTkTextbox(tab_buy_auto, width=700, height=200)
        self.buy_console.pack(pady=10, fill="both", expand=True)
        
        # 2. BUY OWNER
        self._setup_owner_gui(tab_buy_owner, "buy", self.buy_state, self.buy_queue)

    # ==========================
    # UI SETUP: RENT SECTION
    # ==========================
    def setup_rent_section(self):
        sub_tabview = ctk.CTkTabview(self.rent_tab)
        sub_tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        tab_rent_auto = sub_tabview.add("1. Auto Rent Properties")
        tab_rent_owner = sub_tabview.add("2. Rent Owner Scraper")
        
        # 1. AUTO RENT
        title1 = ctk.CTkLabel(tab_rent_auto, text="Scrape 'Rent' Property Links", font=("Arial", 18, "bold"))
        title1.pack(pady=10)
        self.loc_rent_entry = ctk.CTkEntry(tab_rent_auto, placeholder_text="Location Name (e.g. Bandra)...", width=300, height=35)
        self.loc_rent_entry.pack(pady=10)
        self.start_rent_prop_btn = ctk.CTkButton(tab_rent_auto, text="Start Rent Scraping", font=("Arial", 12, "bold"), command=self.start_rent_auto_scraper)
        self.start_rent_prop_btn.pack(pady=5)
        self.rent_console = ctk.CTkTextbox(tab_rent_auto, width=700, height=200)
        self.rent_console.pack(pady=10, fill="both", expand=True)
        
        # 2. RENT OWNER
        self._setup_owner_gui(tab_rent_owner, "rent", self.rent_state, self.rent_queue)

    def _setup_owner_gui(self, parent_frame, mode, state_obj, cmd_q):
        # Top panel: Load File & Connect
        top_frame = ctk.CTkFrame(parent_frame)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        load_btn = ctk.CTkButton(top_frame, text="1. Load Excel", width=120, command=lambda: self.load_excel(mode, state_obj))
        load_btn.pack(side="left", padx=5, pady=5)
        
        conn_btn = ctk.CTkButton(top_frame, text="2. Connect Browser", width=150, fg_color="#2ECC71", hover_color="#27AE60", command=lambda: self.connect_playwright(mode, state_obj, cmd_q))
        conn_btn.pack(side="left", padx=5, pady=5)
        state_obj["db_widgets"]["conn_btn"] = conn_btn
        
        lbl_status = ctk.CTkLabel(top_frame, text="File: None", width=300, anchor="w", text_color="#3498DB")
        lbl_status.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        state_obj["db_widgets"]["file_lbl"] = lbl_status
        
        # Navigation
        nav_frame = ctk.CTkFrame(parent_frame)
        nav_frame.pack(fill="x", padx=10, pady=5)
        
        prev_btn = ctk.CTkButton(nav_frame, text="< Prev", width=60, state="disabled", command=lambda: self.navigate_row(-1, state_obj, cmd_q))
        prev_btn.pack(side="left", padx=10, pady=5)
        state_obj["db_widgets"]["prev_btn"] = prev_btn
        
        row_lbl = ctk.CTkLabel(nav_frame, text="Row: 0 / 0", font=("Arial", 14, "bold"))
        row_lbl.pack(side="left", expand=True, pady=5)
        state_obj["db_widgets"]["row_lbl"] = row_lbl
        
        next_btn = ctk.CTkButton(nav_frame, text="Next >", width=60, state="disabled", command=lambda: self.navigate_row(1, state_obj, cmd_q))
        next_btn.pack(side="right", padx=10, pady=5)
        state_obj["db_widgets"]["next_btn"] = next_btn
        
        # Data Display
        data_frame = ctk.CTkFrame(parent_frame)
        data_frame.pack(fill="x", padx=10, pady=5)
        
        lbl_url = ctk.CTkLabel(data_frame, text="URL: N/A", text_color="#3498DB", wraplength=700)
        lbl_url.pack(anchor="w", padx=10, pady=3)
        state_obj["db_widgets"]["lbl_url"] = lbl_url
        
        lbl_phone = ctk.CTkLabel(data_frame, text="Phone: -", font=("Arial", 16, "bold"))
        lbl_phone.pack(anchor="w", padx=10, pady=3)
        state_obj["db_widgets"]["lbl_phone"] = lbl_phone
        
        lbl_owner = ctk.CTkLabel(data_frame, text="Owner: -")
        lbl_owner.pack(anchor="w", padx=10, pady=3)
        state_obj["db_widgets"]["lbl_owner"] = lbl_owner
        
        lbl_price = ctk.CTkLabel(data_frame, text="Price/Rent: -")
        lbl_price.pack(anchor="w", padx=10, pady=3)
        state_obj["db_widgets"]["lbl_price"] = lbl_price
        
        # Action Buttons
        bot_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        bot_frame.pack(fill="x", padx=10, pady=10)
        
        btn_det = ctk.CTkButton(bot_frame, text="Scrape Basic Details", height=40, state="disabled", command=lambda: self.extract_details(state_obj, cmd_q))
        btn_det.pack(side="left", expand=True, padx=5)
        state_obj["db_widgets"]["ext_det_btn"] = btn_det
        
        btn_num = ctk.CTkButton(bot_frame, text="Scrape Phone Number", height=40, fg_color="#27AE60", hover_color="#2ECC71", state="disabled", command=lambda: self.extract_num(state_obj, cmd_q))
        btn_num.pack(side="right", expand=True, padx=5)
        state_obj["db_widgets"]["ext_num_btn"] = btn_num

    # ==========================
    # LOGIC: AUTO SCRAPERS
    # ==========================
    def start_buy_auto_scraper(self):
        loc = self.loc_buy_entry.get().strip()
        if not loc:
            messagebox.showerror("Error", "Please enter a location!")
            return
        
        self.start_buy_prop_btn.configure(state="disabled", text="Scraping...")
        self.buy_console.insert("end", f"\n[System] Starting auto-scraping 'Buy' for '{loc}'...\n")
        
        def run_script():
            old_stdout = sys.stdout
            sys.stdout = RedirectText(self.buy_console)
            try:
                out = extract_buy_properties(loc)
                self.buy_console.insert("end", f"\n[System] Done! File saved: {out}\n")
            except Exception as e:
                self.buy_console.insert("end", f"\n[Error] {str(e)}\n")
            finally:
                sys.stdout = old_stdout
                self.start_buy_prop_btn.configure(state="normal", text="Start Buy Scraping")
                
        threading.Thread(target=run_script, daemon=True).start()

    def start_rent_auto_scraper(self):
        loc = self.loc_rent_entry.get().strip()
        if not loc:
            messagebox.showerror("Error", "Please enter a location!")
            return
        
        self.start_rent_prop_btn.configure(state="disabled", text="Scraping...")
        self.rent_console.insert("end", f"\n[System] Starting auto-scraping 'Rent' for '{loc}'...\n")
        
        def run_script():
            old_stdout = sys.stdout
            sys.stdout = RedirectText(self.rent_console)
            try:
                out = extract_rent_properties(loc)
                self.rent_console.insert("end", f"\n[System] Done! File saved: {out}\n")
            except Exception as e:
                self.rent_console.insert("end", f"\n[Error] {str(e)}\n")
            finally:
                sys.stdout = old_stdout
                self.start_rent_prop_btn.configure(state="normal", text="Start Rent Scraping")
                
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
            widgets["row_lbl"].configure(text=f"Row: 0 / {state_obj['total']}")
            widgets["file_lbl"].configure(text=f"File: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error Loading Excel", str(e))

    def connect_playwright(self, mode, state_obj, cmd_q):
        if state_obj["worker_status"] == "Connected": return
        state_obj["db_widgets"]["conn_btn"].configure(state="disabled", text="Connecting...")
        
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
        active_tab = self.main_tabview.get()
        if "Buy" in active_tab:
            st = self.buy_state["status"]
            if self.buy_state["worker_status"] == 'Connected':
                 self.buy_state["db_widgets"]["conn_btn"].configure(text="Connected!")
        else:
            st = self.rent_state["status"]
            if self.rent_state["worker_status"] == 'Connected':
                 self.rent_state["db_widgets"]["conn_btn"].configure(text="Connected!")
                
        self.global_status.configure(text=st)
        
        if self.checking_status:
            self.after(1000, self.update_ui_state)

    def _update_tab_state(self, st):
        has_file = st["total"] > 0
        is_conn = st["worker_status"] == "Connected"
        w = st["db_widgets"]
        
        if not w: return
        
        w["ext_det_btn"].configure(state="normal" if is_conn and st["current_index"] >= 0 else "disabled")
        w["ext_num_btn"].configure(state="normal" if is_conn and st["current_index"] >= 0 else "disabled")
        
        w["prev_btn"].configure(state="normal" if (has_file and is_conn and st["current_index"] > 0) else "disabled")
        w["next_btn"].configure(state="normal" if (has_file and is_conn and st["current_index"] < st["total"] - 1) else "disabled")
            
        if st["current_index"] >= 0:
            idx = st["current_index"]
            row = st["rows"][idx]
            w["row_lbl"].configure(text=f"Row: {idx + 1} / {st['total']}")
            w["lbl_url"].configure(text=f"URL: {st['current_url']}")
            w["lbl_phone"].configure(text=f"Phone: {row.get('Phone Number', row.get('Number', '-'))}")
            w["lbl_owner"].configure(text=f"Owner: {row.get('Owner Name', '-')}")
            w["lbl_price"].configure(text=f"Price/Rent: {row.get('Price', row.get('Rent', '-'))} | Config: {row.get('Configuration', '-')}")


if __name__ == "__main__":
    app = UnifiedScraperApp()
    app.mainloop()
