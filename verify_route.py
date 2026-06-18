import requests
import sys

url = "http://127.0.0.1:8000/logistics/dispatch/11/print"
try:
    print(f"Checking {url}...")
    resp = requests.get(url)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        print("Success! Route is active.")
        # Optional: Print first 100 chars to confirm content
        print(resp.text[:100])
    elif resp.status_code == 404:
        print("Error: 404 Not Found")
        print(resp.json())
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text[:200])
except Exception as e:
    print(f"Connection failed: {e}")
