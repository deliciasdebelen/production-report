"""
analisis_integracion_M_A_v3.py - version final con tipos correctos
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

# NSPMantenimiento
cm_cur.execute("SELECT AjusEnt, AjusSal, AjustSalPT, almacenTEMP, almacenPP FROM NSPMantenimiento")
mant = cm_cur.fetchone()
print(f"{SEP}\n  PARAMETROS NSPMantenimiento\n{SEP}")
print(f"  Tipo ajuste ENTRADA PT : {mant[0]}")
print(f"  Tipo ajuste SALIDA MP  : {mant[1]}")
print(f"  Tipo ajuste SAL PT     : {mant[2]}")
print(f"  Almacen TEMP           : {mant[3]}")
print(f"  Almacen PP (prep)      : {mant[4]}")

for odp_num in ['0000008844', '0000008880']:
    odp_short = int(odp_num)
    print(f"\n{'─'*70}\n  FLUJO COMPLETO ODP {odp_num}\n{'─'*70}")

    # A. Orden de produccion
    cm_cur.execute(f"""
    SELECT co_art, CAST(cantidad AS VARCHAR(20)) AS cantidad, status,
           almacendest, ISNULL(num_lote,'') AS num_lote, co_for,
           CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPOrdenproduccion WHERE odp_num = '{odp_num}'""")
    odp = cm_cur.fetchone()
    if not odp: print("  No encontrada"); continue
    print(f"\n[A] ORDEN DE PRODUCCION")
    print(f"    art={odp[0].strip()} cant={odp[1]} status={odp[2].strip()}")
    print(f"    formula={odp[5]} alma_dest={odp[3].strip()} lote={odp[4].strip()}")

    # B. Renglones ODP (insumos)
    cm_cur.execute(f"""
    SELECT reng_num, co_art,
           CAST(requerida AS VARCHAR) AS req,
           CAST(solicitada AS VARCHAR) AS sol,
           CAST(recibida AS VARCHAR) AS rec,
           CAST(devuelta AS VARCHAR) AS dev,
           co_uni, co_alma
    FROM NSPOrdenproduccionreng WHERE odp_num = '{odp_num}'
    ORDER BY reng_num""")
    rengs = cm_cur.fetchall()
    print(f"\n[B] RENGLONES ODP (insumos en formula) - {len(rengs)} articulos:")
    for r in rengs:
        print(f"    reng={r[0]} art={r[1].strip()} req={r[2]} sol={r[3]} "
              f"rec={r[4]} dev={r[5]} alma_origen={r[7].strip()}")

    # C. Requisiciones
    cm_cur.execute(f"""
    SELECT CAST(req_num AS VARCHAR) AS req_num,
           ISNULL(CAST(ESTATUS AS VARCHAR),'') AS ESTATUS,
           CAST(CONFIRMA AS VARCHAR) AS CONFIRMA,
           ISNULL(CAST(tras_num AS VARCHAR),'') AS tras_num,
           CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPRequisicion WHERE odp_num = '{odp_num}'
    ORDER BY req_num""")
    reqs = cm_cur.fetchall()
    print(f"\n[C] REQUISICIONES - {len(reqs)}:")
    for req in reqs:
        print(f"    req={req[0].strip()} status={req[1].strip()} "
              f"confirma={req[2]} traslado={req[3].strip()} fecha={req[4]}")
        cm_cur.execute(f"""
        SELECT reng_num, co_art,
               CAST(requerida AS VARCHAR) AS req,
               CAST(solicitada AS VARCHAR) AS sol,
               CAST(entregada AS VARCHAR) AS ent,
               alma_ori, alma_des,
               ISNULL(num_envio,'') AS num_envio,
               ISNULL(num_lote,'') AS num_lote
        FROM NSPRequisicionreng
        WHERE req_num = {req[0].strip()}
        ORDER BY reng_num""")
        for rr in cm_cur.fetchall():
            print(f"      reng={rr[0]} art={rr[1].strip()} sol={rr[3]} ent={rr[4]} "
                  f"ori={rr[5].strip()} des={rr[6].strip()} "
                  f"traslado={rr[7].strip()} lote={rr[8].strip()}")

    # D. Traslados CARMAL_A
    ca_cur.execute(f"""
    SELECT tras_num, confirma, anulado, alm_orig, alm_dest, motivo_glo
    FROM saTraslado
    WHERE motivo_glo LIKE '%ODP:%{odp_short}%'
       OR motivo_glo LIKE '%ODP: {odp_short}%'
    ORDER BY tras_num""")
    traslados = ca_cur.fetchall()
    print(f"\n[D] TRASLADOS en CARMAL_A ({len(traslados)}):")
    for t in traslados:
        print(f"    tras={t[0].strip()} confirma={t[1]} anulado={t[2]} "
              f"{t[3].strip()} -> {t[4].strip()}")
        print(f"      motivo='{t[5].strip()}'")
        ca_cur.execute(f"""
        SELECT tr.reng_num, tr.co_art, tr.total_art, tr.co_uni,
               (SELECT COUNT(*) FROM saLoteEntrada le WHERE le.rowguid_reng=tr.rowguid) AS n_lotes
        FROM saTrasladoReng tr WHERE tr.tras_num='{t[0]}'
        ORDER BY tr.reng_num""")
        for tr in ca_cur.fetchall():
            flag = " *** DUPLICADO ***" if tr[4] > 1 else ""
            print(f"      reng={tr[0]} art={tr[1].strip()} cant={tr[2]} "
                  f"-> n_lotes_entrada={tr[4]}{flag}")

    # E. Devoluciones
    cm_cur.execute(f"""
    SELECT CAST(dev_num AS VARCHAR) AS dev_num,
           CAST(CONFIRMA AS VARCHAR) AS CONFIRMA,
           ISNULL(Status,'') AS Status,
           CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPDevolucion WHERE odp_num = '{odp_num}'
    ORDER BY dev_num""")
    devs = cm_cur.fetchall()
    print(f"\n[E] DEVOLUCIONES - {len(devs)}:")
    for dev in devs:
        print(f"    dev={dev[0].strip()} confirma={dev[1]} "
              f"status={dev[2].strip()} fecha={dev[3]}")
        cm_cur.execute(f"""
        SELECT reng_num, co_art,
               CAST(cant_dev AS VARCHAR) AS cant_dev,
               alma_ori, alma_des,
               ISNULL(num_lote,'') AS num_lote,
               ISNULL(num_envio,'') AS num_envio
        FROM NSPDevolucionReng WHERE dev_num={dev[0].strip()}
        ORDER BY reng_num""")
        for dr in cm_cur.fetchall():
            print(f"      reng={dr[0]} art={dr[1].strip()} dev={dr[2]} "
                  f"ori={dr[3].strip()} des={dr[4].strip()} "
                  f"lote={dr[5].strip()} traslado_dev={dr[6].strip()}")

    # F. Cierre
    cm_cur.execute(f"""
    SELECT CAST(cie_num AS VARCHAR) AS cie_num,
           CAST(confirma AS VARCHAR) AS confirma,
           CAST(anulado AS VARCHAR) AS anulado,
           ISNULL(CAST(aju_num AS VARCHAR),'') AS aju_num,
           CONVERT(VARCHAR,fec_emis,120) AS fec_emis
    FROM NSPCierreOP WHERE odp_num = '{odp_num}'
    ORDER BY cie_num""")
    cierres = cm_cur.fetchall()
    print(f"\n[F] CIERRES - {len(cierres)}:")
    for cie in cierres:
        print(f"    cie={cie[0].strip()} confirma={cie[1]} anulado={cie[2]} "
              f"aju_num={cie[3].strip()} fecha={cie[4]}")
        cm_cur.execute(f"""
        SELECT co_art, CAST(total_art AS VARCHAR), CAST(costo_uni AS VARCHAR),
               co_uni, ISNULL(nro_lote,'') AS nro_lote
        FROM NSPCierreOPReng WHERE cie_num = '{cie[0].strip()}'""")
        for cr in cm_cur.fetchall():
            print(f"      [PT-entrada] art={cr[0].strip()} cant={cr[1]} "
                  f"costo={cr[2]} lote={cr[4].strip()}")
        cm_cur.execute(f"""
        SELECT co_art, co_alma, CAST(cantidad AS VARCHAR),
               CAST(costo_uni AS VARCHAR), ISNULL(NUM_LOTE,'') AS lote
        FROM NSPCostocierre WHERE num_cierre='{cie[0].strip()}'
        ORDER BY co_art""")
        for ins in cm_cur.fetchall():
            print(f"      [MP-salida ] art={ins[0].strip()} alma={ins[1].strip()} "
                  f"cant={ins[2]} costo={ins[3]} lote={ins[4].strip()}")

    # G. Ajuste generado en CARMAL_A
    ca_cur.execute(f"""
    SELECT ajue_num, co_tipo, motivo, confirma, anulado,
           CONVERT(VARCHAR(19),fecha,120) AS fecha
    FROM saAjuste
    WHERE motivo LIKE '%ODP:%{odp_short}%'
       OR motivo LIKE '%ODP: {odp_short}%'
    ORDER BY fecha""")
    ajustes = ca_cur.fetchall()
    print(f"\n[G] AJUSTES en CARMAL_A ({len(ajustes)}):")
    for a in ajustes:
        print(f"    ajue={a[0].strip()} tipo={a[1].strip()} "
              f"confirma={a[3]} anulado={a[4]} fecha={a[5]}")
        print(f"      motivo='{a[2].strip()}'")
        ca_cur.execute(f"""
        SELECT reng_num, co_art, total_art, costo_uni, co_uni
        FROM saAjusteReng WHERE ajue_num='{a[0]}'
        ORDER BY reng_num""")
        for ar in ca_cur.fetchall():
            print(f"      reng={ar[0]} art={ar[1].strip()} "
                  f"cant={ar[2]} costo={ar[3]}")

# Leer triggers clave
print(f"\n{SEP}\n  LOGICA DE TRIGGERS\n{SEP}")
for trg, db_name, cur_x in [
    ('trg_AjusteReng_Insert_Manufactura', 'CARMAL_A', ca_cur),
    ('TrigEstado_saAjuste',              'CARMAL_A', ca_cur),
    ('TrigEstado_saTraslado',            'CARMAL_A', ca_cur),
    ('trg_RollupTrasNum_Requisicion',    'CARMAL_M', cm_cur),
]:
    cur_x.execute(f"SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID('{trg}')")
    row = cur_x.fetchone()
    if row and row[0]:
        with open(f"trg_{trg}.txt", "w", encoding="utf-8") as f:
            f.write(row[0])
        lines = row[0].split('\n')
        print(f"\n  [{db_name}] {trg} ({len(lines)} lineas):")
        for i, line in enumerate(lines):
            ls = line.strip()
            if ls and any(k in ls for k in ['EXEC','exec','INSERT','UPDATE','DELETE',
                                             'CARMAL','DB2k12','NSP','aju_num',
                                             'saLoteEntrada','saStockAlmacen',
                                             'NSPRequisicion']):
                print(f"    [{i:3d}] {ls[:130]}")

ca.close(); cm.close()
print(f"\n{SEP}\n  ANALISIS COMPLETADO\n{SEP}")
