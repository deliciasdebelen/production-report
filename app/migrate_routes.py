from app.database import engine, SessionLocal
from sqlalchemy import text

def migrate():
    print("Migrating Logistics Routes (SQLite)...")
    with engine.connect() as conn:
        try:
            # 1. Create table logistics_routes
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS logistics_routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("Table logistics_routes checked/created.")

            # 2. Add column route_id to logistics_dispatch if not exists
            # SQLite doesn't have IF NOT EXISTS for columns easily, so we try/except
            try:
                conn.execute(text("SELECT route_id FROM logistics_dispatch LIMIT 1"))
                print("Column route_id already exists.")
            except Exception:
                print("Adding route_id column...")
                # SQLite ALTER TABLE ADD COLUMN
                conn.execute(text("ALTER TABLE logistics_dispatch ADD COLUMN route_id INTEGER REFERENCES logistics_routes(id)"))
                
            conn.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
