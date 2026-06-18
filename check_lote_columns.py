from app.external_db import engine_a
from sqlalchemy import text

def check_lote_entrada():
    try:
        with engine_a.connect() as conn:
            res = conn.execute(text("SELECT TOP 1 * FROM saLoteEntrada")).fetchone()
            if res:
                print(f"Columns in saLoteEntrada: {list(res._mapping.keys())}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_lote_entrada()
