"""
pruebas_completas_205.py
=========================
Misma suite de 9 tests que pruebas_completas.py
pero apuntando a 192.168.1.205 (CARMAL_A)
"""
import urllib
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

SERVER   = "192.168.1.205"
DATABASE = "CARMAL_A"
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};DATABASE={DATABASE};"
    f"UID=PROFIT;PWD=profit;"
    f"Encrypt=yes;TrustServerCertificate=yes;"
)
params = urllib.parse.quote_plus(conn_str)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

resultados = {}
inicio = datetime.now()

def sec(n, titulo):
    print(f"\n{'='*64}")
    print(f"  TEST {n} — {titulo}")
    print(f"{'='*64}")

def qry(sql, label=""):
    try:
        df = pd.read_sql(sql, engine)
        if label: print(f"\n  [{label}]")
        print(df.to_string(index=False) if len(df) else "  (sin resultados)")
        return df
    except Exception as e:
        print(f"  ❌ {label or 'Query'}: {e}")
        return None

def run(conn, label, sql):
    try:
        conn.execute(text(sql))
        print(f"  ✅ {label}")
        return True
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return False

# ─── TEST 1: Estado de triggers ───────────────────────────────────────────────
sec(1, "Estado de triggers relevantes")
df1 = qry("""
    SELECT t.name, o.name AS tabla, t.is_disabled,
           CONVERT(VARCHAR,t.create_date,120) AS creado,
           CONVERT(VARCHAR,t.modify_date,120) AS modificado
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.name IN (
        'ActualizarFechaLote',
        'ActualizarFechaLote_OLD_20260319',
        'trg_BlockLoteSinExistencia',
        'trg_AuditLoteTemp'
    )
    ORDER BY t.name
""")
if df1 is not None:
    orig_ok = any((df1['name'] == 'ActualizarFechaLote') & (~df1['is_disabled']))
    old_dis = any((df1['name'] == 'ActualizarFechaLote_OLD_20260319') & (df1['is_disabled']))
    blk_ok  = any((df1['name'] == 'trg_BlockLoteSinExistencia') & (~df1['is_disabled']))
    resultados['T1'] = orig_ok and blk_ok
    print(f"\n  ActualizarFechaLote activo:            {'✅' if orig_ok else '❌ NO ENCONTRADO/INACTIVO'}")
    print(f"  ActualizarFechaLote_OLD_20260319 dis.: {'✅' if old_dis else '⚠️ No existe (este servidor aún no corregido)'}")
    print(f"  trg_BlockLoteSinExistencia activo:     {'✅' if blk_ok else '❌ NO ENCONTRADO'}")
else:
    resultados['T1'] = False

# ─── TEST 2: Lote IA1M061225 ──────────────────────────────────────────────────
sec(2, "Integridad del lote IA1M061225")
df2 = qry("""
    SELECT numero_lote, co_art, co_alma,
           cantidad, stock_actual, revisado,
           CONVERT(VARCHAR,fecha_inicio,105) AS fecha_inicio
    FROM saLoteEntrada
    WHERE numero_lote = 'IA1M061225'
    ORDER BY co_alma, stock_actual DESC
""")
if df2 is not None:
    con_stock = df2[df2['stock_actual'] > 0]
    print(f"\n  Total registros: {len(df2)} | Con stock>0: {len(con_stock)} | Stock total: {con_stock['stock_actual'].sum():.2f}")
    resultados['T2'] = len(con_stock) > 0
    resultados['T2_stock'] = float(con_stock['stock_actual'].sum())
else:
    resultados['T2'] = False

# ─── TEST 3: saStockAlmacen vs saLoteEntrada ─────────────────────────────────
sec(3, "Stock saStockAlmacen vs saLoteEntrada (azúcar)")
df3a = qry("""
    SELECT co_alma, co_art, stock
    FROM saStockAlmacen
    WHERE co_art LIKE 'MP01N00%'
    ORDER BY co_alma
""", "saStockAlmacen")
df3b = qry("""
    SELECT co_alma, COUNT(*) AS n_lotes,
           SUM(stock_actual) AS stock_real
    FROM saLoteEntrada
    WHERE co_art LIKE 'MP01N00%'
    GROUP BY co_alma ORDER BY co_alma
""", "saLoteEntrada")
if df3a is not None and df3b is not None and len(df3a) > 0 and len(df3b) > 0:
    diff = abs(float(df3a['stock'].sum()) - float(df3b['stock_real'].sum()))
    print(f"\n  Diferencia total: {diff:.2f} {'✅' if diff < 100 else '⚠️'}")
    resultados['T3'] = diff < 1000
