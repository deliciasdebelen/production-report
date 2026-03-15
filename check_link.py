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

def check_link():
    try:
        conn = pyodbc.connect(RAW_CONN_STR)
        cursor = conn.cursor()
        
        # Check Dev 500 and NCR 1608
        print("====== LINK CHECK ======")
        cursor.execute("SELECT nro_doc, co_tipo_doc, doc_orig, tipo_origen, nro_orig FROM saDocumentoVenta WHERE nro_doc LIKE '%1608%' AND co_tipo_doc = 'N/CR'")
        for r in cursor.fetchall():
            print(f"NCR {r.nro_doc} - doc_orig: '{r.doc_orig}', tipo_origen: '{r.tipo_origen}', nro_orig: '{r.nro_orig}'")
            
        cursor.execute("SELECT nro_doc, co_tipo_doc, doc_orig, tipo_origen, nro_orig FROM saDocumentoVenta WHERE nro_doc LIKE '%0592%' AND co_tipo_doc = 'N/CR'")
        for r in cursor.fetchall():
            print(f"NCR {r.nro_doc} - doc_orig: '{r.doc_orig}', tipo_origen: '{r.tipo_origen}', nro_orig: '{r.nro_orig}'")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_link()
