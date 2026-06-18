"""
diag_cierre_8859_exacto.py
SOLO LECTURA — Análisis exacto del traslado activo de ODP 8880
que causa el Error 1453 en el cierre 8859.
"""
import pyodbc

ca = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
cm = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_M;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)

ca_cur = ca.cursor()
cm_cur = cm.cursor()
ODP = '0000008880'
ODP_N = 8880
CIE = '0000008859'

print("=" * 70)
print(f"  ANALISIS EXACTO: ODP {ODP} / CIERRE {CIE}")
print("=" * 70)

# ── 1. Requisición y traslado asociado ────────────────────────────────────
print(f"\n[1] Requisicion para ODP {ODP}:")
cm_cur.execute(f"""
SELECT CAST(req_num AS VARCHAR) AS req_num,
       ISNULL(CAST(ESTATUS AS VARCHAR),'') AS ESTATUS,
       CAST(CONFIRMA AS VARCHAR) AS CONFIRMA,
       ISNULL(CAST(tras_num AS VARCHAR),'') AS tras_num
FROM NSPRequisicion WHERE odp_num = '{ODP}'
""")
reqs = cm_cur.fetchall()
for req in reqs:
    print(f"  req={req[0].strip()} status={req[1].strip()} "
          f"confirma={req[2]} traslado={req[3].strip()}")

# Traslado confirmado
cm_cur.execute(f"""
SELECT ISNULL(CAST(tras_num AS VARCHAR),'') AS tras_num
FROM NSPRequisicion WHERE odp_num = '{ODP}' AND CONFIRMA = 1
""")
row = cm_cur.fetchone()
tras_num = row[0].strip() if row and row[0] else None

if not tras_num:
    print("  SIN traslado confirmado")
