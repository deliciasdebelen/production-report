
from sqlalchemy import text
from app.external_db import engine_a

def check_fact_orig():
    with engine_a.connect() as conn:
        # Check specific origin columns in Reng
        q = text("""
            SELECT TOP 1 nRO_doc, co_art, num_doc_orig, tipo_doc_orig 
            FROM saFacturaVentaReng
        """)
        try:
           row = conn.execute(q).fetchone()
           if row:
               print(f"Found: {row}")
        except Exception as e:
           print(f"Error selecting origin cols: {e}")

if __name__ == "__main__":
    check_fact_orig()
