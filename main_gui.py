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

# Try importing the existing extraction logic
try:
    from extract_owner_details import extract_basic_details, extract_phone_number
    from extract_data import extract_properties
except ImportError:
    pass

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

class UnifiedScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("99Acres Universal Scraper Studio")
        self.geometry("900x750")
        
        # State Variables
        self.app_state = {
            "status": "Idle",
            "file_path": "",
            "output_name": "",
            "rows": [],
            "current_index": -1,
            "total": 0,
            "current_url": "",
            "worker_status": "Idle"
        }
        self.cmd_queue = queue.Queue()
        self.playwright_thread = None
        self.checking_status = True
        
        # Main Tabview
        self.setup_global_controls()
        
        self.tabview = ctk.CTkTabview(self, width=850, height=600)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab1 = self.tabview.add("1. Auto Property Scraper")
        self.tab2 = self.tabview.add("2. Owner Details Scraper")
        
        self.setup_global_controls()
        self.setup_tab_property_scraper()
        self.setup_tab_owner_scraper()
        
        # Loop for queue updates
        self.after(1000, self.update_ui_state)

    def setup_global_controls(self):
        # Frame at the bottom for Chrome Launch / Status
        self.footer = ctk.CTkFrame(self, height=40)
        self.footer.pack(side="bottom", fill="x", padx=20, pady=10)
        
        self.chrome_btn = ctk.CTkButton(self.footer, text="🚀 Launch Chrome (Hidden/Debug Mode)", fg_color="#F39C12", hover_color="#D68910", text_color="white", command=self.launch_chrome)
        self.chrome_btn.pack(side="left", padx=10, pady=10)
        
        self.global_status = ctk.CTkLabel(self.footer, text="Status: Ready", text_color="gray", font=("Arial", 12))
        self.global_status.pack(side="right", padx=20, pady=10)

    def launch_chrome(self):
        """Replicates start_chrome.bat but natively."""
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


    # ==========================
    # TAB 1: Auto Property Scraper
    # ==========================
    def setup_tab_property_scraper(self):
        title = ctk.CTkLabel(self.tab1, text="Scrape Property Links by Location", font=("Arial", 20, "bold"))
        title.pack(pady=20)
        
        desc = ctk.CTkLabel(self.tab1, text="Enter a location (e.g. Bandra, Andheri) and this tool takes over Chrome\nto scroll, collect property links, and save them automatically.", text_color="gray")
        desc.pack(pady=10)
        
        self.loc_entry = ctk.CTkEntry(self.tab1, placeholder_text="Enter Location Name...", width=400, height=40, font=("Arial", 14))
        self.loc_entry.pack(pady=20)
        
        self.start_prop_btn = ctk.CTkButton(self.tab1, text="Start Auto Scraping", font=("Arial", 14, "bold"), height=40, width=200, command=self.start_property_scraper)
        self.start_prop_btn.pack(pady=10)
        
        self.prop_console = ctk.CTkTextbox(self.tab1, width=700, height=300)
        self.prop_console.pack(pady=20)
        self.prop_console.insert("0.0", "Logs will appear here...\nMake sure to click 'Launch Chrome' first.\n")

    def start_property_scraper(self):
        loc = self.loc_entry.get().strip()
        if not loc:
            messagebox.showerror("Error", "Please enter a location!")
            return
        
        self.start_prop_btn.configure(state="disabled", text="Scraping in progress...")
        self.prop_console.insert("end", f"\n[System] Starting auto-scraping for '{loc}'...\n")
        
        def run_script():
            old_stdout = sys.stdout
            sys.stdout = RedirectText(self.prop_console)
            try:
                extract_properties(loc)
                self.prop_console.insert("end", f"\n[System] Done! Check the generated Excel file.\n")
            except Exception as e:
                self.prop_console.insert("end", f"\n[Error] {str(e)}\n")
            finally:
                sys.stdout = old_stdout
                self.start_prop_btn.configure(state="normal", text="Start Auto Scraping")
                
        threading.Thread(target=run_script, daemon=True).start()

    # ==========================
    # TAB 2: Owner Details Scraper
    # ==========================
    def setup_tab_owner_scraper(self):
        # Top panel: File load & Connections
        top_frame = ctk.CTkFrame(self.tab2)
        top_frame.pack(fill="x", padx=10, pady=10)
        
        self.load_btn = ctk.CTkButton(top_frame, text="1. Load Excel File", command=self.load_excel)
        self.load_btn.pack(side="left", padx=10, pady=10)
        
        self.connect_btn = ctk.CTkButton(top_frame, text="2. Connect to Browser", fg_color="#2ECC71", hover_color="#27AE60", command=self.connect_playwright)
        self.connect_btn.pack(side="left", padx=10, pady=10)
        
        self.ip_btn = ctk.CTkButton(top_frame, text="Rotate IP (WARP)", fg_color="#E74C3C", hover_color="#C0392B", command=self.change_ip)
        self.ip_btn.pack(side="right", padx=10, pady=10)
        
        # Navigation
        nav_frame = ctk.CTkFrame(self.tab2)
        nav_frame.pack(fill="x", padx=10, pady=5)
        
        self.prev_btn = ctk.CTkButton(nav_frame, text="< Prev", width=80, command=lambda: self.navigate_row(-1), state="disabled")
        self.prev_btn.pack(side="left", padx=10, pady=10)
        
        self.row_lbl = ctk.CTkLabel(nav_frame, text="Row: 0 / 0", font=("Arial", 14, "bold"))
        self.row_lbl.pack(side="left", expand=True, pady=10)
        
        self.next_btn = ctk.CTkButton(nav_frame, text="Next >", width=80, command=lambda: self.navigate_row(1), state="disabled")
        self.next_btn.pack(side="right", padx=10, pady=10)
        
        # Current Data Display
        data_frame = ctk.CTkFrame(self.tab2)
        data_frame.pack(fill="x", padx=10, pady=10)
        
        self.db_url = ctk.CTkLabel(data_frame, text="URL: N/A", text_color="#3498DB", wraplength=700)
        self.db_url.pack(anchor="w", padx=10, pady=5)
        self.db_phone = ctk.CTkLabel(data_frame, text="Phone: -", font=("Arial", 16, "bold"))
        self.db_phone.pack(anchor="w", padx=10, pady=5)
        self.db_name = ctk.CTkLabel(data_frame, text="Owner: -")
        self.db_name.pack(anchor="w", padx=10, pady=5)
        self.db_rent = ctk.CTkLabel(data_frame, text="Rent: -")
        self.db_rent.pack(anchor="w", padx=10, pady=5)
        
        # Action Buttons
        bot_frame = ctk.CTkFrame(self.tab2, fg_color="transparent")
        bot_frame.pack(fill="x", padx=10, pady=10)
        
        self.extract_det_btn = ctk.CTkButton(bot_frame, text="Scrap Basic Details", height=50, state="disabled", command=self.extract_details)
        self.extract_det_btn.pack(side="left", expand=True, padx=5)
        
        self.extract_num_btn = ctk.CTkButton(bot_frame, text="Scrap Phone Number", height=50, fg_color="#27AE60", hover_color="#2ECC71", state="disabled", command=self.extract_number)
        self.extract_num_btn.pack(side="right", expand=True, padx=5)

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

    def load_excel(self):
        file_path = filedialog.askopenfilename(title="Select Extracted Excel", filetypes=[("Excel Files", "*.xlsx")])
        if not file_path: return
        
        try:
            df = pd.read_excel(file_path)
            url_col = 'Property URL' if 'Property URL' in df.columns else 'Number'
            if url_col not in df.columns:
                messagebox.showerror("Error", "Missing 'Property URL' column.")
                return
                
            new_cols = ["Owner Name", "Phone Number", "Configuration", "Rent", "Area", "Address", "Furnishing", "Available For", "Available From", "Posted By", "Properties Listed", "Localities"]
            for col in new_cols:
                if col not in df.columns: df[col] = "Not Found"
            
            df = df.fillna("N/A")
            
            self.app_state["file_path"] = file_path
            self.app_state["output_name"] = file_path.replace(".xlsx", "_Updated.xlsx")
            self.app_state["rows"] = df.to_dict('records')
            self.app_state["total"] = len(self.app_state["rows"])
            self.app_state["current_index"] = -1
            self.app_state["status"] = "File loaded. Please connect to browser!"
            self.row_lbl.configure(text=f"Row: 0 / {self.app_state['total']}")
        except Exception as e:
            messagebox.showerror("Error Loading Excel", str(e))

    def connect_playwright(self):
        if self.app_state["worker_status"] == "Connected": return
        self.connect_btn.configure(state="disabled", text="Connecting...")
        
        def worker():
            with sync_playwright() as p:
                try:
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    context = browser.contexts[0]
                    context.add_init_script('''
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    ''')
                    page = context.new_page()
                    self.app_state["worker_status"] = "Connected"
                    self.app_state["status"] = "Connected to Browser. Ready to navigate."
                    self.connect_btn.configure(text="Connected!")
                except Exception as e:
                    self.app_state["worker_status"] = "Error"
                    self.app_state["status"] = f"Connection failed: {e}"
                    self.connect_btn.configure(state="normal", text="2. Connect to Browser")
                    return
                
                # Worker Loop
                while self.checking_status:
                    if not self.cmd_queue.empty():
                        cmd = self.cmd_queue.get()
                        action = cmd.get("action")
                        idx = cmd.get("index")
                        
                        if action == "navigate":
                            if 0 <= idx < len(self.app_state["rows"]):
                                row = self.app_state["rows"][idx]
                                url = row.get("Property URL", row.get("Number", ""))
                                self.app_state["current_index"] = idx
                                self.app_state["current_url"] = url
                                self.app_state["status"] = f"Navigating to row {idx+1}..."
                                try:
                                    if page.is_closed(): page = context.new_page()
                                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                                    time.sleep(2)
                                    self.app_state["status"] = f"Ready for extraction (Row {idx+1})"
                                except Exception as e:
                                    self.app_state["status"] = f"Nav error: {e}"
                                    
                        elif action == "extract_details":
                            self.app_state["status"] = f"Extracting basic info..."
                            try:
                                data = extract_basic_details(page)
                                for k, v in data.items(): self.app_state["rows"][idx][k] = v
                                pd.DataFrame(self.app_state["rows"]).to_excel(self.app_state["output_name"], index=False)
                                self.app_state["status"] = "Basic extraction OK!"
                            except Exception as e:
                                self.app_state["status"] = f"Extract Error: {e}"
                                
                        elif action == "extract_number":
                            self.app_state["status"] = f"Extracting phone..."
                            try:
                                data = extract_phone_number(page)
                                num = data.get("Number", "Failed")
                                url_col = 'Property URL' if 'Property URL' in self.app_state["rows"][idx] else 'Number'
                                
                                if num != "Extraction Failed":
                                    self.app_state["rows"][idx][url_col] = num
                                    self.app_state["rows"][idx]["Phone Number"] = num
                                    self.app_state["status"] = f"Number Found: {num}"
                                else:
                                    self.app_state["rows"][idx]["Phone Number"] = "Not Found"
                                    self.app_state["status"] = "Number NOT Found."
                                pd.DataFrame(self.app_state["rows"]).to_excel(self.app_state["output_name"], index=False)
                            except Exception as e:
                                self.app_state["status"] = f"Extract Error: {e}"
                        self.cmd_queue.task_done()
                    time.sleep(0.5)
        
        self.playwright_thread = threading.Thread(target=worker, daemon=True)
        self.playwright_thread.start()

    def navigate_row(self, direction):
        new_idx = self.app_state["current_index"] + direction
        if 0 <= new_idx < self.app_state["total"]:
            self.cmd_queue.put({"action": "navigate", "index": new_idx})

    def extract_details(self):
        if self.app_state["current_index"] >= 0:
            self.cmd_queue.put({"action": "extract_details", "index": self.app_state["current_index"]})

    def extract_number(self):
        if self.app_state["current_index"] >= 0:
            self.cmd_queue.put({"action": "extract_number", "index": self.app_state["current_index"]})

    def update_ui_state(self):
        # Only enable nav if connected and file loaded
        has_file = self.app_state["total"] > 0
        is_conn = self.app_state["worker_status"] == "Connected"
        
        if has_file and is_conn:
            self.prev_btn.configure(state="normal" if self.app_state["current_index"] > 0 else "disabled")
            self.next_btn.configure(state="normal" if self.app_state["current_index"] < self.app_state["total"] - 1 else "disabled")
            
            if self.app_state["current_index"] >= 0:
                self.extract_det_btn.configure(state="normal")
                self.extract_num_btn.configure(state="normal")
                
                # Update Labels
                idx = self.app_state["current_index"]
                row = self.app_state["rows"][idx]
                self.row_lbl.configure(text=f"Row: {idx + 1} / {self.app_state['total']}")
                self.db_url.configure(text=f"URL: {self.app_state['current_url']}")
                self.db_phone.configure(text=f"Phone: {row.get('Phone Number', row.get('Number', '-'))}")
                self.db_name.configure(text=f"Owner: {row.get('Owner Name', '-')}")
                self.db_rent.configure(text=f"Rent: {row.get('Rent', '-')} | Config: {row.get('Configuration', '-')}")
        
        self.global_status.configure(text=self.app_state["status"])
        
        if self.checking_status:
            self.after(1000, self.update_ui_state)

if __name__ == "__main__":
    app = UnifiedScraperApp()
    app.mainloop()
