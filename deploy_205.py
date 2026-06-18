"""
deploy_205.py
=============
Despliega las protecciones de inventario en el servidor 192.168.1.205 (CARMAL_A).

Estrategia de seguridad:
  1. Renombra los objetos ORIGINALES con sufijo _OLD_20260319 (backup in-DB).
  2. Aplica el SP pValidarExistenciaLote modificado (Capa 1).
  3. Crea el trigger trg_BlockLoteSinExistencia (Capa 2).
  4. Verifica que los objetos quedaron correctamente instalados.

Fecha de despliegue: 2026-03-19
"""

import urllib
from sqlalchemy import create_engine, text
import pandas as pd

# ─── Configuración de conexión ────────────────────────────────────────────────
SERVER   = "192.168.1.205"
DATABASE = "CARMAL_A"
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID=PROFIT;PWD=profit;"
    f"Encrypt=yes;TrustServerCertificate=yes;"
)
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

BACKUP_SUFFIX = "_OLD_20260319"

# ─── Helpers ──────────────────────────────────────────────────────────────────
def run_sql(conn, label, sql):
    try:
        conn.execute(text(sql))
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")

def separator(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

# ─── FASE 0: Backup de objetos originales ────────────────────────────────────
separator(f"FASE 0 — Renombrando objetos originales con sufijo {BACKUP_SUFFIX}")

with engine.begin() as conn:

    # 1. Renombrar SP pValidarExistenciaLote → pValidarExistenciaLote_OLD_20260319
    run_sql(conn,
        f"Renombrar SP pValidarExistenciaLote → pValidarExistenciaLote{BACKUP_SUFFIX}",
        f"""
        IF OBJECT_ID('dbo.pValidarExistenciaLote', 'P') IS NOT NULL
        AND OBJECT_ID('dbo.pValidarExistenciaLote{BACKUP_SUFFIX}', 'P') IS NULL
        BEGIN
            EXEC sp_rename 'dbo.pValidarExistenciaLote', 'pValidarExistenciaLote{BACKUP_SUFFIX}';
        END
        ELSE IF OBJECT_ID('dbo.pValidarExistenciaLote{BACKUP_SUFFIX}', 'P') IS NOT NULL
        BEGIN
            PRINT '  ℹ️ Backup {BACKUP_SUFFIX} ya existe, no se sobreescribe.'
        END
        ELSE
        BEGIN
            PRINT '  ℹ️ SP pValidarExistenciaLote no existe en este servidor (se creará desde cero).'
        END
        """
    )

    # 2. Renombrar Trigger trg_BlockLoteSinExistencia → trg_BlockLoteSinExistencia_OLD_20260319
    #    (si ya existe uno previo — en un servidor virgen no existirá)
    run_sql(conn,
        f"Renombrar Trigger trg_BlockLoteSinExistencia → trg_BlockLoteSinExistencia{BACKUP_SUFFIX}",
        f"""
        IF OBJECT_ID('dbo.trg_BlockLoteSinExistencia', 'TR') IS NOT NULL
        AND OBJECT_ID('dbo.trg_BlockLoteSinExistencia{BACKUP_SUFFIX}', 'TR') IS NULL
        BEGIN
            EXEC sp_rename 'dbo.trg_BlockLoteSinExistencia', 'trg_BlockLoteSinExistencia{BACKUP_SUFFIX}';
        END
        ELSE IF OBJECT_ID('dbo.trg_BlockLoteSinExistencia{BACKUP_SUFFIX}', 'TR') IS NOT NULL
        BEGIN
            PRINT '  ℹ️ Backup trigger {BACKUP_SUFFIX} ya existe, no se sobreescribe.'
        END
        ELSE
        BEGIN
            PRINT '  ℹ️ Trigger no existe previamente en este servidor (se creará limpio).'
        END
        """
    )

# ─── FASE 1: SP pValidarExistenciaLote (protegido) ───────────────────────────
separator("FASE 1 — Aplicando SP pValidarExistenciaLote (Capa 1)")

with engine.begin() as conn:
    run_sql(conn, "CREATE OR ALTER pValidarExistenciaLote (con protección)", """
        CREATE OR ALTER PROCEDURE [dbo].[pValidarExistenciaLote]
            @sNumeroLote    CHAR(20),
            @sCo_Alma       CHAR(6)
        AS
        BEGIN
            SET NOCOUNT ON;

            -- BLOQUEO CARMAL: Si el lote tiene stock_actual <= 0, retornar error
            IF EXISTS (
                SELECT 1 FROM saLoteEntrada
                WHERE numero_lote = @sNumeroLote
                  AND co_alma     = @sCo_Alma
                  AND stock_actual <= 0
            )
            BEGIN
                RAISERROR(
                    'El lote %s no tiene existencia disponible (stock_actual <= 0). Operacion cancelada.',
                    16, 1, @sNumeroLote
                )
                RETURN
            END

            -- Si el lote no existe para ese almacen
            IF NOT EXISTS (
                SELECT 1 FROM saLoteEntrada
                WHERE numero_lote = @sNumeroLote
                  AND co_alma     = @sCo_Alma
            )
            BEGIN
                RAISERROR(
                    'El lote %s no existe en el almacen %s.',
                    16, 1, @sNumeroLote, @sCo_Alma
                )
                RETURN
            END

            -- Lote OK — devolver datos
            SELECT numero_lote, co_art, co_alma, cantidad, stock_actual
            FROM saLoteEntrada
            WHERE numero_lote = @sNumeroLote
              AND co_alma     = @sCo_Alma
              AND stock_actual > 0
        END
    """)

# ─── FASE 2: Trigger trg_BlockLoteSinExistencia (Capa 2) ─────────────────────
separator("FASE 2 — Creando Trigger trg_BlockLoteSinExistencia (Capa 2)")

with engine.begin() as conn:

    # Eliminar versión actual (nueva) si existe — el backup ya fue renombrado
    run_sql(conn, "DROP trigger actual si existe (post-rename)", """
        IF OBJECT_ID('dbo.trg_BlockLoteSinExistencia', 'TR') IS NOT NULL
            DROP TRIGGER dbo.trg_BlockLoteSinExistencia
    """)

    run_sql(conn, "CREATE TRIGGER trg_BlockLoteSinExistencia", """
        CREATE TRIGGER [dbo].[trg_BlockLoteSinExistencia]
        ON [dbo].[saLoteSalida]
        AFTER INSERT
        AS
        BEGIN
            SET NOCOUNT ON;

            -- Si algún lote insertado resultó con stock_actual < 0,
            -- cancelar y revertir la transacción completa
            IF EXISTS (
                SELECT 1
                FROM inserted i
                JOIN saLoteEntrada le
                    ON le.numero_lote = i.numero_lote
                   AND le.co_alma     = i.co_alma
                WHERE le.stock_actual < 0
            )
            BEGIN
                RAISERROR(
                    'BLOQUEO: El lote indicado no tiene suficiente existencia disponible. La operacion ha sido cancelada.',
                    16, 1
                )
                ROLLBACK TRANSACTION
                RETURN
            END
        END
    """)

# ─── FASE 3: Verificación final ───────────────────────────────────────────────
separator("FASE 3 — Verificación post-despliegue")

engine_v = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# Verificar SP original renombrado
df_sp_old = pd.read_sql(f"""
    SELECT name, type_desc, modify_date
    FROM sys.procedures
    WHERE name IN (
        'pValidarExistenciaLote',
        'pValidarExistenciaLote{BACKUP_SUFFIX}'
    )
    ORDER BY name
""", engine_v)
print("\n📋 Stored Procedures (SP):")
print(df_sp_old.to_string(index=False) if len(df_sp_old) else "  ❌ NINGÚN SP ENCONTRADO")

# Verificar triggers
df_trg = pd.read_sql(f"""
    SELECT t.name, o.name AS tabla, t.is_disabled, t.modify_date
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.name IN (
        'trg_BlockLoteSinExistencia',
        'trg_BlockLoteSinExistencia{BACKUP_SUFFIX}'
    )
    ORDER BY t.name
""", engine_v)
print("\n⚡ Triggers:")
print(df_trg.to_string(index=False) if len(df_trg) else "  ❌ NINGÚN TRIGGER ENCONTRADO")

print("\n" + "=" * 60)
print("✅ DESPLIEGUE EN 192.168.1.205 COMPLETADO")
print(f"   SP original  → pValidarExistenciaLote{BACKUP_SUFFIX}")
print(f"   SP nuevo     → pValidarExistenciaLote (con protección)")
print(f"   Trigger orig → trg_BlockLoteSinExistencia{BACKUP_SUFFIX}")
print(f"   Trigger nuevo→ trg_BlockLoteSinExistencia (activo en saLoteSalida)")
print("=" * 60)
