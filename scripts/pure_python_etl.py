import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

# SQLite connection
sqlite_path = "production.db.live"
sqlite_conn = sqlite3.connect(sqlite_path)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL connection
pg_url = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"
print(f"Connecting to PG at {pg_url}...")
pg_conn = psycopg2.connect(pg_url)
pg_cursor = pg_conn.cursor()

# Tables to migrate (ordered to respect basic FKs if any)
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

print("Starting pure Python ETL migration...")

for table in tables:
    sqlite_cursor.execute(f"SELECT * FROM {table}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"Skipping {table} (empty)")
        continue
        
    print(f"Migrating {len(rows)} rows from {table}...")
    # Check which columns exist in PostgreSQL
    pg_cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}';")
    pg_columns = {row[0] for row in pg_cursor.fetchall()}
    
    # Filter columns to only those that exist in PG
    iter_columns = rows[0].keys()
    valid_columns = [col for col in iter_columns if col in pg_columns]
    
    if not valid_columns:
        print(f"Skipping {table} (no matching columns)")
        continue
        
    col_names = ", ".join(valid_columns)
    val_placeholders = ", ".join(["%s"] * len(valid_columns))
    
    insert_query = f"INSERT INTO {table} ({col_names}) VALUES ({val_placeholders}) ON CONFLICT DO NOTHING;"
    
    data_to_insert = []
    
    # Define known boolean columns across the schema
    boolean_columns = {'active', 'is_active', 'is_annulled'}
    
    for row in rows:
        row_tuple = []
        for col in valid_columns:
            val = row[col]
            # Map user 58 to 2
            if col in ['user_id', 'created_by_id'] and val == 58:
                val = 2
                
            # Cast 1/0 to python True/False for PostgreSQL boolean columns (except users table's is_active which expects integer in this schema)
            if col in boolean_columns and val is not None:
                if not (table == "users" and col == "is_active"):
                    val = bool(int(val))
                
            row_tuple.append(val)
        data_to_insert.append(tuple(row_tuple))
    
    # Execute batch insert
    try:
        execute_batch(pg_cursor, insert_query, data_to_insert)
        pg_conn.commit()
        print(f"  -> SUCCESS")
        
        # Reset the table sequence if it has an id column
        if "id" in valid_columns:
            pg_cursor.execute(f"SELECT setval('{table}_id_seq', (SELECT MAX(id) FROM {table}));")
            pg_conn.commit()

    except Exception as e:
        print(f"  -> ERROR inserting into {table}: {e}")
        pg_conn.rollback()

sqlite_conn.close()
pg_cursor.close()
pg_conn.close()
print("Migration completed.")
