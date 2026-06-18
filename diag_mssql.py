import paramiko
import time

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

    # Use a docker container with sqlcmd (mssql-tools) to query 205
    # First create temp container that has sqlcmd
    print("=== Usando contenedor temporal con mssql-tools ===")
    
    queries = {
        "LOTES_ACIDO_CITRICO_CON_STOCK": """
            SELECT NumLote, CodArticulo, DescArticulo, 
                   CONVERT(VARCHAR,FechaVencimiento,103) as FecVenc, 
                   CantidadActual, CodAlmacen, Estado,
                   CASE WHEN FechaVencimiento < GETDATE() THEN 'VENCIDO' ELSE 'VIGENTE' END as EstVenc
            FROM saLoteArticulo 
            WHERE CodArticulo='MP04N00X021' AND CantidadActual>0 
            ORDER BY FechaVencimiento DESC
        """,
        "LOTE_ESPECIFICO_3AX2112019": """
            SELECT NumLote, CodArticulo, DescArticulo, 
                   CONVERT(VARCHAR,FechaVencimiento,103) as FecVenc, 
                   CantidadActual, CodAlmacen, Estado
            FROM saLoteArticulo WHERE NumLote='3AX2112019'
        """,
        "ODP_COMPUESTO32": """
            SELECT TOP 5 NumOrdProduccion, CodArticulo, DescArticulo, 
                   CONVERT(VARCHAR,FechaCreacion,103) as FecCrea, Estado, Cantidad
            FROM saOrdenProduccion 
            WHERE DescArticulo LIKE '%COMPUESTO%32%' 
            ORDER BY FechaCreacion DESC
        """,
        "LOTES_AZUCAR_EN_P1PS": """
            SELECT NumLote, CodArticulo, DescArticulo, 
                   CONVERT(VARCHAR,FechaVencimiento,103) as FecVenc, 
                   CantidadActual, CodAlmacen, Estado,
                   CASE WHEN FechaVencimiento < GETDATE() THEN 'VENCIDO' ELSE 'VIGENTE' END as EstVenc
            FROM saLoteArticulo 
            WHERE CodArticulo='MP01N00X153' AND CantidadActual>0 
            ORDER BY FechaVencimiento DESC
        """,
    }
    
    for label, sql in queries.items():
        print(f"\n=== {label} ===")
        clean_sql = " ".join(sql.split())
        
        cmd = (
            f'echo "{JUMP_PASS}" | sudo -S docker run --rm --network host mcr.microsoft.com/mssql-tools '
            f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
            f'-d {SQL_DB} -h -1 -W -Q "{clean_sql}"'
        )
        
        stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
        out = stdout.read().decode(errors='replace').strip()
        err = stderr.read().decode(errors='replace').strip()
        
        if out:
            print(out)
        else:
            print("(sin resultados)")
        
        if err and 'password' not in err.lower() and 'sudo' not in err.lower():
            print(f"ERR: {err[:400]}")
    
    client.close()

if __name__ == "__main__":
    run()
