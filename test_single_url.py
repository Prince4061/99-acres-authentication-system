from playwright.sync_api import sync_playwright
import extract_buy_owner_details

url = "https://www.99acres.com/2-bhk-bedroom-apartment-flat-for-sale-in-kherwadi-western-mumbai-619-sq-ft-spid-K87177512"

with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]
        page = context.new_page()
        
        print(f"Navigating to {url}...")
        page.goto(url, wait_until="domcontentloaded")
        
        print("Extracting details...")
        data = extract_buy_owner_details.extract_basic_details(page)
        
        print("\n--- EXTRACTION RESULTS ---")
        for k, v in data.items():
            print(f"{k}: {v}")
            
    except Exception as e:
        print(f"Error: {e}")
