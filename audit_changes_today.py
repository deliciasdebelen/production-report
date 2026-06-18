"""
AUDITORIA DE CAMBIOS DE HOY - SOLO LECTURA
Verifica qué SPs, triggers y datos fueron modificados hoy en CARMAL_M y CARMAL_A
"""
import pyodbc
from datetime import date

SERVER = "192.168.1.205"
HOY = date.today().strftime("%Y-%m-%d")

def conn(db):
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};'
        f'DATABASE={db};UID=PROFIT;PWD=profit;'
        'Encrypt=yes;TrustServerCertificate=yes;',
        autocommit=True
    )

print("=" * 70)
print(f"  AUDITORIA DE CAMBIOS HOY ({HOY}) - SOLO LECTURA")
print(f"  Servidor: {SERVER}")
print("=" * 70)

for db in ["CARMAL_A", "CARMAL_M"]:
    c = conn(db)
    cur = c.cursor()
    print(f"\n{'─'*70}")
    print(f"  BASE DE DATOS: {db}")
    print(f"{'─'*70}")

    # ── SPs modificados hoy ──────────────────────────────────────────────
    cur.execute(f"""
    SELECT o.name, o.type_desc,
           CONVERT(VARCHAR(19), o.modify_date, 120) AS modify_date
    FROM sys.objects o
    WHERE o.type IN ('P','FN','TF','IF','TR')
      AND CAST(o.modify_date AS DATE) = '{HOY}'
    ORDER BY o.modify_date DESC
    """)
    rows = cur.fetchall()
    print(f"\n  SPs/Funciones/Triggers modificados HOY: {len(rows)}")
    if rows:
        for r in rows:
            print(f"    [{r[1]}] {r[0]} - {r[2]}")
    else:
        print("    (ninguno)")

    # ── Tablas con datos modificados hoy via timestamp ──────────────────
    # Verificar saLoteEntrada con fe_us_mo de hoy
    print(f"\n  Filas de saLoteEntrada modificadas HOY (fe_us_in >= '{HOY}'):")
    try:
        cur.execute(f"""
        SELECT numero_lote, co_alma, co_art, tipo_doc,
               cantidad, stock_actual,
               CONVERT(VARCHAR(36), rowguid) AS rowguid,
               CONVERT(VARCHAR(19), fe_us_in, 120) AS fe_us_in
        FROM saLoteEntrada
        WHERE CAST(fe_us_in AS DATE) = '{HOY}'
        ORDER BY fe_us_in DESC
        """)
        rows2 = cur.fetchall()
        cols = [d[0] for d in cur.description]
        print(f"    Filas: {len(rows2)}")
        for r in rows2:
            print(f"    {dict(zip(cols, r))}")
    except Exception as e:
        print(f"    (tabla no existe o error: {e})")

    c.close()

print("\n" + "=" * 70)
print("  CONCLUSION: Ver arriba si hay SPs/triggers modificados hoy.")
print("=" * 70)
