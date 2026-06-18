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
    print("COLUMNAS DE saCliente CON RELACIÓN A PRECIOS/LISTAS/TIPOS")
    print("=" * 80)
    sql_cols = """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'saCliente' 
          AND (COLUMN_NAME LIKE '%pre%' OR COLUMN_NAME LIKE '%tip%' OR COLUMN_NAME LIKE '%lis%' OR COLUMN_NAME LIKE '%cat%')
        ORDER BY COLUMN_NAME
    """
    print(sqlcmd(client, sql_cols))

    print("\n" + "=" * 80)
    print("VALORES DEL CLIENTE J500769300 EN ESAS COLUMNAS")
    print("=" * 80)
    # Most common columns in Profit: tipo_cli, co_precio, etc.
    sql_client_vals = """
        SELECT co_cli, cli_des, co_precio, tipo_cli, co_cat
        FROM saCliente
        WHERE co_cli = 'J500769300'
    """
    print(sqlcmd(client, sql_client_vals))

    client.close()

if __name__ == "__main__":
    run()
