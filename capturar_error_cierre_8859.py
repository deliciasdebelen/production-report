"""
capturar_error_cierre_8859.py
==============================
Ejecuta nsp_spordenproduccioncierre con los parametros del cierre 8859 / orden 8880
y captura el campo Resultado que el SP devuelve en el CATCH.
SIN MODIFICACIONES - solo lectura del error.
"""
import pyodbc

cm = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_M;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;',
    autocommit=False   # transaccion manual para que el rollback del SP no afecte nada mas
)
cur = cm.cursor()

print("=" * 70)
print("  CAPTURA DE ERROR - CIERRE 8859 / ORDEN 8880")
print("  Ejecutando nsp_spordenproduccioncierre (solo lectura del error)")
print("=" * 70)

# ── 1. Estado previo de la orden y cierre ─────────────────────────────────
print("\n[PRE] Estado de NSPCierreOP para cie_num=8859:")
cur.execute("SELECT cie_num, odp_num, confirma, anulado, aju_num FROM NSPCierreOP WHERE cie_num = '0000008859'")
r = cur.fetchone()
if r:
    print(f"  cie_num={r[0].strip()} odp={r[1].strip()} confirma={r[2]} anulado={r[3]} aju_num={r[4]}")
else:
    print("  No encontrado")

print("\n[PRE] NSPCierreOPReng para cie_num=8859:")
cur.execute("SELECT * FROM NSPCierreOPReng WHERE cie_num = '0000008859'")
if cur.description:
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"  Renglones: {len(rows)}")
    for row in rows:
        print(f"  {dict(zip(cols, row))}")

print("\n[PRE] NSPCostocierre para num_cierre=8859:")
cur.execute("SELECT co_art, co_alma, cantidad, costo_uni, NUM_LOTE FROM NSPCostocierre WHERE num_cierre = '8859      '")
rows2 = cur.fetchall()
print(f"  Insumos: {len(rows2)}")
for row in rows2:
    print(f"  art={row[0].strip()} alma={row[1].strip()} cant={row[2]} costo={row[3]} lote={row[4].strip()}")

print("\n[PRE] NSPOrdenproduccion para odp_num=8880:")
cur.execute("SELECT odp_num, co_art, cantidad, status, almacendest, num_lote FROM NSPOrdenproduccion WHERE odp_num = '0000008880'")
r2 = cur.fetchone()
if r2:
    print(f"  odp={r2[0].strip()} art={r2[1].strip()} cant={r2[2]} status={r2[3].strip()} alma={r2[4].strip()} lote={r2[5].strip() if r2[5] else 'N/A'}")

# ── 2. Ejecutar el SP y capturar Resultado ────────────────────────────────
print("\n[EXEC] Ejecutando nsp_spordenproduccioncierre...")
try:
    # Usar sp_executesql exactamente como Profit Plus lo llama
    cur.execute("""
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

    # Iterar todos los resultsets (el SP puede devolver varios)
    rs_num = 0
    while True:
        if cur.description:
            rs_num += 1
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            print(f"\n  ResultSet #{rs_num}: columnas={cols}")
            for row in rows:
                print(f"    {dict(zip(cols, row))}")
        if not cur.nextset():
            break

    if rs_num == 0:
        print("  (Sin resultsets devueltos - el SP puede haber tenido exito)")

except Exception as e:
    print(f"\n  EXCEPCION PYODBC: {e}")

finally:
    # SIEMPRE hacer rollback para no persistir ningun cambio
    try:
        cm.rollback()
        print("\n[ROLLBACK] Transaccion revertida - sin cambios en la BD.")
    except:
        pass

# ── 3. Verificar NSPLog para el error reciente ────────────────────────────
print("\n[POST] Ultimas entradas en NSPLog relacionadas con cierre 8859:")
try:
    cm2 = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
        'DATABASE=CARMAL_M;UID=PROFIT;PWD=profit;'
        'Encrypt=yes;TrustServerCertificate=yes;',
        autocommit=True
    )
    cur2 = cm2.cursor()
    cur2.execute("""
    SELECT TOP 10 
        CONVERT(VARCHAR(19), fecha, 120) AS fecha,
        err_no, resultado, modulo, accion
    FROM NSPLog
    WHERE resultado LIKE '%8859%'
       OR resultado LIKE '%8880%'
    ORDER BY fecha DESC
    """)
    cols3 = [d[0] for d in cur2.description]
    rows3 = cur2.fetchall()
    print(f"  Entradas: {len(rows3)}")
    for row in rows3:
        print(f"  {dict(zip(cols3, row))}")
    cm2.close()
except Exception as e:
    print(f"  ERROR NSPLog: {e}")

cm.close()
print("\nDone.")
