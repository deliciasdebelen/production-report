import sys
import os
import urllib.parse
from sqlalchemy import create_engine, inspect

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DEFAULT_SERVER = "192.168.1.205"

def get_engine(db_name):
    # Driver 17 fallback logic
    driver = "ODBC Driver 17 for SQL Server"
    base_conn = (
        f"DRIVER={{{driver}}};"
        f"SERVER={DEFAULT_SERVER};"
        f"DATABASE={db_name};"
        "UID=PROFIT;"
        "PWD=profit;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    params = urllib.parse.quote_plus(base_conn)
    url = f"mssql+pyodbc:///?odbc_connect={params}"
    return create_engine(url)

def generate_dbml(db_name):
    print(f"Connecting to {db_name}...")
    try:
        engine = get_engine(db_name)
        inspector = inspect(engine)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    dbml_lines = [f"Project {db_name} {{", "  database_type: 'MSSQL'", "}", ""]
    
    table_names = inspector.get_table_names()
    print(f"Found {len(table_names)} tables.")

    for table_name in table_names:
        safe_table_name = table_name.replace(" ", "_").replace("-", "_").replace(".", "_")
        
        dbml_lines.append(f"Table {safe_table_name} {{")
        
        try:
            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pks = pk_constraint.get('constrained_columns', [])

            for col in columns:
                col_name = col['name']
                col_type = str(col['type']).replace(" ", "_")
                
                settings = []
                if col_name in pks:
                    settings.append("pk")
                
                # Check nullable
                if not col.get('nullable', True):
                    settings.append("not null")

                settings_str = f" [{', '.join(settings)}]" if settings else ""
                
                # DBML syntax: column_name column_type [settings]
                dbml_lines.append(f"  {col_name} {col_type}{settings_str}")
        except:
            pass
            
        dbml_lines.append("}\n")

    # Relationships
    print("Inspecting relationships...")
    for table_name in table_names:
        safe_source = table_name.replace(" ", "_").replace("-", "_").replace(".", "_")
        try:
            fks = inspector.get_foreign_keys(table_name)
            for fk in fks:
                target_table = fk['referred_table']
                safe_target = target_table.replace(" ", "_").replace("-", "_").replace(".", "_")
                
                # Ref: One to Many usually
                # DBML Ref: table1.col1 > table2.col2
                
                # We need source column for DBML relationship
                source_cols = fk['constrained_columns']
                target_cols = fk['referred_columns']
                
                if source_cols and target_cols:
                    s_col = source_cols[0]
                    t_col = target_cols[0]
                    # Source > Target (Many to one)
                    dbml_lines.append(f"Ref: {safe_source}.{s_col} > {safe_target}.{t_col}")
        except:
            pass

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    os.makedirs(output_dir, exist_ok=True)
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    os.makedirs(output_dir, exist_ok=True)
    # Dynamic logic for output name
    if db_name == 'carmal_a':
        filename = "diagrama_carmal.dbml" # Legacy support/Specific request
    else:
        filename = f"diagrama_{db_name}.dbml"
        
    output_file = os.path.join(output_dir, filename)

    with open(output_file, 'w') as f:
        f.write("\n".join(dbml_lines))
    
    print(f"DBML generated at: {output_file}")

if __name__ == "__main__":
    generate_dbml("carmal_m")
