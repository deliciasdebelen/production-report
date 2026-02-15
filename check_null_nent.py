
from sqlalchemy import text
from app.external_db import engine_a

def check_null_nent():
    with engine_a.connect() as conn:
        # Check if there are invoice lines with NULL tipo_doc 
        # that might correspond to a Delivery Note (NENT) logic?
        # In Profit, usually if an Invoice is from NENT, the line HAS tipo_doc='NENT'.
        # If it's NULL, it's a direct invoice.
        
        q = text("""
            SELECT COUNT(*) 
            FROM saFacturaVentaReng 
            WHERE tipo_doc IS NULL
        """)
        count_null = conn.execute(q).scalar()
        print(f"Lines with tipo_doc NULL: {count_null}")
        
        q2 = text("""
            SELECT COUNT(*) 
            FROM saFacturaVentaReng 
            WHERE tipo_doc = 'NENT'
        """)
        count_nent = conn.execute(q2).scalar()
        print(f"Lines with tipo_doc 'NENT': {count_nent}")

if __name__ == "__main__":
    check_null_nent()
