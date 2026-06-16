import sys
import time
import os
import pandas as pd
from playwright.sync_api import sync_playwright

def extract_buy_properties(location="Thane"):
    print(f"Starting connection to extract BUY properties for {location}...")
    
    with sync_playwright() as p:
        try:
            # Connect to your already running Chrome browser
            print("Connecting to existing Chrome session...")
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            
            # Use the existing context
            context = browser.contexts[0]
            
            # Open a new tab to keep things clean
            page = context.new_page()
            
            # Step 1: Go to 99acres homepage
            print("Opening 99acres homepage...")
            page.goto("https://www.99acres.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
            
            # Select 'Buy' mode
            print("Switching to 'Buy' mode...")
            try:
                page.get_by_text("Buy", exact=True).first.click(timeout=5000)
                time.sleep(1)
            except Exception as e:
                print(f"Notice: Could not click Buy tab. Exploring directly. Error: {e}")

            # Step 2: Search for the given location
            print(f"Typing '{location}' in the search bar...")
            search_input_selector = ".component__searchInput, input#keyword2"
            page.wait_for_selector(search_input_selector, timeout=10000)
            page.click(search_input_selector)
            
            page.fill(search_input_selector, location)
            time.sleep(2)
            
            # Step 3: Click the first suggestion
            print("Selecting the first suggestion from the dropdown...")
            try:
                first_suggestion = page.locator("ul#suggestions_custom > li, ul.autoSuggest__autoSuggestList > li").first
                first_suggestion.wait_for(timeout=5000)
                first_suggestion.click()
                time.sleep(1)
            except Exception as e:
                print("Suggestion click failed, pressing Enter directly instead.")
                page.keyboard.press("Enter")
            
            # Step 4: Click the Search Button
            print("Clicking Search Button...")
            try:
                search_btn = page.locator("button#searchform_search_btn, .search__btn").first
                search_btn.click(timeout=5000)
            except Exception as e:
                print("Could not find search button. Pressing Enter.")
                page.keyboard.press("Enter")
                
            print("Waiting for properties to load...")
            time.sleep(5)
            
            # Dismiss safety popup if it appears
            try:
                popup_btn = page.get_by_text("Ok, understood").first
                if popup_btn.is_visible(timeout=1000):
                    popup_btn.click()
                    time.sleep(1)
            except Exception:
                pass
                
            # Filter by Owner
            print("Applying 'Owner' filter...")
            try:
                owner_locator = page.locator('#__Owner__, .tags-and-chips__textOnly:has-text("Owner")').first
                if not owner_locator.is_visible(timeout=3000):
                    owner_locator = page.get_by_text("Owner", exact=True).first
                
                owner_locator.click()
                print("Clicked 'Owner' pill.")
                time.sleep(4)
            except Exception as e:
                print(f"Failed to click Owner filter: {e}. Will still scrape default.")
                
            # Sort by Newest first
            print("Sorting by 'Newest first'...")
            try:
                sort_dropdown = page.locator("div.list_header_sortText, div.SortBy__dropdown, i.iconS_Global_sort").first
                if not sort_dropdown.is_visible(timeout=3000):
                    sort_dropdown = page.get_by_text("Sort By", exact=False).first
                
                sort_dropdown.click()
                time.sleep(1)
                
                newest_option = page.get_by_text("Newest first", exact=False).first
                newest_option.click()
                time.sleep(3)
            except Exception as e:
                print(f"Failed to sort by Newest first: {e}")

            # Step 5: Extract Data
            print("Starting data extraction in the specified format...")
            properties_data = []
            
            # Scroll down slowly to load more properties (Lazy loading bypass)
            max_scrolls = 12
            prev_count = 0
            for i in range(max_scrolls):
                page.mouse.wheel(0, 1500)
                time.sleep(2)
                current_count = page.locator("div.tupleNew__outerTupleWrap").count()
                print(f"Scrolling... ({i+1}/{max_scrolls}) | Properties loaded: {current_count}")
                if current_count >= 100:
                    print("100+ properties loaded! Stopping scroll.")
                    break
                if current_count == prev_count and i > 3:
                    print(f"No new properties loading after {current_count} items. Stopping scroll.")
                    break
                prev_count = current_count
            
            property_cards = page.locator("div.tupleNew__outerTupleWrap").all()
            print(f"Found {len(property_cards)} properties on screen. Extracting...")
            
            for index, card in enumerate(property_cards):
                try:
                    # Property Link - Resilient logic to find the exact property URL
                    url = "N/A"
                    # Strategy 1: Find any link strictly containing -spid- (Specific Property ID)
                    spid_link = card.locator("a[href*='-spid-']").first
                    if spid_link.count() > 0:
                        url = spid_link.get_attribute("href")
                    else:
                        # Strategy 2: Fallback to multiple potential Title / Wrapper locators
                        link_elem = card.locator("a.tupleNew__propertyHeading, a.projectTuple__projectName, a#srp_tuple_property_title, a.tupleNew__propertyHeadingWrap").first
                        if link_elem.count() > 0:
                            url = link_elem.get_attribute("href")
                    
                    if url and not url.startswith("http") and url != "N/A":
                        url = "https://www.99acres.com" + url

                    # Property Code (extract from URL: e.g., spid-T89133361 -> T89133361)
                    property_code = "N/A"
                    if "-spid-" in url:
                        property_code = url.split("-spid-")[-1].split("?")[0].strip()

                    # Title used for Locality and Property Type extraction if direct fields are missing
                    title = card.locator(".tupleNew__propertyHeading").first.inner_text().strip() if card.locator(".tupleNew__propertyHeading").count() > 0 else "N/A"
                    
                    # Locality (Loatlity)
                    locality = "N/A"
                    if " in " in title:
                        locality = title.split(" in ", 1)[-1].split(",")[0].strip()
                    elif title != "N/A":
                        locality = title
                        
                    # Property Type
                    property_type = card.locator(".tupleNew__bOld").first.inner_text().strip() if card.locator(".tupleNew__bOld").count() > 0 else "N/A"
                    if property_type == "N/A" and " for " in title:
                        property_type = title.split(" for ")[0].strip()

                    # Actual Location (Actucally Locaion)
                    actual_location = card.locator(".tupleNew__locationName").first.inner_text().strip() if card.locator(".tupleNew__locationName").count() > 0 else "N/A"

                    # Price
                    price = card.locator(".tupleNew__priceValWrap").first.inner_text().strip() if card.locator(".tupleNew__priceValWrap").count() > 0 else "N/A"
                    
                    # Area/Sqft
                    area = card.locator(".tupleNew__area1Type").first.inner_text().strip() if card.locator(".tupleNew__area1Type").count() > 0 else "N/A"

                    # Possession
                    possession = "N/A"
                    
                    if property_code != "N/A" or title != "N/A" or price != "N/A":
                        # Cleaning spacing
                        price = " ".join(price.split())
                        area = " ".join(area.split())
                        
                        properties_data.append({
                            "Property Code": property_code,
                            "Owner / Broker": "Owner",
                            "Owner Name": url,  # Fallback to URL
                            "Number": url,      # Fallback to URL
                            "City": location,
                            "Loatlity": locality,
                            "Actucally Locaion": actual_location,
                            "Property Type": property_type,
                            "Sqft Areas": area,
                            "Price": price,
                            "Potral": "99acres",
                            "possession": possession
                        })
                        print(f"Extracted: {property_code} | {locality} | {price}")
                    
                except Exception as e:
                    print(f"Skipped a card due to error: {e}")
                    
            # Close this tab so we don't accumulate too many tabs
            page.close()

            # Step 6: Save to CSV and Excel
            if properties_data:
                df = pd.DataFrame(properties_data)
                
                try:
                    excel_filename = f"All_Buy_Properties_{location}_Formatted.xlsx"
                    df.to_excel(excel_filename, index=False)
                    print(f"\nSUCCESS! Structured Excel file saved: {excel_filename}")
                except Exception as e:
                    print(f"\nNote: Could not save Excel file. Reason: {e}")
                
                csv_filename = f"{location}_Extracted_Buy_Properties.csv"
                df.to_csv(csv_filename, index=False)
                print(f"SUCCESS! Saved {len(properties_data)} properties to {csv_filename}")
                
                # Check if Excel was successfully made, return Excel if so, else CSV
                try:
                    if 'excel_filename' in locals() and os.path.exists(excel_filename):
                        return excel_filename
                except:
                    pass
                    
                return csv_filename
            else:
                print("\nNo properties found or extraction failed.")
                return None

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        finally:
            print("Script finished. (Note: Your browser session is still open).")

if __name__ == "__main__":
    loc = sys.argv[1] if len(sys.argv) > 1 else "Thane"
    out_file = extract_buy_properties(loc)
    print(f"OUTPUT_FILE===={out_file}====")
