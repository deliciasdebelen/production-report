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
    print("CAMPOS DE PRECIO EN saDevolucionClienteReng PARA 384")
    print("=" * 80)
    sql_devo_price = """
        SELECT reng_num, co_art, prec_vta, co_precio, reng_neto
        FROM saDevolucionClienteReng
        WHERE doc_num = '0000000384'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql_devo_price))

    print("\n" + "=" * 80)
    print("BUSCANDO TABLAS RELACIONADAS CON 'precio'")
    print("=" * 80)
    sql_price_tables = """
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%precio%' OR TABLE_NAME LIKE '%price%'
        ORDER BY TABLE_NAME
    """
    print(sqlcmd(client, sql_price_tables))

    print("\n" + "=" * 80)
    print("COLUMNAS DE saArticulo RELACIONADAS CON PRECIOS (TODAS)")
    print("=" * 80)
    sql_cols = """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'saArticulo' 
          AND (COLUMN_NAME LIKE '%pre%' OR COLUMN_NAME LIKE '%val%' OR COLUMN_NAME LIKE '%cos%')
        ORDER BY COLUMN_NAME
    """
    print(sqlcmd(client, sql_cols))

    client.close()

if __name__ == "__main__":
    run()
