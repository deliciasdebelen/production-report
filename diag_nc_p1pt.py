"""
diag_nc_p1pt.py
================
Diagnostica por qué los 11 lotes NC en P1-PT tienen
stock_actual = 0 cuando el correcto sería negativo.

Hipótesis a validar:
  A) Las salidas están en saLoteSalida pero stock_actual no se actualizó
  B) Los lotes no existen en saLoteEntrada (nunca se registró la entrada)
  C) El trigger ActualizarFechaLote (o similar) bloqueó la actualización
  D) La cantidad de entrada era igual a la salida pero el stock quedó en 0
     en vez del valor negativo esperado
"""
import urllib
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

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

# Lotes NC con sus datos correctos
NC = [
    {'lote': 'L1260226-01',   'art': 'PT01P01X012', 'correcto': -24.0},
    {'lote': 'L1 A260304-01', 'art': 'PT01P01X013', 'correcto': -24.0},
    {'lote': 'L1 260302-01',  'art': 'PT01D01X019', 'correcto': -60.0},
    {'lote': 'L1 260227-01',  'art': 'PT01P01X012', 'correcto': -12.0},
    {'lote': 'ME260312-03',   'art': 'PT01P01X011', 'correcto':  -4.0},
    {'lote': 'L2 260302-02',  'art': 'PT01D01X011', 'correcto': -60.0},
    {'lote': 'L1 260212-01',  'art': 'PT01P01X013', 'correcto': -122.0},
    {'lote': 'L1 260218-01',  'art': 'PT01P01X013', 'correcto': -96.0},
    {'lote': 'L1 260219-01',  'art': 'PT01P01X013', 'correcto': -624.0},
    {'lote': 'L1 260211-01',  'art': 'PT01P01X017', 'correcto': -480.0},
    {'lote': 'AFR260224-01',  'art': 'PT04D16X001', 'correcto':  -7.0},
]
lotes_str = "','".join([n['lote'] for n in NC])

def q(sql, label=""):
    try:
        df = pd.read_sql(sql, engine)
        if label: print(f"\n{'='*60}\n  {label}\n{'='*60}")
        print(df.to_string(index=False) if len(df) else "  (sin resultados)")
        return df
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return None

# ─── 1. Estado actual en saLoteEntrada ───────────────────────────────────────
print("\n" + "="*60)
print("  PASO 1 — Estado de los 11 lotes en saLoteEntrada (P1-PT)")
print("="*60)
df1 = q(f"""
    SELECT
        numero_lote, tipo_doc, co_art, co_alma,
        cantidad, stock_actual, revisado,
        CONVERT(VARCHAR,fecha_inicio,105)     AS fecha_inicio,
        CONVERT(VARCHAR,fe_us_mo,120)         AS ultima_mod
    FROM saLoteEntrada
    WHERE numero_lote IN ('{lotes_str}')
      AND co_alma = 'P1-PT'
    ORDER BY numero_lote
""")

existentes = set(df1['numero_lote'].str.strip().tolist()) if df1 is not None and len(df1) > 0 else set()
todos_nc   = set(n['lote'] for n in NC)
faltantes  = todos_nc - existentes
if faltantes:
    print(f"\n  ⚠️ FALTANTES (no existen en saLoteEntrada): {sorted(faltantes)}")
else:
    print(f"\n  ✅ Los {len(NC)} lotes existen en saLoteEntrada")

# ─── 2. Salidas registradas en saLoteSalida ───────────────────────────────────
print("\n" + "="*60)
print("  PASO 2 — Salidas en saLoteSalida para los 11 lotes")
print("="*60)
df2 = q(f"""
    SELECT
        numero_lote, co_art, co_alma,
        SUM(cantidad)                    AS total_salida,
        COUNT(*)                         AS n_salidas,
        CONVERT(VARCHAR,MAX(fe_us_in),120) AS ultima_salida
    FROM saLoteSalida
    WHERE numero_lote IN ('{lotes_str}')
      AND co_alma = 'P1-PT'
    GROUP BY numero_lote, co_art, co_alma
    ORDER BY numero_lote
""")

