import sys
import os
import urllib.parse
from sqlalchemy import create_engine, inspect
import traceback

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try Driver 17 first, then 18, then generic
DRIVERS_TO_TRY = [
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 18 for SQL Server",
    "SQL Server"
]

DEFAULT_SERVER = "192.168.1.205"

def get_engine(db_name, driver):
    base_conn = (
        f"DRIVER={{{driver}}};"
        f"SERVER={DEFAULT_SERVER};"
        f"DATABASE={db_name};"
        "UID=PROFIT;"
        "PWD=profit;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    
    print(f"  Attempting with driver: {driver}")
    params = urllib.parse.quote_plus(base_conn)
    url = f"mssql+pyodbc:///?odbc_connect={params}"
    return create_engine(url)

def generate_diagram(db_name):
    print(f"\n--- Processing {db_name} ---")
    
    inspector = None
    
    for driver in DRIVERS_TO_TRY:
        try:
            engine = get_engine(db_name, driver)
            # Try to connect explicitly
            with engine.connect() as conn:
                pass
            
            # If successful, get inspector
            inspector = inspect(engine)
            print(f"  SUCCESS with {driver}")
            break
        except Exception as e:
            print(f"  FAILED with {driver}: {e}")
            # traceback.print_exc()

    if not inspector:
        print(f"Could not connect to {db_name} with any driver.")
        return

    mmd_lines = ["erDiagram"]
    
    try:
        table_names = inspector.get_table_names()
        print(f"Found {len(table_names)} tables in {db_name}")

        if not table_names:
            print("No tables found. Check permissions or connectivity.")
            return

        for table_name in table_names:
            safe_table_name = table_name.replace(" ", "_").replace("-", "_").replace(".", "_")
            
            mmd_lines.append(f"    {safe_table_name} {{")
            
            try:
                columns = inspector.get_columns(table_name)
                # Primary keys
                try:
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    pks = pk_constraint.get('constrained_columns', [])
                except:
                    pks = []

                for col in columns:
                    col_name = col['name']
                    col_type = str(col['type']).replace(" ", "_")
                    
                    modifiers = []
                    if col_name in pks:
                        modifiers.append("PK")
                    
                    modifier_str = f" {', '.join(modifiers)}" if modifiers else ""
                    mmd_lines.append(f"        {col_type} {col_name}{modifier_str}")
                    
            except Exception as e:
                print(f"Error inspecting table {table_name}: {e}")
                mmd_lines.append(f"        string error_inspecting")

            mmd_lines.append("    }")

        # Relationships
        print("Inspecting relationships (this might take a moment)...")
        for table_name in table_names:
            safe_source = table_name.replace(" ", "_").replace("-", "_").replace(".", "_")
            try:
                fks = inspector.get_foreign_keys(table_name)
                for fk in fks:
                    target_table = fk['referred_table']
                    safe_target = target_table.replace(" ", "_").replace("-", "_").replace(".", "_")
                    mmd_lines.append(f"    {safe_target} ||--o{{ {safe_source} : \"has\"")
            except Exception:
                pass

        output_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{db_name}_schema.mmd")

        with open(output_file, 'w') as f:
            f.write("\n".join(mmd_lines))
        
        print(f"Diagram for {db_name} generated at: {output_file}")
        
    except Exception as e:
        print(f"Critical error during introspection: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    generate_diagram("carmal_m")
    generate_diagram("carmal_a")
