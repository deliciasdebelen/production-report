"""
Migration: Add close_comment to support_tickets + Create user_roles table
Run once on the production server.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "production.db")

def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Add close_comment to support_tickets if not exists
    cur.execute("PRAGMA table_info(support_tickets)")
    cols = [row[1] for row in cur.fetchall()]
    if "close_comment" not in cols:
        cur.execute("ALTER TABLE support_tickets ADD COLUMN close_comment TEXT")
        print("✅ Added close_comment to support_tickets")
    else:
        print("⏭️  close_comment already exists in support_tickets")

    # 2. Create user_roles table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id),
            UNIQUE(user_id, role_id)
        )
    """)
    print("✅ Ensured user_roles table exists")

    conn.commit()
    conn.close()
    print("✅ Migration complete.")

if __name__ == "__main__":
    run()
