import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Login
s = requests.Session()
r = s.post(f"{BASE_URL}/login", data={"username": "admin", "password": "admin"})
print(f"Login: {r.status_code}, URL: {r.url}")

# 2. Get Pending
r = s.get(f"{BASE_URL}/logistics/api/production/pending")
print(f"Pending: {r.status_code}")
data = r.json()
if not data:
    print("No pending orders found.")
    exit()

order = data[0]
print(f"Order: {order['id']}, Units: {order['pt_units']}")

# 3. Confirm
payload = {
    "production_id": order['id'],
    "received_qty": order['pt_units'], # exact link
    "alert_email": ""
}
r = s.post(f"{BASE_URL}/logistics/reception/confirm", data=payload)
print(f"Confirm: {r.status_code}")
print(r.text)
