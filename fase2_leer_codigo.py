import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def sqlcmd_raw(client, sql, db=SQL_DB):
    """Run sqlcmd and return full output"""
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -y 0 -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace')

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("FASE 2: LECTURA COMPLETA DE CÓDIGO CRÍTICO")
    print("=" * 70)

    # 1. Trigger TrigEstado_saArtCompuestoGen - full text
    print("\n==== TRIGGER: TrigEstado_saArtCompuestoGen ====")
    sql1 = """
        SELECT sm.definition
        FROM sys.sql_modules sm
        JOIN sys.triggers t ON t.object_id = sm.object_id
        WHERE t.name = 'TrigEstado_saArtCompuestoGen'
    """
    print(sqlcmd_raw(client, sql1))

    # 2. Trigger trg_BlockLoteSinExistencia - full text
    print("\n==== TRIGGER: trg_BlockLoteSinExistencia ====")
    sql2 = """
        SELECT sm.definition
        FROM sys.sql_modules sm
        JOIN sys.triggers t ON t.object_id = sm.object_id
        WHERE t.name = 'trg_BlockLoteSinExistencia'
    """
    print(sqlcmd_raw(client, sql2))

    # 3. Trigger ActualizarFechaLote - full text
    print("\n==== TRIGGER: ActualizarFechaLote ====")
    sql3 = """
        SELECT sm.definition
        FROM sys.sql_modules sm
        JOIN sys.triggers t ON t.object_id = sm.object_id
        WHERE t.name = 'ActualizarFechaLote'
    """
    print(sqlcmd_raw(client, sql3))

    # 4. All stored procedures code
    print("\n==== STORED PROCEDURES LISTADO ====")
    sql4 = """
        SELECT ROUTINE_NAME, ROUTINE_TYPE
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE = 'PROCEDURE'
        ORDER BY ROUTINE_NAME
    """
    print(sqlcmd_raw(client, sql4))

    client.close()

if __name__ == "__main__":
    run()
