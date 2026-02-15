
from app.external_db import engine_a
from sqlalchemy import text

def inspect_doc():
    with engine_a.connect() as conn:
        # Check saDocumentoVenta, which acts as a master table for sales docs
        result = conn.execute(text("SELECT TOP 1 * FROM saDocumentoVenta WHERE co_tipo_doc = 'FACT'"))
        print("Columns:", result.keys())

if __name__ == "__main__":
    inspect_doc()
