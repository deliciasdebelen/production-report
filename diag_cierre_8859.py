"""
diag_stock_negativo_v2.py - Balance completo MP01D16X05-33 (COMPUESTO 33)
"""
import pyodbc

ca = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
ca_cur = ca.cursor()
SEP = "=" * 65
ART = 'MP01D16X05-33'

# Schema saAjuste y saAjusteReng
ca_cur.execute("SELECT TOP 0 * FROM saAjuste")
aj_cols = [d[0] for d in ca_cur.description]
ca_cur.execute("SELECT TOP 0 * FROM saAjusteReng")
ar_cols = [d[0] for d in ca_cur.description]
print(f"saAjuste cols: {aj_cols}")
print(f"saAjusteReng cols: {ar_cols}")

# Buscar ajustes del articulo
cant_col = next((c for c in ar_cols if 'cant' in c.lower()), None)
alma_col = next((c for c in ar_cols if 'alma' in c.lower()), None)
desc_col_aj = next((c for c in aj_cols if 'desc' in c.lower()), None)
tipo_col_aj = next((c for c in aj_cols if 'tipo' in c.lower()), None)

print(f"\ncant_col={cant_col} alma_col={alma_col}")

print(f"\n{SEP}\n[4] saAjusteReng para {ART}\n{SEP}")
ca_cur.execute(f"""
SELECT a.ajue_num, a.{tipo_col_aj}, ar.reng_num,
       CAST(ar.{cant_col} AS VARCHAR) AS cantidad,
       ar.{alma_col},
       CONVERT(VARCHAR, a.fe_us_in, 120) AS fecha
FROM saAjusteReng ar
JOIN saAjuste a ON a.ajue_num = ar.ajue_num
WHERE ar.co_art = '{ART}'
ORDER BY a.fe_us_in
""")
rows = ca_cur.fetchall()
cols2 = [d[0] for d in ca_cur.description]
print(f"  Ajustes: {len(rows)}")
for r in rows:
    d = dict(zip(cols2, r))
    print(f"  aju={str(d['ajue_num']).strip()} tipo={d[tipo_col_aj]} "
          f"alma={str(d[alma_col]).strip()} cant={d['cantidad']} fecha={d['fecha']}")

# Schema saTrasladoReng
ca_cur.execute("SELECT TOP 0 * FROM saTrasladoReng")
tr_cols = [d[0] for d in ca_cur.description]
print(f"\n{SEP}\nsaTrasladoReng cols: {tr_cols}\n{SEP}")

art_col_tr = next((c for c in tr_cols if 'art' in c.lower()), None)
cant_col_tr = next((c for c in tr_cols if 'cant' in c.lower()), None)
lote_col_tr = next((c for c in tr_cols if 'lote' in c.lower()), None)
ori_col = next((c for c in tr_cols if 'ori' in c.lower()), None)
des_col = next((c for c in tr_cols if 'des' in c.lower()), None)

print(f"art={art_col_tr} cant={cant_col_tr} lote={lote_col_tr} ori={ori_col} des={des_col}")

ca_cur.execute(f"""
SELECT tr.tras_num, tr.reng_num,
       CAST(tr.{cant_col_tr} AS VARCHAR) AS cantidad,
       {f'tr.{lote_col_tr}' if lote_col_tr else 'NULL'} AS lote,
       {f'tr.{ori_col}' if ori_col else 'NULL'} AS ori,
       {f'tr.{des_col}' if des_col else 'NULL'} AS des,
       CONVERT(VARCHAR, tr.fe_us_in, 120) AS fecha
FROM saTrasladoReng tr
WHERE tr.{art_col_tr} = '{ART}'
ORDER BY tr.fe_us_in
""")
tr_rows = ca_cur.fetchall()
tr_cols2 = [d[0] for d in ca_cur.description]
print(f"\n  Traslados ({len(tr_rows)}):")
for r in tr_rows:
    d = dict(zip(tr_cols2, r))
    print(f"  tras={str(d['tras_num']).strip()} cant={d['cantidad']} "
          f"lote={str(d['lote']).strip()} ori={str(d['ori']).strip()} "
          f"des={str(d['des']).strip()} fecha={d['fecha']}")

# ── RESUMEN FINAL ─────────────────────────────────────────────
print(f"\n{SEP}\n  RESUMEN BALANCE P1-PS\n{SEP}")
# Entradas en P1-PS (GCOM = Guia de Compra/Entrada)
ca_cur.execute(f"""
SELECT CAST(SUM(cantidad) AS VARCHAR) AS ent
FROM saLoteEntrada
WHERE co_art='{ART}' AND co_alma='P1-PS '
""")
ent = float(ca_cur.fetchone()[0] or 0)

# Salidas de P1-PS (saLoteSalida)
ca_cur.execute(f"""
SELECT CAST(SUM(cantidad) AS VARCHAR) AS sal
FROM saLoteSalida
WHERE co_art='{ART}' AND co_alma='P1-PS '
""")
sal = float(ca_cur.fetchone()[0] or 0)

# Stock actual
ca_cur.execute(f"""
SELECT CAST(stock AS VARCHAR) FROM saStockAlmacen
WHERE co_art='{ART}' AND co_alma='P1-PS ' AND tipo='ACT '
""")
stock_act = float(ca_cur.fetchone()[0] or 0)

print(f"  Entradas en P1-PS (saLoteEntrada):  {ent:.5f} kg")
print(f"  Salidas  de P1-PS (saLoteSalida):   {sal:.5f} kg")
print(f"  Balance teorico (ent - sal):         {ent-sal:.5f} kg")
print(f"  Stock real en saStockAlmacen (ACT):  {stock_act:.5f} kg")
diferencia = stock_act - (ent - sal)
print(f"  Diferencia (stock - balance):        {diferencia:.5f} kg")
print()

if stock_act < 0:
    print("  DIAGNOSTICO: Stock NEGATIVO en P1-PS")
    if ent - sal == 0 and stock_act < 0:
        print("  CAUSA: Se registraron mas salidas que entradas en P1-PS")
        print("         o saStockAlmacen no recibio todas las entradas")
    if sal > ent:
        print(f"  CAUSA CONFIRMADA: Salidas ({sal}) > Entradas ({ent})")
        print(f"  El sistema desconto stock de P1-PS sin que existiera suficiente saldo")
    print()
    print("  ACCION RECOMENDADA:")
    print("  1. Crear un ajuste de entrada en Profit Plus para P1-PS")
    print(f"     por {abs(stock_act):.5f} kg de {ART} para corregir el saldo")
    print("  2. O revisar si la GCOM (Guia de Compra) fue mal contabilizada")
    print("  3. Este stock negativo no bloquea cierres actuales")
    print("     pero puede causar problemas en futuros cierres o reportes")

ca.close()
print(f"\n{SEP}\nDone.\n{SEP}")
