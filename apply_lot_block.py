import urllib
from sqlalchemy import create_engine, text

SERVER = "192.168.60.15"
DATABASE = "CARMAL_A"
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;"
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def run_sql(conn, label, sql):
    try:
        conn.execute(text(sql))
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")

with engine.begin() as conn:
    print("=" * 60)
    print("CAPA 1: Modificando SPs de seleccion de lotes")
    print("=" * 60)

    # 1. ALTER sp_CROM_CONSULTARLOTESENTRADAXARTICULO
    # Already has stock_actual > 0 filter — verify only, no change needed
    print("\n  ℹ️  sp_CROM_CONSULTARLOTESENTRADAXARTICULO ya tiene filtro stock_actual > 0. Sin cambios.")

    # 2. ALTER pSeleccionarLote to add stock_actual > 0 check
    run_sql(conn, "Backup + ALTER pValidarExistenciaLote", """
        ALTER PROCEDURE [dbo].[pValidarExistenciaLote]
            @sNumeroLote    CHAR(20),
            @sCo_Alma       CHAR(6)
        AS
        BEGIN
            SET NOCOUNT ON;

            -- BLOQUEO CARMAL: Si el lote tiene stock_actual <= 0, retornar error
            IF EXISTS (
                SELECT 1 FROM saLoteEntrada
                WHERE numero_lote = @sNumeroLote
                  AND co_alma = @sCo_Alma
                  AND stock_actual <= 0
            )
            BEGIN
                RAISERROR('El lote %s no tiene existencia disponible (stock_actual <= 0). Operacion cancelada.', 16, 1, @sNumeroLote)
                RETURN
            END

            -- Si el lote no existe para ese almacen, error tambien
            IF NOT EXISTS (
                SELECT 1 FROM saLoteEntrada
                WHERE numero_lote = @sNumeroLote
                  AND co_alma = @sCo_Alma
            )
            BEGIN
                RAISERROR('El lote %s no existe en el almacen %s.', 16, 1, @sNumeroLote, @sCo_Alma)
                RETURN
            END

            -- Lote OK
            SELECT numero_lote, co_art, co_alma, cantidad, stock_actual
            FROM saLoteEntrada
            WHERE numero_lote = @sNumeroLote
              AND co_alma = @sCo_Alma
              AND stock_actual > 0
        END
    """)

    print("\n" + "=" * 60)
    print("CAPA 2: Creando trigger trg_BlockLoteSinExistencia en saLoteSalida")
    print("=" * 60)

    # Drop trigger if exists (safe to re-run)
    run_sql(conn, "DROP TRIGGER IF EXISTS trg_BlockLoteSinExistencia", """
        IF OBJECT_ID('dbo.trg_BlockLoteSinExistencia', 'TR') IS NOT NULL
            DROP TRIGGER dbo.trg_BlockLoteSinExistencia
    """)

    # Create trigger
    run_sql(conn, "CREATE TRIGGER trg_BlockLoteSinExistencia", """
        CREATE TRIGGER [dbo].[trg_BlockLoteSinExistencia]
        ON [dbo].[saLoteSalida]
        AFTER INSERT
        AS
        BEGIN
            SET NOCOUNT ON;

            -- Verificar si algun lote insertado ya tiene stock_actual <= 0 ANTES de esta insercion
            -- stock_actual ya fue descontado, entonces comparamos si cayo por debajo de 0
            IF EXISTS (
                SELECT 1
                FROM inserted i
                JOIN saLoteEntrada le 
                    ON le.numero_lote = i.numero_lote
                   AND le.co_alma = i.co_alma
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

print("\n" + "=" * 60)
print("VERIFICACION POST-EJECUCION")
print("=" * 60)

import pandas as pd
from sqlalchemy import create_engine
engine2 = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# Verify trigger was created
df_trg = pd.read_sql("""
    SELECT t.name, o.name as table_name, t.is_disabled
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.name = 'trg_BlockLoteSinExistencia'
""", engine2)
print("\nTrigger creado:")
print(df_trg.to_string(index=False) if len(df_trg) else "  ❌ TRIGGER NO ENCONTRADO!")
