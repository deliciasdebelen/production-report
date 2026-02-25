
from sqlalchemy import text
from app.external_db import engine_a

def inspect_ret_lines():
    with engine_a.connect() as conn:
        try:
            result = conn.execute(text("SELECT TOP 1 * FROM saDevolucionClienteReng"))
            keys = result.keys()
            print(f"Return Line Columns: {list(keys)}")
            result.fetchall()
            
            # Check if there is num_doc_orig
            if 'num_doc_orig' in keys or 'nro_doc_orig' in keys:
                 print("FOUND Origin Column in Lines!")
            else:
                 print("No num_doc_orig in Lines.")
                 
        except Exception as e:
            print(f"Error reading Return Lines: {e}")

if __name__ == "__main__":
    inspect_ret_lines()
