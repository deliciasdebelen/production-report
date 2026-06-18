
from app.external_db import engine_a
from sqlalchemy import text

def inspect_schema():
    with engine_a.connect() as conn:
        # Use simple text execution
        result = conn.execute(text("SELECT TOP 1 * FROM saFacturaVentaReng"))
        print("Columns:", result.keys())

if __name__ == "__main__":
    inspect_schema()
