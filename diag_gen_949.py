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

GEN = "0000000949"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print(f"DIAGNÓSTICO - Generación Compuesto {GEN}")
    print("Problema: Lotes seleccionados pero NO consumidos al cerrar orden")
    print("=" * 70)

    # 1. Encabezado de la generación
    print(f"\n[1] ENCABEZADO GENERACIÓN {GEN}")
    sql1 = f"""
        SELECT gene_num, co_art, co_alma, 
               CONVERT(VARCHAR,fecha,103) AS fecha,
               total_art, gene_art,
               CONVERT(VARCHAR,fe_us_in,120) AS creado_en,
               CONVERT(VARCHAR,fe_us_mo,120) AS modificado_en
        FROM saArtCompuestoGen WHERE gene_num = '{GEN}'
    """
    print(sqlcmd(client, sql1))

    # 2. Renglones - ver qué tiene lote_asignado = 0 vs 1
    print(f"\n[2] RENGLONES DE {GEN} - Estado de asignación de lotes")
    sql2 = f"""
        SELECT reng_num, co_art, co_alma, co_uni, total_art, stotal_art,
               lote_asignado,
               CASE WHEN lote_asignado = 1 THEN 'ASIGNADO' ELSE '*** NO ASIGNADO ***' END AS estado
        FROM saArtCompuestoGenReng
        WHERE gene_num = '{GEN}'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql2))

    # 3. Buscar en saLoteSalida los movimientos de esta generación
    # saLoteSalida tiene tipo_doc - para generación de compuesto es 'GC'
    print(f"\n[3] LOTES SALIDA (saLoteSalida) - tipo_doc='GC' para gen {GEN}")
    sql3 = f"""
        SELECT ls.tipo_doc, ls.reng_num, ls.co_art, ls.co_alma, ls.numero_lote,
               ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS registrado_en
        FROM saLoteSalida ls
        WHERE ls.tipo_doc = 'GC'
          AND ls.reng_num IN (
              SELECT reng_num FROM saArtCompuestoGenReng WHERE gene_num = '{GEN}'
          )
        ORDER BY ls.reng_num
    """
    print(sqlcmd(client, sql3))

    # 4. También buscar por rowguid de los renglones
    print(f"\n[4] LOTES SALIDA via rowguid de renglones de {GEN}")
    sql4 = f"""
        SELECT ls.tipo_doc, ls.reng_num, ls.co_art, ls.co_alma, 
               ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS registrado_en
        FROM saLoteSalida ls
        WHERE ls.Rowguid_Lote IN (
            SELECT rowguid FROM saArtCompuestoGenReng WHERE gene_num = '{GEN}'
        )
        ORDER BY ls.reng_num
    """
    print(sqlcmd(client, sql4))

    # 5. Stock actual del ácido cítrico antes y después - comparar con generaciones cerradas
    print(f"\n[5] STOCK ÁCIDO CÍTRICO (MP04N00X021) EN P1-PS POR LOTE")
    sql5 = """
        SELECT numero_lote, co_alma,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               cantidad, stock_actual,
               (cantidad - stock_actual) AS consumido,
               CASE WHEN fecha_expiracion < GETDATE() THEN 'VENCIDO' ELSE 'VIGENTE' END AS EstVenc
        FROM saLoteEntrada
        WHERE co_art = 'MP04N00X021'
          AND co_alma = 'P1-PS'
          AND (cantidad > 0 OR stock_actual > 0)
        ORDER BY fecha_expiracion DESC, numero_lote
    """
    print(sqlcmd(client, sql5))

    # 6. Verificar generaciones recientes CERRADAS vs NO cerradas (gene_art=1 cerrada)
    print(f"\n[6] GENERACIONES RECIENTES COMPUESTO 32 - gene_art indica si está cerrada")
    sql6 = """
        SELECT TOP 15 gene_num, co_art, co_alma,
               CONVERT(VARCHAR,fecha,103) AS fecha,
               total_art, gene_art,
               CASE WHEN gene_art = 1 THEN 'CERRADA' ELSE 'ABIERTA/PENDIENTE' END AS estado
        FROM saArtCompuestoGen
        WHERE co_art LIKE '%D17%' OR co_art LIKE '%COMP%32%' OR co_art = 'MP01D17X05-32'
        ORDER BY fecha DESC, gene_num DESC
    """
    print(sqlcmd(client, sql6))

    # 7. Buscar todas las salidas de lote en la fecha de la generación 949
    print(f"\n[7] TODOS LOS MOVIMIENTOS saLoteSalida DEL DÍA DE LA GEN {GEN}")
    sql7 = f"""
        DECLARE @fecha_gen DATE = (
            SELECT CAST(fecha AS DATE) FROM saArtCompuestoGen WHERE gene_num = '{GEN}'
        );
        SELECT ls.tipo_doc, ls.co_art, ls.co_alma, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS registrado_en
        FROM saLoteSalida ls
        WHERE CAST(ls.fe_us_in AS DATE) = @fecha_gen
          AND ls.co_art = 'MP04N00X021'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql7))

    # 8. Verificar si hay un problema con saArtCompuestoGenReng - ver si el rowguid 
    # del renglon coincide con lo esperado para el lote de acido citrico
    print(f"\n[8] DETALLE RENGLÓN ÁCIDO CÍTRICO EN GEN {GEN} (con rowguid)")
    sql8 = f"""
        SELECT gene_num, reng_num, co_art, co_alma, total_art, lote_asignado,
               CAST(rowguid AS VARCHAR(50)) AS rowguid
        FROM saArtCompuestoGenReng
        WHERE gene_num = '{GEN}'
          AND co_art = 'MP04N00X021'
    """
    print(sqlcmd(client, sql8))

    # 9. Buscar en saLoteSalida por el rowguid específico del renglón
    print(f"\n[9] saLoteSalida con Rowguid_Lote = rowguid del renglón ácido cítrico")
    sql9 = f"""
        DECLARE @rg UNIQUEIDENTIFIER = (
            SELECT rowguid FROM saArtCompuestoGenReng 
            WHERE gene_num = '{GEN}' AND co_art = 'MP04N00X021'
        );
        SELECT tipo_doc, reng_num, co_art, co_alma, numero_lote, cantidad,
               CAST(Rowguid_Lote AS VARCHAR(50)) AS Rowguid_Lote
        FROM saLoteSalida
        WHERE Rowguid_Lote = @rg
    """
    print(sqlcmd(client, sql9))

    # 10. Comparar con una generación EXITOSA - buscar una que sí tenga salidas registradas
    print(f"\n[10] EJEMPLO: GENERACIÓN EXITOSA CON LOTES CONSUMIDOS (Comparación)")
    sql10 = f"""
        SELECT TOP 1 gene_num INTO #gen_ok
        FROM saArtCompuestoGen
        WHERE gene_art = 1 AND co_art LIKE '%D17%'
          AND gene_num != '{GEN}' AND gene_num != '0000000946'
        ORDER BY fecha DESC;
        
        SELECT g.gene_num, r.co_art, r.lote_asignado, ls.numero_lote, ls.cantidad
        FROM #gen_ok g
        JOIN saArtCompuestoGenReng r ON r.gene_num = g.gene_num
        LEFT JOIN saLoteSalida ls ON ls.Rowguid_Lote = r.rowguid
        ORDER BY r.reng_num;
        
        DROP TABLE #gen_ok;
    """
    print(sqlcmd(client, sql10))

    client.close()

if __name__ == "__main__":
    run()
