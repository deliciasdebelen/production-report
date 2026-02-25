import pyodbc

def main():
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;DATABASE=MasterProfitPro;UID=PROFIT;PWD=profit;Encrypt=yes;TrustServerCertificate=yes;'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        cursor.execute("SELECT t.name AS table_name, c.name AS column_name, ty.name AS type_name FROM sys.tables t INNER JOIN sys.columns c ON t.object_id = c.object_id INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id ORDER BY t.name, c.column_id")
        tables = {}
        for row in cursor.fetchall():
            t_name, c_name, ty_name = row
            if t_name not in tables:
                tables[t_name] = []
            tables[t_name].append(f"{c_name} ({ty_name})")
        
        cursor.execute("SELECT name FROM sys.procedures")
        sps = [row[0] for row in cursor.fetchall()]
        
        with open('masterprofit_schema.md', 'w', encoding='utf-8') as f:
            f.write("# MasterProfitPro Database Schema\n\n")
            f.write("## Tables\n")
            for t_name, cols in tables.items():
                f.write(f"### {t_name}\n")
                f.write(f"- {', '.join(cols)}\n\n")
            
            f.write("## Stored Procedures\n")
            for sp in sps:
                f.write(f"- {sp}\n")
                
        print("Schema dumped to masterprofit_schema.md successfully. Found", len(tables), "tables and", len(sps), "stored procedures.")
    except Exception as e:
        print("Error:", str(e))

if __name__ == '__main__':
    main()