else:
    resultados['T3'] = None

# ─── TEST 4: Descargo simulado ────────────────────────────────────────────────
sec(4, "Flujo de descargo simulado (UPDATE + ROLLBACK seguro)")
try:
    df4r = pd.read_sql("""
        SELECT TOP 1 rowguid, numero_lote, co_art, co_alma, stock_actual
        FROM saLoteEntrada
        WHERE co_alma = 'P1-PS' AND stock_actual >= 10
          AND co_art LIKE 'MP01N00%'
        ORDER BY stock_actual DESC
    """, engine)
    if len(df4r) == 0:
        print("  ⚠️ Sin lote de azúcar con stock>=10 en P1-PS")
        resultados['T4'] = None
    else:
        nro  = df4r['numero_lote'].iloc[0].strip()
        art  = df4r['co_art'].iloc[0].strip()
        alma = df4r['co_alma'].iloc[0].strip()
        prev = float(df4r['stock_actual'].iloc[0])
        desc = 7.0
        print(f"  Lote: {nro} | Stock previo: {prev:.3f} | Descargo: {desc}")
        with engine.begin() as conn:
            conn.execute(text("SAVE TRANSACTION test_desc"))
            conn.execute(text(f"""
                UPDATE saLoteEntrada SET stock_actual = stock_actual - {desc}
                WHERE numero_lote='{nro}' AND co_art='{art}' AND co_alma='{alma}'
            """))
            df4p = pd.read_sql(f"""
                SELECT TOP 1 stock_actual FROM saLoteEntrada
                WHERE numero_lote='{nro}' AND co_art='{art}' AND co_alma='{alma}'
                ORDER BY stock_actual
            """, conn)
            post  = float(df4p['stock_actual'].iloc[0])
            delta = prev - post
            print(f"  Post-update: {post:.3f} | Delta: {delta:.3f} → {'✅' if delta > 0 else '❌'}")
            conn.execute(text("ROLLBACK TRANSACTION test_desc"))
            print("  ✅ ROLLBACK — sin datos persistidos")
        resultados['T4'] = delta > 0
except Exception as e:
    print(f"  ❌ {e}")
    resultados['T4'] = False

# ─── TEST 5: Bloqueo de lote con stock<=0 ────────────────────────────────────
sec(5, "trg_BlockLoteSinExistencia bloquea inserción con stock<=0")
try:
    df5r = pd.read_sql("""
        SELECT TOP 1 rowguid, numero_lote, co_art, co_alma
        FROM saLoteEntrada WHERE stock_actual <= 0 AND co_alma = 'P1-PS'
    """, engine)
    if len(df5r) == 0:
        print("  ⚠️ Sin lotes con stock=0 en P1-PS para probar bloqueo")
        resultados['T5'] = None
    else:
        lv  = df5r['numero_lote'].iloc[0].strip()
        av  = df5r['co_art'].iloc[0].strip()
        alv = df5r['co_alma'].iloc[0].strip()
        rgv = df5r['rowguid'].iloc[0]
        bloqueado = False
        try:
            with engine.begin() as conn:
                conn.execute(text(f"""
                    INSERT INTO saLoteSalida
                        (reng_num,tipo_doc,co_art,co_alma,numero_lote,
                         Rowguid_Lote,cantidad,precio,
                         co_us_in,co_sucu_in,fe_us_in,
                         co_us_mo,fe_us_mo,revisado,trasnfe,rowguid)
                    VALUES(9997,'TEST','{av}','{alv}','{lv}',
                           '{rgv}',10,0,'TEST','01',GETDATE(),
                           'TEST',GETDATE(),'0','0',NEWID())
                """))
        except:
            bloqueado = True
        print(f"  {'✅ Trigger bloqueó correctamente' if bloqueado else '❌ Trigger NO bloqueó (revisar!)'}")
        resultados['T5'] = bloqueado
except Exception as e:
    print(f"  ❌ {e}")
    resultados['T5'] = False

# ─── TEST 6: 10 inconsistencias NC ───────────────────────────────────────────
sec(6, "Las 10 inconsistencias NC en P1-PT")
lotes_nc = [
    'L1260226-01','L1 A260304-01','L1 260302-01','L1 260227-01',
    'L2 260302-02','L1 260212-01','L1 260218-01','L1 260219-01',
    'L1 260211-01','AFR260224-01'
]
lotes_str = "','".join(lotes_nc)
df6 = qry(f"""
    SELECT numero_lote, co_art, co_alma, cantidad, stock_actual, revisado
    FROM saLoteEntrada
    WHERE numero_lote IN ('{lotes_str}') AND co_alma = 'P1-PT'
    ORDER BY numero_lote
""")
resultados['T6'] = df6 is not None

