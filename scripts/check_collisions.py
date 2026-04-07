from sqlalchemy import create_engine, text

# We port-forward 5434 on 192.168.1.79 explicitly from the compose file
pg_bak = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db_bak")
pg_live = create_engine("postgresql://app_user:production_password@192.168.1.79:5434/production_db")

with pg_bak.connect() as bak, pg_live.connect() as live:
    tables_res = bak.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
    tables = [t[0] for t in tables_res if t[0] != 'alembic_version']
    
    print(f"{'Table'.ljust(35)} | {'MAX ID Bak'} | {'MIN ID Today'} | {'MAX ID Today'} | Collision?")
    print("-" * 85)
    
    for table in tables:
        try:
            # Check if it has an ID
            cols = bak.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")).fetchall()
            if 'id' not in [c[0] for c in cols]: continue

            # IDs in backup
            max_bak = bak.execute(text(f'SELECT MAX(id) FROM "{table}"')).scalar()
            
            # IDs created today in live (we assume anything created > Feb 19 is today, or just get all live IDs)
            # Actually, to be safe, get min/max ID in live that is NOT in backup
            live_ids = {r[0] for r in live.execute(text(f'SELECT id FROM "{table}"')).fetchall()}
            bak_ids = {r[0] for r in bak.execute(text(f'SELECT id FROM "{table}"')).fetchall()}
            
            new_live_ids = live_ids - bak_ids
            min_today = min(new_live_ids) if new_live_ids else None
            max_today = max(new_live_ids) if new_live_ids else None
            
            collision = False
            if max_bak and min_today:
                if min_today <= max_bak:
                    collision = True
                    
            print(f"{table.ljust(35)} | {str(max_bak).ljust(10)} | {str(min_today).ljust(12)} | {str(max_today).ljust(12)} | {collision}")
            
        except Exception as e:
            print(f"{table.ljust(35)} | ERROR: {e}")
