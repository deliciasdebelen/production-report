import paramiko
import sys
sys.path.insert(0, '.')
from sp_fix_v2_strings import SP_FIX_V2, SP_FIX_V2_BODY

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

TRIGGER_DROP = """
IF OBJECT_ID('dbo.trg_AutoReconciliarGCOM') IS NOT NULL
    DROP TRIGGER dbo.trg_AutoReconciliarGCOM;
"""

TRIGGER_BODY = """
CREATE TRIGGER [dbo].[trg_AutoReconciliarGCOM]
ON [dbo].[saLoteSalida]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF NOT EXISTS (SELECT 1 FROM inserted WHERE tipo_doc = 'GCOM')
        RETURN;
    EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision = 0, @fecha_desde = NULL;
END;
"""

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, filename='/tmp/fix.sql', db=SQL_DB):
    sftp = client.open_sftp()
    with sftp.file(filename, 'w') as f:
        f.write(sql_content)
    sftp.close()
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {filename} 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    return stdout.read().decode(errors='replace').strip()

def run(apply=False):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("FIX v2: sp_ReconciliarLotesGCOM (matching mejorado)")
    print("=" * 70)

    # 1. DROP + CREATE SP
    print("\n[1] Reinstalando SP v2...")
    r1 = sqlcmd_file(client, SP_FIX_V2, '/tmp/sp_drop.sql')
    print(f"  DROP: {r1 if r1 else 'OK'}")
    r2 = sqlcmd_file(client, SP_FIX_V2_BODY, '/tmp/sp_create.sql')
    print(f"  CREATE: {r2 if r2 else 'OK'}")

    # 2. DRY RUN
    print("\n[2] DRY RUN — sp_ReconciliarLotesGCOM @solo_revision=1 ...")
    dry = sqlcmd(client, "EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=1, @fecha_desde='2026-01-01'")
    print(dry)

    # 3. Aplicar si se pide
    if apply:
        print("\n[3] APLICANDO CAMBIOS (@solo_revision=0)...")
        apply_result = sqlcmd(client, "EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=0, @fecha_desde='2026-01-01'")
        print(apply_result)
    else:
        print("\n[3] Para aplicar cambios ejecutar: python3 apply_fix_v2.py --apply")

    # 4. Reinstalar trigger
    print("\n[4] Reinstalando trigger trg_AutoReconciliarGCOM...")
    r3 = sqlcmd_file(client, TRIGGER_DROP, '/tmp/trg_drop.sql')
    print(f"  DROP: {r3 if r3 else 'OK'}")
    r4 = sqlcmd_file(client, TRIGGER_BODY, '/tmp/trg_create.sql')
    print(f"  CREATE: {r4 if r4 else 'OK'}")

    # 5. Resumen
    print("\n[5] Objetos activos en carmal_a:")
    print(sqlcmd(client, """
        SELECT o.name, o.type_desc, CONVERT(VARCHAR, o.modify_date, 120) AS modificado
        FROM sys.objects o
        WHERE o.name IN ('sp_ReconciliarLotesGCOM', 'trg_AutoReconciliarGCOM')
    """))

    client.close()

if __name__ == "__main__":
    apply = '--apply' in sys.argv
    run(apply=apply)
