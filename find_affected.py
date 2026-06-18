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

def find_affected_documents():
    try:
        conn = pyodbc.connect(RAW_CONN_STR)
        cursor = conn.cursor()
        
        print("====== BUSCANDO DEVOLUCIONES AFECTADAS ======")
        query_dev = """
        SELECT c.doc_num, c.total_bruto, c.total_neto, c.saldo,
               ISNULL(SUM(r.total_art * r.prec_vta), 0) AS suma_reng_bruto
        FROM saDevolucionCliente c
        LEFT JOIN saDevolucionClienteReng r ON c.doc_num = r.doc_num
        GROUP BY c.doc_num, c.total_bruto, c.total_neto, c.saldo
        HAVING ABS(c.total_bruto - ISNULL(SUM(r.total_art * r.prec_vta), 0)) > 0.05
        ORDER BY c.doc_num DESC
        """
        cursor.execute(query_dev)
        afectados_dev = cursor.fetchall()
        print(f"Encontradas {len(afectados_dev)} devoluciones afectadas:")
        for r in afectados_dev:
            print(f"- DEV {r.doc_num}: Header Bruto={r.total_bruto:.2f}, Neto={r.total_neto:.2f}, Saldo={r.saldo:.2f} | Suma Lineas={r.suma_reng_bruto:.2f} | Dif={r.total_bruto - r.suma_reng_bruto:.2f}")

        print("\\n====== BUSCANDO NOTAS DE CREDITO AFECTADAS ======")
        query_ncr = """
        SELECT c.nro_doc, c.total_bruto, c.total_neto, c.saldo,
               ISNULL(SUM(r.total_art * r.prec_vta), 0) AS suma_reng_bruto
        FROM saDocumentoVenta c
        LEFT JOIN saDocumentoVentaReng r ON c.nro_doc = r.nro_doc AND c.co_tipo_doc = r.co_tipo_doc
        WHERE RTRIM(c.co_tipo_doc) IN ('N/CR', 'NCR', 'AJPA')
          AND c.fec_emis >= '2024-01-01'  -- To limit the scope if there are tons of old data, wait, let's keep it generally from 2025 onwards.
        GROUP BY c.nro_doc, c.total_bruto, c.total_neto, c.saldo
        HAVING ABS(c.total_bruto - ISNULL(SUM(r.total_art * r.prec_vta), 0)) > 0.05
        ORDER BY c.nro_doc DESC
        """
        
        query_ncr_all = """
        SELECT c.nro_doc, c.total_bruto, c.total_neto, c.saldo,
               ISNULL(SUM(r.total_art * r.prec_vta), 0) AS suma_reng_bruto
        FROM saDocumentoVenta c
        LEFT JOIN saDocumentoVentaReng r ON c.nro_doc = r.nro_doc AND c.co_tipo_doc = r.co_tipo_doc
        WHERE RTRIM(c.co_tipo_doc) IN ('N/CR', 'NCR')
        GROUP BY c.nro_doc, c.total_bruto, c.total_neto, c.saldo
        HAVING ABS(c.total_bruto - ISNULL(SUM(r.total_art * r.prec_vta), 0)) > 0.05
        ORDER BY c.nro_doc DESC
        """
        cursor.execute(query_ncr_all)
        afectados_ncr = cursor.fetchall()
        print(f"Encontradas {len(afectados_ncr)} Notas de Credito afectadas:")
        for r in afectados_ncr:
            # Avoid printing all if too many, just first 20
            print(f"- NCR {r.nro_doc}: Header Bruto={r.total_bruto:.2f}, Neto={r.total_neto:.2f}, Saldo={r.saldo:.2f} | Suma Lineas={r.suma_reng_bruto:.2f} | Dif={r.total_bruto - r.suma_reng_bruto:.2f}")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_affected_documents()
