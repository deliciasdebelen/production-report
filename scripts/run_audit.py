import sys
import os
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DEFAULT_SERVER = "192.168.1.205"

def get_engine(db_name):
    # Driver 17 fallback logic
    driver = "ODBC Driver 17 for SQL Server"
    base_conn = (
        f"DRIVER={{{driver}}};"
        f"SERVER={DEFAULT_SERVER};"
        f"DATABASE={db_name};"
        "UID=PROFIT;"
        "PWD=profit;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    params = urllib.parse.quote_plus(base_conn)
    url = f"mssql+pyodbc:///?odbc_connect={params}"
    return create_engine(url)

AUDIT_QUERY = """
SELECT 
    a.co_art AS Codigo,
    a.art_des AS Descripcion,
    a.stock_min AS Stock_Min_Definido,
    a.stock_max AS Stock_Max_Definido,
    -- Stock Lógico en el Administrativo
    (SELECT SUM(st.total_art) FROM saAjusteReng st WHERE st.co_art = a.co_art) as Stock_Admin_Calculado,
    -- Stock Físico en Lotes de Manufactura
    ISNULL(SUM(l.stock_actual), 0) AS Total_en_Lotes,
    -- La Inconsistencia
    (ISNULL(SUM(l.stock_actual), 0) - a.stock_min) as Diferencia_Fisica
FROM saArticulo a
LEFT JOIN saLoteEntrada l ON a.co_art = l.co_art
WHERE a.maneja_lote = 1
GROUP BY a.co_art, a.art_des, a.stock_min, a.stock_max
HAVING ISNULL(SUM(l.stock_actual), 0) <> a.stock_min -- Filtra solo lo que no coincide
ORDER BY Diferencia_Fisica DESC;
"""

def run_audit(db_name="carmal_a"):
    print(f"Connecting to {db_name}...")
    try:
        engine = get_engine(db_name)
        with engine.connect() as conn:
            print("Executing query...")
            df = pd.read_sql_query(text(AUDIT_QUERY), conn)
            
            if df.empty:
                print("No inconsistencies found (Query returned 0 rows).")
            else:
                print(f"Found {len(df)} inconsistencies.")
                print(df.to_string())
                
                # Save to CSV for user
                output_csv = os.path.join(os.path.dirname(__file__), '..', 'docs', 'audit_results.csv')
                df.to_csv(output_csv, index=False)
                print(f"Results saved to {output_csv}")
                
    except Exception as e:
        print(f"Error executing audit: {e}")

if __name__ == "__main__":
    # We assume 'carmal_a' is the target as it usually contains saArticulo
    run_audit("carmal_a")
