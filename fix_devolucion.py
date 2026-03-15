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

def fix_dev():
    try:
        conn = pyodbc.connect(RAW_CONN_STR)
        cursor = conn.cursor()
        
        # We manually update total_neto and saldo to match total_bruto on dev 294
        print("====== VAMOS A CORREGIR DEV 0000000294 ======")
        query_dev = """
        UPDATE saDevolucionCliente
        SET total_neto = total_bruto, saldo = total_bruto
        WHERE doc_num = '0000000294'
        """
        cursor.execute(query_dev)
        print("DEV 294 corrected.")

        # We manually update NCR 592
        query_ncr = """
        UPDATE saDocumentoVenta
        SET total_neto = total_bruto, saldo = 0 -- as the original ncr was entirely applied? wait..
        WHERE nro_doc = '00000592  ' AND co_tipo_doc = 'N/CR  '
        """
        # If the NCR was entirely applied to the devolved invoice, then if neto is corrected, saldo should become 0.
        # But wait, original saldo was 4.85, and neto was 59496.55, bruto was 59491.70.
        # If neto decreases by 4.85, then applied amnts cover it all, so saldo decreases by 4.85 to 0.
        cursor.execute(query_ncr)
        print("NCR 592 corrected.")
        
        # Verify it
        cursor.execute("SELECT total_bruto, total_neto, saldo FROM saDevolucionCliente WHERE doc_num = '0000000294'")
        r_dev = cursor.fetchone()
        print(f"DEV 294 NOW -> Bruto: {r_dev.total_bruto}, Neto: {r_dev.total_neto}, Saldo: {r_dev.saldo}")

        cursor.execute("SELECT total_bruto, total_neto, saldo FROM saDocumentoVenta WHERE nro_doc = '00000592  ' AND co_tipo_doc = 'N/CR  '")
        r_ncr = cursor.fetchone()
        print(f"NCR 592 NOW -> Bruto: {r_ncr.total_bruto}, Neto: {r_ncr.total_neto}, Saldo: {r_ncr.saldo}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_dev()
