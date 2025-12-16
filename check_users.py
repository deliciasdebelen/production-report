import sqlite3

con = sqlite3.connect('production.db')
cur = con.cursor()
try:
    cur.execute("SELECT id, username, role, password_hash FROM users")
    users = cur.fetchall()
    print("--- Users ---")
    for u in users:
        print(f"ID: {u[0]}, User: {u[1]}, Role: {u[2]}, Hash: {u[3][:10]}...")
except Exception as e:
    print(f"Error querying users: {e}")
con.close()
