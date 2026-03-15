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
        
        cursor.execute("SELECT num_doc FROM saDevolucionClienteReng WHERE doc_num = '0000000500'")
        row = cursor.fetchone()
        if row and row.num_doc:
            factura = row.num_doc
            print(f"Original Factura: {factura}")
            cursor.execute("SELECT total_bruto, total_neto FROM saFacturaVenta WHERE doc_num = ?", factura)
            f = cursor.fetchone()
            if f:
                print(f"Factura Totales -> Bruto: {f.total_bruto}, Neto: {f.total_neto}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search()
