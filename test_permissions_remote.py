
import requests
import sys

BASE_URL = "http://192.168.1.79:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

def login(username, password):
    s = requests.Session()
    resp = s.post(f"{BASE_URL}/login", data={"username": username, "password": password}, allow_redirects=False)
    if "user_id" in s.cookies:
        return s
    return None

def main():
    print(f"Testing against {BASE_URL}")
    
    # 1. Login Admin
    print("Logging in as Admin...")
    s_admin = login(ADMIN_USER, ADMIN_PASS)
    if not s_admin:
        print("FATAL: Could not login as admin")
        sys.exit(1)
        
    # 2. Create Test Production User (Role 2)
    test_user = "test_prod_user"
    test_pass = "test1234"
    print(f"Creating test user '{test_user}' (Role 2)...")
    resp = s_admin.post(f"{BASE_URL}/maintenance/users", data={
        "username": test_user, "password": test_pass, "role": 2
    })
    
    if resp.status_code not in [200, 302, 303]:
        print(f"Failed to create user: {resp.status_code}")
        # Proceeding anyway just in case it exists
    
    # 3. Login as Test User
    print(f"Logging in as '{test_user}'...")
    s_test = login(test_user, test_pass)
    if not s_test:
        print("FATAL: Could not login as test user. Maybe creation failed?")
        sys.exit(1)
        
    # 4. Fetch a Planning Order to link
    print("Fetching pending planning orders...")
    try:
        r = s_test.get(f"{BASE_URL}/api/planning/pending")
        plans = r.json()
    except:
        plans = []
        
    if not plans:
        print("SKIP: No pending plans to test linking. Creating one with Admin...")
        # Create plan as admin
        r = s_admin.post(f"{BASE_URL}/api/planning", json={
            "article": "TEST",
            "presentation": "1kg",
            "units": 100,
            "date": "2025-01-07" # Future/Today
        })
        if r.status_code == 200:
            plan_id = r.json()['id']
            print(f"Created temp plan ID {plan_id}")
        else:
            print(f"Failed to create plan: {r.text}")
            sys.exit(1)
    else:
        plan_id = plans[0]['id']
        print(f"Using existing plan ID {plan_id}")

    # 5. Try to Create Production Report as Test User
    print("Attempting to CREATE Production Report as Role 2...")
    data = {
        "planning_order_id": plan_id,
        "batch_qty": 1,
        "article_type": "TEST PRODUCT",
        "kg_produced": 10.0,
        "presentation": "1kg",
        "pt_units": 10,
        "boxes": 1,
        "mp_containers": 0, "mp_caps_clean": 0, "mp_caps_dirty": 0,
        "cons_count": 0, "cons_unit_weight": 0, "cons_qty": 0,
        "mp_waste_kg": 0 
    }
    # Need to handle missing fields defaults if backend requires them in Form
    
    resp = s_test.post(f"{BASE_URL}/api/production", data=data)
    
    print(f"Response Code: {resp.status_code}")
    print(f"Response Body: {resp.text}")
    
    if resp.status_code == 200:
        print("SUCCESS: Role 2 created a report.")
    elif resp.status_code == 403:
        print("FAILURE: Role 2 received 403 Forbidden.")
    else:
        print("FAILURE: Other error.")

    # Cleanup User
    print("Cleaning up user...")
    # Find ID?
    # Get user list as admin
    # This part is tricky without an API. Maintenance page lists them.
    # We'll skip cleanup or try best effort blind delete if we knew ID.
    
if __name__ == "__main__":
    main()
