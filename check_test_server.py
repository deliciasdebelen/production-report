import urllib.parse
from sqlalchemy import create_engine, text

# Connection string for Profit Plus TESTING SERVER
RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.60.15;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

params_test = urllib.parse.quote_plus(RAW_CONN_STR)
engine_test = create_engine(f"mssql+pyodbc:///?odbc_connect={params_test}")

def check_devoluciones_test():
    try:
        with engine_test.connect() as conn:
            print("--- AUDITORIA TEST SERVER (192.168.60.15): saDevolucionClienteReng ---")
            
            query1 = text("""
            SELECT COUNT(*) as total_rows
            FROM saDevolucionClienteReng
            """)
            total_rows = conn.execute(query1).scalar()
            
            query_count = text("""
            SELECT COUNT(*) 
            FROM saDevolucionClienteReng
            WHERE ABS((prec_vta * total_art) - reng_neto) > 0.01
            """)
            
            mismatches = conn.execute(query_count).scalar()
            print(f"Total rows in test DB: {total_rows}")
            print(f"Rows where prec_vta * total_art != reng_neto (diff > 0.01): {mismatches}")
            
            if mismatches > 0:
                print("\nShowing details of recent mismatches:")
                query_details = text("""
                SELECT TOP 20 RTRIM(doc_num) as doc_num, reng_num, RTRIM(co_art) as co_art, prec_vta, total_art, reng_neto, 
                       (prec_vta * total_art) as calc_val, 
                       ABS((prec_vta * total_art) - reng_neto) as diff,
                       monto_desc
                FROM saDevolucionClienteReng
                WHERE ABS((prec_vta * total_art) - reng_neto) > 0.01
                ORDER BY doc_num DESC
                """)
                res = conn.execute(query_details)
                print(f"{'doc_num':<15} | {'reng_num':<8} | {'prec_vta':<12} | {'total_art':<10} | {'reng_neto':<12} | {'calc_val':<12} | {'diff':<8} | {'monto_desc':<10}")
                print("-" * 110)
                for r in res:
                    print(f"{str(r.doc_num):<15} | {str(r.reng_num):<8} | {str(r.prec_vta):<12} | {str(r.total_art):<10} | {str(r.reng_neto):<12} | {str(r.calc_val):<12} | {str(round(r.diff,2)):<8} | {str(r.monto_desc):<10}")
                    
            print("\n--- REVISANDO DOCUMENTOS RECIENTES (Últimos 5 creados) ---")
            q_recent = text("""
            SELECT TOP 5 d.doc_num, r.reng_num, RTRIM(r.co_art) as co_art, r.prec_vta, r.total_art, r.reng_neto, 
                   ABS((r.prec_vta * r.total_art) - r.reng_neto) as diff, r.monto_desc
            FROM saDevolucionCliente d
            JOIN saDevolucionClienteReng r ON d.doc_num = r.doc_num
            ORDER BY d.doc_num DESC
            """)
            recents = conn.execute(q_recent)
            print("Documentos más recientes (independientemente si cuadran o no):")
            print(f"{'doc_num':<15} | {'reng':<5} | {'prec_vta':<12} | {'total_art':<10} | {'reng_neto':<12} | {'diff':<8} | {'monto_desc':<10}")
            for r in recents:
                print(f"{str(r.doc_num):<15} | {str(r.reng_num):<5} | {str(r.prec_vta):<12} | {str(r.total_art):<10} | {str(r.reng_neto):<12} | {str(round(r.diff,2)):<8} | {str(r.monto_desc):<10}")

    except Exception as e:
        print("ERROR CONNECTION TO TEST SERVER:", e)

if __name__ == '__main__':
    check_devoluciones_test()
