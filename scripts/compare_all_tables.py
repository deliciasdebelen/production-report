from sqlalchemy import create_engine, text

pg_bak = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db_bak")
pg_live = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db")

with pg_bak.connect() as bak, pg_live.connect() as live:
    tables_res = bak.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
    tables = [t[0] for t in tables_res if t[0] not in ('alembic_version', 'sysdiagrams')]
    
    print(f"{'Table'.ljust(35)} | {'Bak Count'.rjust(10)} | {'Live Count'.rjust(10)} | {'Missing IDs'}")
    print("-" * 80)
    
    for table in tables:
        try:
            bak_count = bak.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            live_count = live.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            
            cols = bak.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall()
            col_names = [c[0] for c in cols]
            
            missing_ids_info = "N/A"
            if 'id' in col_names:
                bak_ids = {r[0] for r in bak.execute(text(f'SELECT id FROM "{table}"')).fetchall()}
                live_ids = {r[0] for r in live.execute(text(f'SELECT id FROM "{table}"')).fetchall()}
                missing_ids = bak_ids - live_ids
                if missing_ids:
                    missing_ids_info = f"{len(missing_ids)} MISSING! (e.g. {list(missing_ids)[:3]})"
                else:
                    missing_ids_info = "0 missing"
            else:
                if bak_count > live_count:
                     missing_ids_info = f"{bak_count - live_count} missing rows!"
                else:
                     missing_ids_info = "0 missing rows"
                    
            print(f"{table.ljust(35)} | {str(bak_count).rjust(10)} | {str(live_count).rjust(10)} | {missing_ids_info}")
            
        except Exception as e:
            print(f"{table.ljust(35)} | ERROR: {e}")
