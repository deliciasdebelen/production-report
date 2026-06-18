import urllib, pandas as pd
from sqlalchemy import create_engine, text

SERVER = "192.168.60.15"
DATABASE = "CARMAL_A"
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# === VERIFY: Check current SP definitions for the 3 target SPs ===
def check_sp_exists(sp_name):
    df = pd.read_sql(f"""
        SELECT ROUTINE_NAME, ROUTINE_TYPE
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_NAME = '{sp_name}'
    """, engine)
    return len(df) > 0

# Check if saLoteEntrada and saCobro exist in this DB
df_tables = pd.read_sql("""
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME IN ('saLoteEntrada','saLoteSalida','saAjuste')
    ORDER BY TABLE_NAME
""", engine)
print("Tables present in CARMAL_A on 192.168.60.15:")
print(df_tables.to_string(index=False))

# Verify key SPs exist
key_sps = [
    'nsa_ASIGNACIONDELOTES_Sal',
    'pValidarExistenciaLote',
    'pSeleccionarLote',
    'pSeleccionarRenglonesLote',
    'sp_CROM_CONSULTARLOTESENTRADAXARTICULO',
    'pValidarLoteStock'
]

print("\nPresence of key SPs in CARMAL_A on 192.168.60.15:")
for sp in key_sps:
    exists = check_sp_exists(sp)
    print(f"  {'✅' if exists else '❌'} {sp}: {'EXISTS' if exists else 'NOT FOUND'}")

# Also get a quick count of affected lot records
lots_str = "'L1260226-01','L1 A260304-01','L1 260302-01','L1 260227-01','L2 260302-02','L1 260212-01','L1 260218-01','L1 260219-01','L1 260211-01','AFR260224-01'"
df_lotes = pd.read_sql(f"""
    SELECT numero_lote, co_art, co_alma, tipo_doc, quantidade=cantidad, stock_actual
    FROM saLoteEntrada
    WHERE numero_lote IN ({lots_str}) AND co_alma='P1-PT'
    ORDER BY co_art, numero_lote
""", engine)
print("\nLotes afectados en CARMAL_A 192.168.60.15:")
print(df_lotes.to_string(index=False))
