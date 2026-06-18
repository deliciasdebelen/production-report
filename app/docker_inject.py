import json
import sqlite3
import sys

def inject_data():
    try:
        with open("/app/app/logistics_data_193.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            
        conn = sqlite3.connect("/app/production.db")
        cur = conn.cursor()
        
        for table_name, rows in data.items():
            if not rows:
                continue
            
            print(f"Injecting {len(rows)} rows into {table_name}...")
            
            for row in rows:
                columns = ', '.join(row.keys())
                placeholders = ', '.join(['?'] * len(row))
                sql = f"INSERT OR IGNORE INTO {table_name} ({columns}) VALUES ({placeholders})"
                
                cur.execute(sql, tuple(row.values()))
                
        conn.commit()
        conn.close()
        print("Successfully injected all data.")
        
    except Exception as e:
        print("Injection Error:", e)

if __name__ == "__main__":
    inject_data()
