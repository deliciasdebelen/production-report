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
    print("REVISANDO saArtPrecio PARA CAMBIO DE PRECIOS EN RANGO 30/10/2025 AL 24/11/2025")
    print("=" * 80)
    # Let's search if any price records were created/modified or active during this range
    sql_prices_range = """
        SELECT co_art, co_precio, monto, 
               CONVERT(VARCHAR, desde, 120) as Desde,
               CONVERT(VARCHAR, hasta, 120) as Hasta,
               co_us_in,
               CONVERT(VARCHAR, fe_us_in, 120) as CreadoEl,
               co_us_mo,
               CONVERT(VARCHAR, fe_us_mo, 120) as ModificadoEl
        FROM saArtPrecio
        WHERE co_art IN ('PT01D01X026', 'PT04D44X001')
          AND co_precio = 'CAD'
          AND (
               (fe_us_in >= '2025-10-30' AND fe_us_in <= '2025-11-25')
               OR (fe_us_mo >= '2025-10-30' AND fe_us_mo <= '2025-11-25')
               OR (desde >= '2025-10-30' AND desde <= '2025-11-25')
          )
    """
    print(sqlcmd(client, sql_prices_range))

    print("\n" + "=" * 80)
    print("REVISANDO HistorialCambiosPrecios SI TIENE REGISTROS EN ESTE RANGO")
    print("=" * 80)
    # Check columns of HistorialCambiosPrecios first
    sql_cols = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'HistorialCambiosPrecios' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql_cols)[:500])

    sql_hist_range = """
        SELECT TOP 20 * FROM HistorialCambiosPrecios
        WHERE fecha >= '2025-10-30' AND fecha <= '2025-11-25'
    """
    # Let's see if the column name is 'fecha' or what columns it has
    print(sqlcmd(client, "SELECT TOP 5 * FROM HistorialCambiosPrecios")[:500])

    client.close()

if __name__ == "__main__":
    run()
