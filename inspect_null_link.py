
from sqlalchemy import text
from app.external_db import engine_a

def inspect_null_link():
    with engine_a.connect() as conn:
        # Get one line with NULL tipo_doc
        q = text("SELECT TOP 1 * FROM saFacturaVentaReng WHERE tipo_doc IS NULL")
        row = conn.execute(q).fetchone()
        
        if row:
            print(f"Row found: Doc={row.doc_num}, Line={row.reng_num}, Art={row.co_art}")
            # Check Header for this doc
            q_head = text("SELECT * FROM saDocumentoVenta WHERE co_tipo_doc = 'FACT' AND nro_doc = :d")
            head = conn.execute(q_head, {"d": row.doc_num}).fetchone()
            if head:
                # Use _mapping to get keys safely if needed, or just print keys if compatible
                print(f"Header: DocOrig={head.doc_orig}") 
                # Note: doc_orig might be the column name we saw earlier 'doc_orig'
            else:
                print("Header not found in saDocumentoVenta")
        else:
            print("No rows with NULL tipo_doc found.")

if __name__ == "__main__":
    inspect_null_link()
