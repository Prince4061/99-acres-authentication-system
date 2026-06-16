from bs4 import BeautifulSoup
import json

def test():
    with open('temp_html_buy.txt', 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- EXTRACTING POSITION ---")
    pos_els = soup.find_all(string=lambda text: text and ('Under Construction' in text or 'Ready to move' in text or 'Possession' in text))
    for el in pos_els:
        parent = el.parent
        print(f"Text: '{el.strip()}' | Tag: {parent.name} | Class: {parent.get('class')}")

    print("\n--- EXTRACTING GRID DATA ---")
    labels = ['Area', 'Configuration', 'Price', 'Address', 'Floor Number', 'Facing', 'Overlooking', 'Possession in']
    grid_data = {}
    
    for label in labels:
        label_el = soup.find(string=lambda text: text and text.strip() == label)
        if label_el and label_el.parent:
            # Usually the value is in a sibling or a parent's sibling
            container = label_el.parent.parent
            if container:
                # Get all text in this container
                text = container.get_text(separator=' | ', strip=True)
                grid_data[label] = text

    print(json.dumps(grid_data, indent=2))

if __name__ == '__main__':
    test()
