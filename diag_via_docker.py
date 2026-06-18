import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"
SQL_USER = "sa"
SQL_PASS = "GRW7czL3*"
SQL_DB = "carmal_a"

def query_via_container(client, sql):
    """Execute SQL query on 205 via docker container that has sqlcmd"""
    cmd = f'echo "{JUMP_PASS}" | sudo -S docker exec production-report-db sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" -d {SQL_DB} -h -1 -W -Q "{sql}"'
    stdin, stdout, stderr = client.exec_command(cmd, timeout=20)
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    return out, err

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)
    
    # Check if we can reach 205 from the container
    print("=== TEST CONECTIVIDAD A 205 ===")
    cmd = f'echo "{JUMP_PASS}" | sudo -S docker exec production-report-db timeout 5 bash -c "cat < /dev/tcp/{TARGET_SQL}/1433 && echo OPEN || echo CLOSED" 2>&1'
    stdin, stdout, stderr = client.exec_command(cmd)
    print(stdout.read().decode(errors='replace').strip())
    
    # Try using sqlcmd from the container
    print("\n=== LOTES ACIDO CITRICO (MP04N00X021) con stock > 0 ===")
    sql = "SELECT NumLote, CodArticulo, CONVERT(VARCHAR,FechaVencimiento,103), CantidadActual, CodAlmacen, Estado FROM saLoteArticulo WHERE CodArticulo='MP04N00X021' AND CantidadActual>0 ORDER BY FechaVencimiento DESC"
    out, err = query_via_container(client, sql)
    print(out or "(sin resultados)")
    if err and 'sudo' not in err and 'password' not in err.lower():
        print(f"ERR: {err[:400]}")
    
    print("\n=== LOTE ESPECIFICO 3AX2112019 ===")
    sql2 = "SELECT NumLote, CodArticulo, DescArticulo, CONVERT(VARCHAR,FechaVencimiento,103), CantidadActual, CodAlmacen, Estado FROM saLoteArticulo WHERE NumLote='3AX2112019'"
    out, err = query_via_container(client, sql2)
    print(out or "(sin resultados)")

    print("\n=== ODP COMPUESTO 32 RECIENTES ===")
    sql3 = "SELECT TOP 5 NumOrdProduccion, CodArticulo, DescArticulo, CONVERT(VARCHAR,FechaCreacion,103), Estado, Cantidad FROM saOrdenProduccion WHERE DescArticulo LIKE '%COMPUESTO%32%' ORDER BY FechaCreacion DESC"
    out, err = query_via_container(client, sql3)
    print(out or "(sin resultados)")

    client.close()

if __name__ == "__main__":
    run()
