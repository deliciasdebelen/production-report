import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 80)
    print("BUSCANDO DEVOLUCIÓN 304 EN saDevolucionCliente (COLUMNAS CORRECTAS)")
    print("=" * 80)
    sql_devo_304 = """
        SELECT doc_num, co_cli, total_bruto, total_neto, monto_imp, saldo, anulado,
               CONVERT(VARCHAR, fec_emis, 103) as FecEmis, comentario
        FROM saDevolucionCliente
        WHERE doc_num = '0000000304' OR doc_num = '00000304' OR doc_num LIKE '%304'
    """
    print(sqlcmd(client, sql_devo_304))

    print("\n" + "=" * 80)
    print("BUSCANDO DEVOLUCIONES ASOCIADAS A LA FACTURA 10161 A NIVEL DE RENGLONES")
    print("=" * 80)
    # Search saDevolucionClienteReng for references to the invoice
    sql_devo_orig = """
        SELECT DISTINCT r.doc_num, d.co_cli, d.total_bruto, d.total_neto, 
               CONVERT(VARCHAR, d.fec_emis, 103) as FecEmis, d.anulado
        FROM saDevolucionClienteReng r
        JOIN saDevolucionCliente d ON d.doc_num = r.doc_num
        WHERE r.tipo_doc = 'FACT' AND r.num_doc IN ('0000010161', '000010161')
    """
    print(sqlcmd(client, sql_devo_orig))

    client.close()

if __name__ == "__main__":
    run()
