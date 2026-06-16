import time

def extract_basic_details(page):
    """Extracts non-OTP details from the page using robust locators."""
    data = {
        "Owner Name": "Name not found",
        "Configuration": "Not Found",
        "Price": "Not Found",
        "Area": "Not Found",
        "Address": "Not Found",
        "Floor Number": "Not Found",
        "Facing": "Not Found",
        "Overlooking": "Not Found",
        "Possession in": "Not Found",
        "Position": "Not Found",
        "Properties Listed": "Not Found",
        "Localities": "Not Found",
        "Highlights": "Not Found",
        "Property Age": "Not Found",
        "Furnishing": "Not Found"
    }

    try:
        # Extract Configuration
        config_parts = []
        for sel in ["#bedRoomNum", "#bathroomNum", "#balconyNum"]:
            if page.locator(sel).count() > 0:
                config_parts.append(page.locator(sel).first.inner_text().strip())
        if config_parts:
            data["Configuration"] = ", ".join(config_parts)

        # Extract Price (it was Rent previously)
        if page.locator("#pdPrice2").count() > 0:
            data["Price"] = page.locator("#pdPrice2").first.inner_text().strip()

        # Extract Area
        if page.locator("#builtupArea_span").count() > 0:
            area_val = page.locator("#builtupArea_span").first.inner_text().strip()
            # Try to get the label like "Built-up area: " or "Carpet area: "
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
            
        # Comprehensive JS script to extract all requested grid fields, position, properties listed, and name
        js_extract_all = """
        () => {
            let res = {};
            
            // Helpful function to find text following a label by walking DOM
            function getNextTextAfterLabel(label) {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                let node;
                let foundLabel = false;
                while (node = walker.nextNode()) {
                    let text = node.nodeValue.trim();
                    if (text === '') continue;
                    
                    if (!foundLabel) {
                        if (text.toLowerCase() === label.toLowerCase() || text.toLowerCase() === label.toLowerCase() + ' :' || text.toLowerCase() === label.toLowerCase() + ':') {
                            foundLabel = true;
                        } else if (text.toLowerCase().startsWith(label.toLowerCase() + ':') || text.toLowerCase().startsWith(label.toLowerCase() + ' :')) {
                            return text.split(':')[1].replace(/[^a-zA-Z0-9 ]/g, '').trim(); 
                        }
                    } else {
                        // We found the label in the previous node! Return the first non-empty text node.
                        if (text !== 'i' && text !== '₹' && text.length > 0 && text !== ':') {
                             // Handle specific weirdness like "22 nd of 23 Floors"
                             if (label.toLowerCase() === 'floor number') {
                                 let combined = text;
                                 let checkNodes = 0;
                                 let innerWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                                 innerWalker.currentNode = node;
                                 let nextN;
                                 while ((nextN = innerWalker.nextNode()) && checkNodes < 3) {
                                     let nTxt = nextN.nodeValue.trim();
                                     if(nTxt.length > 0 && nTxt !== 'i') {
                                         if (nTxt.includes('Floor')) {
                                            combined += ' ' + nTxt;
                                            break;
                                         } else if(nTxt === 'nd' || nTxt === 'rd' || nTxt === 'th' || nTxt === 'st') {
                                             combined += nTxt;
                                         } else {
                                             combined += ' ' + nTxt;
                                         }
                                     }
                                     checkNodes++;
                                 }
                                 return combined;
                             }
                             // Clean up Furnishing
                             if (label.toLowerCase() === 'furnishing') {
                                 return text.replace(/[^a-zA-Z0-9- ]/g, '').trim();
                             }
                             return text;
                        }
                    }
                }
                return null;
            }

            // 1. Grid Items via robust Tree Walking
            let targetLabels = ['Configuration', 'Price', 'Floor Number', 'Facing', 'Overlooking', 'Possession in', 'Property Age', 'Furnishing'];
            for (let label of targetLabels) {
                let val = getNextTextAfterLabel(label);
                if (val) {
                    res[label] = val;
                }
            }

            // Address specific locator
            let addr = getNextTextAfterLabel('Address');
            if (addr) res['Address'] = addr;
            
            // Area Specific Extraction (Handles "Carpet area:" etc)
            const areaWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let aNode;
            while (aNode = areaWalker.nextNode()) {
                let aTxt = aNode.nodeValue.trim().toLowerCase();
                if (aTxt.startsWith('carpet area') || aTxt.startsWith('built-up area') || aTxt.startsWith('super built-up area') || aTxt.startsWith('plot area')) {
                     
                     // If the value is on the same node (e.g. "Carpet area: 619 sq.ft")
                     if (aTxt.includes(':') && aTxt.split(':')[1].trim().length > 0) {
                         res['Area'] = aNode.nodeValue.trim();
                         break;
                     }
                     
                     // Else, it's split across nodes
                     let combinedArea = [aNode.nodeValue.trim() + ":"];
                     let areaLimit = 0;
                     let iNode;
                     let tempWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                     tempWalker.currentNode = aNode;
                     while((iNode = tempWalker.nextNode()) && areaLimit < 10) { 
                         let v = iNode.nodeValue.trim();
                         if (v.length > 0 && v !== 'i') {
                             if (v.toLowerCase().includes('sq.ft.') || v.toLowerCase().includes('sq.m.') || v.toLowerCase().includes('sq.yd.')) {
                                 combinedArea.push(v);
                                 break;
                             } else {
                                 combinedArea.push(v);
                             }
                         }
                         areaLimit++;
                     }
                     if(combinedArea.length > 1) {
                         res['Area'] = combinedArea.join(' ').replace(/\\s+/g, ' ');
                         break;
                     }
                }
            }

            // Highlights Extraction (Specific layout for Key Highlights)
            let hlElements = document.querySelectorAll('div[class*="PremiumPdKeyHighlight__highlightContent"] span, div[class*="pd__highlightContent"] span, div[class*="PremiumPdKeyHighlight"]');
            if (hlElements.length > 0) {
                 res['Highlights'] = Array.from(hlElements)
                     .map(el => el.textContent.trim())
                     .filter(t => t.length > 3 && !t.toLowerCase().includes('view') && t !== '...' && !t.toLowerCase().includes('key highlight'))
                     .join(', ');
                     
                 // De-duplicate
                 if (res['Highlights']) {
                     res['Highlights'] = Array.from(new Set(res['Highlights'].split(', '))).join(', ');
                 }
            } else {
                 let hlContent = getNextTextAfterLabel('Key Highlights');
                 if (hlContent && !hlContent.toLowerCase().includes('key highlight')) {
                     res['Highlights'] = hlContent;
                 }
            }

            // 2. Position (Under Construction, Ready to Move)
            const pWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let pNode;
            while (pNode = pWalker.nextNode()) {
                let ptext = pNode.nodeValue.trim().toLowerCase();
                if (ptext === 'under construction') {
                    res['Position'] = 'Under Construction';
                    break;
                } else if (ptext === 'ready to move') {
                    res['Position'] = 'Ready to Move';
                    break;
                }
            }
            
            // 3. Properties Listed and Localities
            let statsWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            let sNode;
            while (sNode = statsWalker.nextNode()) {
                let txt = sNode.nodeValue.trim();
                if (txt.includes("Properties Listed:")) {
                    res['Properties Listed'] = txt.replace("Properties Listed:", "").trim();
                } else if (txt.includes("Localities :")) {
                    res['Localities'] = txt.replace("Localities :", "").trim();
                }
            }
            
            return res;
        }
        """
        
        extracted_data = page.evaluate(js_extract_all)
        
        # Merge JS extracted data with fallback data
        for key in ["Floor Number", "Facing", "Overlooking", "Possession in", "Position", "Properties Listed", "Localities", "Address", "Area", "Configuration", "Price", "Highlights", "Property Age", "Furnishing"]:
            if extracted_data.get(key) and extracted_data.get(key) != "Not Found":
                # Only overwrite if it wasn't already successfully found via exact locators, or if it's one of the new fields
                if key not in data or data[key] == "Not Found" or key in ["Floor Number", "Facing", "Overlooking", "Possession in", "Position"]:
                     data[key] = extracted_data[key]

        # Extract Owner Name
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
