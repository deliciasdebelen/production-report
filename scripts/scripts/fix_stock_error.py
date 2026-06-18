
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.external_db import engine_a
    print("Successfully imported engine_a")
except ImportError as e:
    print(f"Failed to import engine_a: {e}")
    sys.exit(1)

def run_fix():
    # Update BOTH candidates
    guids_to_fix = [
        '850DFC1A-4283-4B92-B129-84CFAE76352E',
        'DB79E78A-EAD6-4060-B56A-54EC619F912A'
    ]
    new_stock = 24.0

    print(f"\n--- Attempting to Update Stock for {len(guids_to_fix)} records to {new_stock} ---\n")

    with engine_a.connect() as conn:
        try:
            trans = conn.begin()
            
            for guid in guids_to_fix:
                print(f"Updating GUID: {guid}")
                query = text(f"""
                    UPDATE saLoteEntrada 
                    SET stock_actual = :stock
                    WHERE rowguid = :guid
                """)
                result = conn.execute(query, {"stock": new_stock, "guid": guid})
                print(f"Rows affected: {result.rowcount}")

            trans.commit()
            print("Updates committed successfully.")

            # Verify the update
            print("\n--- Verifying Updates ---")
            for guid in guids_to_fix:
                check_query = text(f"SELECT stock_actual FROM saLoteEntrada WHERE rowguid = :guid")
                check_result = conn.execute(check_query, {"guid": guid}).fetchone()
                if check_result:
                    print(f"GUID {guid} Stock: {check_result[0]}")
                else:
                    print(f"Could not verify record {guid}.")

        except Exception as e:
            trans.rollback()
            print(f"Error executing update: {e}")
            print("Transaction rolled back.")

if __name__ == "__main__":
    run_fix()
