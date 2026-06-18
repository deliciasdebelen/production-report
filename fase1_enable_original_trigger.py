"""
fase1_enable_original_trigger.py
==================================
1. Habilita el trigger original ActualizarFechaLote (2023-11-24, sin Regla 2)
2. Desactiva ActualizarFechaLote_OLD_20260319 (el problemático con Regla 2)
3. Verifica el estado del lote IA1M061225 en detalle
"""
import urllib
import pandas as pd
from sqlalchemy import create_engine, text

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
        if label:
            print(f"\n{'='*60}\n  {label}\n{'='*60}")
        print(df.to_string(index=False) if len(df) else "  (sin resultados)")
        return df
    except Exception as e:
        print(f"  ❌ {label if label else 'Query'}: {e}")
        return None

def ddl(conn, label, sql):
    try:
        conn.execute(text(sql))
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")

# ─── PASO A: Habilitar el trigger original ────────────────────────────────────
print("\n" + "="*60)
print("  HABILITANDO trigger original ActualizarFechaLote")
print("="*60)

with engine.begin() as conn:
    # Habilitar el original (el bueno, de 2023)
    ddl(conn, "ENABLE TRIGGER ActualizarFechaLote ON saLoteEntrada",
        "ENABLE TRIGGER dbo.ActualizarFechaLote ON dbo.saLoteEntrada")

    # Deshabilitar el problemático backup (que tiene la Regla 2)
    ddl(conn, "DISABLE TRIGGER ActualizarFechaLote_OLD_20260319 ON saLoteEntrada",
        "DISABLE TRIGGER dbo.ActualizarFechaLote_OLD_20260319 ON dbo.saLoteEntrada")

# ─── VERIFICAR estado final de todos los triggers del lote ───────────────────
q("""
    SELECT
        t.name                             AS trigger_nombre,
        o.name                             AS tabla,
        t.is_disabled,
        CONVERT(VARCHAR,t.create_date,120) AS creado,
        CONVERT(VARCHAR,t.modify_date,120) AS modificado
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.name LIKE 'ActualizarFechaLote%'
    ORDER BY t.name
""", "Estado final de todos los triggers ActualizarFechaLote")

# ─── PASO B: Estado real del lote IA1M061225 ─────────────────────────────────
q("""
    SELECT
        numero_lote, tipo_doc, co_art, co_alma,
        cantidad, stock_actual, revisado,
        CONVERT(VARCHAR,fecha_inicio,105)     AS fecha_inicio,
        CONVERT(VARCHAR,fecha_expiracion,105) AS vencimiento,
        CONVERT(VARCHAR,fe_us_in,120)         AS ingresado,
        CONVERT(VARCHAR,fe_us_mo,120)         AS modificado
    FROM saLoteEntrada
    WHERE numero_lote = 'IA1M061225'
""", "Estado real del lote IA1M061225 (todos los almacenes)")

# ─── PASO C: Lotes del azúcar con stock disponible para usar ─────────────────
q("""
    SELECT
        numero_lote, co_alma,
        cantidad, stock_actual, revisado,
        CONVERT(VARCHAR,fecha_inicio,105)     AS fecha_inicio,
        CONVERT(VARCHAR,fecha_expiracion,105) AS vencimiento
    FROM saLoteEntrada
    WHERE co_art       = 'MPO1N000153'
      AND stock_actual > 0
    ORDER BY fecha_inicio
""", "Lotes del azúcar con stock disponible (MPO1N000153)")

print("\n  📋 RESUMEN DE ACCIONES:")
print("     ✅ ActualizarFechaLote (original 2023) → HABILITADO")
print("     ✅ ActualizarFechaLote_OLD_20260319 (con Regla 2) → DESHABILITADO")
print("     🧪 Reproducir 'Generar Compuesto' en Profit Plus")
print("     🧪 Verificar: SELECT * FROM _AuditLoteTemp ORDER BY fec_captura DESC;")
