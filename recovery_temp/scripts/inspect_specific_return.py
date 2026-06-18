import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app.external_db import engine_a
except ImportError:
    # Fallback if run directly
    sys.path.append(os.path.join(os.getcwd(), '..'))
    from app.external_db import engine_a

def search_link():
    doc_ret = "0000000413"
    doc_nc = "00001343"
    
    print(f"Searching link betweeen Return {doc_ret} and NC {doc_nc}...\n")
    
    with engine_a.connect() as conn:
        # 1. Look for NC ID in Return Table
        print(f"Scanning saDevolucionCliente for '{doc_nc}'...")
        q_ret = text("SELECT * FROM saDevolucionCliente WHERE doc_num = :d")
        ret_row = conn.execute(q_ret, {"d": doc_ret}).fetchone()
        
        if ret_row:
            count = 0
            for key, val in ret_row._mapping.items():
                if str(val).strip() == doc_nc:
                    print(f"  MATCH FOUND: saDevolucionCliente.{key} = {val}")
                    count += 1
            if count == 0: print("  No direct match in Return columns.")

        # 2. Look for Return ID in NC Table
        print(f"\nScanning saDocumentoVenta for '{doc_ret}'...")
        q_nc = text("SELECT * FROM saDocumentoVenta WHERE nro_doc = :d AND co_tipo_doc = 'N/C'")
        nc_row = conn.execute(q_nc, {"d": doc_nc}).fetchone()
        
        if nc_row:
             count = 0
             for key, val in nc_row._mapping.items():
                if str(val).strip() == doc_ret:
                    print(f"  MATCH FOUND: saDocumentoVenta.{key} = {val}") 
                    count += 1
             if count == 0: print("  No direct match in NC columns.")
        else:
             print("NC Not found")

if __name__ == "__main__":
    search_link()
