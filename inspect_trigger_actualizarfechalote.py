"""
inspect_trigger_actualizarfechalote.py
========================================
Lee la definición exacta del trigger ActualizarFechaLote
y busca lotes relacionados con el azúcar en tablas de documentos.
"""
import urllib
import pandas as pd
from sqlalchemy import create_engine

SERVER   = "192.168.60.15"
DATABASE = "CARMAL_A"
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID=PROFIT;PWD=profit;"
    f"Encrypt=yes;TrustServerCertificate=yes;"
)
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def q(sql, label=""):
    try:
        df = pd.read_sql(sql, engine)
        if label: print(f"\n{'='*60}\n  {label}\n{'='*60}")
        if len(df) == 0:
            print("  (sin resultados)")
        else:
            print(df.to_string(index=False))
        return df
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return None

# 1. Definición del trigger deshabilitado
q("""
    SELECT OBJECT_DEFINITION(OBJECT_ID('ActualizarFechaLote')) AS definicion
""", "Definición de ActualizarFechaLote")

# 2. Definición de ActualizarFechaLote_OLD (el clon activo)
q("""
    SELECT OBJECT_DEFINITION(OBJECT_ID('ActualizarFechaLote_OLD')) AS definicion
""", "Definición de ActualizarFechaLote_OLD")

# 3. Buscar el lote en tablas relacionadas (puede estar en saCompuesto, saOrdenProduccion, saEntradaAlmacen, etc.)
for tabla in ['saDocumentoEntrada', 'saEntradaAlmacen', 'saOrdenProduccion',
              'saCompuestoReng', 'saMovimientoAlmacen', 'saEntradaReng']:
    q(f"""
        IF OBJECT_ID('dbo.{tabla}') IS NOT NULL
        BEGIN
            SELECT TOP 5 * FROM dbo.{tabla}
            WHERE (nro_lote = 'IA1M061225' OR numero_lote = 'IA1M061225')
        END
    """, f"Buscar lote IA1M061225 en {tabla}")

# 4. Buscar el lote en CUALQUIER tabla que tenga columna numero_lote o nro_lote
q("""
    SELECT DISTINCT
        t.TABLE_NAME,
        c.COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS c
    JOIN INFORMATION_SCHEMA.TABLES t ON t.TABLE_NAME = c.TABLE_NAME
    WHERE c.COLUMN_NAME IN ('nro_lote','numero_lote','nro_lot','cod_lote')
      AND t.TABLE_TYPE = 'BASE TABLE'
    ORDER BY t.TABLE_NAME
""", "Tablas con columna de lote")

# 5. Estado actual del trigger
q("""
    SELECT
        t.name, o.name AS tabla,
        t.is_disabled,
        CONVERT(VARCHAR,t.modify_date,120) AS modify_date,
        CONVERT(VARCHAR,t.create_date,120) AS create_date
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.name IN ('ActualizarFechaLote','ActualizarFechaLote_OLD')
""", "Estado de ambos triggers ActualizarFechaLote")

# 6. Movimientos hacia saLoteEntrada — buscar el artículo MPO1N000153
q("""
    SELECT TOP 20
        numero_lote, tipo_doc, co_art, co_alma,
        cantidad, stock_actual,
        CONVERT(VARCHAR,fecha_inicio,105) AS fecha_inicio,
        CONVERT(VARCHAR,fe_us_in,120)     AS registrado
    FROM saLoteEntrada
    WHERE co_art = 'MPO1N000153'
    ORDER BY fe_us_in DESC
""", "Todos los lotes del artículo MPO1N000153 en saLoteEntrada")
