"""
DIAGNOSTICO SOLO LECTURA - Estado post-fix de todos los artículos del cierre 8855
NO modifica nada.
"""
import pyodbc

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

print("=" * 70)
print("  REVISION POST-FIX - CIERRE 8855 / ORDEN 8844")
print("  Servidor produccion: 192.168.1.205 | SOLO LECTURA")
print("=" * 70)

# ─── 1. Artículos involucrados en el cierre ──────────────────────────────────
print("\n[1] RENGLONES DEL CIERRE 8855 (NSPCierreOPReng + NSPCostocierre)")
cm_cur.execute("""
SELECT cie_num, reng_num, co_art, total_art, costo_uni, co_uni, nro_lote
FROM NSPCierreOPReng WHERE cie_num = '0000008855'
""")
cierre_reng = cm_cur.fetchall()
print(f"  PT (entrada, tipo 000001): {len(cierre_reng)} renglon(es)")
for r in cierre_reng:
    print(f"    art={r[2].strip()} cant={r[3]} costo={r[4]} lote={r[6].strip()}")

cm_cur.execute("""
SELECT co_art, co_alma, cantidad, costo_uni, CO_UNI, NUM_LOTE, num_odp
FROM NSPCostocierre WHERE num_cierre = '8855      '
""")
insumos = cm_cur.fetchall()
print(f"\n  Insumos (salida, tipo 000002): {len(insumos)} renglon(es)")
for r in insumos:
    print(f"    art={r[0].strip()} alma={r[1].strip()} cant={r[2]} costo={r[3]} lote={r[5].strip()}")

# ─── 2. Duplicados actuales en saLoteEntrada para todos los artículos ────────
articulos_cierre = set()
for r in insumos:
    articulos_cierre.add(r[0].strip())
for r in cierre_reng:
    articulos_cierre.add(r[2].strip())

print(f"\n[2] ESTADO DE DUPLICADOS EN saLoteEntrada")
print(f"    Artículos del cierre: {articulos_cierre}")

any_dup = False
for art in sorted(articulos_cierre):
    ca_cur.execute(f"""
    SELECT numero_lote, co_alma, COUNT(*) AS n, SUM(stock_actual) AS stock_sum
    FROM saLoteEntrada
    WHERE co_art = '{art}'
    GROUP BY numero_lote, co_alma
    HAVING COUNT(*) > 1
    ORDER BY n DESC, numero_lote
    """)
    dups = ca_cur.fetchall()
    if dups:
        any_dup = True
        print(f"\n  *** DUPLICADOS RESTANTES para {art}: ***")
        for d in dups:
            print(f"    lote={d[0].strip()} alma={d[1].strip()} n={d[2]} stock_sum={d[3]}")
            # Ver detalle de cada fila duplicada
            ca_cur.execute(f"""
            SELECT tipo_doc, cantidad, stock_actual,
                   CONVERT(VARCHAR(36), rowguid) AS rg,
                   CONVERT(VARCHAR(19), fe_us_in, 120) AS fe_us_in,
                   (SELECT COUNT(*) FROM saLoteSalida ls WHERE ls.Rowguid_Lote = le.rowguid) AS fk
            FROM saLoteEntrada le
            WHERE co_art = '{art}'
              AND numero_lote = '{d[0]}'
              AND co_alma = '{d[1]}'
            ORDER BY fe_us_in
            """)
            for row in ca_cur.fetchall():
                print(f"      tipo={row[0]} cant={row[1]} stock={row[2]} fk={row[5]} fe_us_in={row[4]}")
    else:
        print(f"  OK - {art}: sin duplicados (lote+alma)")

if not any_dup:
    print("\n  ✓ No hay duplicados para ningún artículo del cierre 8855.")

# ─── 3. Verificar el lote específico del insumo crítico ─────────────────────
print(f"\n[3] LOTE PMA260417 para MP01N00X102 en P1-PP (el que causaba el error)")
ca_cur.execute("""
SELECT numero_lote, co_alma, tipo_doc, cantidad, stock_actual,
       CONVERT(VARCHAR(36), rowguid) AS rg,
       CONVERT(VARCHAR(19), fe_us_in, 120) AS fe_us_in
FROM saLoteEntrada
WHERE co_art = 'MP01N00X102'
  AND co_alma = 'P1-PP '
ORDER BY numero_lote, fe_us_in
""")
rows = ca_cur.fetchall()
cols = [d[0] for d in ca_cur.description]
for r in rows:
    print(f"  {dict(zip(cols, r))}")

# ─── 4. Cambios realizados en esta sesión (últimos 40 min) ──────────────────
print(f"\n[4] CAMBIOS REALIZADOS EN ESTA SESION (registro de modificaciones)")
print("""
  CAMBIO 1 - Script: fix_lotes_duplicados_8855_v2_exec.py
    Articulo: ST01D22X001
    Tabla: CARMAL_A.dbo.saLoteEntrada
    Accion: UPDATE numero_lote (renombrar con sufijo -ORI)
    Filas: 4 filas AJUS con stock=0 y sin duplicado TRAS en P1-ST
      MA250523-01 (P1-ST, AJUS) -> MA250523-01-ORI
      MA250523-02 (P1-ST, AJUS) -> MA250523-02-ORI
      MA250526-01 (P1-ST, AJUS) -> MA250526-01-ORI
      MA250526-02 (P1-ST, AJUS) -> MA250526-02-ORI

  CAMBIO 2 - Script: fix_lotes_MP01N00X102_exec.py
    Articulo: MP01N00X102
    Tabla: CARMAL_A.dbo.saLoteEntrada
    Accion: UPDATE numero_lote (renombrar con sufijo -B)
    Filas: 5 filas con duplicados (todas sin FK en saLoteSalida)
      PMA240304 (P1-PP1, AJUS) -> PMA240304-B  [stock=54.20]
      PMA240502 (P1-PP1, AJUS) -> PMA240502-B  [stock=441.50]
      PMA240503 (P1-PP1, AJUS) -> PMA240503-B  [stock=222.60]
      PMA240506 (P1-PP1, AJUS) -> PMA240506-B  [stock=218.60]
      PMA260417 (P1-PP,  TRAS) -> PMA260417-B  [stock=126.00]  <<< CAUSA DEL ERROR 8855
""")

# ─── 5. Estado del NSPCierreOP ───────────────────────────────────────────────
print(f"\n[5] ESTADO DE NSPCierreOP para cierre 8855")
cm_cur.execute("""
SELECT cie_num, odp_num, confirma, anulado, aju_num,
       CONVERT(VARCHAR(19), fec_emis, 120) AS fec_emis,
       CONVERT(VARCHAR(19), fe_us_in, 120) AS fe_us_in
FROM NSPCierreOP WHERE cie_num = '0000008855'
""")
r = cm_cur.fetchone()
if r:
    print(f"  cie_num={r[0].strip()} odp={r[1].strip()} confirma={r[2]} anulado={r[3]} aju_num={r[4]} fec_emis={r[5]}")
    print(f"  El cierre NO está confirmado — pendiente de reintento.")
else:
    print("  No encontrado")

ca.close()
cm.close()
print("\nDone.")