# ─── 3. Balance: entrada vs salida vs stock_actual ───────────────────────────
print("\n" + "="*60)
print("  PASO 3 — Balance entrada vs salida vs stock_actual")
print("="*60)
df3 = q(f"""
    SELECT
        le.numero_lote,
        le.co_art,
        le.co_alma,
        le.cantidad                  AS cant_entrada,
        ISNULL(sal.total_sal, 0)     AS total_salidas,
        le.cantidad - ISNULL(sal.total_sal, 0) AS stock_calculado,
        le.stock_actual,
        le.cantidad - ISNULL(sal.total_sal, 0) - le.stock_actual AS divergencia
    FROM saLoteEntrada le
    LEFT JOIN (
        SELECT numero_lote, co_art, co_alma, SUM(cantidad) AS total_sal
        FROM saLoteSalida
        WHERE numero_lote IN ('{lotes_str}') AND co_alma = 'P1-PT'
        GROUP BY numero_lote, co_art, co_alma
    ) sal ON sal.numero_lote = le.numero_lote
          AND sal.co_art     = le.co_art
          AND sal.co_alma    = le.co_alma
    WHERE le.numero_lote IN ('{lotes_str}')
      AND le.co_alma = 'P1-PT'
    ORDER BY le.numero_lote
""")

if df3 is not None and len(df3) > 0:
    con_div = df3[abs(df3['divergencia']) > 0.001]
    print(f"\n  Lotes con divergencia (stock_actual ≠ calculado): {len(con_div)}")
    sin_sal = df3[df3['total_salidas'] == 0]
    print(f"  Lotes SIN salidas registradas:                   {len(sin_sal)}")
    if len(sin_sal) > 0:
        print(f"  → {sin_sal['numero_lote'].str.strip().tolist()}")

# ─── 4. Buscar en tablas de ajuste origen de los movimientos ─────────────────
print("\n" + "="*60)
print("  PASO 4 — Buscar documentos AJUS relacionados en saAjuste")
print("="*60)
# saAjuste tiene campo8='MANUFACTURA' o similar. Ver si algún ajuste referencia estos artículos
for art in set(n['art'] for n in NC):
    q(f"""
        SELECT TOP 5
            ar.ajue_num, ar.co_tipo, ar.co_art, ar.co_alma,
            ar.total_art, ar.lote_asignado,
            CONVERT(VARCHAR,ar.fe_us_in,120) AS registrado
        FROM saAjusteReng ar
        WHERE ar.co_art = '{art}'
          AND ar.co_alma = 'P1-PT'
        ORDER BY ar.fe_us_in DESC
    """, f"saAjusteReng — Artículo {art} en P1-PT")

# ─── 5. Revisar si el trigger ActualizarFechaLote afecta tablas P1-PT ────────
print("\n" + "="*60)
print("  PASO 5 — ¿Existen otros triggers sobre saLoteEntrada activos?")
print("="*60)
q("""
    SELECT t.name, o.name AS tabla, t.is_disabled,
           CONVERT(VARCHAR,t.modify_date,120) AS modificado
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE o.name IN ('saLoteEntrada','saLoteSalida','saAjusteReng')
      AND t.is_disabled = 0
    ORDER BY o.name, t.name
""")

# ─── 6. Verificar si stock negativo está bloqueado por restricción ────────────
print("\n" + "="*60)
print("  PASO 6 — ¿Existe CHECK constraint que impide stock_actual < 0?")
print("="*60)
q("""
    SELECT cc.name AS constraint_nombre, cc.definition, t.name AS tabla
    FROM sys.check_constraints cc
    JOIN sys.objects t ON cc.parent_object_id = t.object_id
    WHERE t.name = 'saLoteEntrada'
""")

# ─── 7. Buscar sp o procedimientos que actualizan stock en P1-PT ─────────────
print("\n" + "="*60)
print("  PASO 7 — SP que actualizan saLoteEntrada.stock_actual")
print("="*60)
q("""
    SELECT DISTINCT o.name AS sp_name,
           CONVERT(VARCHAR,o.modify_date,120) AS modificado
    FROM sys.sql_modules m
    JOIN sys.objects o ON m.object_id = o.object_id
    WHERE o.type = 'P'
      AND m.definition LIKE '%stock_actual%'
      AND m.definition LIKE '%saLoteEntrada%'
    ORDER BY o.name
""")

print(f"\n{'='*60}")
print(f"  DIAGNÓSTICO COMPLETADO — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}")
