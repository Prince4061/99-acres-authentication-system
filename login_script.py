from playwright.sync_api import sync_playwright
import time

def login_to_99acres():
    print("Starting Playwright and connecting to your existing Chrome...")
    with sync_playwright() as p:
        try:
            # Connect to the Chrome browser running on port 9222
            # Explicitly using 127.0.0.1 here because localhost sometimes resolves to ipv6 (::1) and fails
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("Successfully connected to your Chrome browser!")
            
            # Use the first available context
            context = browser.contexts[0]
            
            # Create a new page
            page = context.new_page()
            
            print("Navigating to 99acres...")
            page.goto("https://www.99acres.com/", wait_until="domcontentloaded")
            
            print("Waiting for site to load fully...")
            time.sleep(3) # Human-like pause

            print("Looking for the Profile Icon to open the login menu...")
            try:
                # Based on the latest DOM inspection, the header icon is slightly different.
                # It's better to just click anywhere near that user icon or use the updated class.
                profile_icon_selector = ".theader__userIcon"
                page.wait_for_selector(profile_icon_selector, timeout=10000)
                page.hover(profile_icon_selector)
                time.sleep(1)
                page.click(profile_icon_selector)
            except Exception as e:
                print(f"Profile icon check info: {e}")

            print("Clicking on 'LOGIN / REGISTER'...")
            # Using get_by_text is more reliable
            try:
                login_btn = page.get_by_text("LOGIN / REGISTER", exact=False)
                login_btn.wait_for(timeout=5000)
                login_btn.click()
                print("Login modal opened successfully!")
            except Exception as e:
                print("Could not find the text LOGIN/REGISTER, maybe you are already logged in?")
            
            print("\n*** ACTION REQUIRED ***")
            print("Please enter your number and verify the OTP manually in your Chrome browser.")
            print("Once you are logged in, we can move to the next script for extracting data.")
            print("Keeping the connection alive for 1 minute before script exits... (You can take your time to login)")
            time.sleep(60)
            
        except Exception as e:
            print(f"Failed to connect or automate: {e}")
            print("\n*** IMPORTANT ***")
            print("Make sure you started Chrome using the 'start_chrome.bat' file first!")
        finally:
            print("Script finished. (Note: Your browser window will remain open)")

if __name__ == "__main__":
    login_to_99acres()

