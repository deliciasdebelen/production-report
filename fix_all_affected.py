import pyodbc
from decimal import Decimal

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

def fix_all():
    conn = pyodbc.connect(RAW_CONN_STR)
    cursor = conn.cursor()
    
    report_lines = []
    report_lines.append("# Reporte de Corrección de Documentos (Triggers Anomalos)")
    report_lines.append("Este documento expone los valores **ANTES** y **DESPUÉS** de la corrección sistemática de Devoluciones y Notas de Crédito que fueron alteradas originalmente por los triggers `TR_ForzarTotalesEnDetalle` y `TR_saDevolucionCliente_CalcularNeto`.\\n")
    
    query_dev = """
    SELECT c.doc_num, 
           CAST(c.total_bruto AS float) AS dev_bruto, 
           CAST(c.total_neto AS float) AS dev_neto, 
           CAST(c.saldo AS float) AS dev_saldo,
           CAST(ISNULL(SUM(r.total_art * r.prec_vta), 0) AS float) AS suma_reng
    FROM saDevolucionCliente c
    LEFT JOIN saDevolucionClienteReng r ON c.doc_num = r.doc_num
    GROUP BY c.doc_num, c.total_bruto, c.total_neto, c.saldo
    HAVING ABS(c.total_bruto - ISNULL(SUM(r.total_art * r.prec_vta), 0)) > 0.05
    ORDER BY c.doc_num ASC
    """
    cursor.execute(query_dev)
    devs = cursor.fetchall()
    
    report_lines.append(f"## Total de Devoluciones Corregidas: {len(devs)}\\n")
    report_lines.append("| Devolución | NCR Vinculada | Antes (Bruto) | Correcto (Suma) | Dif Corregida | Saldo Resultante NCR |")
    report_lines.append("|---|---|---|---|---|---|")
    
    updates_dev = []
    updates_ncr = []
    
    for dev in devs:
        doc_num = dev.doc_num
        old_bruto = dev.dev_bruto
        old_neto = dev.dev_neto
        correct_bruto = dev.suma_reng
        diff = old_bruto - correct_bruto
        
        # Link NCR
        cursor.execute("SELECT nro_doc, CAST(total_bruto AS float) AS total_bruto, CAST(total_neto AS float) AS total_neto, CAST(saldo AS float) AS saldo FROM saDocumentoVenta WHERE doc_orig = 'DEVO' AND nro_orig = ? AND co_tipo_doc = 'N/CR'", doc_num)
        ncrs = cursor.fetchall()
        
        ncr_str = ", ".join([n.nro_doc.strip() for n in ncrs]) if ncrs else "Ninguna"
        
        # Prepare Dev Update
        impuestos_y_recargos = old_neto - old_bruto
        new_dev_neto = correct_bruto + impuestos_y_recargos
        updates_dev.append((correct_bruto, new_dev_neto, new_dev_neto, doc_num))
        
        final_saldos = []
        
        # Prepare NCR Updates
        for ncr in ncrs:
            old_ncr_bruto = ncr.total_bruto
            old_ncr_neto = ncr.total_neto
            old_ncr_saldo = ncr.saldo
            
            # Preserve explicit profit taxes / modifiers
            imp_ncr = old_ncr_neto - old_ncr_bruto
            new_ncr_neto = correct_bruto + imp_ncr
            
            # Recalculate balance
            monto_aplicado = old_ncr_neto - old_ncr_saldo
            new_ncr_saldo = new_ncr_neto - monto_aplicado
            if new_ncr_saldo < 0: 
                new_ncr_saldo = 0.0
                
            final_saldos.append(f"{new_ncr_saldo:.2f}")
            updates_ncr.append((correct_bruto, new_ncr_neto, new_ncr_saldo, ncr.nro_doc))
            
        sds_str = ", ".join(final_saldos) if final_saldos else "-"
        report_lines.append(f"| {doc_num.strip()} | {ncr_str} | {old_bruto:.2f} | {correct_bruto:.2f} | {diff:.2f} | {sds_str} |")
        
    report_lines.append("\\n## Metodología\\n")
    report_lines.append("Las actualizaciones se aplicaron sobre la base de datos `carmal_a` forzando el `total_bruto` a ser exactamente la suma de (cantidad × precio) de cada uno de sus renglones. El `total_neto` fue ajustado en proporción para mantener vigentes los impuestos, mientras los `saldos` remanentes de las notas de crédito se depuraron asumiendo el nuevo monto neto menos el monto histórico ya aplicado.\\n")
    
    # Exec Updates
    for u in updates_dev:
        cursor.execute("UPDATE saDevolucionCliente SET total_bruto=?, total_neto=?, saldo=? WHERE doc_num=?", u[0], u[1], u[2], u[3])
        
    for u in updates_ncr:
        cursor.execute("UPDATE saDocumentoVenta SET total_bruto=?, total_neto=?, saldo=? WHERE nro_doc=? AND co_tipo_doc='N/CR'", u[0], u[1], u[2], u[3])
        
    conn.commit()
    conn.close()
    
    report_path = r"C:\\Users\\ovargas\\.gemini\\antigravity\\brain\\9e88accf-a30c-41b5-bcb4-7452b68c10be\\reporte_correccion.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\\n".join(report_lines))
        
    print(f"Updates executed successfully. Report saved to {report_path}")

if __name__ == "__main__":
    fix_all()
