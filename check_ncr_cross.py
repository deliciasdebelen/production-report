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
    print("DETALLES DE NCR 1942, 2065, 1019 EN saDocumentoVenta")
    print("=" * 80)
    sql_details = """
        SELECT nro_doc, co_tipo_doc, co_cli, doc_orig, nro_orig, 
               total_bruto, total_neto, saldo, anulado,
               CONVERT(VARCHAR, fec_emis, 103) as FecEmis,
               CONVERT(VARCHAR, fec_reg, 103) as FecReg
        FROM saDocumentoVenta
        WHERE co_tipo_doc = 'N/CR'
          AND nro_doc IN ('00001942', '00002065', '00001019')
    """
    print(sqlcmd(client, sql_details))

    print("\n" + "=" * 80)
    print("COLUMNAS DE saCobroDocReng")
    print("=" * 80)
    sql_cols = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saCobroDocReng' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql_cols))

    print("\n" + "=" * 80)
    print("HISTORIAL DE APLICACIÓN EN saCobroDocReng (¿Dónde se usaron estas NCR?)")
    print("=" * 80)
    # Let's search if these NCRs are applied in saCobroDocReng.
    # We will search by matching nro_doc = NCR or doc_num = NCR
    # Let's write a query that searches for these document numbers in saCobroDocReng
    sql_cross = """
        SELECT cob_num, reng_num, co_tipo_doc, nro_doc, mont_cob, rowguid
        FROM saCobroDocReng
        WHERE nro_doc IN ('00001942', '00002065', '00001019')
           OR nro_doc LIKE '%1942' OR nro_doc LIKE '%2065' OR nro_doc LIKE '%1019'
    """
    print(sqlcmd(client, sql_cross))

    client.close()

if __name__ == "__main__":
    run()
