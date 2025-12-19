import urllib.request
import json
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def get_json(url):
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode()), response.getcode()
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        print(f"Connection error: {e}")
        return None, 0

def test_navigation():
    print("--- Testing Navigation Endpoints (urllib) ---")
    
    # 1. Test Latest
    latest, code = get_json(f"{BASE_URL}/api/planning/latest")
    if code == 200:
        print(f"✅ Latest Plan Found: ID={latest.get('id')}, Order={latest.get('order_number')}")
        latest_id = latest.get('id')
    else:
        print(f"❌ Latest Plan Failed: {code}")
        # Try finding ANY plan if latest fails, maybe DB is empty?
        # But user said "does not work", implying they might have data.
        return

    # 2. Test Navigate Prev
    url = f"{BASE_URL}/api/planning/{latest_id}/navigate?direction=prev"
    prev, code = get_json(url)
    if code == 200:
        print(f"✅ Prev Plan Found: ID={prev.get('id')}")
    elif code == 404:
        print("⚠️ No previous record (Valid 404)")
    else:
        print(f"❌ Prev Plan Error: {code}")

    # 3. Test Navigate Next
    url = f"{BASE_URL}/api/planning/{latest_id}/navigate?direction=next"
    next_p, code = get_json(url)
    if code == 404:
        print("✅ Next Plan Correctly 404 (No next record for latest)")
    elif code == 200:
         print(f"❓ Next Plan Found: ID={next_p.get('id')}")
    else:
        print(f"❌ Next Plan Error: {code}")

if __name__ == "__main__":
    test_navigation()
