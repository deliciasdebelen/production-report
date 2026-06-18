import urllib.parse
from sqlalchemy import create_engine, text

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

params_a = urllib.parse.quote_plus(RAW_CONN_STR)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params_a}")

tables_to_check_triggers = [
    'saPedidoVentaReng',
    'saFacturaVentaReng',
    'saDevolucionClienteReng'
]

def check_orders():
    with engine.connect() as conn:
        print("--- AUDITORIA: saPedidoVentaReng (prec_vta * total_art vs reng_neto) ---")
        
        # Check all cases
        query1 = text("""
        SELECT COUNT(*) as total_rows
        FROM saPedidoVentaReng
        """)
        total_rows = conn.execute(query1).scalar()
        
        # Check mismatches. Allowing 0.01 tolerance for floating point rounding.
        query2 = text("""
        SELECT TOP 20 doc_num, reng_num, co_art, prec_vta, total_art, reng_neto, 
               (prec_vta * total_art) as calc_val, 
               ABS((prec_vta * total_art) - reng_neto) as diff,
               monto_desc
        FROM saPedidoVentaReng
        WHERE ABS((prec_vta * total_art) - reng_neto) > 0.01
        ORDER BY doc_num DESC
        """)
        
        query2_count = text("""
        SELECT COUNT(*) 
        FROM saPedidoVentaReng
        WHERE ABS((prec_vta * total_art) - reng_neto) > 0.01
        """)
        
        mismatches = conn.execute(query2_count).scalar()
        print(f"Total rows in saPedidoVentaReng: {total_rows}")
        print(f"Rows where (prec_vta * total_art) != reng_neto: {mismatches}")
        
        if mismatches > 0:
            print("\nExamples of affected documents (Top 20):")
            res = conn.execute(query2)
            print(f"{'doc_num':<15} | {'reng_num':<8} | {'co_art':<15} | {'prec_vta':<15} | {'total_art':<10} | {'reng_neto':<15} | {'calc_val':<15} | {'diff':<15} | {'desc'}")
            print("-" * 130)
            for r in res:
                print(f"{str(r.doc_num):<15} | {str(r.reng_num):<8} | {str(r.co_art):<15} | {str(r.prec_vta):<15} | {str(r.total_art):<10} | {str(r.reng_neto):<15} | {str(r.calc_val):<15} | {str(r.diff):<15} | {str(r.monto_desc)}")

def check_triggers():
    with engine.connect() as conn:
        print("\n--- AUDITORIA: Triggers que afectan 'reng_neto' ---")
        for table in tables_to_check_triggers:
            print(f"\nChecking triggers for {table}...")
            # Find all triggers for the table
            query_triggers = text(f"""
            SELECT tr.name AS TriggerName, m.definition AS TriggerDefinition
            FROM sys.triggers tr
            JOIN sys.tables t ON tr.parent_id = t.object_id
            JOIN sys.sql_modules m ON tr.object_id = m.object_id
            WHERE t.name = '{table}'
            """)
            
            res = conn.execute(query_triggers).fetchall()
            if not res:
                print(f"  No triggers found for {table}.")
            for r in res:
                trigger_name = r.TriggerName
                definition = r.TriggerDefinition.lower()
                
                # Check if trigger manipulates reng_neto in an UPDATE or INSERT
                # Very basic check: does it contain 'reng_neto'?
                if 'reng_neto' in definition:
                    print(f"  [!] Trigger '{trigger_name}' refences 'reng_neto'.")
                    
                    # Output a snippet where it's found
                    lines = definition.split('\n')
                    for i, line in enumerate(lines):
                        if 'reng_neto' in line:
                            print(f"      Line {i+1}: {line.strip()[:100]}")
                else:
                    print(f"  [ ] Trigger '{trigger_name}' exists but does not reference 'reng_neto'.")

if __name__ == '__main__':
    check_orders()
    check_triggers()
