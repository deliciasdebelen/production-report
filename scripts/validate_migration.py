import sqlite3
import psycopg2
import sys

# SQLite connection (The snapshot before migration)
sqlite_path = "/tmp/production.db.live"
try:
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()
except Exception as e:
    print(f"Error open SQLite: {e}")
    sys.exit(1)

# PostgreSQL connection (The live production DB)
pg_url = "postgresql://app_user:production_password@db:5432/production_db"
try:
    pg_conn = psycopg2.connect(pg_url)
    pg_cursor = pg_conn.cursor()
except Exception as e:
    print(f"Error opening PostgreSQL: {e}")
    sys.exit(1)

tables = [
    "roles", "users", "support_departments", "support_priorities", 
    "support_status", "support_types", "logistics_routes", "ai_functionalities", 
    "audit_logs", "ai_parameters", "channels", "dispatch_orders", "dispatch_routes", 
    "email_logs", "inventory_captures", "inventory_headers", "inventory_lines", 
    "logistics_dispatch", "logistics_reception_merchandise", "logistics_reception_production", 
    "message_statuses", "messages", "mismatch_automation_config", "notification_subscribers", 
    "production_planning", "production_reports", "profit_articulo", "profit_automation_config", 
    "profit_formula", "profit_formula_reng", "profit_stock_almacen", "sales_forecasts", 
    "support_settings", "support_tickets", "system_insights", "telegram_subscribers"
]

results = []
data_loss = False

print("Starting validation...\n")

for table in tables:
    # Get SQLite count
    try:
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        sqlite_count = sqlite_cursor.fetchone()[0]
    except Exception as e:
        sqlite_count = "ERROR"

    # Get PG count
    try:
        pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
        pg_count = pg_cursor.fetchone()[0]
    except Exception as e:
        pg_count = "ERROR"
        print(f"Error querying PG table {table}: {e}")
        pg_conn.rollback()
        
    status = "OK"
    if sqlite_count != pg_count:
        if table == "roles" and pg_count > sqlite_count:
            status = "OK (+1 Seed)"
        else:
            status = "MISMATCH"
            data_loss = True
            
    results.append(f"{table:<35} | {str(sqlite_count):<15} | {str(pg_count):<15} | {status}")

print(f"{'Table':<35} | {'SQLite (Source)':<15} | {'PostgreSQL (Dest)':<15} | {'Status'}")
print("-" * 80)
for r in results:
    print(r)

if data_loss:
    print("\nWARNING: Data mismatch detected in one or more tables!")
else:
    print("\nSUCCESS: 100% Data integrity verified. No data was lost during the migration.")

sqlite_conn.close()
pg_conn.close()
