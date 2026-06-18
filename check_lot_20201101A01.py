import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"

def sqlcmd(client, sql, db):
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
    print("BÚSQUEDA EN BASE DE DATOS CARMAL_A")
    print("=" * 80)
    
    sql_ent_a = """
        SELECT numero_lote, co_art, co_alma, cantidad, stock_actual,
               CONVERT(VARCHAR, fecha_inicio, 103) as FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) as FecExp
        FROM saLoteEntrada
        WHERE numero_lote LIKE '%20201101A01%'
    """
    print("saLoteEntrada (exacto):")
    print(sqlcmd(client, sql_ent_a, "carmal_a"))

    sql_ent_a_like = """
        SELECT TOP 10 numero_lote, co_art, co_alma, cantidad, stock_actual
        FROM saLoteEntrada
        WHERE numero_lote LIKE '%20201101%' OR numero_lote LIKE '%1101A01%'
    """
    print("\nsaLoteEntrada (búsqueda parcial '%20201101%' o '%1101A01%'):")
    print(sqlcmd(client, sql_ent_a_like, "carmal_a"))

    print("\n" + "=" * 80)
    print("BÚSQUEDA EN BASE DE DATOS CARMAL_M")
    print("=" * 80)
    
    sql_ent_m = """
        SELECT numero_lote, co_art, co_alma, cantidad, stock_actual,
               CONVERT(VARCHAR, fecha_inicio, 103) as FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) as FecExp
        FROM saLoteEntrada
        WHERE numero_lote LIKE '%20201101A01%'
    """
    print("saLoteEntrada (exacto):")
    print(sqlcmd(client, sql_ent_m, "carmal_m"))

    sql_ent_m_like = """
        SELECT TOP 10 numero_lote, co_art, co_alma, cantidad, stock_actual
        FROM saLoteEntrada
        WHERE numero_lote LIKE '%20201101%' OR numero_lote LIKE '%1101A01%'
    """
    print("\nsaLoteEntrada (búsqueda parcial '%20201101%' o '%1101A01%'):")
    print(sqlcmd(client, sql_ent_m_like, "carmal_m"))

    client.close()

if __name__ == "__main__":
    run()
