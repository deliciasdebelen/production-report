"""
Analizar 10 inconsistencias de stock en carmal_a:
- saLoteEntrada: numero_lote, co_art, co_alma, stock_actual, tipo_doc
- saAjuste / saAjusteReng: ajue_num, co_art, co_alma, total_art, co_tipo
"""
import pyodbc

conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=192.168.1.205;DATABASE=carmal_a;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;'
)
cursor = conn.cursor()

cases = [
    ("L1260226-01",   "PT01P01X012", "P1-PT", -24.0),
    ("L1 A260304-01", "PT01P01X013", "P1-PT", -24.0),
    ("L1 260302-01",  "PT01D01X019", "P1-PT", -60.0),
    ("L1 260227-01",  "PT01P01X012", "P1-PT", -12.0),
    ("L2 260302-02",  "PT01D01X011", "P1-PT", -60.0),
    ("L1 260212-01",  "PT01P01X013", "P1-PT", -122.0),
    ("L1 260218-01",  "PT01P01X013", "P1-PT", -96.0),
    ("L1 260219-01",  "PT01P01X013", "P1-PT", -624.0),
    ("L1 260211-01",  "PT01P01X017", "P1-PT", -480.0),
    ("AFR260224-01",  "PT04D16X001", "P1-PT", -7.0),
]

print("=" * 90)
print("ANÁLISIS DE INCONSISTENCIAS DE STOCK (saLoteEntrada) — carmal_a")
print("=" * 90)

for i, (lote, art, alma, expected) in enumerate(cases, 1):
    print(f"\n[{i:02d}] {art}  |  Lote: {lote}  |  Almacén: {alma}")
    print(f"     Stock esperado: {expected:>10.5f}  |  Stock reportado actual: 0.00000")

    # 1. Stock actual en saLoteEntrada
    cursor.execute("""
        SELECT numero_lote, co_art, co_alma, tipo_doc, cantidad, stock_actual, fecha_inicio, fecha_expiracion
        FROM saLoteEntrada
        WHERE co_art = ? AND co_alma = ? AND RTRIM(numero_lote) = RTRIM(?)
    """, art, alma, lote)
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"     saLoteEntrada: tipo_doc={r.tipo_doc!r:8s}  cant={float(r.cantidad or 0):>10.5f}  stock_actual={float(r.stock_actual or 0):>12.5f}  fecha={r.fecha_inicio}")
    else:
        # Try without alma filter
        cursor.execute("""
            SELECT numero_lote, co_art, co_alma, tipo_doc, cantidad, stock_actual, fecha_inicio
            FROM saLoteEntrada
            WHERE co_art = ? AND RTRIM(numero_lote) = RTRIM(?)
        """, art, lote)
        rows2 = cursor.fetchall()
        if rows2:
            print(f"     saLoteEntrada (cualquier alma): {len(rows2)} registros")
            for r in rows2:
                print(f"       tipo_doc={r.tipo_doc!r:8s}  alma={r.co_alma!r:10s}  cant={float(r.cantidad or 0):>10.5f}  stock_actual={float(r.stock_actual or 0):>12.5f}")
        else:
            print(f"     saLoteEntrada: NO ENCONTRADO (ni con ni sin filtro de almacén)")

    # 2. Resumen de ajustes donde participó este artículo+almacén
    cursor.execute("""
        SELECT a.ajue_num, a.fecha, r.co_tipo, r.total_art, r.stotal_art
        FROM saAjuste a
        JOIN saAjusteReng r ON a.ajue_num = r.ajue_num
        WHERE r.co_art = ? AND r.co_alma = ?
        ORDER BY a.fecha DESC
    """, art, alma)
    ajustes = cursor.fetchall()
    if ajustes:
        print(f"     Ajustes ({len(ajustes)} registros en saAjusteReng):")
        for r in ajustes[:5]:
            print(f"       Ajuste {r.ajue_num} fecha={r.fecha}  co_tipo={r.co_tipo!r}  total={float(r.total_art or 0):>10.5f}")
    else:
        print(f"     saAjusteReng: Sin ajustes para este art/alma")

print()
print("=" * 90)
print("RESUMEN: ¿Existen registros en saLoteEntrada con stock_actual = 0 que deberían ser negativos?")
print("=" * 90)

# Check how many lotes with tipo_doc AJUS have stock_actual = 0
cursor.execute("""
    SELECT COUNT(*) FROM saLoteEntrada 
    WHERE tipo_doc = 'AJUS' AND co_alma = 'P1-PT' AND stock_actual = 0
""")
c = cursor.fetchone()[0]
print(f"  Total de registros AJUS en P1-PT con stock_actual=0: {c}")

cursor.execute("""
    SELECT COUNT(*) FROM saLoteEntrada 
    WHERE tipo_doc = 'AJUS' AND co_alma = 'P1-PT' AND stock_actual < 0
""")
c2 = cursor.fetchone()[0]
print(f"  Total de registros AJUS en P1-PT con stock_actual<0: {c2}")

cursor.execute("""
    SELECT COUNT(*) FROM saLoteEntrada 
    WHERE tipo_doc = 'AJUS' AND co_alma = 'P1-PT'
""")
c3 = cursor.fetchone()[0]
print(f"  Total de registros AJUS en P1-PT: {c3}")

conn.close()
print("\nFIN DEL ANÁLISIS.")
