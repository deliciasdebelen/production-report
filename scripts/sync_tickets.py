from sqlalchemy import create_engine, text

pg_bak = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db_bak")
pg_live = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db")

with pg_bak.connect() as bak, pg_live.connect() as live:
    for table in ['support_tickets', 'messages']:
        try:
            bak_cols = [c[0] for c in bak.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall()]
            live_cols = [c[0] for c in live.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall()]
            common_cols = [c for c in bak_cols if c in live_cols]
            
            old_rows = bak.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
            if not old_rows: continue
            
            live_ids = {r[0] for r in live.execute(text(f'SELECT id FROM "{table}"')).fetchall()} if 'id' in common_cols else set()
            
            rows_to_insert = []
            for row in old_rows:
                if 'id' in common_cols and row['id'] in live_ids: continue
                rows_to_insert.append({col: row[col] for col in common_cols})
            
            if rows_to_insert:
                col_list_str = ", ".join([f'"{c}"' for c in common_cols])
                placeholders = ", ".join([f":{c}" for c in common_cols])
                insert_sql = text(f'INSERT INTO "{table}" ({col_list_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING')
                
                live.execute(insert_sql, rows_to_insert)
                live.commit()
                print(f"Synced {table}: {len(rows_to_insert)} rows.")
            
            # Reset seq
            if 'id' in common_cols:
                max_id = live.execute(text(f'SELECT MAX(id) FROM "{table}"')).scalar()
                if isinstance(max_id, int):
                    live.execute(text(f"SELECT setval('{table}_id_seq', {max_id + 1}, false)"))
                    live.commit()
        except Exception as e:
            live.rollback()
            print(f"Error {table}: {e}")
            
print("Done.")
