"""
Script para inspeccionar columnas reales de saFacturaVenta en Carmal.
Ejecutar con: docker exec production-report python3 /tmp/inspect_carmal.py
"""
import sys
sys.path.insert(0, '/app')

from app.external_db import external_engine
from sqlalchemy import text

def inspect(table):
    print(f"\n=== {table} ===")
    try:
        with external_engine.connect() as conn:
            r = conn.execute(text(f"SELECT TOP 1 * FROM {table}"))
            cols = list(r.keys())
            row = r.fetchone()
            for i, c in enumerate(cols):
                val = row[i] if row else None
                print(f"  {c:40s} = {val}")
    except Exception as e:
        print(f"  ERROR: {e}")

if __name__ == "__main__":
    tables = [
        "saFacturaVenta",
        "saNotaCreditoVenta",
        "saPedidoVenta",
        "saArticulo",
        "saCliente",
        "saVendedor",
    ]
    for t in tables:
        inspect(t)
