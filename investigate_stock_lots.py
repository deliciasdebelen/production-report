import urllib, pandas as pd
from sqlalchemy import create_engine

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

lots_str = "'L1260226-01','L1 A260304-01','L1 260302-01','L1 260227-01','L2 260302-02','L1 260212-01','L1 260218-01','L1 260219-01','L1 260211-01','AFR260224-01'"
arts_in  = "'PT01P01X012','PT01P01X013','PT01D01X019','PT01D01X011','PT01P01X017','PT04D16X001'"

# 1. Originating AJUS documents in saAjuste/saAjusteReng
df_ajus = pd.read_sql(f"""
    SELECT a.ajue_num, CONVERT(varchar,a.fecha,103) as fecha,
           a.motivo, a.anulado,
           r.co_art, r.co_alma, r.co_tipo, r.total_art
    FROM saAjuste a
    JOIN saAjusteReng r ON a.ajue_num = r.ajue_num
    WHERE r.co_art IN ({arts_in})
      AND r.co_alma = 'P1-PT'
      AND a.fecha >= '2026-02-01'
    ORDER BY r.co_art, a.fecha, a.ajue_num
""", engine)
print("=== AJUSTES (Feb-Mar 2026) POR ARTICULO EN P1-PT ===")
print(df_ajus.to_string(index=False))

# 2. saLoteSalida outflows
df_ls = pd.read_sql(f"""
    SELECT ls.numero_lote, ls.co_art, ls.co_alma, ls.tipo_doc, ls.cantidad,
           CONVERT(varchar,ls.fe_us_in,103) as fecha
    FROM saLoteSalida ls
    WHERE ls.numero_lote IN ({lots_str}) AND ls.co_alma = 'P1-PT'
    ORDER BY ls.co_art, ls.numero_lote, ls.fe_us_in
""", engine)
print("\n=== SALIDAS EN saLoteSalida ===")
print(df_ls.to_string(index=False))
