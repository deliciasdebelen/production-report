import sqlite3

def create_table():
    db_path = "production.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- Creating inventory_captures table ---")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                capture_type VARCHAR NOT NULL,
                article_code VARCHAR NOT NULL,
                article_description VARCHAR NOT NULL,
                batch VARCHAR NOT NULL,
                quantity FLOAT NOT NULL,
                capture_date VARCHAR NOT NULL,
                capture_time VARCHAR NOT NULL,
                out_of_range BOOLEAN DEFAULT 0,
                user_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        print("Table inventory_captures created (if not existed).")
    except Exception as e:
        print(f"Error creating table: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_table()
