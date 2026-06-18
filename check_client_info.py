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
    print("NOMBRES DE LOS CLIENTES EN saCliente")
    print("=" * 80)
    sql_clients = """
        SELECT co_cli, cli_des 
        FROM saCliente 
        WHERE co_cli IN ('J500769300', 'J502690255', 'J507148262')
    """
    print(sqlcmd(client, sql_clients))

    print("\n" + "=" * 80)
    print("HISTORIAL DE DOCUMENTOS DE J500769300 (TOP 20)")
    print("=" * 80)
    sql_history = """
        SELECT TOP 20 nro_doc, co_tipo_doc, total_neto, saldo, anulado,
               CONVERT(VARCHAR, fec_emis, 103) as FecEmis, doc_orig, nro_orig
        FROM saDocumentoVenta
        WHERE co_cli = 'J500769300'
        ORDER BY fec_emis DESC
    """
    print(sqlcmd(client, sql_history))

    print("\n" + "=" * 80)
    print("DETALLES DEL DOCUMENTO DE ORIGEN DE NCR 1019: DEVO 0000000384")
    print("=" * 80)
    sql_devo = """
        SELECT nro_doc, co_tipo_doc, co_cli, total_neto, saldo, anulado,
               CONVERT(VARCHAR, fec_emis, 103) as FecEmis, doc_orig, nro_orig
        FROM saDocumentoVenta
        WHERE co_tipo_doc = 'DEVO' AND nro_doc = '0000000384'
    """
    print(sqlcmd(client, sql_devo))

    client.close()

if __name__ == "__main__":
    run()
