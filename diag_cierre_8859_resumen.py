"""
diag_cierre_8859_resumen.py
SOLO LECTURA - Resumen enfocado para cierre 8859
"""
import pyodbc

ca = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True
)
ca_cur = ca.cursor()

ARTICULOS = ['MP01N00X143', 'MP01N00X144', 'MP01N00X152', 'MP01P01X28']
ODP_NUM   = 8880
ALMA      = 'P1-PP '

print("=" * 70)
print(f"  RESUMEN DUPLICADOS - CIERRE 8859 / ODP {ODP_NUM}")
print("=" * 70)

# ── 1. Traslado de requisicion para ODP 8880 ──────────────────────────────
print("\n[1] Traslado ODP 8880:")
ca_cur.execute(f"""
SELECT tras_num, confirma, alm_orig, alm_dest, motivo_glo
FROM saTraslado
WHERE motivo_glo LIKE '%ODP:%{ODP_NUM}%'
   OR motivo_glo LIKE '%ODP: {ODP_NUM}%'
""")
traslados = ca_cur.fetchall()
tras_nums = []
for t in traslados:
    tras_nums.append(t[0].strip())
    print(f"  tras={t[0].strip()} confirma={t[1]} orig={t[2].strip()} dest={t[3].strip()}")

# ── 2. Renglones de esos traslados ────────────────────────────────────────
print("\n[2] Renglones del traslado para los 4 articulos:")
rg_rengs = []
if tras_nums:
    tras_in = ','.join([f"'{n}'" for n in tras_nums])
    arts_in = ','.join([f"'{a}'" for a in ARTICULOS])
    ca_cur.execute(f"""
    SELECT tr.tras_num, tr.reng_num, tr.co_art, tr.total_art,
           CONVERT(VARCHAR(36), tr.rowguid) AS rowguid_reng
    FROM saTrasladoReng tr
    WHERE tr.tras_num IN ({tras_in})
      AND tr.co_art   IN ({arts_in})
    ORDER BY tr.co_art
    """)
    for r in ca_cur.fetchall():
        rg_rengs.append((r[2].strip(), r[4]))  # (art, rowguid_reng)
        print(f"  art={r[2].strip()} cant={r[3]} rg_reng={r[4]}")

# ── 3. Para cada rowguid_reng, cuantas filas en saLoteEntrada ─────────────
print("\n[3] Filas en saLoteEntrada por rowguid_reng del traslado:")
for art, rg_reng in rg_rengs:
    ca_cur.execute(f"""
    SELECT COUNT(*) AS n,
           MIN(CONVERT(VARCHAR(36), rowguid)) AS primer_rg,
           MAX(CONVERT(VARCHAR(36), rowguid)) AS ultimo_rg,
           SUM(CASE WHEN stock_actual > 0 THEN 1 ELSE 0 END) AS con_stock
    FROM saLoteEntrada
    WHERE rowguid_reng = '{rg_reng}'
    """)
    r = ca_cur.fetchone()
    flag = "*** DUPLICADO - CAUSA ERROR 1453 ***" if r[0] > 1 else "OK"
    print(f"  art={art} n={r[0]} con_stock={r[3]} {flag}")
    if r[0] > 1:
        # Detalle de las filas
        ca_cur.execute(f"""
        SELECT numero_lote, tipo_doc, cantidad, stock_actual,
               CONVERT(VARCHAR(36), rowguid) AS rg,
               CONVERT(VARCHAR(19), fe_us_in, 120) AS fe_us_in,
               (SELECT COUNT(*) FROM saLoteSalida ls
                WHERE ls.Rowguid_Lote = le.rowguid) AS fk
        FROM saLoteEntrada le
        WHERE rowguid_reng = '{rg_reng}'
        ORDER BY fe_us_in
        """)
        for row in ca_cur.fetchall():
            print(f"    lote={row[0].strip()} tipo={row[1]} "
                  f"cant={row[2]} stock={row[3]} fk={row[6]} "
                  f"rg={row[4]} fe={row[5]}")

# ── 4. Resumen de todos los duplicados en P1-PP para los 4 articulos ──────
print("\n[4] Resumen de duplicados en P1-PP para los 4 articulos:")
for art in ARTICULOS:
    ca_cur.execute(f"""
    SELECT numero_lote, COUNT(*) AS n, SUM(stock_actual) AS ss,
           SUM(CASE WHEN stock_actual > 0 THEN 1 ELSE 0 END) AS con_stock
    FROM saLoteEntrada
    WHERE co_art = '{art}' AND co_alma = '{ALMA}'
    GROUP BY numero_lote
    HAVING COUNT(*) > 1
    ORDER BY n DESC
    """)
    dups = ca_cur.fetchall()
    total_filas = sum(d[1] for d in dups)
    if dups:
        print(f"\n  {art}: {len(dups)} lote(s) duplicados, {total_filas} filas extra")
        for d in dups:
            print(f"    lote={d[0].strip()} n={d[1]} stock_sum={d[2]} con_stock={d[3]}")
    else:
        print(f"  {art}: OK sin duplicados en P1-PP")

ca.close()
print("\nDone.")
