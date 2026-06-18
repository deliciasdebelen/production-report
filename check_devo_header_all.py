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
    print("DETALLES DE TODOS LOS CAMPOS DE saDevolucionCliente PARA 384")
    print("=" * 80)
    # We will select all numeric, discount, tax and charge columns
    sql_header = """
        SELECT doc_num, total_bruto, total_neto, monto_imp, saldo,
               porc_desc_glob, monto_desc_glob, porc_reca, monto_reca, otros1, otros2, otros3
        FROM saDevolucionCliente
        WHERE doc_num = '0000000384'
    """
    print(sqlcmd(client, sql_header))

    print("\n" + "=" * 80)
    print("REVISIÓN DE DESCUENTOS Y OTROS EN RENGLONES (SUMAS)")
    print("=" * 80)
    sql_reng_details = """
        SELECT SUM(monto_desc) as SumMontoDesc,
               SUM(monto_imp) as SumMontoImp,
               SUM(monto_desc_glob) as SumDescGlob,
               SUM(monto_reca_glob) as SumRecaGlob
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000384'
    """
    print(sqlcmd(client, sql_reng_details))

    client.close()

if __name__ == "__main__":
    run()
