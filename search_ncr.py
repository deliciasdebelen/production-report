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
    print("COLUMNAS DE saDocumentoVenta")
    print("=" * 80)
    sql_cols = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saDocumentoVenta' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql_cols)[:2000])

    print("\n" + "=" * 80)
    print("BÚSQUEDA DE NCR 1942, 2065, 1019 EN saDocumentoVenta")
    print("=" * 80)
    # Most common columns in saDocumentoVenta: nro_doc, co_tipo_doc, co_cli, fec_reg, total_bruto, total_neto, saldo, anulado
    # Let's write a query that checks what documents exist with matching nro_doc
    sql_query = """
        SELECT nro_doc, co_tipo_doc, co_cli, fec_reg, total_bruto, total_neto, saldo, anulado
        FROM saDocumentoVenta
        WHERE nro_doc LIKE '%1942' OR nro_doc LIKE '%2065' OR nro_doc LIKE '%1019'
    """
    print(sqlcmd(client, sql_query))

    print("\n" + "=" * 80)
    print("BÚSQUEDA EN saDocumentoCompra")
    print("=" * 80)
    sql_query_compra = """
        SELECT nro_doc, co_tipo_doc, co_prov, fec_reg, total_bruto, total_neto, saldo, anulado
        FROM saDocumentoCompra
        WHERE nro_doc LIKE '%1942' OR nro_doc LIKE '%2065' OR nro_doc LIKE '%1019'
    """
    print(sqlcmd(client, sql_query_compra))

    client.close()

if __name__ == "__main__":
    run()
