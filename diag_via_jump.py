import paramiko
import time

# Nos conectamos al servidor 79 (linux) y desde ahi consultamos el 205 con sqlcmd
JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"
SQL_USER = "sa"
SQL_PASS = "GRW7czL3*"
SQL_DB = "carmal_a"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)
    
    queries = [
        # Lotes de ACIDO CITRICO en P1-PS
        f"sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P '{SQL_PASS}' -d {SQL_DB} -h -1 -W -Q \"SELECT NumLote, CodArticulo, DescArticulo, CONVERT(VARCHAR,FechaVencimiento,103) FecVenc, CantidadActual, CodAlmacen, Estado FROM saLoteArticulo WHERE CodArticulo='MP04N00X021' AND CantidadActual>0 ORDER BY FechaVencimiento DESC\"",
        
        f"sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P '{SQL_PASS}' -d {SQL_DB} -h -1 -W -Q \"SELECT NumLote, CodArticulo, CONVERT(VARCHAR,FechaVencimiento,103) FecVenc, CantidadActual, CodAlmacen FROM saLoteArticulo WHERE NumLote='3AX2112019'\"",
        
        f"sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P '{SQL_PASS}' -d {SQL_DB} -h -1 -W -Q \"SELECT TOP 3 NumOrdProduccion, CodArticulo, DescArticulo, CONVERT(VARCHAR,FechaCreacion,103) FecCrea, Estado, Cantidad FROM saOrdenProduccion WHERE DescArticulo LIKE '%COMPUESTO%32%' ORDER BY FechaCreacion DESC\"",
    ]
    
    labels = [
        "=== LOTES ACIDO CITRICO (MP04N00X021) CON STOCK > 0 ===",
        "=== LOTE ESPECIFICO 3AX2112019 ===",
        "=== ODP COMPUESTO 32 RECIENTES ===",
    ]
    
    for label, q in zip(labels, queries):
        print(f"\n{label}")
        stdin, stdout, stderr = client.exec_command(q, timeout=15)
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        print(out if out.strip() else "(sin resultados)")
        if err.strip():
            print(f"ERR: {err[:300]}")
    
    client.close()

if __name__ == "__main__":
    run()
