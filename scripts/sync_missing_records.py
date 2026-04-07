from sqlalchemy import create_engine, text

pg_bak = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db_bak")
pg_live = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db")

with pg_bak.connect() as bak, pg_live.connect() as live:
    skip_tables = ['support_tickets', 'messages']

    tables_res = bak.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
    
    fk_priorities = [
        "roles", "users", "support_departments", "support_priorities", "support_status",
        "support_types", "logistics_routes", "ai_functionalities", "channels", "articles",
        "inventory_headers", "inventory_lines", "production_planning", "logistics_reception_production",
        "logistics_dispatch"
    ]
    
    all_tables = [t[0] for t in tables_res if t[0] != 'alembic_version' and t[0] != 'sysdiagrams']
    ordered_tables = [t for t in fk_priorities if t in all_tables] + [t for t in all_tables if t not in fk_priorities]

    for table in ordered_tables:
        if table in skip_tables: continue
        
        # Get columns in BAK
        bak_cols = [c[0] for c in bak.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall()]
        # Get columns in LIVE
        live_cols = [c[0] for c in live.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall()]
        
        common_cols = [c for c in bak_cols if c in live_cols]
        if not common_cols: continue
        
        has_id = 'id' in common_cols
        
        old_rows = bak.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
        if not old_rows: continue
        
        if has_id:
            live_ids = {r[0] for r in live.execute(text(f'SELECT id FROM "{table}"')).fetchall()}
        else:
            live_ids = set()

        rows_to_insert = []
        for row in old_rows:
            if has_id and row['id'] in live_ids:
                continue
            
            # Map only common columns
            mapped = {col: row[col] for col in common_cols}
            rows_to_insert.append(mapped)
        
        if not rows_to_insert:
            print(f"Skipping {table}: 0 new rows.")
            continue

        print(f"Syncing {table} ({len(rows_to_insert)} rows...)")
        
        col_list_str = ", ".join([f'"{c}"' for c in common_cols])
        placeholders = ", ".join([f":{c}" for c in common_cols])
        insert_sql = text(f'INSERT INTO "{table}" ({col_list_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING')
        
        try:
            live.execute(insert_sql, rows_to_insert)
            live.commit()
            print(f" -> OK: {table}")
        except Exception as e:
            live.rollback()
            print(f" -> ERROR syncing {table}: {e}")
            
    # Reset Sequences only if ID is int
    print("Resetting Sequences for INT IDs...")
    for table in ordered_tables:
        cols = [c[0] for c in bak.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall()]
        if 'id' in cols:
             max_id = live.execute(text(f'SELECT MAX(id) FROM "{table}"')).scalar()
             if isinstance(max_id, int):
                 live.execute(text(f"SELECT setval('{table}_id_seq', {max_id + 1}, false)"))
                 live.commit()

    print("SYNC COMPLETE.")
