"""
fase1_fix_trigger.py
=====================
1. Verifica el campo 'revisado' del lote IA1M061225 en saLoteEntrada
2. Aplica el parche a ActualizarFechaLote_OLD — neutraliza la Regla 2
   para evitar el deadlock con la generación de compuestos de Profit Plus.

ESTRATEGIA:
  - Renombrar ActualizarFechaLote_OLD → ActualizarFechaLote_OLD_20260319 (backup)
  - Crear versión corregida con Regla 2 segura (sin marcar revisado prematuramente)
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

# ─── DIAGNÓSTICO PREVIO ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("  VERIFICACIÓN PREVIA AL PARCHE")
print("="*60)

# 1. Campo revisado del lote problemático (si existe en algún almacén)
q("""
    SELECT numero_lote, co_art, co_alma,
           cantidad, stock_actual, revisado,
           CONVERT(VARCHAR,fe_us_mo,120) AS ultima_mod
    FROM saLoteEntrada
    WHERE numero_lote = 'IA1M061225'
""", "Campo revisado del lote IA1M061225")

# 2. Lotes del azúcar con revisado = 'X' (marcados como quemados)
q("""
    SELECT numero_lote, co_art, co_alma,
           cantidad, stock_actual, revisado,
           CONVERT(VARCHAR,fecha_inicio,105) AS fecha_inicio
    FROM saLoteEntrada
    WHERE co_art    = 'MPO1N000153'
      AND revisado  = 'X'
""", "Lotes del azúcar con revisado = 'X' (quemados por trigger)")

# 3. Lotes del azúcar con stock > 0 (candidatos válidos para el descargo)
q("""
    SELECT numero_lote, co_art, co_alma,
           cantidad, stock_actual, revisado,
           CONVERT(VARCHAR,fecha_inicio,105) AS fecha_inicio
    FROM saLoteEntrada
    WHERE co_art       = 'MPO1N000153'
      AND stock_actual > 0
    ORDER BY fecha_inicio DESC
""", "Lotes del azúcar disponibles (stock_actual > 0)")

# ─── BACKUP DEL TRIGGER ACTUAL ────────────────────────────────────────────────
print("\n" + "="*60)
print("  BACKUP: ActualizarFechaLote_OLD → _20260319")
print("="*60)

with engine.begin() as conn:
    ddl(conn, "Renombrar ActualizarFechaLote_OLD → ActualizarFechaLote_OLD_20260319", """
        IF OBJECT_ID('dbo.ActualizarFechaLote_OLD', 'TR') IS NOT NULL
        AND OBJECT_ID('dbo.ActualizarFechaLote_OLD_20260319', 'TR') IS NULL
            EXEC sp_rename 'dbo.ActualizarFechaLote_OLD', 'ActualizarFechaLote_OLD_20260319'
    """)

# ─── APLICAR TRIGGER PARCHEADO ────────────────────────────────────────────────
print("\n" + "="*60)
print("  APLICANDO: ActualizarFechaLote_OLD (versión corregida)")
print("  Regla 2 neutralizada — ya no marca revisado durante compuestos")
print("="*60)

with engine.begin() as conn:
    ddl(conn, "CREATE TRIGGER ActualizarFechaLote_OLD (parcheado)", """
        CREATE TRIGGER [dbo].[ActualizarFechaLote_OLD]
        ON [dbo].[saLoteEntrada]
        AFTER INSERT, UPDATE
        AS
        BEGIN
            SET NOCOUNT ON;

            -- ── REGLA 1: Manufactura (CARMAL_M → CARMAL_A) ────────────────
            -- Actualiza fecha de lote desde saAjuste cuando campo8='MANUFACTURA'
            -- INTACTA: no toca la generación de compuestos
            UPDATE l SET
                l.fecha_inicio      = a.fec_emis,
                l.fecha_expiracion  = a.fec_venc
            FROM saLoteEntrada l
            INNER JOIN inserted i
                ON l.rowguid = i.rowguid
            INNER JOIN saAjusteReng ar
                ON ar.co_art   COLLATE Latin1_General_100_CI_AI = l.co_art   COLLATE Latin1_General_100_CI_AI
               AND ar.co_alma  COLLATE Latin1_General_100_CI_AI = l.co_alma  COLLATE Latin1_General_100_CI_AI
            INNER JOIN saAjuste a
                ON a.ajus_num  = ar.ajue_num
               AND a.campo8    = 'MANUFACTURA'
               AND a.anulado   = 0
            WHERE l.stock_actual > 0
              AND l.revisado IS NULL
              AND i.revisado  IS NULL;

            -- ── REGLA 2 (DESACTIVADA — causa deadlock con generación de compuestos) ──
            -- La lógica original marcaba revisado='X' en saLoteEntrada al conectar
            -- con saArtCompuestoGenReng, lo que producía ROLLBACK silencioso en Profit.
            -- Se mantiene comentada para auditoría; reactivar solo tras validación.
            /*
            UPDATE l SET l.revisado = 'X'
            FROM saLoteEntrada l
            INNER JOIN inserted i       ON l.rowguid = i.rowguid
            INNER JOIN saAjusteReng ar  ON ar.co_art  COLLATE Latin1_General_100_CI_AI = l.co_art  COLLATE Latin1_General_100_CI_AI
                                       AND ar.co_alma COLLATE Latin1_General_100_CI_AI = l.co_alma COLLATE Latin1_General_100_CI_AI
            INNER JOIN saArtCompuestoGenReng r ON r.co_art   = ar.co_art
            INNER JOIN saArtCompuestoGen     g ON g.gene_num = r.gene_num
            WHERE r.lote_asignado = 1
              AND l.stock_actual  > 0
              AND l.revisado     IS NULL
              AND NOT EXISTS (SELECT 1 FROM deleted);
            */

        END
    """)

# ─── VERIFICACIÓN FINAL ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("  VERIFICACIÓN POST-PARCHE")
print("="*60)

q("""
    SELECT
        t.name                             AS trigger_nombre,
        o.name                             AS tabla,
        t.is_disabled,
        CONVERT(VARCHAR,t.modify_date,120) AS modificado,
        CONVERT(VARCHAR,t.create_date,120) AS creado
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.name LIKE 'ActualizarFechaLote%'
    ORDER BY t.name
""", "Estado de todos los triggers ActualizarFechaLote")

print("\n  ✅ PARCHE APLICADO: Regla 2 desactivada en ActualizarFechaLote_OLD")
print("  🧪 SIGUIENTE PASO: Reproducir 'Generar Compuesto' en Profit y verificar:")
print("     SELECT * FROM dbo._AuditLoteTemp ORDER BY fec_captura DESC;")
print("     (Debe mostrar INSERT sin DELETE — sin reverso)")
