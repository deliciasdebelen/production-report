"""
analisis_integracion_M_A.py
============================
Análisis completo SOLO LECTURA de la integración CARMAL_M <-> CARMAL_A.
Mapea tablas, SPs y flujo de datos para:
  1. Órdenes de producción
  2. Requisiciones
  3. Devoluciones
  4. Entregas parciales
  5. Cierres
"""
import pyodbc, sys

SERVER = "192.168.1.205"

def conn(db):
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};'
        f'DATABASE={db};UID=PROFIT;PWD=profit;'
        'Encrypt=yes;TrustServerCertificate=yes;',
        autocommit=True
    )

ca = conn("CARMAL_A")
cm = conn("CARMAL_M")
ca_cur = ca.cursor()
cm_cur = cm.cursor()

SEP = "=" * 70

# ══════════════════════════════════════════════════════════════════════════
# 1. TABLAS DE CARMAL_M
# ══════════════════════════════════════════════════════════════════════════
print(SEP)
print("  [1] TABLAS EN CARMAL_M")
print(SEP)
cm_cur.execute("""
SELECT t.name AS tabla,
       SUM(p.rows) AS filas,
       CONVERT(VARCHAR,t.create_date,120) AS creada,
       CONVERT(VARCHAR,t.modify_date,120) AS modificada
FROM sys.tables t
JOIN sys.partitions p ON t.object_id = p.object_id AND p.index_id IN (0,1)
WHERE t.name LIKE 'NSP%'
GROUP BY t.name, t.create_date, t.modify_date
ORDER BY t.name
""")
for r in cm_cur.fetchall():
    print(f"  {r[0]:<45} filas={r[1]}")

# ══════════════════════════════════════════════════════════════════════════
# 2. SPs EN CARMAL_M (visibles e invisibles)
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [2] STORED PROCEDURES EN CARMAL_M")
print(SEP)
cm_cur.execute("""
SELECT p.name,
       LEN(ISNULL(m.definition,'')) AS len_def,
       CASE WHEN LEN(ISNULL(m.definition,''))=0 THEN 'CIFRADO' ELSE 'VISIBLE' END AS estado,
       CONVERT(VARCHAR,p.modify_date,120) AS modify_date
FROM sys.procedures p
LEFT JOIN sys.sql_modules m ON p.object_id = m.object_id
ORDER BY p.name
""")
sps = cm_cur.fetchall()
print(f"  Total SPs: {len(sps)}")
for r in sps:
    print(f"  [{r[2]}] {r[0]:<55} mod={r[3]}")

# ══════════════════════════════════════════════════════════════════════════
# 3. SPs EN CARMAL_A RELACIONADOS CON MANUFACTURA
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [3] SPs EN CARMAL_A RELACIONADOS CON MANUFACTURA")
print(SEP)
ca_cur.execute("""
SELECT p.name,
       LEN(ISNULL(m.definition,'')) AS len_def,
       CASE WHEN LEN(ISNULL(m.definition,''))=0 THEN 'CIFRADO' ELSE 'VISIBLE' END AS estado,
       CONVERT(VARCHAR,p.modify_date,120) AS modify_date
FROM sys.procedures p
LEFT JOIN sys.sql_modules m ON p.object_id = m.object_id
WHERE p.name LIKE '%Ajuste%'
   OR p.name LIKE '%Lote%'
   OR p.name LIKE '%Stock%'
   OR p.name LIKE '%Costo%'
   OR p.name LIKE '%Traslado%'
   OR p.name LIKE '%Renglon%'
ORDER BY p.name
""")
for r in ca_cur.fetchall():
    print(f"  [{r[2]}] {r[0]:<55} mod={r[3]}")

# ══════════════════════════════════════════════════════════════════════════
# 4. TRIGGERS EN CARMAL_M Y CARMAL_A
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [4] TRIGGERS EN CARMAL_M")
print(SEP)
cm_cur.execute("""
SELECT t.name AS trigger_name, o.name AS tabla,
       LEN(ISNULL(m.definition,'')) AS len_def,
       CASE WHEN LEN(ISNULL(m.definition,''))=0 THEN 'CIFRADO' ELSE 'VISIBLE' END AS estado
FROM sys.triggers t
JOIN sys.objects o ON t.parent_id = o.object_id
LEFT JOIN sys.sql_modules m ON t.object_id = m.object_id
ORDER BY o.name, t.name
""")
for r in cm_cur.fetchall():
    print(f"  [{r[3]}] {r[0]:<50} ON {r[1]}")

