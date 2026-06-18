
import sys
import os
from sqlalchemy import text

sys.path.append(os.getcwd())
try:
    from app.external_db import engine_a
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), '..'))
    from app.external_db import engine_a

def apply_fix():
    print("Reading sp_definition.sql...")
    try:
        with open("sp_definition.sql", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: sp_definition.sql not found. Run get_sp_def.py first.")
        return

    new_lines = []
    
    # 1. Change CREATE to ALTER
    # Handling potential formatting differences
    if lines[8].strip().startswith("CREATE   PROCEDURE"):
         lines[8] = lines[8].replace("CREATE", "ALTER")
    elif lines[8].strip().startswith("CREATE PROCEDURE"):
         lines[8] = lines[8].replace("CREATE", "ALTER")
    else:
        # Fallback search
        for i, line in enumerate(lines):
             if "CREATE   PROCEDURE" in line:
                 lines[i] = line.replace("CREATE", "ALTER")
                 break
             if "CREATE PROCEDURE" in line:
                 lines[i] = line.replace("CREATE", "ALTER")
                 break

    # 2. Scan and Remove Redundant Joins
    print("Scanning for redundant joins and usages...")
    removed_count = 0
    replacement_count = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Replace SE.numero_lote with SL.numero_lote
        if "SE.numero_lote" in line:
            lines[i] = line.replace("SE.numero_lote", "SL.numero_lote")
            replacement_count += 1

        # Target Line: LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid
        if "LEFT JOIN saLoteEntrada AS SE ON SL.rowguid_lote = SE.rowguid" in line:
             # Just disable it unconditionally as per analysis step 1140/1173
             print(f"  Removing redundant join at line {i+1}")
             lines[i] = "-- " + lines[i] # Comment out
             removed_count += 1
        
        i += 1

    print(f"Total replacements SE->SL: {replacement_count}")
    print(f"Total redundant joins removed: {removed_count}")
    
    # Normalize line endings and remove excessive blank lines for safety
    clean_lines = [line.rstrip() for line in lines] 
    full_sql = "\n".join(clean_lines)
    
    # Remove potential leading empty lines before comments/ALTER
    full_sql = full_sql.strip()

    # Write optimized SQL for inspection
    with open("sp_optimized.sql", "w", encoding="utf-8") as f:
        f.write(full_sql)
        
    # Execute
    print("\nExecuting ALTER PROCEDURE...")
    try:
        with engine_a.connect() as conn:
            with conn.begin():
                conn.execute(text(full_sql))
        print("Success! SP updated.")
    except Exception as e:
        print(f"ERROR executing SQL: {e}")
        # Identify if it is a specific SQL error
        if hasattr(e, 'orig') and hasattr(e.orig, 'args'):
             print(f"Detailed DB Error: {e.orig.args}")

if __name__ == "__main__":
    apply_fix()
