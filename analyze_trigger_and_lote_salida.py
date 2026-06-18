import urllib, pandas as pd
from sqlalchemy import create_engine, text

conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

lots_str = "'L1260226-01','L1 A260304-01','L1 260302-01','L1 260227-01','L2 260302-02','L1 260212-01','L1 260218-01','L1 260219-01','L1 260211-01','AFR260224-01'"
arts_in  = "'PT01P01X012','PT01P01X013','PT01D01X019','PT01D01X011','PT01P01X017','PT04D16X001'"

# === PART 1: TRIGGERS on saLoteEntrada ===
print("=" * 70)
print("PARTE 1: TRIGGERS SOBRE saLoteEntrada")
print("=" * 70)

df_trg = pd.read_sql("""
    SELECT t.name AS trigger_name,
           o.name AS table_name,
           t.is_disabled,
           t.is_instead_of_trigger,
           CASE WHEN t.is_instead_of_trigger = 1 THEN 'INSTEAD OF'
                ELSE 'AFTER' END AS tipo_trigger,
           m.definition
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    JOIN sys.sql_modules m ON t.object_id = m.object_id
    WHERE o.name IN ('saLoteEntrada', 'saLoteSalida')
    ORDER BY o.name, t.name
""", engine)

if len(df_trg) == 0:
    print("No se encontraron triggers en saLoteEntrada ni saLoteSalida")
else:
    for _, row in df_trg.iterrows():
        print(f"\nTrigger: {row['trigger_name']} | Tabla: {row['table_name']} | Tipo: {row['tipo_trigger']} | Deshabilitado: {row['is_disabled']}")
        print("-" * 60)
        print(row['definition'])

# === PART 2: SPs that UPDATE saLoteEntrada ===
print("\n" + "=" * 70)
print("PARTE 2: STORED PROCEDURES QUE ACTUALIZAN saLoteEntrada")
print("=" * 70)

df_sp = pd.read_sql("""
    SELECT r.ROUTINE_NAME, r.ROUTINE_TYPE,
           r.ROUTINE_DEFINITION
    FROM INFORMATION_SCHEMA.ROUTINES r
    WHERE r.ROUTINE_DEFINITION LIKE '%saLoteEntrada%'
      AND r.ROUTINE_DEFINITION LIKE '%stock_actual%'
    ORDER BY r.ROUTINE_NAME
""", engine)

if len(df_sp) == 0:
    print("Ningun SP encontrado que actualice stock_actual en saLoteEntrada")
else:
    for _, row in df_sp.iterrows():
        print(f"\n{'='*50}")
        print(f"SP: {row['ROUTINE_NAME']} ({row['ROUTINE_TYPE']})")
        print(f"{'='*50}")
        # Print only the relevant lines around stock_actual
        lines = row['ROUTINE_DEFINITION'].split('\n')
        for i, line in enumerate(lines):
            if 'stock_actual' in line.lower() or 'stockactual' in line.lower():
                start = max(0, i-3)
                end = min(len(lines), i+4)
                print(f"... líneas {start}-{end}:")
                print('\n'.join(lines[start:end]))
                print("...")

# === PART 3: saLoteSalida movements AFTER stock_actual reached 0 ===
print("\n" + "=" * 70)
print("PARTE 3: SALIDAS EN saLoteSalida CUANDO STOCK YA ERA 0")
print("=" * 70)
print("(Analisis: suma de salidas vs cantidad original del lote)")

df_analysis = pd.read_sql(f"""
    SELECT 
        le.numero_lote,
        le.co_art,
        le.tipo_doc as tipo_doc_origen,
        le.cantidad as cant_original,
        le.stock_actual as stock_actual_hoy,
        ISNULL(SUM(ls.cantidad), 0) as total_consumido_salidas,
        le.cantidad - ISNULL(SUM(ls.cantidad), 0) as stock_teorico_calculado
    FROM saLoteEntrada le
    LEFT JOIN saLoteSalida ls 
        ON ls.numero_lote = le.numero_lote 
       AND ls.co_alma = le.co_alma
    WHERE le.numero_lote IN ({lots_str})
      AND le.co_alma = 'P1-PT'
      AND le.tipo_doc = 'AJUS'
    GROUP BY le.numero_lote, le.co_art, le.tipo_doc, le.cantidad, le.stock_actual
    ORDER BY le.co_art, le.numero_lote
""", engine)

print(df_analysis.to_string(index=False))

print("\n--- INTERPRETACION ---")
for _, row in df_analysis.iterrows():
    diff = row['stock_teorico_calculado']
    if diff < 0:
        print(f"[ALERTA] {row['numero_lote']} ({row['co_art']}): El total consumido supera la cantidad original en {abs(diff):.0f} unidades. Stock deberia ser {diff:.0f}")
    elif diff == 0:
        print(f"[OK] {row['numero_lote']} ({row['co_art']}): Stock teorico coincide con 0.")
    else:
        print(f"[REVISAR] {row['numero_lote']} ({row['co_art']}): Quedan {diff:.0f} unidades teoricas pero stock_actual es {row['stock_actual_hoy']}")
