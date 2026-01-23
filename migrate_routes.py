from app.database import engine, SessionLocal
from sqlalchemy import text

def migrate():
    print("Migrating Logistics Routes...")
    with engine.connect() as conn:
        try:
            # 1. Create table logistics_routes if not exists (Handled by create_all usually, but explicit check is good)
            # Actually, let's just use raw SQL for safety in this environment
            conn.execute(text("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='logistics_routes' AND xtype='U')
            BEGIN
                CREATE TABLE logistics_routes (
                    id INTEGER IDENTITY(1,1) NOT NULL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    active BIT DEFAULT 1,
                    created_at DATETIME2 DEFAULT CURRENT_TIMESTAMP
                );
            END
            """))
            print("Table logistics_routes checked/created.")

            # 2. Add column route_id to logistics_dispatch if not exists
            # Check col
            try:
                conn.execute(text("SELECT route_id FROM logistics_dispatch WHERE 1=0"))
                print("Column route_id already exists.")
            except Exception:
                print("Adding route_id column...")
                conn.execute(text("ALTER TABLE logistics_dispatch ADD route_id INTEGER NULL REFERENCES logistics_routes(id)"))
                
            conn.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
