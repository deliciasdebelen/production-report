
from sqlalchemy import text
from app.external_db import engine_a
from app.services.stock_solver import StockSolver

def apply_fix_529():
    doc_num = '0000000529'
    with engine_a.connect() as conn:
        print(f"--- Applying Fix for {doc_num} ---")
        
        # 1. Get GUID
        row = conn.execute(text("SELECT rowguid FROM saDevolucionCliente WHERE doc_num = :d"), {"d": doc_num}).fetchone()
        if not row:
            print("Doc not found")
            return
            
        guid = str(row.rowguid)
        print(f"Found GUID: {guid}")
        
        # 2. Call Fix
        print("Calling StockSolver.fix_issue...")
        # Since I simulated 'RETURN_MATH_ERROR' (Net mismatch), I use that type.
        # Rule B also applies, but let's test Math Error first.
        result = StockSolver.fix_issue(guid, "RETURN_MATH_ERROR")
        print(f"Result: {result}")
        
        # 3. Verify
        row_after = conn.execute(text("SELECT total_neto, saldo FROM saDevolucionCliente WHERE doc_num = :d"), {"d": doc_num}).fetchone()
        print(f"After Fix: Net={row_after.total_neto}, Saldo={row_after.saldo}")

if __name__ == "__main__":
    apply_fix_529()
