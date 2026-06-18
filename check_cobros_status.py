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
    print("DETALLES DE LA FACTURA 0000010161 EN saDocumentoVenta")
    print("=" * 80)
    sql_fact = """
        SELECT nro_doc, co_tipo_doc, co_cli, total_neto, saldo, anulado
        FROM saDocumentoVenta
        WHERE nro_doc = '0000010161' OR nro_doc = '000010161'
    """
    print(sqlcmd(client, sql_fact))

    print("\n" + "=" * 80)
    print("DOCUMENTOS CON SALDO PENDIENTE DEL CLIENTE J500769300")
    print("=" * 80)
    sql_cli_docs = """
        SELECT nro_doc, co_tipo_doc, total_neto, saldo, anulado,
               CONVERT(VARCHAR, fec_emis, 103) as FecEmis
        FROM saDocumentoVenta
        WHERE co_cli = 'J500769300'
          AND saldo <> 0
          AND anulado = 0
        ORDER BY fec_emis DESC
    """
    print(sqlcmd(client, sql_cli_docs))

    print("\n" + "=" * 80)
    print("DOCUMENTOS CON SALDO PENDIENTE DEL CLIENTE J502690255 (NCR 1942)")
    print("=" * 80)
    sql_cli_1942 = """
        SELECT nro_doc, co_tipo_doc, total_neto, saldo, anulado,
               CONVERT(VARCHAR, fec_emis, 103) as FecEmis
        FROM saDocumentoVenta
        WHERE co_cli = 'J502690255'
          AND saldo <> 0
          AND anulado = 0
        ORDER BY fec_emis DESC
    """
    print(sqlcmd(client, sql_cli_1942))

    print("\n" + "=" * 80)
    print("DOCUMENTOS CON SALDO PENDIENTE DEL CLIENTE J507148262 (NCR 2065)")
    print("=" * 80)
    sql_cli_2065 = """
        SELECT nro_doc, co_tipo_doc, total_neto, saldo, anulado,
               CONVERT(VARCHAR, fec_emis, 103) as FecEmis
        FROM saDocumentoVenta
        WHERE co_cli = 'J507148262'
          AND saldo <> 0
          AND anulado = 0
        ORDER BY fec_emis DESC
    """
    print(sqlcmd(client, sql_cli_2065))

    client.close()

if __name__ == "__main__":
    run()
