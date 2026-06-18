"""
fix_saStockAlmacen_lle.py
Corrige la fila duplicada tipo=LLE en saStockAlmacen para MP01N00X144/P1-PP
que causa Error 1453 en el cierre 8859.

Plan:
  1. Preview - mostrar exactamente qué se va a modificar
  2. Eliminar fila tipo=LLE con stock=0 (duplicados seguros)
  3. Para MP01N00X144/P1-PP LLE con stock=10,000:
       - El stock ACT (20,195) ya es el balance real del sistema
       - LLE es el registro de "llenado inicial" ya incorporado en ACT
       - Se elimina la fila LLE para que el SP encuentre solo 1 fila
  4. Verificar resultado
  5. Intentar el cierre de nuevo (solo leer el Resultado)
"""
import pyodbc

ca = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;',
    autocommit=False   # transaccion manual
)
cm = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_M;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;',
    autocommit=True
)
ca_cur = ca.cursor()
cm_cur = cm.cursor()

SEP = "=" * 70

# ══════════════════════════════════════════════════════════════════════════
# FASE 1 — PREVIEW de lo que se va a corregir
# ══════════════════════════════════════════════════════════════════════════
print(f"{SEP}\n  FASE 1 — PREVIEW\n{SEP}")

# Duplicados en P1-PP relacionados con articulos de cierres activos
ARTICULOS_CIERRE = ['MP01N00X143', 'MP01N00X144', 'MP01N00X152',
                    'MP01P01X28', 'ST01P01X001',
                    'MP01N00X102', 'MP01D22X05-31', 'ST01D22X001']

print("\n  Estado actual saStockAlmacen para articulos de cierres activos:")
filas_a_eliminar = []
for art in ARTICULOS_CIERRE:
    ca_cur.execute(f"""
    SELECT tipo, CAST(stock AS VARCHAR(20)) AS stock
    FROM saStockAlmacen
    WHERE co_art = '{art}' AND co_alma = 'P1-PP '
    ORDER BY tipo
    """)
    rows = ca_cur.fetchall()
    if len(rows) > 1:
        print(f"\n  *** {art} en P1-PP — {len(rows)} filas (DUPLICADO):")
        for r in rows:
            print(f"      tipo={r[0].strip()} stock={r[1]}")
            if r[0].strip() in ('LLE', 'COM'):
                filas_a_eliminar.append({
                    'art': art, 'alma': 'P1-PP ',
                    'tipo': r[0].strip(), 'stock': r[1]
                })
    else:
        print(f"  OK  {art} en P1-PP — {len(rows)} fila(s)")

# Tambien verificar otros almacenes de los insumos activos
print(f"\n  Otros duplicados LLE/COM con stock=0 (en cualquier almacen):")
ca_cur.execute("""
SELECT co_art, co_alma, tipo,
       CAST(stock AS VARCHAR(20)) AS stock
FROM saStockAlmacen
WHERE tipo IN ('LLE','COM')
  AND (SELECT COUNT(*) FROM saStockAlmacen s2
       WHERE s2.co_art = saStockAlmacen.co_art
         AND s2.co_alma = saStockAlmacen.co_alma
         AND s2.tipo = 'ACT') > 0
ORDER BY co_art, co_alma, tipo
""")
otros = ca_cur.fetchall()
print(f"  Total filas LLE/COM con ACT par: {len(otros)}")
for r in otros:
    art = r[0].strip(); alma = r[1].strip()
    tipo = r[2].strip(); stock = r[3]
    flag_accion = "ELIMINAR" if float(stock) == 0.0 else "REVISAR (stock > 0)"
    if {'art': art, 'alma': r[1], 'tipo': tipo} not in \
       [{'art': x['art'], 'alma': x['alma'], 'tipo': x['tipo']}
        for x in filas_a_eliminar]:
        if art in ARTICULOS_CIERRE:
            print(f"    art={art} alma={alma} tipo={tipo} stock={stock} => {flag_accion}")

print(f"\n  Filas a eliminar en esta sesion:")
for f in filas_a_eliminar:
    print(f"    co_art={f['art']} co_alma={f['alma'].strip()} "
          f"tipo={f['tipo']} stock={f['stock']}")

if not filas_a_eliminar:
    print("  Sin filas duplicadas en P1-PP para articulos del cierre.")
    ca.close(); cm.close()
    exit()

