
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


def inspect_alma_99():
    target_alma = 'P1-99 '
    print(f"\n--- INSPECTING ALMACEN {target_alma} ---\n", flush=True)

    with engine_a.connect() as conn:
        # 1. saLoteEntrada in 99
        print(f"Checking saLoteEntrada for co_alma='{target_alma}'...", flush=True)
        q1 = text("SELECT COUNT(*) FROM saLoteEntrada WHERE co_alma = :alma")
        c1 = conn.execute(q1, {"alma": target_alma}).scalar()
        print(f"  Count: {c1}")
        if c1 > 0:
            q1_rows = text("SELECT TOP 5 rowguid, co_art, numero_lote, co_alma, stock_actual FROM saLoteEntrada WHERE co_alma = :alma")
            for r in conn.execute(q1_rows, {"alma": target_alma}):
                print(f"    - {r.numero_lote} ({r.co_art}): Stock={r.stock_actual}")

        # 2. saLoteSalida in 99
        print(f"\nChecking saLoteSalida for co_alma='{target_alma}'...", flush=True)
        q2 = text("SELECT COUNT(*) FROM saLoteSalida WHERE co_alma = :alma")
        c2 = conn.execute(q2, {"alma": target_alma}).scalar()
        print(f"  Count: {c2}")
        if c2 > 0:
             q2_rows = text("SELECT TOP 5 rowguid, co_art, numero_lote, co_alma, cantidad FROM saLoteSalida WHERE co_alma = :alma")
             for r in conn.execute(q2_rows, {"alma": target_alma}):
                print(f"    - {r.numero_lote} ({r.co_art}): Qty={r.cantidad}")

        # 3. saStockAlmacen in 99
        print(f"\nChecking saStockAlmacen for co_alma='{target_alma}'...", flush=True)
        q3 = text("SELECT COUNT(*) FROM saStockAlmacen WHERE co_alma = :alma AND stock <> 0")
        c3 = conn.execute(q3, {"alma": target_alma}).scalar()
        print(f"  Count (Active Stock): {c3}")
        if c3 > 0:
            q3_rows = text("SELECT TOP 5 co_art, co_alma, stock FROM saStockAlmacen WHERE co_alma = :alma AND stock <> 0")
            for r in conn.execute(q3_rows, {"alma": target_alma}):
                print(f"    - {r.co_art}: Stock={r.stock}")

if __name__ == "__main__":
    inspect_alma_99()
