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
    print("MEDIOS DE PAGO DEL COBRO 0000009343 EN saCobroTPReng")
    print("=" * 80)
    sql_tp = """
        SELECT reng_num, co_tar, co_ban, forma_pag, mont_doc
        FROM saCobroTPReng
        WHERE cob_num = '0000009343'
    """
    print(sqlcmd(client, sql_tp))

    print("\n" + "=" * 80)
    print("MEDIOS DE PAGO DEL COBRO 0000009345")
    print("=" * 80)
    sql_tp2 = """
        SELECT reng_num, co_tar, co_ban, forma_pag, mont_doc
        FROM saCobroTPReng
        WHERE cob_num = '0000009345'
    """
    print(sqlcmd(client, sql_tp2))

    client.close()

if __name__ == "__main__":
    run()
