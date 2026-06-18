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
        f'-d {db} -W -h -1 -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    # 1. List all tables in carmal_a to find correct names
    print("=== TABLAS EN carmal_a (filtro: Lote, Orden, Articulo, Stock) ===")
    sql = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
          AND (TABLE_NAME LIKE '%Lote%' 
            OR TABLE_NAME LIKE '%Orden%' 
            OR TABLE_NAME LIKE '%Prod%'
            OR TABLE_NAME LIKE '%Stock%'
            OR TABLE_NAME LIKE '%Articulo%'
            OR TABLE_NAME LIKE '%Almacen%')
        ORDER BY TABLE_NAME
    """
    print(sqlcmd(client, sql))

    # 2. Also list ALL tables to see naming convention
    print("\n=== TODAS LAS TABLAS (primeras 80) ===")
    sql2 = """
        SELECT TOP 80 TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE' 
        ORDER BY TABLE_NAME
    """
    print(sqlcmd(client, sql2))

    client.close()

if __name__ == "__main__":
    run()
