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
    print("VALORES DE PRECIO DE LOS RENGLONES ANTES DE LA CORRECCIÓN")
    print("=" * 80)
    
    # Quick query function using sftp and sqlcmd -i
    def run_query(sql):
        sftp = client.open_sftp()
        temp_sql_path = "/tmp/query_rengs.sql"
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

    print("\n[saFacturaVentaReng 10161]:")
    print(run_query("SELECT reng_num, co_art, prec_vta, prec_vta_om FROM saFacturaVentaReng WHERE doc_num = '0000010161' ORDER BY reng_num"))
    
    print("\n[saDevolucionClienteReng 384]:")
    print(run_query("SELECT reng_num, co_art, prec_vta, prec_vta_om FROM saDevolucionClienteReng WHERE doc_num = '0000000384' ORDER BY reng_num"))

    print("\n" + "=" * 80)
    print("EJECUTANDO LA CORRECCIÓN DE LOS RENGLONES EN UNA TRANSACCIÓN")
    print("=" * 80)
    
    update_sql = """
    BEGIN TRANSACTION;
    
    UPDATE dr
    SET dr.prec_vta = fr.prec_vta,
        dr.prec_vta_om = fr.prec_vta_om
    FROM saDevolucionClienteReng dr
    JOIN saFacturaVentaReng fr 
        ON fr.reng_num = dr.reng_num
    WHERE dr.doc_num = '0000000384' 
      AND fr.doc_num = '0000010161';
    
    IF @@ERROR = 0
    BEGIN
        COMMIT TRANSACTION;
        SELECT 'TRANSACCIÓN APLICADA CON ÉXITO' as Resultado;
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
    print("VALORES DESPUÉS DE LA CORRECCIÓN")
    print("=" * 80)
    
    print("\n[saDevolucionClienteReng 384]:")
    print(run_query("SELECT reng_num, co_art, prec_vta, prec_vta_om FROM saDevolucionClienteReng WHERE doc_num = '0000000384' ORDER BY reng_num"))

    client.close()

if __name__ == "__main__":
    run()
