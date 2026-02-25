
from sqlalchemy import text
from app.external_db import engine_a

def inspect_returns_link():
    with engine_a.connect() as conn:
        print("--- Inspecting saDevolucionCliente (Returns) ---")
        q_ret = text("SELECT TOP 1 * FROM saDevolucionCliente WHERE co_tipo_doc = 'DEVC'") # Assuming DEVC? Or just check contents
        # Actually saDevolucionCliente is the table.
        # But let's check keys.
        try:
            result = conn.execute(text("SELECT TOP 1 * FROM saDevolucionCliente"))
            keys = result.keys()
            print(f"ALL Return Columns: {list(keys)}")
            result.fetchall()
        except Exception as e:
            print(f"Error reading Returns: {e}")

        print("\n--- Inspecting saNotaCreditoVenta (Credit Notes) ---")
        try:
             # Check if ANY N/CR comes from DEVC
             q_link = text("SELECT TOP 1 * FROM saDocumentoVenta WHERE co_tipo_doc = 'N/CR' AND doc_orig IN ('DEVC', 'DEV', 'DEVOL')")
             row_link = conn.execute(q_link).fetchone()
             
             if row_link:
                 print(f"FOUND N/CR from Return! Doc={row_link.nro_doc}, Orig={row_link.doc_orig}, NroOrig={row_link.nro_orig}")
             else:
                 print("No N/CR found with doc_orig = 'DEVC'. Checking numeric link...")
                 
                 # Check if saDevolucionCliente has a field pointing to Invoice
                 # (Use the keys printed above)

        except Exception as e:
             print(f"Error reading N/CR: {e}")

if __name__ == "__main__":
    inspect_returns_link()
