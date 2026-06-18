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
    print("DETALLES DEL ARTÍCULO ME01N00X026")
    print("=" * 80)
    sql_art = "SELECT co_art, art_des, unidad, tipo FROM saArticulo WHERE co_art = 'ME01N00X026'"
    print(sqlcmd(client, sql_art))

    print("\n" + "=" * 80)
    print("TODAS LAS ENTRADAS DEL LOTE 20201101A1 EN saLoteEntrada")
    print("=" * 80)
    sql_ent = """
        SELECT numero_lote, co_art, co_alma, cantidad, stock_actual,
               CONVERT(VARCHAR, fecha_inicio, 103) as FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) as FecExp,
               revisado, rowguid
        FROM saLoteEntrada
        WHERE numero_lote = '20201101A1'
    """
    print(sqlcmd(client, sql_ent))

    print("\n" + "=" * 80)
    print("CONSUMOS/SALIDAS DEL LOTE 20201101A1 EN saLoteSalida")
    print("=" * 80)
    sql_sal = """
        SELECT ls.numero_lote, ls.co_art, ls.co_alma, ls.cantidad, ls.tipo_doc,
               CONVERT(VARCHAR, ls.fe_us_in, 103) as FecSalida, ls.co_us_in
        FROM saLoteSalida ls
        WHERE ls.numero_lote = '20201101A1'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql_sal))

    client.close()

if __name__ == "__main__":
    run()
