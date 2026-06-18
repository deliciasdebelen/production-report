"""
buscar_sp_lotes_carmalm.py
===========================
Busca en CARMAL_M qué SP genera los registros de lotes
visibles en la pantalla "Lotes" de Profit Plus.
Lotes con formato: 2603050846-8, 2603091030-08, etc.
"""
import urllib
import pandas as pd
from sqlalchemy import create_engine

SERVER   = "192.168.60.15"
conn_str_template = (
    "DRIVER={{ODBC Driver 17 for SQL Server}};"
    "SERVER={server};DATABASE={{db}};"
    "UID=PROFIT;PWD=profit;"
    "Encrypt=yes;TrustServerCertificate=yes;"
).format(server=SERVER)

def get_engine(db):
    cs = conn_str_template.replace("{db}", db)
    return create_engine(f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(cs)}")

def q(engine, sql, label=""):
    try:
        df = pd.read_sql(sql, engine)
        if label: print(f"\n{'='*60}\n  {label}\n{'='*60}")
        print(df.to_string(index=False) if len(df) else "  (sin resultados)")
        return df
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return None

em = get_engine("CARMAL_M")
ea = get_engine("CARMAL_A")

# ─── 1. SPs en CARMAL_M que insertan en saLoteEntrada ────────────────────────
print("\n" + "="*60)
print("  [CARMAL_M] SPs que insertan en saLoteEntrada")
print("="*60)
q(em, """
    SELECT o.name AS sp_name,
           CONVERT(VARCHAR,o.modify_date,120) AS modificado
    FROM sys.sql_modules m
    JOIN sys.objects o ON m.object_id = o.object_id
    WHERE o.type = 'P'
      AND m.definition LIKE '%saLoteEntrada%'
      AND m.definition LIKE '%INSERT%'
    ORDER BY o.name
""")

# ─── 2. SPs en CARMAL_M con 'lote' y 'stock' ────────────────────────────────
print("\n" + "="*60)
print("  [CARMAL_M] SPs que mencionan lote + stock")
print("="*60)
q(em, """
    SELECT o.name AS sp_name,
           CONVERT(VARCHAR,o.modify_date,120) AS modificado
    FROM sys.sql_modules m
    JOIN sys.objects o ON m.object_id = o.object_id
    WHERE o.type = 'P'
      AND (m.definition LIKE '%numero_lote%' OR m.definition LIKE '%LoteEntrada%')
    ORDER BY o.modify_date DESC
""")

# ─── 3. Buscar patrón de número de lote (ej. 2603050846) en CARMAL_A ─────────
# Los lotes parecen ser YYMMDD + correlativo
print("\n" + "="*60)
print("  [CARMAL_A] Lotes con patrón 2603* en saLoteEntrada")
print("="*60)
q(ea, """
    SELECT TOP 20
        numero_lote, tipo_doc, co_art, co_alma,
        cantidad, stock_actual,
        CONVERT(VARCHAR,fecha_inicio,105) AS fecha_inicio,
        CONVERT(VARCHAR,fe_us_in,120)     AS ingresado
    FROM saLoteEntrada
    WHERE numero_lote LIKE '2603%'
    ORDER BY fe_us_in DESC
""")

# ─── 4. Buscar en CARMAL_M si hay tabla propia de lotes ──────────────────────
print("\n" + "="*60)
print("  [CARMAL_M] Tablas relacionadas con lotes")
print("="*60)
q(em, """
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME LIKE '%lot%' OR TABLE_NAME LIKE '%Lot%'
      OR TABLE_NAME LIKE '%stock%' OR TABLE_NAME LIKE '%Stock%'
    ORDER BY TABLE_NAME
""")

# ─── 5. SPs en CARMAL_M con nombre que suena a generación de lotes ───────────
print("\n" + "="*60)
print("  [CARMAL_M] SPs con 'Lote' o 'Genera' en el nombre")
print("="*60)
q(em, """
    SELECT name,
           CONVERT(VARCHAR,modify_date,120) AS modificado,
           CONVERT(VARCHAR,create_date,120) AS creado
    FROM sys.procedures
    WHERE name LIKE '%Lote%'
       OR name LIKE '%Genera%'
       OR name LIKE '%Stock%'
       OR name LIKE '%Compuesto%'
    ORDER BY modify_date DESC
""")

# ─── 6. Definición de los SP más relevantes en CARMAL_M ──────────────────────
print("\n" + "="*60)
print("  [CARMAL_M] SP que generan movimientos hacia CARMAL_A")
print("="*60)
q(em, """
    SELECT DISTINCT o.name AS sp_name,
           CONVERT(VARCHAR,o.modify_date,120) AS modificado
    FROM sys.sql_modules m
    JOIN sys.objects o ON m.object_id = o.object_id
    WHERE o.type = 'P'
      AND (m.definition LIKE '%CARMAL_A%'
        OR m.definition LIKE '%carmal_a%'
        OR m.definition LIKE '%saLoteEntrada%')
    ORDER BY o.name
""")
