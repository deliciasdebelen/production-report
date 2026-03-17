import sqlite3

def patch_db():
    conn = sqlite3.connect('production.db.live')
    c = conn.cursor()
    
    print("Patching user_id=1 to 58 in live DB for postgres migration...")
    
    c.execute("UPDATE inventory_headers SET user_id=58 WHERE user_id=1")
    print(f"inventory_headers: {c.rowcount} rows patched")
    
    c.execute("UPDATE support_tickets SET created_by_id=58 WHERE created_by_id=1")
    print(f"support_tickets: {c.rowcount} rows patched")
    
    conn.commit()
    conn.close()
    print("Done patching.")

if __name__ == "__main__":
    patch_db()
