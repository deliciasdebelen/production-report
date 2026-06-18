import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def sqlcmd(client, sql, db=SQL_DB, header=True):
    h = "" if header else " -h -1"
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W{h} -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("DIAGNÓSTICO: Compuesto 32 - Error de asignación de lote Ácido Cítrico")
    print("=" * 70)

    # 1. Lotes de ACIDO CITRICO con stock positivo
    print("\n1. LOTES ACIDO CITRICO (MP04N00X021) con CantidadActual > 0")
    print("-" * 70)
    sql = """
        SELECT NumLote, CodArticulo, DescArticulo, 
               CONVERT(VARCHAR,FechaVencimiento,103) AS FecVenc, 
               CantidadActual, CodAlmacen, Estado,
               CASE WHEN FechaVencimiento < GETDATE() THEN 'VENCIDO' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteArticulo 
        WHERE CodArticulo = 'MP04N00X021' AND CantidadActual > 0 
        ORDER BY CodAlmacen, FechaVencimiento DESC
    """
    print(sqlcmd(client, sql))

    # 2. Detalle del lote 3AX2112019 específico
    print("\n2. DETALLE LOTE 3AX2112019 (el que aparece en la pantalla)")
    print("-" * 70)
    sql2 = """
        SELECT NumLote, CodArticulo, DescArticulo, 
               CONVERT(VARCHAR,FechaVencimiento,103) AS FecVenc, 
               CantidadActual, CantidadOriginal, CodAlmacen, Estado
        FROM saLoteArticulo 
        WHERE NumLote = '3AX2112019'
    """
    print(sqlcmd(client, sql2))

    # 3. ODP de Compuesto 32 generación 0000000946
    print("\n3. ORDEN DE PRODUCCIÓN 0000000946 (Compuesto 32)")
    print("-" * 70)
    sql3 = """
        SELECT NumOrdProduccion, CodArticulo, DescArticulo,
               CONVERT(VARCHAR,FechaCreacion,103) AS FecCrea,
               Estado, Cantidad, CantProd, CodAlmacen
        FROM saOrdenProduccion
        WHERE NumOrdProduccion = '0000000946'
    """
    print(sqlcmd(client, sql3))

    # 4. Renglones de la ODP (fórmula)
    print("\n4. RENGLONES (INGREDIENTES) ODP 0000000946")
    print("-" * 70)
    sql4 = """
        SELECT r.NumOrdProduccion, r.NumRenglon, r.CodArticulo, r.DescArticulo,
               r.Cantidad, r.CantidadUsada
        FROM saOrdenProduccionRenglon r
        WHERE r.NumOrdProduccion = '0000000946'
        ORDER BY r.NumRenglon
    """
    print(sqlcmd(client, sql4))

    # 5. Verificar si hay lotes de acido citrico en P1-PS
    print("\n5. LOTES ACIDO CITRICO EN ALMACÉN P1-PS ESPECÍFICAMENTE")
    print("-" * 70)
    sql5 = """
        SELECT NumLote, CodArticulo, 
               CONVERT(VARCHAR,FechaVencimiento,103) AS FecVenc,
               CantidadActual, CodAlmacen, Estado,
               CASE WHEN FechaVencimiento < GETDATE() THEN 'VENCIDO' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteArticulo 
        WHERE CodArticulo = 'MP04N00X021'
          AND CodAlmacen = 'P1-PS'
        ORDER BY FechaVencimiento DESC
    """
    print(sqlcmd(client, sql5))

    # 6. Stock general del artículo
    print("\n6. STOCK GENERAL ACIDO CITRICO EN saArticulo")
    print("-" * 70)
    sql6 = """
        SELECT a.CodArticulo, a.DesArticulo, a.SaldoActual, a.Unidad
        FROM saArticulo a
        WHERE a.CodArticulo = 'MP04N00X021'
    """
    print(sqlcmd(client, sql6))

    # 7. Stock por almacen (saStockAlmacen)
    print("\n7. STOCK POR ALMACÉN - saStockAlmacen (ACIDO CITRICO)")
    print("-" * 70)
    sql7 = """
        SELECT sa.CodArticulo, sa.DescArticulo, sa.CodAlmacen, sa.Saldo, sa.SaldoEnTransito
        FROM saStockAlmacen sa
        WHERE sa.CodArticulo = 'MP04N00X021'
        ORDER BY sa.Saldo DESC
    """
    print(sqlcmd(client, sql7))

    # 8. Verificar configuracion de control de vencimiento
    print("\n8. CONFIGURACIÓN CONTROL DE VENCIMIENTO EN saParametros")
    print("-" * 70)
    sql8 = """
        SELECT * FROM saParametros WHERE Nombre LIKE '%Venc%' OR Nombre LIKE '%Lote%' OR Nombre LIKE '%venc%'
    """
    result8 = sqlcmd(client, sql8)
    print(result8 if result8 else "(Tabla no encontrada o sin parámetros de vencimiento)")

    client.close()

if __name__ == "__main__":
    run()
