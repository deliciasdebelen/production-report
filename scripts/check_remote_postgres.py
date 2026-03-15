import sqlalchemy
from sqlalchemy import create_engine, text

POSTGRES_URL = "postgresql://app_user:production_password@192.168.1.79:5434/production_db"

def check_postgres():
    print(f"Connecting to {POSTGRES_URL}...")
    try:
        engine = create_engine(POSTGRES_URL)
        with engine.connect() as conn:
            print("SUCCESS: Connected to PostgreSQL!")
            
            # List tables
            res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in res]
            print(f"Tables in DB: {tables}")
            
            if not tables:
                print("WARNING: No tables found in public schema!")
                return
            
            # Check row counts for key tables
            for table in ['users', 'roles', 'production_reports', 'production_planning']:
                if table in tables:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f" - Table '{table}': {count} rows")
                else:
                    print(f" - Table '{table}': MISSING")
                    
    except Exception as e:
        print(f"FAILURE: Could not connect to PostgreSQL: {e}")

if __name__ == "__main__":
    check_postgres()
