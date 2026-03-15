
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.getcwd())

try:
    from app.external_db import engine_a
    print("Successfully imported engine_a", flush=True)
except ImportError as e:
    print(f"Failed to import engine_a: {e}")
    sys.exit(1)

def fix_traslado_header():
    tras_num = '0000012073'
    target_alma = 'P1-PP'

    print(f"\n--- FIXING TRASLADO HEADER: {tras_num} ---\n", flush=True)

    with engine_a.connect() as conn:
        try:
            trans = conn.begin()
            
            # Check before
            q_check = text("SELECT alm_orig FROM saTraslado WHERE tras_num = :tnum")
            val_before = conn.execute(q_check, {"tnum": tras_num}).scalar()
            print(f"  Origin Warehouse BEFORE: '{val_before}'")
            
            if str(val_before).strip() != target_alma:
                print(f"  Updating to '{target_alma}'...")
                q_upd = text("UPDATE saTraslado SET alm_orig = :new_alma WHERE tras_num = :tnum")
                res = conn.execute(q_upd, {"new_alma": target_alma, "tnum": tras_num})
                print(f"  Rows updated: {res.rowcount}")
            else:
                print("  Already matches target. No update needed.")

            trans.commit()
            print("\n--- DONE ---")
            
            # Verify after commit
            val_after = conn.execute(q_check, {"tnum": tras_num}).scalar()
            print(f"  Origin Warehouse AFTER: '{val_after}'")

        except Exception as e:
            trans.rollback()
            print(f"Error: {e}")

if __name__ == "__main__":
    fix_traslado_header()
