import urllib.request
import json
import time

try:
    print("Waiting for server wakeup...")
    time.sleep(2)
    url = "http://localhost:8000/api/debug/db-connection"
    response = urllib.request.urlopen(url)
    data = response.read().decode('utf-8')
    print("RESPONSE:", data)
except Exception as e:
    print("ERROR:", e)