else:
    print(f"\n  Traslado confirmado: {tras_num}")

    # ── 2. Renglones del traslado ─────────────────────────────────────────
    print(f"\n[2] Renglones de saTrasladoReng para traslado {tras_num}:")
    ca_cur.execute(f"""
    SELECT tr.reng_num, tr.co_art,
           CAST(tr.total_art AS VARCHAR) AS cant,
           tr.co_uni,
           CONVERT(VARCHAR(36), tr.rowguid) AS rowguid_reng
    FROM saTrasladoReng tr
    WHERE tr.tras_num = '{tras_num}'
    ORDER BY tr.reng_num
    """)
    renglones = ca_cur.fetchall()
    cols_r = [d[0] for d in ca_cur.description]
    print(f"  {len(renglones)} renglon(es):")
    for r in renglones:
        d = dict(zip(cols_r, r))
        print(f"  reng={d['reng_num']} art={d['co_art'].strip()} "
              f"cant={d['cant']} rg_reng={d['rowguid_reng']}")

    # ── 3. saLoteEntrada por rowguid_reng — ESTE ES EL PROBLEMA ──────────
    print(f"\n[3] saLoteEntrada por rowguid_reng — conteo de duplicados:")
    print(f"  {'ART':<30} {'RENG':>4} {'N':>5} {'STOCK_SUM':>12} {'CON_FK':>6}  STATUS")
    print(f"  {'-'*70}")
    
    problema_encontrado = False
    problemas = []
    
    for r in renglones:
        d = dict(zip(cols_r, r))
        rg_reng = d['rowguid_reng']
        art = d['co_art'].strip()
        reng = d['reng_num']
        
        ca_cur.execute(f"""
        SELECT x.n, x.stock_sum, x.con_fk
        FROM (
            SELECT COUNT(*) AS n,
                   SUM(stock_actual) AS stock_sum,
                   0 AS con_fk
            FROM saLoteEntrada le
            WHERE le.rowguid_reng = '{rg_reng}'
        ) x
        """)
        res = ca_cur.fetchone()
        n, ss, fk = res[0], res[1], res[2]
        
        if n > 1:
            flag = "*** DUPLICADO - CAUSA ERROR 1453 ***"
            problema_encontrado = True
            problemas.append({'rg_reng': rg_reng, 'art': art, 'reng': reng,
                              'n': n, 'ss': ss, 'fk': fk})
        elif n == 0:
            flag = "SIN FILAS - anomalia"
        else:
            flag = "OK"
        
        print(f"  {art:<30} {reng:>4} {n:>5} {str(ss):>12} {str(fk):>6}  {flag}")

    # ── 4. Detalle de cada duplicado ──────────────────────────────────────
    if problema_encontrado:
        print(f"\n[4] DETALLE DE DUPLICADOS (filas a limpiar):")
        for p in problemas:
            print(f"\n  art={p['art']} reng={p['reng']} "
                  f"n={p['n']} stock_sum={p['ss']} con_fk={p['fk']}")
            ca_cur.execute(f"""
            SELECT numero_lote, co_alma, tipo_doc,
                   CAST(cantidad AS VARCHAR) AS cant,
                   CAST(stock_actual AS VARCHAR) AS stock,
                   CONVERT(VARCHAR(36), rowguid) AS rg,
                   CONVERT(VARCHAR(19), fe_us_in, 120) AS fe_us_in,
                   (SELECT COUNT(*) FROM saLoteSalida ls
                    WHERE ls.Rowguid_Lote = le.rowguid) AS fk
            FROM saLoteEntrada le
            WHERE le.rowguid_reng = '{p['rg_reng']}'
            ORDER BY fe_us_in
            """)
            filas = ca_cur.fetchall()
            cols_f = [d[0] for d in ca_cur.description]
            for i, f in enumerate(filas):
                fd = dict(zip(cols_f, f))
                accion = "MANTENER (primera/con FK)" if (i == 0 or fd['fk'] > 0) else "CANDIDATA A ELIMINAR"
                if fd['fk'] > 0:
                    accion = "MANTENER (tiene FK)"
                elif i == 0:
                    accion = "MANTENER (la mas antigua)"
                else:
                    accion = "*** ELIMINAR (duplicada, sin FK)"
                    
                print(f"    [{i}] lote={fd['numero_lote'].strip()} "
                      f"alma={fd['co_alma'].strip()} tipo={fd['tipo_doc']} "
                      f"cant={fd['cant']} stock={fd['stock']} "
                      f"fk={fd['fk']} fe={fd['fe_us_in']}")
                print(f"         rg={fd['rg']}")
                print(f"         => {accion}")
    else:
        print(f"\n[4] No se encontraron duplicados en el traslado {tras_num}.")
        print("    El error puede venir de otro rowguid_reng.")
        # Buscar en NSPCostocierre los insumos del cierre
        print(f"\n    Insumos en NSPCostocierre para cierre {CIE}:")
        cm_cur.execute(f"""
        SELECT co_art, co_alma, CAST(cantidad AS VARCHAR), NUM_LOTE
        FROM NSPCostocierre WHERE num_cierre = '{CIE.strip()}'
        """)
        for ins in cm_cur.fetchall():
            print(f"    art={ins[0].strip()} alma={ins[1].strip()} "
                  f"cant={ins[2]} lote={ins[3].strip()}")

# ── 5. NSPRequisicionreng — num_envio y lote asignado ─────────────────────
print(f"\n[5] NSPRequisicionreng — que lote/traslado tiene asignado cada insumo:")
cm_cur.execute(f"""
SELECT req.req_num, rr.reng_num, rr.co_art,
       CAST(rr.requerida AS VARCHAR) AS req,
       CAST(rr.solicitada AS VARCHAR) AS sol,
       CAST(rr.entregada AS VARCHAR) AS ent,
       rr.alma_ori, rr.alma_des,
       ISNULL(rr.num_lote,'') AS num_lote,
       ISNULL(CAST(rr.num_envio AS VARCHAR),'') AS num_envio
FROM NSPRequisicion req
JOIN NSPRequisicionreng rr ON rr.req_num = req.req_num
WHERE req.odp_num = '{ODP}'
ORDER BY rr.reng_num
""")
for rr in cm_cur.fetchall():
    print(f"  reng={rr[1]} art={rr[2].strip()} sol={rr[4]} ent={rr[5]} "
          f"ori={rr[6].strip()} des={rr[7].strip()} "
          f"lote={rr[8].strip()} traslado={rr[9].strip()}")

ca.close(); cm.close()
print("\nDone.")