print(f"\n  TRIGGERS EN CARMAL_A (relacionados con manufactura):")
ca_cur.execute("""
SELECT t.name AS trigger_name, o.name AS tabla,
       LEN(ISNULL(m.definition,'')) AS len_def,
       CASE WHEN LEN(ISNULL(m.definition,''))=0 THEN 'CIFRADO' ELSE 'VISIBLE' END AS estado
FROM sys.triggers t
JOIN sys.objects o ON t.parent_id = o.object_id
LEFT JOIN sys.sql_modules m ON t.object_id = m.object_id
WHERE o.name IN ('saAjuste','saAjusteReng','saTraslado','saTrasladoReng',
                 'saLoteEntrada','saLoteSalida','saStockAlmacen')
ORDER BY o.name, t.name
""")
for r in ca_cur.fetchall():
    print(f"  [{r[3]}] {r[0]:<50} ON {r[1]}")

# ══════════════════════════════════════════════════════════════════════════
# 5. SCHEMA DETALLADO DE TABLAS CLAVE EN CARMAL_M
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [5] SCHEMA TABLAS CLAVE CARMAL_M")
print(SEP)
tablas_m = [
    'NSPOrdenproduccion', 'NSPOrdenproduccionreng',
    'NSPRequisicion', 'NSPRequisicionreng',
    'NSPCierreOP', 'NSPCierreOPReng',
    'NSPCostocierre', 'NSPMantenimiento',
    'NSPFormula', 'NSPFormulaReng',
    'NSPDevolucion', 'NSPDevolucionReng',
]
for tabla in tablas_m:
    cm_cur.execute(f"SELECT TOP 0 * FROM {tabla}")
    if cm_cur.description:
        cols = [d[0] for d in cm_cur.description]
        cm_cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        n = cm_cur.fetchone()[0]
        print(f"\n  {tabla} ({n} filas):")
        print(f"    {cols}")
    else:
        print(f"  {tabla}: (sin columnas)")

# ══════════════════════════════════════════════════════════════════════════
# 6. FLUJO REAL: ODP activa de ejemplo (8844 y 8880)
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [6] FLUJO DE DATOS: ODPs 8844 y 8880")
print(SEP)

