import sys
import os

# Add /app/app to the path to import external_db
sys.path.append('/app/app')

from external_db import create_engine_for_db
from sqlalchemy import text

def check_triggers(engine, table_name):
    query = text("""
    SELECT 
        sysobjects.name AS trigger_name, 
        OBJECTPROPERTY( id, 'ExecIsUpdateTrigger') AS isupdate, 
        OBJECTPROPERTY(id, 'ExecIsTriggerDisabled') AS [disabled],
        sm.definition AS trigger_content
    FROM sysobjects 
    INNER JOIN sys.tables t ON sysobjects.parent_obj = t.object_id 
    INNER JOIN sys.sql_modules sm ON sysobjects.id = sm.object_id
    WHERE sysobjects.type = 'TR' AND t.name = :table_name
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"table_name": table_name})
        triggers = result.fetchall()
        for trig in triggers:
            print(f"Trigger: {trig.trigger_name} (Disabled: {trig.disabled})")
            print(f"Content:\n{trig.trigger_content}")
            print("-" * 50)
            
if __name__ == "__main__":
    engine_a = create_engine_for_db('carmal_a')
    print("Checking triggers on carmal_a (saTasa and tasas)...")
    try:
        check_triggers(engine_a, 'saTasa')
        check_triggers(engine_a, 'tasas')
    except Exception as e:
        print(f"Error on carmal_a: {e}")
    
    engine_n = create_engine_for_db('carmal_n')
    print("\nTables in carmal_n matching 'tasa':")
    try:
        query = text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%tasa%'")
        with engine_n.connect() as conn:
            for row in conn.execute(query):
                print(row.TABLE_NAME)
    except Exception as e:
        print(f"Error on carmal_n: {e}")
