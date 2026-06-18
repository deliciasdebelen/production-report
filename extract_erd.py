import pyodbc
import sys
import os

SERVER = "192.168.1.205"
DATABASE = "carmal_n"
UID = "PROFIT"
PWD = "profit"

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={UID};"
    f"PWD={PWD};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

def extract_schema():
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # 1. Get Tables and Columns
        cursor.execute("""
            SELECT 
                t.name AS table_name,
                c.name AS column_name,
                y.name AS type_name,
                c.max_length,
                c.is_nullable
            FROM sys.tables t
            INNER JOIN sys.columns c ON t.object_id = c.object_id
            INNER JOIN sys.types y ON c.user_type_id = y.user_type_id
            WHERE t.type = 'U'
            ORDER BY t.name, c.column_id
        """)
        
        tables = {}
        for row in cursor.fetchall():
            t_name = row.table_name
            if t_name not in tables:
                tables[t_name] = []
            tables[t_name].append({
                "column_name": row.column_name,
                "type": row.type_name,
                "length": row.max_length,
                "nullable": row.is_nullable
            })
            
        # 2. Get Foreign Keys (Relationships)
        cursor.execute("""
            SELECT 
                fk.name AS fk_name,
                tp.name AS parent_table,
                cp.name AS parent_column,
                tr.name AS referenced_table,
                cr.name AS referenced_column
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
            INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
            INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
        """)
        
        fks = []
        for row in cursor.fetchall():
            fks.append({
                "name": row.fk_name,
                "parent_table": row.parent_table,
                "parent_column": row.parent_column,
                "referenced_table": row.referenced_table,
                "referenced_column": row.referenced_column
            })
            
        # Generate Mermaid Markdown
        # Since it can be huge, let's also generate a simplified version or just raw text
        # If there are too many tables, mermaid will fail to render over ~200 nodes.
        # Let's see how many tables there are.
        
        table_count = len(tables)
        print(f"INFO: Found {table_count} tables and {len(fks)} foreign keys.")
        
        out_file = "carmal_n_schema_raw.json"
        import json
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"tables": tables, "fks": fks}, f, indent=2)
            
        print(f"SUCCESS: Saved raw schema to {out_file}")
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    extract_schema()
