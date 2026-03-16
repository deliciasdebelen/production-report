import sqlite3
import sys

def main():
    try:
        conn = sqlite3.connect('/tmp/production_sqlite_backup.db')
        c = conn.cursor()
        
        print("--- inventory_headers ---")
        c.execute('SELECT id, user_id FROM inventory_headers')
        for row in c.fetchall():
            print(row)
            
        print("--- support_tickets ---")
        c.execute('SELECT id, created_by_id FROM support_tickets')
        for row in c.fetchall():
            print(row)
            
        conn.close()
    except Exception as e:
        print("ERROR:", e)

if __name__ == '__main__':
    main()
