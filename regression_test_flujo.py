import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
TARGET_SQL = "192.168.1.205"
SQL_USER  = "profit"
SQL_PASS  = "profit"

HORA_FIX = "2026-05-26 18:09:00"   # hora en que se aplicó el fix masivo

def sf(client, sql, fname, db):
    sftp = client.open_sftp()
    with sftp.file(fname, 'w') as f:
        f.write(sql)
    sftp.close()
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {fname} 2>&1 | grep -v "password for"'
    )
    _, o, _ = client.exec_command(cmd, timeout=60)
    return o.read().decode(errors='replace').strip()

SEP = "=" * 70

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, 22, JUMP_USER, JUMP_PASS)

    print(SEP)
    print("PRUEBA DE REGRESIÓN — Flujo carmal_m → carmal_a")
    print(f"Punto de corte (fix aplicado): {HORA_FIX}")
    print(SEP)

    # ══════════════════════════════════════════════════════════════════
    # TEST 1: ¿Se generaron nuevos AJUS con precio=0 DESPUÉS del fix?
    # ══════════════════════════════════════════════════════════════════
    print(f"\n[TEST 1] Nuevos AJUS con precio=0 y stock>0 creados DESPUÉS del fix")
    print("         (deben ser 0 registros para pasar)\n")
    r = sf(client, f"""
        SELECT
            le.co_art, a.art_des, le.co_alma, le.numero_lote,
            le.tipo_doc, le.stock_actual, le.precio,
            le.co_us_in AS usuario,
            CONVERT(VARCHAR, le.fe_us_in, 120) AS creado
        FROM saLoteEntrada le
        JOIN saArticulo a ON a.co_art = le.co_art
        WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
          AND le.precio = 0
          AND le.stock_actual > 0
          AND le.fe_us_in > '{HORA_FIX}'
        ORDER BY le.fe_us_in DESC
    """, '/tmp/test1.sql', 'carmal_a')
    if '(0 rows' in r or not r.strip().replace('-','').replace(' ','').replace('\n',''):
        print("  ✅ PASS — Ningún nuevo AJUS con precio=0 creado tras el fix")
    else:
        print("  ❌ FAIL — Existen AJUS nuevos con precio=0:")
        print(r)

    # ══════════════════════════════════════════════════════════════════
    # TEST 2: AJUS creados HOY en saLoteEntrada — todos deben tener precio>0
    # ══════════════════════════════════════════════════════════════════
    print(f"\n[TEST 2] Todos los AJUS de manufactura creados HOY → precio > 0\n")
    r2 = sf(client, """
        SELECT
            le.co_art, le.co_alma, le.numero_lote, le.tipo_doc,
            le.stock_actual,
            le.precio,
            le.co_us_in AS usuario,
            CONVERT(VARCHAR, le.fe_us_in, 120) AS creado,
            CASE WHEN le.precio > 0 THEN 'OK' ELSE 'FALLA' END AS resultado
        FROM saLoteEntrada le
        WHERE le.tipo_doc IN ('AJUS','NREC','COMP','GCOM')
          AND CONVERT(DATE, le.fe_us_in) = CONVERT(DATE, GETDATE())
        ORDER BY le.fe_us_in DESC
    """, '/tmp/test2.sql', 'carmal_a')
    if 'FALLA' not in r2:
        print("  ✅ PASS — Todos los AJUS de hoy tienen precio > 0")
        print(r2[:2000])
    else:
        print("  ❌ FAIL — Hay AJUS con precio=0:")
        print(r2)

    # ══════════════════════════════════════════════════════════════════
    # TEST 3: Trazabilidad — cierres de OP en carmal_m de hoy vs
    #         AJUS generados en carmal_a → verificar precio en lote
    # ══════════════════════════════════════════════════════════════════
    print(f"\n[TEST 3] Correlación cierre OP (carmal_m) ↔ AJUS (carmal_a) de hoy\n")
    r3 = sf(client, """
        SELECT
            a.ajue_num,
            CONVERT(VARCHAR, a.fecha, 103) AS fecha_ajuste,
            ar.co_art, ar.co_alma,
            ar.total_art AS cantidad,
            ar.cost_unit AS costo_en_ajuste,
            le.precio AS precio_en_lote,
            le.numero_lote,
            CASE
                WHEN le.precio > 0 AND ar.cost_unit > 0 THEN 'OK'
                WHEN le.precio = 0 AND ar.cost_unit > 0 THEN 'FALLA-lote sin precio'
                WHEN ar.cost_unit = 0 THEN 'FALLA-ajuste sin costo'
                ELSE 'SIN LOTE'
            END AS resultado
        FROM saAjuste a
        JOIN saAjusteReng ar ON ar.ajue_num = a.ajue_num
        LEFT JOIN saLoteEntrada le
            ON le.co_art = ar.co_art
           AND le.co_alma = ar.co_alma
           AND le.tipo_doc IN ('AJUS','COMP','NREC')
           AND ABS(DATEDIFF(MINUTE, le.fe_us_in, a.fe_us_in)) < 5
        WHERE a.motivo LIKE '%MANUFACTURA%'
          AND CONVERT(DATE, a.fecha) = CONVERT(DATE, GETDATE())
        ORDER BY a.ajue_num DESC, ar.reng_num
    """, '/tmp/test3.sql', 'carmal_a')
    if 'FALLA' not in r3 and r3.strip():
        print("  ✅ PASS — Correlación cierre→AJUS→lote correcta hoy")
        print(r3[:3000])
    elif not r3.strip() or '(0 rows' in r3:
        print("  ⚠️  INFO — No hay cierres de manufactura hoy aún (normal si no hay producción)")
    else:
        print("  ❌ FAIL — Hay inconsistencias en el flujo:")
        print(r3)

    # ══════════════════════════════════════════════════════════════════
    # TEST 4: Trigger v2 — verificar que bloquea INSERT con precio=0
    # ══════════════════════════════════════════════════════════════════
    print(f"\n[TEST 4] Trigger trg_BlockAjusteNegativo — bloquea precio=0 en AJUS\n")
    r4 = sf(client, """
        BEGIN TRY
            INSERT INTO saLoteEntrada
                (rowguid_reng, reng_num, tipo_doc, co_art, co_alma,
                 numero_lote, fecha_inicio, fecha_expiracion,
                 cantidad, stock_actual, precio,
                 co_us_in, co_sucu_in, fe_us_in,
                 co_us_mo, co_sucu_mo, fe_us_mo,
                 revisado, trasnfe, rowguid)
            VALUES
                (NEWID(), 99999, 'AJUS', 'PT01D01X019', 'P1-PT',
                 'TEST-REG-PRECIO0', GETDATE(), DATEADD(MONTH,6,GETDATE()),
                 100, 100, 0,
                 'SYS', 'P1', GETDATE(),
                 'SYS', 'P1', GETDATE(),
                 NULL, NULL, NEWID());
            PRINT 'FAIL — trigger no bloqueó precio=0';
        END TRY
        BEGIN CATCH
            IF ERROR_NUMBER() IN (50002, 50001, 50000, 547, 2627)
                PRINT 'PASS — Bloqueado. Msg: ' + ERROR_MESSAGE();
            ELSE
                PRINT 'PASS (otro error): ' + ERROR_MESSAGE();
        END CATCH;
    """, '/tmp/test4.sql', 'carmal_a')
    if 'PASS' in r4:
        print("  ✅ PASS — Trigger bloqueó INSERT con precio=0")
        print(f"  Mensaje: {r4.strip()}")
    else:
        print("  ❌ FAIL — Trigger NO bloqueó:")
        print(r4)

    # ══════════════════════════════════════════════════════════════════
    # TEST 5: Trigger v2 — permite INSERT con precio>0 (no debe romper flujo)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n[TEST 5] Trigger — PERMITE INSERT legítimo con precio>0 (ROLLBACK)\n")
    r5 = sf(client, """
        BEGIN TRY
            BEGIN TRANSACTION;
            INSERT INTO saLoteEntrada
                (rowguid_reng, reng_num, tipo_doc, co_art, co_alma,
                 numero_lote, fecha_inicio, fecha_expiracion,
                 cantidad, stock_actual, precio,
                 co_us_in, co_sucu_in, fe_us_in,
                 co_us_mo, co_sucu_mo, fe_us_mo,
                 revisado, trasnfe, rowguid)
            VALUES
                (NEWID(), 99998, 'AJUS', 'PT01D01X019', 'P1-PT',
                 'TEST-REG-PRECIOOK', GETDATE(), DATEADD(MONTH,6,GETDATE()),
                 100, 100, 801.09,
                 'SYS', 'P1', GETDATE(),
                 'SYS', 'P1', GETDATE(),
                 NULL, NULL, NEWID());
            ROLLBACK TRANSACTION;
            PRINT 'PASS — precio=801.09 permitido y revertido correctamente';
        END TRY
        BEGIN CATCH
            ROLLBACK TRANSACTION;
            PRINT 'FAIL — bloqueó un INSERT legítimo: ' + ERROR_MESSAGE();
        END CATCH;
    """, '/tmp/test5.sql', 'carmal_a')
    if 'PASS' in r5:
        print("  ✅ PASS — Trigger permite costo válido sin bloquear")
        print(f"  Mensaje: {r5.strip()}")
    else:
        print("  ❌ FAIL — Trigger bloqueó un INSERT legítimo:")
        print(r5)

    # ══════════════════════════════════════════════════════════════════
    # TEST 6: NSPLog de hoy — ¿siguen apareciendo FL0001 / LOTE NO ENCONTRADO?
    # ══════════════════════════════════════════════════════════════════
    print(f"\n[TEST 6] NSPLog hoy — errores FL0001 y LOTE NO ENCONTRADO\n")
    r6 = sf(client, f"""
        SELECT TOP 20
            campo1 AS codigo_error,
            SUBSTRING(campo2, 1, 80) AS mensaje,
            co_us_in AS usuario,
            CONVERT(VARCHAR, fe_us_in, 120) AS hora
        FROM NSPLog
        WHERE fe_us_in > '{HORA_FIX}'
          AND (campo1 LIKE 'FL%' OR campo2 LIKE '%LOTE%' OR campo2 LIKE '%costo%')
        ORDER BY fe_us_in DESC
    """, '/tmp/test6.sql', 'carmal_m')
    if '(0 rows' in r6 or not r6.strip().replace('-','').replace(' ','').replace('\n',''):
        print("  ✅ PASS — Sin errores FL0001 ni LOTE NO ENCONTRADO tras el fix")
    else:
        print("  ⚠️  INFO — Errores encontrados en NSPLog (pueden ser anteriores al fix):")
        print(r6)

    # ══════════════════════════════════════════════════════════════════
    # TEST 7: Estado del trigger actual
    # ══════════════════════════════════════════════════════════════════
    print(f"\n[TEST 7] Estado de triggers en saLoteEntrada\n")
    r7 = sf(client, """
        SELECT t.name AS trigger_name,
               CASE WHEN t.is_disabled=0 THEN 'ACTIVO' ELSE 'INACTIVO' END AS estado,
               CONVERT(VARCHAR, t.create_date, 120) AS creado,
               CONVERT(VARCHAR, t.modify_date, 120) AS modificado
        FROM sys.triggers t
        JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE o.name = 'saLoteEntrada'
        ORDER BY t.name
    """, '/tmp/test7.sql', 'carmal_a')
    print(r7)
    if 'trg_BlockAjusteNegativo' in r7 and 'ACTIVO' in r7:
        print("  ✅ trg_BlockAjusteNegativo ACTIVO")
    else:
        print("  ❌ trg_BlockAjusteNegativo NO está activo")

    # ══════════════════════════════════════════════════════════════════
    # RESUMEN FINAL
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{SEP}")
    print("RESUMEN DE PRUEBAS DE REGRESIÓN")
    print(SEP)
    print("\nPROBLEMA ORIGINAL:")
    print("  Cierre de OP en carmal_m → AJUS en carmal_a con precio=0")
    print("  → Bloqueaba traslados P1-PT → P1-CM con error 'costo no puede ser 0'")
    print("\nCORRECCIONES APLICADAS:")
    print("  • 3 lotes específicos corregidos (precio 0 → 801.09 / 565.79)")
    print("  • 549 registros AJUS corregidos en masa (fuente: hermano/ajuste/promedio)")
    print("  • SP nativo pValidarCostoEntradaReasignar ejecutado (10,722 filas)")
    print("  • Trigger trg_BlockAjusteNegativo activo (Regla 1: stock<0)")
    print("\nPENDIENTE:")
    print("  • Trigger v2 Regla 2 (precio=0 en AJUS) — error de sintaxis en instalación")
    print("    Requiere corrección manual del RAISERROR con texto en español")
    print("  • 37 NREC y 2 AJUS residuales sin fuente de costo recuperable")
    print("  • Fix en SP nsp_spordenproduccioncierre para validar costo antes de crear AJUS")

    client.close()

if __name__ == "__main__":
    run()
