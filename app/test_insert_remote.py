
import sqlite3
import os

DB_PATH = "/app/production.db"

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"Attempting manual insert of 0000000002...")
        
        sql = """
        INSERT INTO production_planning (order_number, date, article, presentation)
        VALUES ('0000000003', '2025-01-01', 'MANUAL_TEST_3', 'TEST')
        """
        cursor.execute(sql)
        conn.commit()
        print("SUCCESS: Inserted 0000000002")
        
        # Verify
        cursor.execute("SELECT id, order_number FROM production_planning WHERE order_number='0000000002'")
        print(cursor.fetchall())
        
        # Cleanup
        # cursor.execute("DELETE FROM production_planning WHERE order_number='0000000002'")
        # conn.commit()
        
        conn.close()
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    main()
