"""
fase1_validar_trigger.py
=========================
Lee la definición completa del trigger ActualizarFechaLote_OLD
para validar si su lógica es correcta y completa.
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

# 1. Leer definición completa de ambos triggers
for nombre in ['ActualizarFechaLote_OLD', 'ActualizarFechaLote']:
    print(f"\n{'='*64}")
    print(f"  DEFINICIÓN: {nombre}")
    print(f"{'='*64}")
    try:
        df = pd.read_sql(
            f"SELECT OBJECT_DEFINITION(OBJECT_ID('{nombre}')) AS definicion",
            engine
        )
        raw = df['definicion'].iloc[0]
        if raw:
            # Limpiar escape sequences para lectura humana
            print(raw.replace('\\r\\n', '\n').replace('\\t', '    '))
        else:
            print("  (definición vacía o NULL)")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# 2. También ver si existe saAjuste (tabla mencionada en la definición del trigger original)
print(f"\n{'='*64}")
print("  Verificar tabla saAjuste (referenciada por ActualizarFechaLote)")
print(f"{'='*64}")
try:
    df2 = pd.read_sql("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE 'saAjuste%'
        ORDER BY TABLE_NAME
    """, engine)
    print(df2.to_string(index=False))
except Exception as e:
    print(f"  ❌ {e}")

# 3. Ver qué lotes de MPO1N000153 existen en cualquier almacén
print(f"\n{'='*64}")
print("  Todos los lotes de MPO1N000153 (cualquier almacén / tipo_doc)")
print(f"{'='*64}")
try:
    df3 = pd.read_sql("""
        SELECT numero_lote, tipo_doc, co_art, co_alma,
               cantidad, stock_actual,
               CONVERT(VARCHAR,fecha_inicio,105)      AS fecha_inicio,
               CONVERT(VARCHAR,fecha_expiracion,105)  AS vencimiento,
               CONVERT(VARCHAR,fe_us_in,120)          AS ingresado
        FROM saLoteEntrada
        WHERE co_art = 'MPO1N000153'
        ORDER BY fecha_inicio DESC
    """, engine)
    if len(df3):
        print(df3.to_string(index=False))
    else:
        print("  ⚠️ NINGÚN lote registrado para MPO1N000153 en toda la BD")
except Exception as e:
    print(f"  ❌ {e}")

# 4. Buscar el lote en saAjuste (tabla de ajustes cabecera)
print(f"\n{'='*64}")
print("  Buscar referencias a lote IA1M061225 en saAjuste")
print(f"{'='*64}")
try:
    df4 = pd.read_sql("""
        SELECT TOP 10 *
        FROM saAjuste
        WHERE campo8 = 'MANUFACTURA'
           OR ajus_num LIKE '%IA1M061225%'
        ORDER BY fec_emis DESC
    """, engine)
    print(df4.to_string(index=False) if len(df4) else "  (sin resultados)")
except Exception as e:
    print(f"  ❌ {e}")
