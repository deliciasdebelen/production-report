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
    print("DETALLES DE saArtPrecio PARA PT01D01X026 Y PT04D44X001 (PRECIOS CAD)")
    print("=" * 80)
    sql_prices_all = """
        SELECT co_art, co_precio, co_alma, monto, 
               CONVERT(VARCHAR, desde, 120) as Desde,
               CONVERT(VARCHAR, hasta, 120) as Hasta,
               co_us_in,
               CONVERT(VARCHAR, fe_us_in, 120) as CreadoEl,
               co_us_mo,
               CONVERT(VARCHAR, fe_us_mo, 120) as ModificadoEl
        FROM saArtPrecio
        WHERE co_art IN ('PT01D01X026', 'PT04D44X001')
          AND co_precio = 'CAD'
    """
    print(sqlcmd(client, sql_prices_all))

    print("\n" + "=" * 80)
    print("REVISANDO saAjPrecioCostoReng (AJUSTES DE PRECIO DE ESTOS ARTÍCULOS)")
    print("=" * 80)
    # Check if there are any price adjustments in saAjPrecioCostoReng or saAjPrecioCostoM
    sql_cols = "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'saAjPrecioCostoReng' ORDER BY ORDINAL_POSITION"
    print(sqlcmd(client, sql_cols)[:500])

    sql_aj_reng = """
        SELECT TOP 20 aj.ajus_num, r.co_art, r.tipo_precio, r.monto_nuevo,
               CONVERT(VARCHAR, aj.fecha, 120) as Fecha
        FROM saAjPrecioCostoReng r
        JOIN saAjPrecioCostoM aj ON aj.ajus_num = r.ajus_num
        WHERE r.co_art IN ('PT01D01X026', 'PT04D44X001')
        ORDER BY aj.fecha DESC
    """
    print(sqlcmd(client, sql_aj_reng))

    client.close()

if __name__ == "__main__":
    run()
