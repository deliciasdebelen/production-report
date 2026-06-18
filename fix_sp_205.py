"""
fix_sp_205.py
=============
Crea el SP pValidarExistenciaLote en 192.168.1.205 usando
DROP + CREATE (compatible con SQL Server 2012/2014).
CREATE OR ALTER no está disponible en versiones antiguas.
"""
import urllib
from sqlalchemy import create_engine, text

SERVER   = "192.168.1.205"
DATABASE = "CARMAL_A"
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID=PROFIT;PWD=profit;"
    f"Encrypt=yes;TrustServerCertificate=yes;"
)
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def ddl(conn, label, sql):
    try:
        conn.execute(text(sql))
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")

print("\n" + "="*60)
print("  Creando SP pValidarExistenciaLote (DROP + CREATE, SQL 2012+)")
print("="*60)

with engine.begin() as conn:
    # Paso 1: DROP si existe (el original ya fue renombrado a _OLD, este DROP es del nuevo si fallo)
    ddl(conn, "DROP SP si existe version fallida", """
        IF OBJECT_ID('dbo.pValidarExistenciaLote', 'P') IS NOT NULL
            DROP PROCEDURE dbo.pValidarExistenciaLote
    """)

    # Paso 2: CREATE (sin ALTER, compatible con SQL Server 2012)
    ddl(conn, "CREATE PROCEDURE pValidarExistenciaLote", """
        CREATE PROCEDURE [dbo].[pValidarExistenciaLote]
            @sNumeroLote    CHAR(20),
            @sCo_Alma       CHAR(6)
        AS
        BEGIN
            SET NOCOUNT ON;

            -- BLOQUEO: Si el lote tiene stock_actual <= 0, retornar error
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

            -- Lote OK
            SELECT numero_lote, co_art, co_alma, cantidad, stock_actual
            FROM saLoteEntrada
            WHERE numero_lote = @sNumeroLote
              AND co_alma     = @sCo_Alma
              AND stock_actual > 0
        END
    """)

# Verificar
import pandas as pd
engine2 = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
df = pd.read_sql("""
    SELECT name, type_desc, CONVERT(VARCHAR,modify_date,120) AS modificado
    FROM sys.procedures WHERE name LIKE 'pValidarExistenciaLote%' ORDER BY name
""", engine2)
print("\n  SPs en 192.168.1.205:")
print(df.to_string(index=False))

# También verificar trigger
df2 = pd.read_sql("""
    SELECT t.name, o.name AS tabla, t.is_disabled,
           CONVERT(VARCHAR,t.modify_date,120) AS modificado
    FROM sys.triggers t JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.name LIKE 'trg_Block%' OR t.name LIKE 'ActualizarFechaLote%'
    ORDER BY t.name
""", engine2)
print("\n  Triggers en 192.168.1.205:")
print(df2.to_string(index=False) if len(df2) else "  (ninguno)")
