
from sqlalchemy import text
from app.external_db import engine_a

def check_header_nent():
    with engine_a.connect() as conn:
        q = text("""
            SELECT COUNT(*) 
            FROM saFacturaVentaReng FVR
            JOIN saDocumentoVenta FV ON FVR.doc_num = FV.nro_doc AND FV.co_tipo_doc = 'FACT'
            WHERE FVR.tipo_doc IS NULL
            AND (FV.doc_orig = 'NENT' OR FV.comentario LIKE '%Ent%') 
            -- Identifying NENT origin via doc_orig or comment if schematic link is weak
        """)
        # Note: doc_orig might be 'N/E' or 'NENT'.
        
        # Let's verify what values doc_orig takes first
        q_vals = text("SELECT DISTINCT doc_orig FROM saDocumentoVenta WHERE co_tipo_doc='FACT'")
        print("Doc Orig values:")
        for r in conn.execute(q_vals).fetchall():
            print(f"'{r.doc_orig}'")
            
    # Then run the count once we know the value

if __name__ == "__main__":
    check_header_nent()
