import sys
from sqlalchemy import text
sys.path.append('/app/app')
from external_db import create_engine_for_db

trigger_sql = """
CREATE TRIGGER trg_SyncTasas_CarmalN
ON dbo.saTasa
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    -- Deletes
    DELETE target
    FROM carmal_n.dbo.snTasa target
    INNER JOIN deleted d ON target.co_mone = d.co_mone AND target.fecha = d.fecha
    WHERE NOT EXISTS (SELECT 1 FROM inserted i WHERE i.co_mone = d.co_mone AND i.fecha = d.fecha);

    -- Inserts and Updates
    MERGE carmal_n.dbo.snTasa AS target
    USING inserted AS source
    ON (target.co_mone = source.co_mone AND target.fecha = source.fecha)
    WHEN MATCHED THEN
        UPDATE SET 
            target.tasa_c = source.tasa_c,
            target.tasa_v = source.tasa_v,
            target.campo1 = source.campo1,
            target.campo2 = source.campo2,
            target.campo3 = source.campo3,
            target.campo4 = source.campo4,
            target.campo5 = source.campo5,
            target.campo6 = source.campo6,
            target.campo7 = source.campo7,
            target.campo8 = source.campo8,
            target.co_us_in = source.co_us_in,
            target.co_sucu_in = source.co_sucu_in,
            target.fe_us_in = source.fe_us_in,
            target.co_us_mo = source.co_us_mo,
            target.co_sucu_mo = source.co_sucu_mo,
            target.fe_us_mo = source.fe_us_mo,
            target.revisado = source.revisado,
            target.trasnfe = source.trasnfe
    WHEN NOT MATCHED THEN
        INSERT (co_mone, fecha, tasa_c, tasa_v, campo1, campo2, campo3, campo4, campo5, campo6, campo7, campo8, co_us_in, co_sucu_in, fe_us_in, co_us_mo, co_sucu_mo, fe_us_mo, revisado, trasnfe)
        VALUES (source.co_mone, source.fecha, source.tasa_c, source.tasa_v, source.campo1, source.campo2, source.campo3, source.campo4, source.campo5, source.campo6, source.campo7, source.campo8, source.co_us_in, source.co_sucu_in, source.fe_us_in, source.co_us_mo, source.co_sucu_mo, source.fe_us_mo, source.revisado, source.trasnfe);
END;
"""

if __name__ == "__main__":
    engine_a = create_engine_for_db('carmal_a')
    
    try:
        with engine_a.begin() as conn:
            print("Dropping existing trigger if it exists...")
            conn.execute(text("IF OBJECT_ID('trg_SyncTasas_CarmalN', 'TR') IS NOT NULL DROP TRIGGER trg_SyncTasas_CarmalN"))
        
        with engine_a.begin() as conn:
            print("Creating new synchronization trigger...")
            conn.execute(text(trigger_sql))
            
        print("Trigger created successfully.")
            
    except Exception as e:
        print(f"Error creating trigger: {e}")

