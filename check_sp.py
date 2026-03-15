import pyodbc

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

def search():
    try:
        conn = pyodbc.connect(RAW_CONN_STR)
        cursor = conn.cursor()
        
        # Any SP that contains UPDATE saDocumentoVenta or INSERT INTO saDocumentoVenta
        # and has 'NCR' and 'Devolu'
        print("======== SPs modifying saDocumentoVenta with NCR and Devolucion ========")
        query = """
        SELECT o.name, m.definition
        FROM sys.sql_modules m
        INNER JOIN sys.objects o ON m.object_id = o.object_id
        WHERE o.type_desc = 'SQL_STORED_PROCEDURE'
          AND (m.definition LIKE '%UPDATE saDocumentoVenta%' OR m.definition LIKE '%INSERT INTO saDocumentoVenta%' OR m.definition LIKE '%UPDATE%saDocumentoVenta%')
          AND m.definition LIKE '%NCR%'
          AND m.definition LIKE '%Devoluc%'
        """
        cursor.execute(query)
        sps = cursor.fetchall()
        for r in sps:
            print(f"- {r.name}")
            # print a snippet
            idx = r.definition.upper().find('UPDATE SADOCUMENTOVENTA')
            if idx == -1:
                idx = r.definition.upper().find('UPDATE dbo.saDocumentoVenta'.upper())
            if idx == -1:
                idx = r.definition.upper().find('UPDATE')
                
            start = max(0, idx - 100)
            end = min(len(r.definition), idx + 500)
            print("  Snippet:", r.definition[start:end].replace('\\n', ' '))
            
        print("\\n======== ALL triggers in DB with UPDATE saDocumentoVenta or NCR ========")
        query2 = """
        SELECT o.name, m.definition
        FROM sys.sql_modules m
        INNER JOIN sys.objects o ON m.object_id = o.object_id
        WHERE o.type_desc = 'SQL_TRIGGER'
          AND (m.definition LIKE '%UPDATE saDocumentoVenta%' OR m.definition LIKE '%saDocumentoVenta%')
          AND m.definition LIKE '%ncr%'
        """
        cursor.execute(query2)
        trs = cursor.fetchall()
        for r in trs:
            print(f"- {r.name}")

        print("\\n======== Check for custom tasks / jobs modifying NCR ========")
        # just list things modified recently
        query3 = """
        SELECT name, type_desc, modify_date 
        FROM sys.objects 
        WHERE type IN ('P', 'TR') 
        ORDER BY modify_date DESC
        """
        cursor.execute(query3)
        recent = cursor.fetchmany(10)
        for r in recent:
            print(f"- {r.name} ({r.type_desc}) last modified: {r.modify_date}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search()
