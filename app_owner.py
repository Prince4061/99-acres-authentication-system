import os
import threading
import json
import time
import queue
import pandas as pd
from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright
from extract_owner_details import extract_basic_details, extract_phone_number

app = Flask(__name__)

# Global state
state = {
    "status": "Idle",
    "file_path": "",
    "output_name": "",
    "rows": [],
    "current_index": -1,
    "total": 0,
    "current_url": "",
    "worker_status": "Idle"
}

cmd_queue = queue.Queue()

def playwright_worker():
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0]
            
            # Inject stealth script on every page to hide automation signals
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en', 'hi'] });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                delete window.__playwright;
                delete window.__pw_manual;
            """)
            
            page = context.new_page()
            state["worker_status"] = "Connected"
            state["status"] = "Connected to Chrome. Ready to navigate."
        except Exception as e:
            state["worker_status"] = "Error"
            state["status"] = f"Failed to connect to Chrome: {e}"
            return

        # Figure out the url column from the keys if it exists
        url_col = 'Property URL'
        if len(state["rows"]) > 0:
            if 'Property URL' in state["rows"][0]:
                url_col = 'Property URL'
            elif 'Number' in state["rows"][0]:
                url_col = 'Number'

        while True:
            cmd = cmd_queue.get()
            action = cmd.get("action")
            
            if action == "navigate":
                idx = cmd.get("index")
                if 0 <= idx < len(state["rows"]):
                    row_data = state["rows"][idx]
                    url = row_data.get("Property URL", row_data.get("Number", ""))
                    
                    state["current_index"] = idx
                    state["current_url"] = url
                    state["status"] = f"Navigating to row {idx+1}..."
                    if url and str(url).startswith("http"):
                        try:
                            # Use domcontentloaded for faster apparent navigation
                            if page.is_closed():
                                page = context.new_page()
                            page.goto(url, wait_until="domcontentloaded", timeout=60000)
                            time.sleep(2)
                            state["status"] = f"Navigated to row {idx+1}. Ready for extraction."
                        except Exception as e:
                            # If page was manually closed, try to recreate and navigate again
                            if "closed" in str(e).lower() or "target" in str(e).lower():
                                try:
                                    page = context.new_page()
                                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                                    time.sleep(2)
                                    state["status"] = f"Navigated to row {idx+1} after reconnecting."
                                except Exception as e2:
                                    state["status"] = f"Navigation error on row {idx+1}: {e2}"
                            else:
                                state["status"] = f"Navigation error on row {idx+1}: {e}"
                    else:
                        state["status"] = f"Row {idx+1} has no valid URL."
            
            elif action == "extract_details":
                idx = cmd.get("index")
                if 0 <= idx < len(state["rows"]):
                    state["status"] = f"Extracting basic details (no OTP) for row {idx+1}..."
                    try:
                        data = extract_basic_details(page)
                        for k, v in data.items():
                            state["rows"][idx][k] = v
                                
                        state["status"] = f"Success! Details extracted for row {idx+1}."
                        
                        # Save to excel
                        df = pd.DataFrame(state["rows"])
                        df.to_excel(state["output_name"], index=False)
                    except Exception as e:
                        state["status"] = f"Extraction error on row {idx+1}: {e}"

            elif action == "extract_number":
                idx = cmd.get("index")
                if 0 <= idx < len(state["rows"]):
                    state["status"] = f"Extracting phone number (post-OTP) for row {idx+1}..."
                    try:
                        data = extract_phone_number(page)
                        if data.get("Number") != "Extraction Failed":
                            extracted_num = data.get("Number")
                            # The user wants the old link replaced with the number
                            url_col = 'Property URL' if 'Property URL' in df.columns else 'Number'
                            
                            state["rows"][idx][url_col] = extracted_num
                            state["rows"][idx]["Phone Number"] = extracted_num
                            state["status"] = f"Success! Extracted Number: {extracted_num} for row {idx+1}."
                        else:
                            state["rows"][idx]["Phone Number"] = "Not Found / Limit"
                            state["status"] = f"Failed to find number for row {idx+1}."
                        
                        # Save to excel
                        df = pd.DataFrame(state["rows"])
                        df.to_excel(state["output_name"], index=False)
                    except Exception as e:
                        state["status"] = f"Number extraction error on row {idx+1}: {e}"

            elif action == "quit":
                page.close()
                break

            cmd_queue.task_done()

@app.route('/')
def index():
    return render_template('owner.html')

@app.route('/api/load', methods=['POST'])
def load_file():
    global state
    data = request.json
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found."})
        
    try:
        df = pd.read_excel(file_path)
        
        url_col = 'Property URL' if 'Property URL' in df.columns else 'Number'
        if url_col not in df.columns:
            return jsonify({"success": False, "error": f"Missing URL column in {file_path}. Required either 'Property URL' or 'Number'."})
            
        new_cols = [
            "Owner Name", "Phone Number", "Configuration", "Rent", 
            "Area", "Address", "Furnishing", "Available For", 
            "Available From", "Posted By", "Properties Listed", "Localities"
        ]
        
        for col in new_cols:
            if col not in df.columns:
                df[col] = "Not Found"
                
        state["file_path"] = file_path
        state["output_name"] = file_path.replace(".xlsx", "_Updated.xlsx")
        
        df = df.fillna("N/A")
        
        state["rows"] = df.to_dict('records')
        state["total"] = len(state["rows"])
        state["current_index"] = -1
        state["current_url"] = ""
        state["status"] = "File loaded successfully. Processing started..."
        
        if state["worker_status"] != "Connected":
            thread = threading.Thread(target=playwright_worker)
            thread.daemon = True
            thread.start()
            
        return jsonify({"success": True, "total": state["total"]})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    safe_state = {
        "status": state["status"],
        "current_index": state["current_index"],
        "total": state["total"],
        "current_url": state["current_url"]
    }
    if 0 <= state["current_index"] < state["total"]:
        row_data = state["rows"][state["current_index"]]
        safe_state["current_row_data"] = {
            "Phone Number": row_data.get("Phone Number", row_data.get("Number", "N/A")),
            "Owner Name": row_data.get("Owner Name", "N/A"),
            "Rent": row_data.get("Rent", "N/A"),
            "Configuration": row_data.get("Configuration", "N/A"),
            "Address": row_data.get("Address", "N/A")
        }
    else:
        safe_state["current_row_data"] = None
        
    return jsonify(safe_state)

@app.route('/api/navigate', methods=['POST'])
def navigate():
    data = request.json
    idx = data.get('index', 0)
    cmd_queue.put({"action": "navigate", "index": int(idx)})
    return jsonify({"success": True})

@app.route('/api/extract/details', methods=['POST'])
def extract_details():
    data = request.json
    idx = data.get('index', 0)
    cmd_queue.put({"action": "extract_details", "index": int(idx)})
    return jsonify({"success": True})

@app.route('/api/extract/number', methods=['POST'])
def extract_number():
    data = request.json
    idx = data.get('index', 0)
    cmd_queue.put({"action": "extract_number", "index": int(idx)})
    return jsonify({"success": True})

@app.route('/api/change_ip', methods=['POST'])
def change_ip():
    """Uses Cloudflare WARP to rotate the public IP."""
    import subprocess
    import time
    import os

    warp_cli = r"C:\\Program Files\\Cloudflare\\Cloudflare WARP\\warp-cli.exe"
    if not os.path.exists(warp_cli):
        return jsonify({"success": False, "error": "Cloudflare WARP not found. Please install 1.1.1.1 WARP first."})

    try:
        # Accept TOS just in case it's the first run (silently fails if already accepted)
        subprocess.run([warp_cli, 'tos', 'accept'], capture_output=True, timeout=5)

        # Disconnect VPN -> Reverts to original ISP IP
        subprocess.run([warp_cli, 'disconnect'], capture_output=True, timeout=10)
        time.sleep(2)

        # Connect VPN -> Fetches a new WARP IP
        subprocess.run([warp_cli, 'connect'], capture_output=True, timeout=10)
        time.sleep(4)  # Wait for WARP tunnel to establish

        # Get new public IP
        try:
            import urllib.request
            new_ip = urllib.request.urlopen('https://api.ipify.org', timeout=8).read().decode()
        except:
            new_ip = None

        return jsonify({"success": True, "adapter": "Cloudflare WARP", "new_ip": new_ip or "Unknown"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5001, use_reloader=False)
