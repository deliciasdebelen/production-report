"""
fix_lle_8860_8869.py
Identifica y elimina filas LLE en saStockAlmacen para los insumos
de los cierres 8860 (ODP 8881) y 8869 (ODP 8885) que causan Error 1453.
"""
import pyodbc

ca = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=False)
cm = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_M;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
ca_cur = ca.cursor()
cm_cur = cm.cursor()
SEP = "=" * 65

# ── Obtener todos los insumos de los cierres afectados ───────
CIERRES_AFECTADOS = {
    '0000008860': '0000008881',
    '0000008869': '0000008885',
    '0000008854': '0000008875',  # pendiente desde ayer
    '0000008868': '0000008879',  # verificar tambien
}

# Buscar insumos en NSPRequisicionReng via traslados ligados al cierre
print(f"{SEP}\n[1] Buscando insumos de los cierres afectados\n{SEP}")

# Obtener todos los arts que aparecen en los traslados de estas ODPs
arts_en_riesgo = set()
for cie_num, odp_num in CIERRES_AFECTADOS.items():
    # Buscar via NSPRequisicion -> NSPRequisicionReng
    cm_cur.execute(f"""
    SELECT DISTINCT rr.co_art, rr.alma_des
    FROM NSPRequisicion r
    JOIN NSPRequisicionReng rr ON rr.req_num = r.req_num
    WHERE r.odp_num = '{odp_num}'
    """)
    rows = cm_cur.fetchall()
    print(f"\n  Cierre {cie_num} / ODP {odp_num} — insumos: {len(rows)}")
    for r in rows:
        art = r[0].strip()
        alma = r[1].strip() if r[1] else 'P1-PP'
        print(f"    art={art} alma={alma}")
        arts_en_riesgo.add(art)

# ── Buscar duplicados LLE para esos articulos ─────────────────
print(f"\n{SEP}\n[2] Verificar LLE duplicados en saStockAlmacen\n{SEP}")

filas_a_eliminar = []
for art in sorted(arts_en_riesgo):
    ca_cur.execute(f"""
    SELECT co_alma, tipo, CAST(stock AS VARCHAR(20)) AS stock
    FROM saStockAlmacen
    WHERE co_art = '{art}'
      AND tipo   = 'LLE '
      AND EXISTS (SELECT 1 FROM saStockAlmacen s2
                  WHERE s2.co_art = '{art}'
                    AND s2.co_alma = saStockAlmacen.co_alma
                    AND s2.tipo   = 'ACT ')
    ORDER BY co_alma
    """)
    lles = ca_cur.fetchall()
    if lles:
        print(f"\n  *** {art} tiene {len(lles)} fila(s) LLE con par ACT:")
        for r in lles:
            alma = r[0].strip()
            stock = float(r[2])
            print(f"    alma={alma} tipo=LLE stock={stock}")
            filas_a_eliminar.append({
                'art': art, 'alma': r[0], 'stock': stock
            })
    else:
        # Verificar si tiene algun duplicado (no solo LLE)
        ca_cur.execute(f"""
        SELECT tipo, co_alma, CAST(stock AS VARCHAR(20))
        FROM saStockAlmacen
        WHERE co_art = '{art}'
          AND (SELECT COUNT(*) FROM saStockAlmacen s2
               WHERE s2.co_art='{art}' AND s2.co_alma=saStockAlmacen.co_alma) > 1
        ORDER BY co_alma, tipo
        """)
        dups = ca_cur.fetchall()
        if dups:
            print(f"\n  *** {art} tiene duplicados (no LLE):")
            for r in dups:
                print(f"    tipo={r[0].strip()} alma={r[1].strip()} stock={r[2]}")
        else:
            print(f"  OK  {art} — sin duplicados LLE")

if not filas_a_eliminar:
    print("\n  No se encontraron filas LLE a eliminar.")
    print("  El Error 1453 puede ser por otra causa. Verificar manualmente.")
    ca.close(); cm.close()
    exit(0)

# ── Eliminar los LLE encontrados ──────────────────────────────
print(f"\n{SEP}\n[3] ELIMINANDO FILAS LLE ENCONTRADAS\n{SEP}")
print(f"  Total filas a eliminar: {len(filas_a_eliminar)}")
for f in filas_a_eliminar:
    print(f"  art={f['art']} alma={f['alma'].strip()} stock_LLE={f['stock']}")

try:
    total_eliminadas = 0
    for f in filas_a_eliminar:
        art  = f['art']
        alma = f['alma']

        # Confirmar ACT existe
        ca_cur.execute(f"""
        SELECT CAST(stock AS VARCHAR(20))
        FROM saStockAlmacen
        WHERE co_art='{art}' AND co_alma='{alma}' AND tipo='ACT '
        """)
        act = ca_cur.fetchone()
        if not act:
            print(f"  SKIP {art}/{alma.strip()} — sin ACT, no se elimina")
            continue

        ca_cur.execute(f"""
        DELETE FROM saStockAlmacen
        WHERE co_art  = '{art}'
          AND co_alma  = '{alma}'
          AND tipo     = 'LLE '
        """)
        n = ca_cur.rowcount
        print(f"  DELETE {art}/{alma.strip()} LLE → {n} fila(s) eliminada(s) "
              f"(ACT stock={act[0]})")
        total_eliminadas += n

    ca.commit()
    print(f"\n  COMMIT — Total eliminadas: {total_eliminadas} fila(s)")

except Exception as e:
    ca.rollback()
    print(f"\n  ROLLBACK por error: {e}")
    ca.close(); cm.close()
    exit(1)

# ── Verificacion post-limpieza ────────────────────────────────
print(f"\n{SEP}\n[4] VERIFICACION POST-LIMPIEZA\n{SEP}")
ca2 = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
cur2 = ca2.cursor()
for art in sorted(arts_en_riesgo):
    cur2.execute(f"""
    SELECT tipo, co_alma, CAST(stock AS VARCHAR(20))
    FROM saStockAlmacen WHERE co_art='{art}'
    ORDER BY co_alma, tipo
    """)
    rows = cur2.fetchall()
    n_per_alma = {}
    for r in rows:
        key = r[1].strip()
        n_per_alma[key] = n_per_alma.get(key, 0) + 1
    duplicados = {k: v for k, v in n_per_alma.items() if v > 1}
    status = f"DUPLICADOS RESTANTES: {duplicados}" if duplicados else "OK — sin duplicados"
    print(f"  {art}: {status}")

ca2.close()
ca.close()
cm.close()
print(f"\n{SEP}\n  LIMPIEZA COMPLETADA\n{SEP}")
print("  Ahora ejecutar los cierres desde Profit Plus:")
for cie, odp in CIERRES_AFECTADOS.items():
    print(f"    ODP {odp} / Cierre {cie}")
