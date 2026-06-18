import re
import subprocess

html = open(r'c:\Users\ovargas\Projects\production-report\app\templates\logistics\dispatch.html', encoding='utf-8').read()
script_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)

if script_match:
    js_code = script_match.group(1)
    with open('temp_script.js', 'w', encoding='utf-8') as f:
        f.write(js_code)
    
    # Let's try to run node to check syntax if available
    try:
        result = subprocess.run(['node', '-c', 'temp_script.js'], capture_output=True, text=True)
        print("Node Syntax Check:", result.stdout)
        if result.stderr:
             print("Node Syntax Error:", result.stderr)
    except FileNotFoundError:
        print("Node not found, skipping syntax check.")
else:
    print("No script tags found.")
