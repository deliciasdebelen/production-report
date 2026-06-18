
from sqlalchemy import text
from app.external_db import engine_a

def check_tipo_doc():
    with engine_a.connect() as conn:
        q = text("""
            SELECT DISTINCT tipo_doc 
            FROM saFacturaVentaReng 
            WHERE tipo_doc LIKE 'NENT%'
        """)
        results = conn.execute(q).fetchall()
        
        print("Existing tipo_doc values starting with NENT:")
        for row in results:
            print(f"'{row.tipo_doc}'")

if __name__ == "__main__":
    check_tipo_doc()
