"""
analisis_integracion_M_A_v2.py
Flujo completo con columnas correctas + SPs visibles leidos
"""
import pyodbc

SERVER = "192.168.1.205"
def conn(db):
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};'
        f'DATABASE={db};UID=PROFIT;PWD=profit;'
        'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)

ca = conn("CARMAL_A")
cm = conn("CARMAL_M")
ca_cur = ca.cursor()
cm_cur = cm.cursor()

SEP = "=" * 70

# ──────────────────────────────────────────────────────────────────────────
# NSPMantenimiento - parametros clave
# ──────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}\n  NSPMantenimiento (config global de manufactura)\n{SEP}")
cm_cur.execute("SELECT AjusEnt, AjusSal, AjustSalPT, almacenTEMP, almacenPP FROM NSPMantenimiento")
r = cm_cur.fetchone()
print(f"  AjusEnt={r[0]}  AjusSal={r[1]}  AjustSalPT={r[2]}")
print(f"  almacenTEMP={r[3]}  almacenPP={r[4]}")
ajus_ent = r[0].strip() if r[0] else ''
ajus_sal = r[1].strip() if r[1] else ''

# ──────────────────────────────────────────────────────────────────────────
# FLUJO POR ODP
# ──────────────────────────────────────────────────────────────────────────
for odp_num in ['0000008844', '0000008880']:
    odp_short = int(odp_num)
    print(f"\n{'─'*70}")
    print(f"  FLUJO COMPLETO ODP {odp_num}")
    print(f"{'─'*70}")

    # 1. Orden de produccion
    cm_cur.execute(f"""
    SELECT odp_num, co_for, co_art, status, cantidad,
           almacendest, num_lote, CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPOrdenproduccion WHERE odp_num = '{odp_num}'
    """)
    odp = cm_cur.fetchone()
    if not odp:
        print("  ODP no encontrada"); continue
    print(f"\n  [A] NSPOrdenproduccion:")
    print(f"      art={odp[2].strip()} cant={odp[4]} status={odp[3].strip()}")
    print(f"      formula={odp[1]} alma_dest={odp[5].strip()} lote={odp[6].strip() if odp[6] else ''}")

    # 2. Renglones de la orden (insumos requeridos)
    cm_cur.execute(f"""
    SELECT reng_num, co_art, requerida, solicitada, recibida, devuelta,
           co_uni, co_alma, costo
    FROM NSPOrdenproduccionreng WHERE odp_num = '{odp_num}'
    ORDER BY reng_num
    """)
    rengs = cm_cur.fetchall()
    print(f"\n  [B] NSPOrdenproduccionreng ({len(rengs)} insumos):")
    for r in rengs:
        print(f"      reng={r[0]} art={r[1].strip()} req={r[2]} sol={r[3]} "
              f"rec={r[4]} dev={r[5]} alma={r[7].strip()}")

    # 3. Requisiciones
    cm_cur.execute(f"""
    SELECT req_num, ESTATUS, CONFIRMA, tras_num,
           CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPRequisicion WHERE odp_num = '{odp_num}'
    ORDER BY req_num
    """)
    reqs = cm_cur.fetchall()
    print(f"\n  [C] NSPRequisicion ({len(reqs)} requisicion(es)):")
    for req in reqs:
        tras = req[3].strip() if req[3] else 'N/A'
        print(f"      req={req[0].strip()} status={req[1].strip()} confirma={req[2]} "
              f"traslado_asociado={tras} fecha={req[4]}")

        cm_cur.execute(f"""
        SELECT reng_num, co_art, requerida, solicitada, entregada,
               alma_ori, alma_des, num_envio, num_lote, lote_rowguid
        FROM NSPRequisicionreng WHERE req_num = '{req[0]}'
        ORDER BY reng_num
        """)
        for rr in cm_cur.fetchall():
            envio = rr[7].strip() if rr[7] else ''
            lote  = rr[8].strip() if rr[8] else ''
            print(f"        reng={rr[0]} art={rr[1].strip()} req={rr[2]} "
                  f"sol={rr[3]} ent={rr[4]} "
                  f"ori={rr[5].strip()} des={rr[6].strip()} "
                  f"traslado={envio} lote={lote}")

    # 4. Traslados en CARMAL_A asociados
    ca_cur.execute(f"""
    SELECT tras_num, confirma, anulado, alm_orig, alm_dest, motivo_glo
    FROM saTraslado
    WHERE motivo_glo LIKE '%ODP:%{odp_short}%'
       OR motivo_glo LIKE '%ODP: {odp_short}%'
    ORDER BY tras_num
    """)
    traslados = ca_cur.fetchall()
    print(f"\n  [D] saTraslado en CARMAL_A ({len(traslados)} traslado(s)):")
    for t in traslados:
        print(f"      tras={t[0].strip()} confirma={t[1]} anulado={t[2]} "
              f"{t[3].strip()} -> {t[4].strip()}")
        print(f"        motivo='{t[5].strip()}'")
        # Renglones del traslado
        ca_cur.execute(f"""
        SELECT reng_num, co_art, total_art, co_uni,
               CONVERT(VARCHAR(36),rowguid) AS rg
        FROM saTrasladoReng WHERE tras_num = '{t[0]}'
        ORDER BY reng_num
        """)
        for tr in ca_cur.fetchall():
            print(f"        reng={tr[0]} art={tr[1].strip()} cant={tr[2]} uni={tr[3].strip()}")
        # Lotes generados
        ca_cur.execute(f"""
        SELECT le.numero_lote, le.co_alma, le.tipo_doc,
               le.cantidad, le.stock_actual,
               CONVERT(VARCHAR(36),le.rowguid) AS rg
        FROM saLoteEntrada le
        JOIN saTrasladoReng tr ON tr.rowguid = le.rowguid_reng
        WHERE tr.tras_num = '{t[0]}'
        ORDER BY le.co_art, le.numero_lote
        """)
        lotes = ca_cur.fetchall()
        if lotes:
            print(f"        => saLoteEntrada ({len(lotes)} fila(s) generadas):")
            for l in lotes[:5]:
                print(f"           lote={l[0].strip()} alma={l[1].strip()} "
                      f"tipo={l[2]} cant={l[3]} stock={l[4]}")
            if len(lotes) > 5:
                print(f"           ... ({len(lotes)-5} mas)")

    # 5. Devoluciones
    cm_cur.execute(f"""
    SELECT dev_num, CONFIRMA, Status,
           CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPDevolucion WHERE odp_num = '{odp_num}'
    ORDER BY dev_num
    """)
    devs = cm_cur.fetchall()
    print(f"\n  [E] NSPDevolucion ({len(devs)} devolucion(es)):")
    for dev in devs:
        print(f"      dev={dev[0].strip()} confirma={dev[1]} "
              f"status={dev[2].strip()} fecha={dev[3]}")
        cm_cur.execute(f"""
        SELECT reng_num, co_art, cant_dev, alma_ori, alma_des,
               num_lote, num_envio
        FROM NSPDevolucionReng WHERE dev_num = '{dev[0]}'
        ORDER BY reng_num
        """)
        for dr in cm_cur.fetchall():
            envio = dr[6].strip() if dr[6] else ''
            print(f"        reng={dr[0]} art={dr[1].strip()} cant_dev={dr[2]} "
                  f"ori={dr[3].strip()} des={dr[4].strip()} "
                  f"lote={dr[5].strip()} traslado_dev={envio}")

    # 6. Cierre
    cm_cur.execute(f"""
    SELECT cie_num, confirma, anulado, aju_num,
           CONVERT(VARCHAR,fec_emis,120) AS fec_emis
    FROM NSPCierreOP WHERE odp_num = '{odp_num}'
    ORDER BY cie_num
    """)
    cierres = cm_cur.fetchall()
    print(f"\n  [F] NSPCierreOP ({len(cierres)} cierre(s)):")
    for cie in cierres:
        print(f"      cie={cie[0].strip()} confirma={cie[1]} anulado={cie[2]} "
              f"aju_num={cie[3]} fecha={cie[4]}")
        # Renglones del cierre (PT)
        cm_cur.execute(f"""
        SELECT reng_num, co_art, total_art, costo_uni, co_uni, nro_lote
        FROM NSPCierreOPReng WHERE cie_num = '{cie[0]}'
        """)
        for cr in cm_cur.fetchall():
            print(f"        reng={cr[0]} art={cr[1].strip()} cant={cr[2]} "
                  f"costo={cr[3]} lote={cr[5].strip()}")
        # Insumos del cierre (NSPCostocierre)
        cm_cur.execute(f"""
        SELECT co_art, co_alma, cantidad, costo_uni, NUM_LOTE
        FROM NSPCostocierre WHERE num_cierre = '{cie[0].strip()}'
        ORDER BY co_art
        """)
        insumos = cm_cur.fetchall()
        print(f"        NSPCostocierre ({len(insumos)} insumo(s)):")
        for ins in insumos:
            print(f"          art={ins[0].strip()} alma={ins[1].strip()} "
                  f"cant={ins[2]} costo={ins[3]} lote={ins[4].strip()}")

    # 7. Ajuste en CARMAL_A generado por el cierre
    ca_cur.execute(f"""
    SELECT ajue_num, co_tipo, motivo, confirma, anulado,
           CONVERT(VARCHAR(19),fecha,120) AS fecha
    FROM saAjuste
    WHERE motivo LIKE '%ODP:%{odp_short}%'
       OR motivo LIKE '%ODP: {odp_short}%'
       OR motivo LIKE '%{odp_num}%'
    ORDER BY fecha
    """)
    ajustes = ca_cur.fetchall()
    print(f"\n  [G] saAjuste en CARMAL_A ({len(ajustes)} ajuste(s)):")
    for a in ajustes:
        print(f"      ajue={a[0].strip()} tipo={a[1].strip()} "
              f"confirma={a[3]} anulado={a[4]} fecha={a[5]}")
        print(f"        motivo='{a[2].strip()}'")
        # Renglones del ajuste
        ca_cur.execute(f"""
        SELECT reng_num, co_art, total_art, costo_uni, co_uni
        FROM saAjusteReng WHERE ajue_num = '{a[0]}'
        ORDER BY reng_num
        """)
        for ar in ca_cur.fetchall():
            print(f"        reng={ar[0]} art={ar[1].strip()} "
                  f"cant={ar[2]} costo={ar[3]} uni={ar[4].strip()}")

