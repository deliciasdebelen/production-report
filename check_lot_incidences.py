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
    print("INSPECCIONANDO LAS ENTRADAS DE LOTE 20201101A1 CON STOCK > 0 EN P1-PP")
    print("=" * 80)
    # We want to see all entries in P1-PP that have stock_actual > 0, listing their specific start and expiry dates.
    sql_ent_pp = """
        SELECT le.co_alma, le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 120) as FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 120) as FecExp,
               le.co_us_in, CONVERT(VARCHAR, le.fe_us_in, 120) as FeUsIn
        FROM saLoteEntrada le
        WHERE le.numero_lote = '20201101A1' 
          AND le.co_alma = 'P1-PP'
          AND le.stock_actual > 0
        ORDER BY le.fecha_inicio
    """
    print(sqlcmd(client, sql_ent_pp))

    print("\n" + "=" * 80)
    print("INSPECCIONANDO ENTRADAS EN P1-PP1 CON STOCK > 0")
    print("=" * 80)
    sql_ent_pp1 = """
        SELECT le.co_alma, le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_inicio, 120) as FecIni,
               CONVERT(VARCHAR, le.fecha_expiracion, 120) as FecExp,
               le.co_us_in, CONVERT(VARCHAR, le.fe_us_in, 120) as FeUsIn
        FROM saLoteEntrada le
        WHERE le.numero_lote = '20201101A1' 
          AND le.co_alma = 'P1-PP1'
          AND le.stock_actual > 0
        ORDER BY le.fecha_inicio
    """
    print(sqlcmd(client, sql_ent_pp1))

    client.close()

if __name__ == "__main__":
    run()