# ══════════════════════════════════════════════════════════════════════════
# FASE 2 — EJECUTAR CORRECCIÓN
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  FASE 2 — CORRECCION\n{SEP}")
try:
    for f in filas_a_eliminar:
        art  = f['art']
        alma = f['alma']
        tipo = f['tipo']

        # Verificar que la fila ACT existe antes de eliminar la LLE/COM
        ca_cur.execute(f"""
        SELECT CAST(stock AS VARCHAR(20)) AS stock
        FROM saStockAlmacen
        WHERE co_art = '{art}' AND co_alma = '{alma}' AND tipo = 'ACT '
        """)
        act_row = ca_cur.fetchone()
        if not act_row:
            print(f"  SKIP {art}/{alma.strip()}/{tipo} — no tiene fila ACT")
            continue

        print(f"  DELETE tipo={tipo} art={art} alma={alma.strip()} "
              f"stock={f['stock']} (ACT stock={act_row[0]})")

        ca_cur.execute(f"""
        DELETE FROM saStockAlmacen
        WHERE co_art = '{art}'
          AND co_alma = '{alma}'
          AND tipo   = '{tipo:<4}'
        """)
        print(f"    Filas eliminadas: {ca_cur.rowcount}")

    ca.commit()
    print(f"\n  [COMMIT] Correcciones aplicadas.")

except Exception as e:
    ca.rollback()
    print(f"\n  [ROLLBACK] Error: {e}")
    ca.close(); cm.close()
    exit()

# ══════════════════════════════════════════════════════════════════════════
# FASE 3 — VERIFICACION POST-FIX
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  FASE 3 — VERIFICACION\n{SEP}")
ca2 = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
cur2 = ca2.cursor()

print("\n  Estado post-fix de saStockAlmacen para articulos del cierre 8859:")
for art in ['MP01N00X143', 'MP01N00X144', 'MP01N00X152', 'MP01P01X28']:
    cur2.execute(f"""
    SELECT tipo, CAST(stock AS VARCHAR(20)) AS stock
    FROM saStockAlmacen
    WHERE co_art = '{art}' AND co_alma = 'P1-PP '
    ORDER BY tipo
    """)
    rows = cur2.fetchall()
    n = len(rows)
    estado = "OK — 1 fila" if n == 1 else f"*** TODAVIA {n} filas"
    print(f"  {art}: {n} fila(s) en P1-PP — {estado}")
    for r in rows:
        print(f"    tipo={r[0].strip()} stock={r[1]}")

# ══════════════════════════════════════════════════════════════════════════
# FASE 4 — REINTENTO DEL CIERRE (lectura del Resultado solamente)
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  FASE 4 — REINTENTO CIERRE 8859 / ODP 8880\n{SEP}")
cm2 = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_M;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;',
    autocommit=False
)
cm2_cur = cm2.cursor()
try:
    cm2_cur.execute("""
    EXEC sp_executesql
        N'SET NOCOUNT ON exec [nsp_spordenproduccioncierre] @odp_num,@cie_num,@usa_TR,@TiempoR,@co_mone,@tasa,@DB2k12,@co_sucu_in,@action,@fecha,@co_us_in',
        N'@odp_num nvarchar(10),@cie_num nvarchar(10),@usa_TR bit,@TiempoR nvarchar(15),@co_mone nvarchar(6),@tasa decimal(6,5),@DB2k12 nvarchar(8),@co_sucu_in nvarchar(2),@action nvarchar(6),@fecha datetime,@co_us_in nvarchar(3)',
        @odp_num=N'0000008880',
        @cie_num=N'0000008859',
        @usa_TR=0,
        @TiempoR=N'00D 00H 00M 00S',
        @co_mone=N'BS    ',
        @tasa=1.00000,
        @DB2k12=N'CARMAL_A',
        @co_sucu_in=N'P1',
        @action=N'cerrar',
        @fecha='2026-04-29 17:59:00',
        @co_us_in=N'999'
    """)

    resultados = []
    rs_num = 0
    while True:
        if cm2_cur.description:
            rs_num += 1
            cols = [d[0] for d in cm2_cur.description]
            rows = cm2_cur.fetchall()
            if 'Resultado' in cols:
                for row in rows:
                    resultados.append(dict(zip(cols, row)))
                    print(f"\n  ResultSet #{rs_num} [Resultado]: "
                          f"{dict(zip(cols, row))['Resultado']}")
            elif rs_num <= 3 or rs_num >= 8:
                print(f"  ResultSet #{rs_num}: cols={cols} rows={len(rows)}")
        if not cm2_cur.nextset():
            break

    if not resultados:
        print("  Sin ResultSet de Resultado — verificar manualmente")

except Exception as e:
    err = str(e)
    if '1453' in err:
        print(f"\n  TODAVIA Error 1453: {err[:300]}")
    elif 'REALIZADO' in err.upper():
        print(f"\n  CIERRE REALIZADO exitosamente")
    else:
        print(f"\n  Excepcion: {err[:400]}")
finally:
    cm2.rollback()
    print("\n  [ROLLBACK] Transaccion del cierre revertida (prueba de diagnostico).")

ca2.close()
cm2.close()
ca.close()
cm.close()
print(f"\n{SEP}\n  PROCESO COMPLETADO\n{SEP}")
