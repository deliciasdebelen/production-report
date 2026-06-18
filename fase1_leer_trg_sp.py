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
    print("FASE 1: LECTURA DE TRIGGERS Y STORED PROCEDURES - Módulo Compuesto")
    print("=" * 70)

    # 1. Texto del trigger TrigEstado_saArtCompuestoGen
    print("\n[TRG-1] TRIGGER: TrigEstado_saArtCompuestoGen")
    sql_trg1 = """
        SELECT sm.definition
        FROM sys.sql_modules sm
        JOIN sys.triggers t ON t.object_id = sm.object_id
        WHERE t.name = 'TrigEstado_saArtCompuestoGen'
    """
    print(sqlcmd(client, sql_trg1))

    # 2. Texto del trigger trg_BlockLoteSinExistencia en saLoteSalida
    print("\n[TRG-2] TRIGGER: trg_BlockLoteSinExistencia (en saLoteSalida)")
    sql_trg2 = """
        SELECT sm.definition
        FROM sys.sql_modules sm
        JOIN sys.triggers t ON t.object_id = sm.object_id
        WHERE t.name = 'trg_BlockLoteSinExistencia'
    """
    print(sqlcmd(client, sql_trg2))

    # 3. Texto del trigger ActualizarFechaLote (activo en saLoteEntrada)
    print("\n[TRG-3] TRIGGER: ActualizarFechaLote (saLoteEntrada)")
    sql_trg3 = """
        SELECT sm.definition
        FROM sys.sql_modules sm
        JOIN sys.triggers t ON t.object_id = sm.object_id
        WHERE t.name = 'ActualizarFechaLote'
    """
    print(sqlcmd(client, sql_trg3))

    # 4. Stored Procedures relacionados con compuesto
    print("\n[SP-1] LISTA DE SPs RELACIONADOS CON COMPUESTO")
    sql_sp1 = """
        SELECT ROUTINE_NAME, ROUTINE_TYPE
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_NAME LIKE '%Compuesto%'
           OR ROUTINE_NAME LIKE '%ArtComp%'
           OR ROUTINE_NAME LIKE '%LoteSal%'
           OR ROUTINE_NAME LIKE '%LoteEnt%'
           OR ROUTINE_NAME LIKE '%GCOM%'
        ORDER BY ROUTINE_NAME
    """
    print(sqlcmd(client, sql_sp1))

    # 5. Lista completa de SPs para contexto
    print("\n[SP-2] TODOS LOS STORED PROCEDURES DE carmal_a")
    sql_sp2 = """
        SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE = 'PROCEDURE'
        ORDER BY ROUTINE_NAME
    """
    print(sqlcmd(client, sql_sp2))

    # 6. Verificar todos los triggers de la BD
    print("\n[TRG-ALL] TODOS LOS TRIGGERS EN carmal_a")
    sql_trg_all = """
        SELECT t.name AS trigger_name, o.name AS table_name,
               t.is_disabled, t.is_instead_of_trigger,
               sm.definition
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        JOIN sys.sql_modules sm ON sm.object_id = t.object_id
        ORDER BY o.name, t.name
    """
    print(sqlcmd(client, sql_trg_all))

    client.close()

if __name__ == "__main__":
    run()
