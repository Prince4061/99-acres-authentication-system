from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import subprocess
import sys
import re

app = Flask(__name__)
app.secret_key = 'super_secret_scraper_key'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        location = request.form.get('location')
        if location:
            try:
                # Call our updated Playwright script via subprocess to avoid thread blocking/deadlocks
                print(f"Scraping requested for location: {location}")
                
                result = subprocess.run(
                    [sys.executable, "extract_data.py", location], 
                    capture_output=True, 
                    text=True,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                print("== Subprocess Output ==")
                print(result.stdout)
                if result.stderr:
                    print("== Subprocess Error ==")
                    print(result.stderr)
                
                # Check if file was successfully created and returned
                match = re.search(r'OUTPUT_FILE====(.*?)====', result.stdout)
                if match:
                    generated_file = match.group(1).strip()
                    if generated_file and generated_file != 'None' and os.path.exists(generated_file):
                        print(f"Sending back: {generated_file}")
                        return send_file(generated_file, as_attachment=True)
                
                flash('No properties found or extraction failed. Make sure your browser is running with start_chrome.bat!', 'error')
            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'error')
        else:
            flash('Please enter a location.', 'error')
            
        return redirect(url_for('index'))
        
    return render_template('index.html')

if __name__ == '__main__':
    # Running Flask with debug off so it easily binds, runs on localhost:5000
    app.run(debug=True, port=5000)
