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

    print("=" * 70)
    print("DIAGNÓSTICO: Compuesto 32 - Asignación de Lotes")
    print("=" * 70)

    # 1. Columnas de saLoteEntrada
    print("\n[1] COLUMNAS DE saLoteEntrada")
    sql = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saLoteEntrada' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql))

    # 2. Columnas de saLoteSalida
    print("\n[2] COLUMNAS DE saLoteSalida")
    sql2 = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saLoteSalida' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql2))

    # 3. Columnas de saArtCompuesto / saArtCompuestoGen
    print("\n[3] COLUMNAS DE saArtCompuestoGen")
    sql3 = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saArtCompuestoGen' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql3))

    # 4. Columnas saArtCompuestoGenReng
    print("\n[4] COLUMNAS DE saArtCompuestoGenReng")
    sql4 = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saArtCompuestoGenReng' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql4))

    client.close()

if __name__ == "__main__":
    run()