for odp_num in ['0000008844', '0000008880']:
    print(f"\n  --- ODP {odp_num} ---")

    # Orden de produccion
    cm_cur.execute(f"""
    SELECT odp_num, co_art, cantidad, status, almacendest, num_lote,
           co_for, CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPOrdenproduccion WHERE odp_num = '{odp_num}'
    """)
    r = cm_cur.fetchone()
    if r:
        print(f"  ODP: art={r[1].strip()} cant={r[2]} status={r[3].strip()} "
              f"alma={r[4].strip()} lote={r[5].strip() if r[5] else ''} formula={r[6]}")

    # Renglones de la orden (insumos)
    cm_cur.execute(f"""
    SELECT reng_num, co_art, cantidad, co_uni, co_alma, costo
    FROM NSPOrdenproduccionreng WHERE odp_num = '{odp_num}'
    ORDER BY reng_num
    """)
    reng = cm_cur.fetchall()
    print(f"  Renglones ODP: {len(reng)}")
    for r in reng:
        print(f"    reng={r[0]} art={r[1].strip()} cant={r[2]} "
              f"uni={r[3].strip()} alma={r[4].strip()} costo={r[5]}")

    # Requisiciones
    cm_cur.execute(f"""
    SELECT req_num, status, CONVERT(VARCHAR,fecha,120) AS fecha
    FROM NSPRequisicion WHERE odp_num = '{odp_num}'
    """)
    reqs = cm_cur.fetchall()
    print(f"  Requisiciones: {len(reqs)}")
    for req in reqs:
        print(f"    req={req[0].strip()} status={req[1].strip()} fecha={req[2]}")
        # Renglones de la requisicion
        cm_cur.execute(f"""
        SELECT reng_num, co_art, cantidad, co_uni, alma_des, num_envio
        FROM NSPRequisicionreng WHERE req_num = '{req[0]}'
        ORDER BY reng_num
        """)
        for rr in cm_cur.fetchall():
            traslado_info = f" -> traslado={rr[5].strip()}" if rr[5] and rr[5].strip() else ""
            print(f"      reng={rr[0]} art={rr[1].strip()} cant={rr[2]} "
                  f"alma={rr[4].strip()}{traslado_info}")

    # Cierres
    cm_cur.execute(f"""
    SELECT cie_num, confirma, anulado, aju_num,
           CONVERT(VARCHAR,fec_emis,120) AS fec_emis
    FROM NSPCierreOP WHERE odp_num = '{odp_num}'
    """)
    cierres = cm_cur.fetchall()
    print(f"  Cierres: {len(cierres)}")
    for cie in cierres:
        print(f"    cie={cie[0].strip()} confirma={cie[1]} anulado={cie[2]} "
              f"aju_num={cie[3]} fecha={cie[4]}")

    # Devoluciones si existen
    try:
        cm_cur.execute(f"""
        SELECT COUNT(*) FROM NSPDevolucion WHERE odp_num = '{odp_num}'
        """)
        nd = cm_cur.fetchone()[0]
        if nd > 0:
            print(f"  Devoluciones: {nd}")
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════
# 7. RELACION ENTRE TABLAS M y A: via ajuste_num y tras_num
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [7] DOCUMENTOS EN CARMAL_A GENERADOS POR MANUFACTURA")
print(SEP)

for odp_num_short in [8844, 8880]:
    odp_full = str(odp_num_short).zfill(10)
    print(f"\n  --- ODP {odp_full} ---")

    # Ajustes en CARMAL_A
    ca_cur.execute(f"""
    SELECT ajue_num, co_tipo, motivo,
           CONVERT(VARCHAR(19),fecha,120) AS fecha,
           confirma, anulado
    FROM saAjuste
    WHERE motivo LIKE '%ODP:%{odp_num_short}%'
       OR motivo LIKE '%ODP: {odp_num_short}%'
       OR motivo LIKE '%{odp_full}%'
    ORDER BY fecha
    """)
    ajustes = ca_cur.fetchall()
    print(f"  Ajustes en saAjuste: {len(ajustes)}")
    for a in ajustes:
        print(f"    ajue={a[0].strip()} tipo={a[1].strip()} "
              f"confirma={a[4]} anulado={a[5]} fecha={a[3]}")
        print(f"    motivo='{a[2].strip()}'")

    # Traslados en CARMAL_A
    ca_cur.execute(f"""
    SELECT tras_num, confirma, anulado, alm_orig, alm_dest,
           motivo_glo
    FROM saTraslado
    WHERE motivo_glo LIKE '%ODP:%{odp_num_short}%'
       OR motivo_glo LIKE '%ODP: {odp_num_short}%'
    ORDER BY tras_num
    """)
    traslados = ca_cur.fetchall()
    print(f"  Traslados en saTraslado: {len(traslados)}")
    for t in traslados:
        print(f"    tras={t[0].strip()} confirma={t[1]} anulado={t[2]} "
              f"orig={t[3].strip()} dest={t[4].strip()}")
        print(f"    motivo='{t[5].strip()}'")

# ══════════════════════════════════════════════════════════════════════════
# 8. NSPMantenimiento - parametros globales de manufactura
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}")
print("  [8] NSPMantenimiento (parametros globales)")
print(SEP)
cm_cur.execute("SELECT TOP 0 * FROM NSPMantenimiento")
cols = [d[0] for d in cm_cur.description]
print(f"  Columnas: {cols}")
cm_cur.execute("SELECT * FROM NSPMantenimiento")
row = cm_cur.fetchone()
if row:
    for col, val in zip(cols, row):
        print(f"  {col}: {val}")

ca.close()
cm.close()
print(f"\n{SEP}")
print("  ANALISIS COMPLETADO")
print(SEP)
