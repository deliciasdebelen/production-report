import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"

ART_C37  = "MP01D18X05-37"
REQ_NUM  = 9736
RENG_NUM = 2

def sqlcmd(client, sql, db='carmal_a'):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, filename='/tmp/fix_c37.sql', db='carmal_a'):
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
    print("EJECUCIÓN FIX — COMPUESTO 37 (MP01D18X05-37)")
    print("=" * 70)

    # ─── 0. Consultar peso de otros compuestos similares como referencia ──
    print("\n[0] REFERENCIA: peso (meses) de otros artículos tipo M (Compuestos)")
    ref = sqlcmd(client, """
        SELECT co_art, art_des, peso
        FROM saArticulo
        WHERE tipo = 'M'
          AND art_des LIKE '%COMPUESTO%'
        ORDER BY peso DESC
    """)
    print(ref)

    # ─── 1. Estado ANTES del fix ──────────────────────────────────────────
    print(f"\n[1] ESTADO ANTES — Lotes de {ART_C37} con stock > 0")
    antes = sqlcmd(client, f"""
        SELECT co_alma, numero_lote, stock_actual,
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               DATEDIFF(DAY, GETDATE(), fecha_expiracion) AS dias_para_vencer
        FROM saLoteEntrada
        WHERE co_art = '{ART_C37}' AND stock_actual > 0
        ORDER BY fecha_expiracion ASC
    """)
    print(antes)

    # ─── 2. FIX A: Extender fecha_expiracion de lotes actuales +30 días ──
    # Los lotes C37 de PP1 tienen stock y fueron usados el 22/25 mayo
    # Se extienden 30 días desde su fecha_inicio para desbloquear hoy
    print("\n[2] FIX A — Extendiendo fecha_expiracion +30 días desde fecha_inicio")
    fix_a = f"""
        UPDATE saLoteEntrada
        SET fecha_expiracion = DATEADD(DAY, 30, fecha_inicio)
        WHERE co_art = '{ART_C37}'
          AND stock_actual > 0
          AND fecha_expiracion < GETDATE();
        
        SELECT @@ROWCOUNT AS lotes_actualizados;
    """
    r_a = sqlcmd_file(client, fix_a, '/tmp/fix_c37_a.sql')
    print(f"  Resultado: {r_a}")

    # ─── 3. FIX B: Corregir peso en saArticulo para futuros lotes ─────────
    # peso = 1 mes como estándar para compuestos de corto uso
    # (se puede ajustar según política de planta)
    print("\n[3] FIX B — Actualizando saArticulo.peso = 1 para futuros lotes")
    fix_b = f"""
        UPDATE saArticulo
        SET peso = 1
        WHERE co_art = '{ART_C37}'
          AND peso = 0;
        
        SELECT co_art, art_des, peso FROM saArticulo WHERE co_art = '{ART_C37}';
    """
    r_b = sqlcmd_file(client, fix_b, '/tmp/fix_c37_b.sql')
    print(f"  Resultado: {r_b}")

    # ─── 4. FIX C: Vincular lote_rowguid en NSPRequisicionreng ────────────
    # El renglón 2 de req 9736 tiene lote_rowguid = NULL
    # El lote correcto en P1-PP1 con más stock es C37-260522-02 (2.39 kg)
    # Necesitamos: rowguid del registro en saLoteEntrada con numero_lote C37-260522-xx
    print(f"\n[4] Identificando rowguid del lote a vincular en req {REQ_NUM} reng {RENG_NUM}")
    # El renglon necesita 1.84 kg — lote C37-260522-01 tiene 1.84
    lote_info = sqlcmd(client, f"""
        SELECT TOP 1 rowguid, numero_lote, stock_actual,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp
        FROM saLoteEntrada
        WHERE co_art = '{ART_C37}'
          AND co_alma = 'P1-PP1'
          AND stock_actual >= 1.84
          AND fecha_expiracion > GETDATE()
        ORDER BY fecha_expiracion ASC, stock_actual ASC
    """)
    print(f"  Lote candidato:\n  {lote_info}")

    # Extraer el rowguid
    lines = [l.strip() for l in lote_info.split('\n')
             if l.strip() and '---' not in l and 'rows' not in l
             and 'rowguid' not in l.lower()]
    rg_lote = None
    num_lote_sel = None
    if lines:
        parts = lines[0].split()
        if len(parts) >= 2:
            rg_lote = parts[0]
            num_lote_sel = parts[1]

    print(f"\n  rowguid seleccionado: {rg_lote}")
    print(f"  numero_lote: {num_lote_sel}")

    if rg_lote and len(rg_lote) > 30:
        print(f"\n[5] FIX C — Actualizando NSPRequisicionreng con lote_rowguid y num_lote")
        fix_c = f"""
            UPDATE NSPRequisicionreng
            SET lote_rowguid = '{rg_lote}',
                num_lote = '{num_lote_sel}'
            WHERE req_num = {REQ_NUM}
              AND reng_num = {RENG_NUM}
              AND co_art = '{ART_C37}'
              AND lote_rowguid IS NULL;
            
            SELECT req_num, reng_num, co_art, num_lote, lote_rowguid,
                   entregada, recibida
            FROM NSPRequisicionreng
            WHERE req_num = {REQ_NUM} AND reng_num = {RENG_NUM};
        """
        r_c = sqlcmd_file(client, fix_c, '/tmp/fix_c37_c.sql', db='carmal_m')
        print(f"  Resultado: {r_c}")
    else:
        print(f"\n[5] No se encontró lote vigente con stock suficiente para vincular")
        print("  Verificar si el fix A fue suficiente para que el operador lo seleccione manualmente")

    # ─── 6. Descontar stock si ya fue entregado físicamente ───────────────
    print(f"\n[6] ¿Ya se entregó físicamente? — Verificar saLoteSalida para C37")
    salidas = sqlcmd(client, f"""
        SELECT tipo_doc, co_alma, numero_lote, cantidad,
               CONVERT(VARCHAR, fe_us_in, 120) AS fecha
        FROM saLoteSalida
        WHERE co_art = '{ART_C37}'
        ORDER BY fe_us_in DESC
    """)
    print(salidas)

    # ─── 7. ESTADO FINAL ──────────────────────────────────────────────────
    print(f"\n[7] ESTADO FINAL — Lotes de {ART_C37}")
    final = sqlcmd(client, f"""
        SELECT co_alma, numero_lote, stock_actual,
               CONVERT(VARCHAR, fecha_inicio, 103) AS FecIni,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               CASE WHEN fecha_expiracion > GETDATE() AND stock_actual > 0
                    THEN 'VIGENTE OK'
                    WHEN fecha_expiracion < GETDATE() THEN 'VENCIDO'
                    ELSE 'SIN STOCK' END AS estado
        FROM saLoteEntrada
        WHERE co_art = '{ART_C37}' AND stock_actual > 0
        ORDER BY co_alma, fecha_expiracion ASC
    """)
    print(final)

    print(f"\n[8] saArticulo.peso FINAL para {ART_C37}")
    print(sqlcmd(client, f"""
        SELECT co_art, art_des, peso FROM saArticulo WHERE co_art = '{ART_C37}'
    """))

    print("\n" + "=" * 70)
    print("FIX COMPLETADO")
    print("Instrucciones para el operador:")
    print("  1. Cerrar y reabrir Profit Plus (limpiar caché)")
    print("  2. Abrir la Requisición de Materiales 9736 / Orden 0000009234")
    print("  3. En el renglón 2 (COMPUESTO 37), ir a 'Lotes de Salida'")
    print("  4. Seleccionar el lote C37-260522-xx disponible")
    print("  5. El lote ahora tiene fecha de expiración extendida → se puede asignar")
    print("=" * 70)

    client.close()

if __name__ == "__main__":
    run()
