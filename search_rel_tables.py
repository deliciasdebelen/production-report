
from sqlalchemy import text
from app.external_db import engine_a

def search_tables():
    with engine_a.connect() as conn:
        q = text("SELECT name FROM sys.tables WHERE name LIKE 'saDocumento%' OR name LIKE 'saRelacion%' OR name LIKE 'saDocRel%'")
        rows = conn.execute(q).fetchall()
        print("Found Tables:")
        for r in rows:
            print(r[0])

if __name__ == "__main__":
    search_tables()
