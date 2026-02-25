
from app.database import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        print("Checking column route_id in logistics_dispatch...")
        cols = db.execute(text("PRAGMA table_info(logistics_dispatch)")).fetchall()
        col_names = [c[1] for c in cols]
        
        if "route_id" not in col_names:
            print("Adding route_id column...")
            # Note: SQLite supports ADD COLUMN. FK support in ADD COLUMN exists in newer versions, 
            # but usually it's safer to just add the int column if strict FK isn't critical for existing rows.
            # However, we'll try to add it with the definition from models.
            try:
                db.execute(text("ALTER TABLE logistics_dispatch ADD COLUMN route_id INTEGER REFERENCES logistics_routes(id)"))
                db.commit()
                print("Done adding route_id.")
            except Exception as e:
                print(f"Standard ADD failed ({e}), trying without constraint...")
                db.execute(text("ALTER TABLE logistics_dispatch ADD COLUMN route_id INTEGER"))
                db.commit()
                print("Done adding route_id (no constraint).")
        else:
            print("Column route_id already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
