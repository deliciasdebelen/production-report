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
    print("DETALLES DE saDevolucionCliente PARA EL DOCUMENTO 384")
    print("=" * 80)
    sql_devo_header = """
        SELECT doc_num, co_cli, total_bruto, total_neto, monto_imp, saldo, anulado
        FROM saDevolucionCliente
        WHERE doc_num = '0000000384' OR doc_num = '00000384' OR doc_num LIKE '%384'
    """
    print(sqlcmd(client, sql_devo_header))

    print("\n" + "=" * 80)
    print("COLUMNAS DE saDevolucionClienteReng (RENGLONES)")
    print("=" * 80)
    sql_cols = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saDevolucionClienteReng' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql_cols)[:2000])

    print("\n" + "=" * 80)
    print("RENGLONES DE LA DEVOLUCIÓN DE CLIENTE 384 (saDevolucionClienteReng)")
    print("=" * 80)
    # Let's query details from the return lines.
    # Usually: reng_num, co_art, co_alma, total_art (quantity), prec_vta (price), reng_neto (subtotal/neto per line)
    # Let's write a query that checks what columns exist
    sql_devo_reng = """
        SELECT reng_num, co_art, co_alma, total_art, prec_vta, reng_neto, tipo_imp, porc_imp
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000384' OR doc_num = '00000384' OR doc_num LIKE '%384'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql_devo_reng))

    print("\n" + "=" * 80)
    print("VERIFICAR LA SUMA DE LOS RENGLONES")
    print("=" * 80)
    sql_sum = """
        SELECT SUM(reng_neto) as SumaRengNeto, 
               SUM(reng_neto * (1 + porc_imp/100.0)) as SumaConImpuesto
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000384' OR doc_num = '00000384' OR doc_num LIKE '%384'
    """
    print(sqlcmd(client, sql_sum))

    client.close()

if __name__ == "__main__":
    run()
