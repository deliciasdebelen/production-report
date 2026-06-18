import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 80)
    print("VALORES ACTUALES ANTES DE LA CORRECCIÓN")
    print("=" * 80)
    
    # We will define a quick query function using temp files
    def run_query(sql):
        sftp = client.open_sftp()
        temp_sql_path = "/tmp/query.sql"
        with sftp.file(temp_sql_path, "w") as f:
            f.write(sql)
        sftp.close()
        
        cmd = (
            f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
            f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
            f'-d {SQL_DB} -W -i {temp_sql_path} 2>&1 | grep -v "password for"'
        )
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        return stdout.read().decode(errors='replace').strip()

    print("\n[saDevolucionCliente 384]:")
    print(run_query("SELECT doc_num, total_bruto, total_neto, saldo FROM saDevolucionCliente WHERE doc_num = '0000000384'"))
    
    print("\n[saDocumentoVenta N/CR 1019]:")
    print(run_query("SELECT nro_doc, co_tipo_doc, total_bruto, total_neto, saldo FROM saDocumentoVenta WHERE nro_doc = '00001019' AND co_tipo_doc = 'N/CR'"))

    print("\n" + "=" * 80)
    print("EJECUTANDO LA CORRECCIÓN DESDE ARCHIVO SQL EN TRANSACCIÓN")
    print("=" * 80)
    
    update_sql = """
    BEGIN TRANSACTION;
    
    /* 1. Actualizar la cabecera de la devolución 384 */
    UPDATE saDevolucionCliente
    SET total_bruto = 67055.30,
        total_neto = 73313.79,
        saldo = 73313.79
    WHERE doc_num = '0000000384';
    
    /* 2. Actualizar la cabecera de la Nota de Crédito 1019 */
    UPDATE saDocumentoVenta
    SET total_bruto = 67055.30,
        total_neto = 73313.79,
        saldo = 0.00
    WHERE nro_doc = '00001019' AND co_tipo_doc = 'N/CR';
    
    IF @@ERROR = 0
    BEGIN
        COMMIT TRANSACTION;
        SELECT 'TRANSACCIÓN APLICADA Y CONFIRMADA CON ÉXITO' as Resultado;
    END
    ELSE
    BEGIN
        ROLLBACK TRANSACTION;
        SELECT 'ERROR: TRANSACCIÓN REVERTIDA (ROLLBACK)' as Resultado;
    END
    """
    
    result = run_query(update_sql)
    print(result)

    print("\n" + "=" * 80)
    print("VALORES ACTUALES DESPUÉS DE LA CORRECCIÓN")
    print("=" * 80)
    
    print("\n[saDevolucionCliente 384]:")
    print(run_query("SELECT doc_num, total_bruto, total_neto, saldo FROM saDevolucionCliente WHERE doc_num = '0000000384'"))
    
    print("\n[saDocumentoVenta N/CR 1019]:")
    print(run_query("SELECT nro_doc, co_tipo_doc, total_bruto, total_neto, saldo FROM saDocumentoVenta WHERE nro_doc = '00001019' AND co_tipo_doc = 'N/CR'"))

    client.close()

if __name__ == "__main__":
    run()
