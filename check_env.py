import requests

def check(name, url):
    try:
        resp = requests.get(url, timeout=2)
        print(f"[{name}] Status: {resp.status_code} (OK)")
    except Exception as e:
        print(f"[{name}] Status: DOWN (Error: {str(e)})")

if __name__ == "__main__":
    check("LOCAL", "http://localhost:8000/login")
    check("PROD", "http://192.168.1.79:8000/login")