# ──────────────────────────────────────────────────────────────────────────
# TRIGGERS VISIBLES - LOGICA CLAVE
# ──────────────────────────────────────────────────────────────────────────
print(f"\n{SEP}\n  TRIGGERS VISIBLES CLAVE EN CARMAL_A\n{SEP}")
for trg in ['trg_AjusteReng_Insert_Manufactura', 'TrigEstado_saAjuste',
            'TrigEstado_saTraslado', 'trg_RollupTrasNum_Requisicion']:
    for db_name, cur_x in [("CARMAL_A", ca_cur), ("CARMAL_M", cm_cur)]:
        cur_x.execute(f"""
        SELECT definition FROM sys.sql_modules
        WHERE object_id = OBJECT_ID('{trg}')
        """)
        row = cur_x.fetchone()
        if row and row[0]:
            text = row[0]
            print(f"\n  [{db_name}] {trg} ({len(text)} chars)")
            with open(f"trg_{trg}_{db_name}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            print(f"  Guardado en trg_{trg}_{db_name}.txt")
            # Mostrar las lineas clave
            for i, line in enumerate(text.split('\n')):
                ls = line.strip()
                if any(k in ls for k in ['EXEC ', 'exec ', 'INSERT', 'UPDATE',
                                         'CARMAL', 'DB2k12', 'NSP', 'aju_num']):
                    print(f"    [{i:3d}] {ls[:120]}")

ca.close()
cm.close()
print(f"\n{SEP}\n  ANALISIS COMPLETADO\n{SEP}")
