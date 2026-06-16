import time

def extract_basic_details(page):
    """Extracts non-OTP details from the page using exact locators."""
    data = {
        "Owner Name": "Name not found",
        "Configuration": "Not Found",
        "Rent": "Not Found",
        "Area": "Not Found",
        "Address": "Not Found",
        "Furnishing": "Not Found",
        "Available For": "Not Found",
        "Available From": "Not Found",
        "Posted By": "Not Found",
        "Properties Listed": "Not Found",
        "Localities": "Not Found"
    }

    try:
        # Extract Configuration
        config_parts = []
        for sel in ["#bedRoomNum", "#bathroomNum", "#balconyNum"]:
            if page.locator(sel).count() > 0:
                config_parts.append(page.locator(sel).first.inner_text().strip())
        if config_parts:
            data["Configuration"] = ", ".join(config_parts)

        # Extract Rent
        if page.locator("#pdPrice2").count() > 0:
            data["Rent"] = page.locator("#pdPrice2").first.inner_text().strip()

        # Extract Area
        if page.locator("#builtupArea_span").count() > 0:
            area_val = page.locator("#builtupArea_span").first.inner_text().strip()
            # Try to get the label like "Built-up area: "
            try:
                label_el = page.locator("#builtupArea_span").first.evaluate("el => el.parentElement.querySelector('.MobileText__color-black-60').innerText")
                label_el = label_el.strip() + " "
            except:
                label_el = ""
            try:
                unit_el = page.locator("#builtupArea_span").first.evaluate("el => el.parentElement.querySelector('#areaUnitSecondaryId').innerText")
            except:
                unit_el = "sq.ft."
            data["Area"] = f"{label_el}{area_val} {unit_el}".strip()

        # Extract Address
        if page.locator("td").filter(has_text="Address").count() > 0:
            addr_val = page.locator("td").filter(has_text="Address").first.evaluate("el => el.nextElementSibling ? el.nextElementSibling.innerText : ''")
            if addr_val: data["Address"] = addr_val.replace("\\n", ", ").strip()

        # Extract Furnishing
        if page.locator("#furnishingLabel").count() > 0:
            data["Furnishing"] = page.locator("#furnishingLabel").first.inner_text().strip()

        # Extract Available For
        if page.locator("#availableForLabel").count() > 0:
            data["Available For"] = page.locator("#availableForLabel").first.inner_text().strip()
            
        # Extract Available From
        try:
            avail_found = False
            if page.locator("#availableFromLabel").count() > 0:
                data["Available From"] = page.locator("#availableFromLabel").first.inner_text().strip()
                avail_found = True
            
            if not avail_found and page.locator("td").filter(has_text="Available From").count() > 0:
                avail_val = page.locator("td").filter(has_text="Available From").first.evaluate("el => el.nextElementSibling ? el.nextElementSibling.innerText : ''")
                if avail_val: 
                    data["Available From"] = avail_val.strip()
                    avail_found = True
                    
            if not avail_found:
                js_avail = """
                () => {
                    const els = Array.from(document.querySelectorAll('*')).filter(el => el.childNodes.length === 1 && el.textContent.trim() === "Available From");
                    for (let el of els) {
                        if (el.nextElementSibling) return el.nextElementSibling.innerText.trim();
                        if (el.parentElement && el.parentElement.nextElementSibling) return el.parentElement.nextElementSibling.innerText.trim();
                    }
                    return null;
                }
                """
                val = page.evaluate(js_avail)
                if val:
                    data["Available From"] = val
        except:
            pass

        # Extract Posted By and On
        if page.locator("#postedOnAndByLabel").count() > 0:
            data["Posted By"] = page.locator("#postedOnAndByLabel").first.inner_text().strip()

        # Extract Owner Info (Name, Properties Listed, Localities)
        name_selectors = [
            "#OwnerDetails div.component__primaryInfo",
            "div[style*='font-weight: 500']",
            ".AdvertiserContactDetails__advertiserName",
            ".pd_posted_by_name",
            "div.user-info-name",
            "div[class*='ContactDetails'] span"
        ]
        name_found = False
        for selector in name_selectors:
            try:
                if page.locator(selector).count() > 0:
                    name_els = page.locator(selector).all()
                    for name_el in name_els:
                        if name_el.is_visible(timeout=500):
                            opt_name = name_el.evaluate("el => Array.from(el.childNodes).filter(node => node.nodeType === 3).map(node => node.textContent).join('').trim()")
                            if not opt_name:
                                opt_name = name_el.inner_text().strip()
                            opt_name = opt_name.replace("Posted by", "").replace("POSTED BY OWNER:", "").strip()
                            if len(opt_name) > 2 and len(opt_name) < 40 and "₹" not in opt_name and "SQ.FT" not in opt_name:
                                data['Owner Name'] = opt_name
                                name_found = True
                                break
                    if name_found: break
            except: pass
             
        # Look for "Properties Listed" and "Localities"
        js_find_owner_stats = """
        () => {
            let res = {listed: "Not Found", locs: "Not Found"};
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let node;
            while (node = walker.nextNode()) {
                let txt = node.nodeValue.trim();
                if (txt.includes("Properties Listed:")) {
                    res.listed = txt.replace("Properties Listed:", "").trim();
                } else if (txt.includes("Localities :")) {
                    res.locs = txt.replace("Localities :", "").trim();
                }
            }
            return res;
        }
        """
        stats = page.evaluate(js_find_owner_stats)
        if stats.get("listed"): data["Properties Listed"] = stats["listed"]
        if stats.get("locs"): data["Localities"] = stats["locs"]

    except Exception as e:
        print(f"Error extracting details: {e}")
        
    return data

def extract_phone_number(page):
    """Extracts the phone number from the page (usually from modal after OTP/CAPTCHA)."""
    import time
    data = {"Number": "Extraction Failed"}

    # Wait briefly to allow the modal + CAPTCHA completion to update the DOM
    time.sleep(2)

    js_search = """
    () => {
        function searchInDoc(doc) {
            try {
                const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT, null, false);
                let node;
                while (node = walker.nextNode()) {
                    let text = node.nodeValue.trim();
                    // Full number: +91-XXXXXXXXXX or +91 XXXXXXXXXX
                    if (text.match(/^\\+91[-\\s]\\d{10}$/)) {
                        return text;
                    }
                    // Partial in a bigger string: grab it
                    let m = text.match(/\\+91[-\\s]\\d{10}/);
                    if (m) return m[0];
                }
            } catch(e) {}
            return null;
        }
        
        // 1. Search main page
        let result = searchInDoc(document);
        if (result) return result;
        
        // 2. Search all iframes
        for (let frame of document.querySelectorAll('iframe')) {
            try {
                let r = searchInDoc(frame.contentDocument);
                if (r) return r;
            } catch(e) {}
        }
        return null;
    }
    """

    try:
        phone = page.evaluate(js_search)
        if phone:
            data['Number'] = phone
            return data

        # Also try Playwright's built-in frame search
        for frame in page.frames:
            try:
                phone = frame.evaluate(js_search)
                if phone:
                    data['Number'] = phone
                    return data
            except:
                pass

        # Fallback: look for any element containing '+91'
        for frame in [page] + list(page.frames):
            try:
                els = frame.locator("*:has-text('+91')").all()
                for el in els:
                    txt = el.text_content().strip()
                    import re
                    m = re.search(r'\+91[-\s]\d{10}', txt)
                    if m:
                        data['Number'] = m.group(0)
                        return data
            except:
                pass

    except Exception as e:
        print(f"Error extracting phone number: {e}")

    return data

