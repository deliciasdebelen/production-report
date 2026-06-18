import paramiko
import sqlite3
import json
import os

def fetch_and_extract():
    try:
        print("Connecting to 192.168.1.193...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.1.193", 22, "administrador", "GRW7czL3*")
        
        sftp = client.open_sftp()
        print("Downloading production.db...")
        sftp.get("/home/administrador/production-report/production.db", "production_193.db")
        sftp.close()
        client.close()
        
        print("Extracting logistics tables...")
        conn = sqlite3.connect("production_193.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        tables = [
            "logistics_dispatch",
            "logistics_reception_merchandise",
            "logistics_reception_production"
        ]
        
        extracted_data = {}
        for table in tables:
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                extracted_data[table] = [dict(row) for row in rows]
                print(f"Extracted {len(rows)} rows from {table}")
            except sqlite3.OperationalError as e:
                print(f"Table {table} might not exist: {e}")
                
        with open("logistics_data_193.json", "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=4, default=str)
            
        conn.close()
        print("Data extraction complete. Saved to logistics_data_193.json")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    fetch_and_extract()
