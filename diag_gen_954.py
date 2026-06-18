import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

GEN = "0000000954"

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, filename='/tmp/fix954.sql', db=SQL_DB):
    sftp = client.open_sftp()
    with sftp.file(filename, 'w') as f:
        f.write(sql_content)
    sftp.close()
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {filename} 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print(f"DIAGNÓSTICO + RECONCILIACIÓN — Generación {GEN}")
    print("=" * 70)

    # 1. Encabezado
    print(f"\n[1] ENCABEZADO GEN {GEN}")
    sql1 = f"""
        SELECT gene_num, co_art, co_alma,
               CONVERT(VARCHAR, fecha, 103) AS fecha,
               total_art, gene_art,
               CASE WHEN gene_art = 1 THEN 'CERRADA' ELSE 'ABIERTA' END AS estado,
               CONVERT(VARCHAR, fe_us_in, 120) AS creado,
               CONVERT(VARCHAR, fe_us_mo, 120) AS modificado
        FROM saArtCompuestoGen WHERE gene_num = '{GEN}'
    """
    print(sqlcmd(client, sql1))

    # 2. Renglones e ingredientes
    print(f"\n[2] RENGLONES — estado de lote_asignado")
    sql2 = f"""
        SELECT reng_num, co_art, co_alma, co_uni, total_art,
               lote_asignado,
               CASE WHEN lote_asignado = 1 THEN 'OK' ELSE '*** PENDIENTE ***' END AS estado
        FROM saArtCompuestoGenReng
        WHERE gene_num = '{GEN}'
        ORDER BY reng_num
    """
    print(sqlcmd(client, sql2))

    # 3. GCOMs registrados para esta generación (por fecha)
    print(f"\n[3] GCOMs EN saLoteSalida DEL DÍA DE LA GEN (tipo_doc=GCOM)")
    sql3 = f"""
        DECLARE @fgen DATE = (SELECT CAST(fecha AS DATE) FROM saArtCompuestoGen WHERE gene_num = '{GEN}');
        SELECT ls.tipo_doc, ls.reng_num, ls.co_art, ls.co_alma, ls.numero_lote,
               ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               CAST(ls.rowguid_reng AS VARCHAR(50)) AS rg_reng_actual,
               CASE WHEN r.rowguid IS NOT NULL THEN 'VINCULADO OK' ELSE '*** HUERFANO ***' END AS estado_vinculo
        FROM saLoteSalida ls
        LEFT JOIN saArtCompuestoGenReng r ON r.rowguid = ls.rowguid_reng
        WHERE ls.tipo_doc = 'GCOM'
          AND CAST(ls.fe_us_in AS DATE) BETWEEN ISNULL(@fgen, CAST(GETDATE() AS DATE)) AND CAST(GETDATE() AS DATE)
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql3))

    # 4. GCOMs huérfanos hoy (sin vínculo a GenReng)
    print(f"\n[4] GCOMs HUÉRFANOS RECIENTES (últimas 48 horas)")
    sql4 = """
        SELECT ls.co_art, ls.co_alma, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               CAST(ls.rowguid_reng AS VARCHAR(50)) AS rg_reng_actual,
               CASE WHEN r.rowguid IS NOT NULL THEN 'VINCULADO' ELSE 'HUERFANO' END AS estado
        FROM saLoteSalida ls
        LEFT JOIN saArtCompuestoGenReng r ON r.rowguid = ls.rowguid_reng
        WHERE ls.tipo_doc = 'GCOM'
          AND ls.fe_us_in >= DATEADD(HOUR, -48, GETDATE())
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql4))

    # 5. Verificar si el trigger está activo
    print("\n[5] ESTADO DEL TRIGGER trg_AutoReconciliarGCOM")
    sql5 = """
        SELECT t.name, o.name AS tabla,
               CASE WHEN t.is_disabled = 0 THEN 'ACTIVO' ELSE '*** DESACTIVADO ***' END AS estado
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE t.name = 'trg_AutoReconciliarGCOM'
    """
    print(sqlcmd(client, sql5))

    # 6. Ejecutar reconciliación manual para la fecha de hoy
    print(f"\n[6] EJECUTANDO sp_ReconciliarLotesGCOM — DRY RUN (fecha hoy)")
    dry = sqlcmd(client, "EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=1, @fecha_desde='2026-05-22'")
    print(dry)

    # 7. Si hay reconciliaciones pendientes, aplicar
    if 'REVISION' in dry:
        lines = [l for l in dry.split('\n') if 'REVISION' in l]
        parts = lines[0].split() if lines else []
        n_huerfanos = int(parts[1]) if len(parts) > 1 else 0
        n_reconciliar = int(parts[2]) if len(parts) > 2 else 0
        print(f"\n  → {n_huerfanos} huérfanos | {n_reconciliar} reconciliaciones posibles")

        if n_reconciliar > 0:
            print(f"\n[7] APLICANDO RECONCILIACIÓN ({n_reconciliar} registros)...")
            apply_r = sqlcmd(client, "EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=0, @fecha_desde='2026-05-22'")
            print(apply_r)
        else:
            print(f"\n[7] Sin reconciliaciones automáticas posibles — revisando alternativas...")
            # Quizas la gen 954 es del dia de hoy pero no coincide en fecha
            # Buscar por rango ampliado
            print("    Intentando con fecha_desde='2026-05-20'...")
            dry2 = sqlcmd(client, "EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=1, @fecha_desde='2026-05-20'")
            print(dry2)
            if 'REVISION' in dry2:
                parts2 = [l.split() for l in dry2.split('\n') if 'REVISION' in l]
                n2 = int(parts2[0][2]) if parts2 and len(parts2[0]) > 2 else 0
                if n2 > 0:
                    print(f"\n    Aplicando con rango ampliado ({n2} registros)...")
                    apply2 = sqlcmd(client, "EXEC dbo.sp_ReconciliarLotesGCOM @solo_revision=0, @fecha_desde='2026-05-20'")
                    print(apply2)

    # 8. Estado final de los renglones
    print(f"\n[8] ESTADO FINAL DE RENGLONES GEN {GEN}")
    sql8 = f"""
        SELECT r.reng_num, r.co_art, r.total_art, r.lote_asignado,
               ls.numero_lote, ls.cantidad AS cant_salida,
               CASE WHEN r.lote_asignado = 1 THEN '✓ ASIGNADO' ELSE '✗ PENDIENTE' END AS estado,
               le.stock_actual AS stock_restante
        FROM saArtCompuestoGenReng r
        LEFT JOIN saLoteSalida ls ON ls.rowguid_reng = r.rowguid AND ls.tipo_doc = 'GCOM'
        LEFT JOIN saLoteEntrada le ON le.rowguid = ls.Rowguid_Lote
        WHERE r.gene_num = '{GEN}'
        ORDER BY r.reng_num
    """
    print(sqlcmd(client, sql8))

    client.close()

if __name__ == "__main__":
    run()