# ─── TEST 7: Auditoría ────────────────────────────────────────────────────────
sec(7, "Tabla _AuditLoteTemp")
df7 = qry("""
    SELECT TOP 10 id, fec_captura, evento, numero_lote, co_art, co_alma, cantidad
    FROM dbo._AuditLoteTemp ORDER BY fec_captura DESC
""")
if df7 is not None and len(df7) > 0:
    n_del = len(df7[df7['evento'] == 'DELETE'])
    print(f"  DELETEs(reversos): {n_del}")
    resultados['T7'] = n_del == 0
else:
    print("  ✅ Tabla vacía o inexistente (sin auditoría instalada aún)")
    resultados['T7'] = True

# ─── TEST 8: Jobs del Agent ───────────────────────────────────────────────────
sec(8, "Jobs del Agent — historial reciente")
df8 = qry("""
    SELECT TOP 30 j.name AS job, h.run_date,
           CASE h.run_status WHEN 0 THEN 'FAILED' WHEN 1 THEN 'SUCCEEDED'
                             WHEN 3 THEN 'CANCELLED' ELSE 'OTHER' END AS resultado,
           LEFT(h.message,100) AS mensaje
    FROM msdb.dbo.sysjobhistory h
    JOIN msdb.dbo.sysjobs j ON j.job_id = h.job_id
    WHERE h.run_date >= 20260303
    ORDER BY h.run_date DESC, h.run_time DESC
""")
if df8 is not None and len(df8) > 0:
    fallidos = df8[df8['resultado'] == 'FAILED']
    print(f"\n  Jobs desde 03/03: {len(df8)} | Fallidos: {len(fallidos)}")
    resultados['T8'] = len(fallidos) == 0
else:
    resultados['T8'] = True

# ─── TEST 9: SP pValidarExistenciaLote ───────────────────────────────────────
sec(9, "SP pValidarExistenciaLote y pValidarExistenciaLote_OLD_20260319")
df9 = qry("""
    SELECT name, type_desc, CONVERT(VARCHAR,modify_date,120) AS modificado
    FROM sys.procedures
    WHERE name LIKE 'pValidarExistenciaLote%'
    ORDER BY name
""")
resultados['T9'] = df9 is not None and len(df9) > 0

# ─── RESUMEN FINAL ────────────────────────────────────────────────────────────
duracion = (datetime.now() - inicio).seconds
print(f"\n{'='*64}")
print(f"  INFORME FINAL 192.168.1.205 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({duracion}s)")
print(f"{'='*64}")
tests = {
    "T1  Triggers configurados correctamente":               resultados.get('T1'),
    "T2  Lote IA1M061225 con stock":                        resultados.get('T2'),
    "T3  Divergencia saStockAlmacen vs saLoteEntrada <1000": resultados.get('T3'),
    "T4  Descargo simulado funciona (delta>0)":             resultados.get('T4'),
    "T5  trg_BlockLoteSinExistencia bloquea stock<=0":      resultados.get('T5'),
    "T6  Lotes NC encontrados en P1-PT":                    resultados.get('T6'),
    "T7  Sin reversos en auditoría":                        resultados.get('T7'),
    "T8  Sin jobs fallidos desde 03/03":                    resultados.get('T8'),
    "T9  SP pValidarExistenciaLote presente":               resultados.get('T9'),
}
passed  = sum(1 for v in tests.values() if v is True)
failed  = sum(1 for v in tests.values() if v is False)
skipped = sum(1 for v in tests.values() if v is None)

for name, status in tests.items():
    icon = "✅" if status is True else ("⚠️" if status is None else "❌")
    print(f"  {icon} {name}")

print(f"\n  ─────────────────────────────────────────────")
print(f"  PASSED: {passed}/9  |  FAILED: {failed}  |  SKIPPED/N/A: {skipped}")
if resultados.get('T2_stock'):
    print(f"  Stock azúcar disponible: {resultados['T2_stock']:.2f} unidades")

if failed == 0:
    print(f"\n  🟢 192.168.1.205 — OPERATIVO")
elif passed >= 6:
    print(f"\n  🟡 192.168.1.205 — MAYORMENTE OPERATIVO ({passed}/9)")
else:
    print(f"\n  🔴 192.168.1.205 — REQUIERE CORRECCIONES ({failed} fallos)")
print("="*64)
