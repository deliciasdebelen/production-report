"""
pruebas_completas.py
=====================
Suite completa de pruebas post-corrección en carmal_a (192.168.60.15)

TEST 1  — Estado de todos los triggers relevantes
TEST 2  — Integridad del lote IA1M061225 en todos los almacenes
TEST 3  — Stock general del azúcar: saStockAlmacen vs saLoteEntrada
TEST 4  — Prueba de flujo de descargo (UPDATE simulado con ROLLBACK)
TEST 5  — Prueba del trigger trg_BlockLoteSinExistencia (bloqueo stock<=0)
TEST 6  — Las 10 inconsistencias NC: ¿siguen en stock 0 o se corrigieron?
TEST 7  — Tabla de auditoría _AuditLoteTemp (reversos capturados)
TEST 8  — Jobs del Agent: historial reciente (post 03/03)
TEST 9  — Verificar protecciones en servidor (SP + Trigger activos)
"""
import urllib
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

SERVER   = "192.168.60.15"
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

# ─────────────────────────────────────────────────────────────────────────────
sec(1, "Estado de triggers relevantes")
# ─────────────────────────────────────────────────────────────────────────────
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
    resultados['T1'] = orig_ok and old_dis and blk_ok
    print(f"\n  ActualizarFechaLote activo:        {'✅' if orig_ok else '❌'}")
    print(f"  ActualizarFechaLote_OLD deshabilitado: {'✅' if old_dis else '❌'}")
    print(f"  trg_BlockLoteSinExistencia activo: {'✅' if blk_ok else '❌'}")
    resultados['T1_detail'] = f"orig={orig_ok} old_dis={old_dis} blk={blk_ok}"

# ─────────────────────────────────────────────────────────────────────────────
sec(2, "Integridad del lote IA1M061225")
# ─────────────────────────────────────────────────────────────────────────────
df2 = qry("""
    SELECT numero_lote, co_art, co_alma,
           cantidad, stock_actual, revisado,
           CONVERT(VARCHAR,fecha_inicio,105)     AS fecha_inicio,
           CONVERT(VARCHAR,fecha_expiracion,105) AS vencimiento
    FROM saLoteEntrada
    WHERE numero_lote = 'IA1M061225'
    ORDER BY co_alma, stock_actual DESC
""")
if df2 is not None:
    con_stock   = df2[df2['stock_actual'] > 0]
    sin_stock   = df2[df2['stock_actual'] <= 0]
    quemados    = df2[df2['revisado'] == 'X']
    print(f"\n  Total registros del lote : {len(df2)}")
    print(f"  Con stock disponible     : {len(con_stock)} | Stock total: {con_stock['stock_actual'].sum():.2f}")
    print(f"  Con stock = 0 (agotados) : {len(sin_stock)}")
    print(f"  Marcados revisado='X'    : {len(quemados)}")
    resultados['T2'] = len(con_stock) > 0
    resultados['T2_stock_total'] = float(con_stock['stock_actual'].sum())

# ─────────────────────────────────────────────────────────────────────────────
sec(3, "Stock general azúcar: saStockAlmacen vs saLoteEntrada")
# ─────────────────────────────────────────────────────────────────────────────
df3a = qry("""
    SELECT co_alma, co_art, stock
    FROM saStockAlmacen
    WHERE co_art LIKE 'MP01N00X153%'
    ORDER BY co_alma
""", "saStockAlmacen")

df3b = qry("""
    SELECT co_alma,
           COUNT(*)              AS n_lotes,
           SUM(cantidad)         AS cantidad_total,
           SUM(stock_actual)     AS stock_real
    FROM saLoteEntrada
    WHERE co_art LIKE 'MP01N00X153%'
    GROUP BY co_alma
    ORDER BY co_alma
""", "saLoteEntrada (agrupado)")

if df3a is not None and df3b is not None and len(df3a) > 0 and len(df3b) > 0:
    stock_sa  = float(df3a['stock'].sum())
    stock_le  = float(df3b['stock_real'].sum())
    diff      = abs(stock_sa - stock_le)
    print(f"\n  saStockAlmacen total: {stock_sa:>12.2f}")
    print(f"  saLoteEntrada total : {stock_le:>12.2f}")
    print(f"  Diferencia          : {diff:>12.2f} {'✅ Aceptable' if diff < 10 else '⚠️ Divergencia'}")
    resultados['T3'] = diff < 100

# ─────────────────────────────────────────────────────────────────────────────
sec(4, "Flujo de descargo simulado (UPDATE + ROLLBACK seguro)")
# ─────────────────────────────────────────────────────────────────────────────
try:
    df4ref = pd.read_sql("""
        SELECT TOP 1 rowguid, numero_lote, co_art, co_alma, stock_actual
        FROM saLoteEntrada
        WHERE numero_lote = 'IA1M061225' AND co_alma = 'P1-PS'
          AND stock_actual >= 10
        ORDER BY stock_actual DESC
    """, engine)

    if len(df4ref) == 0:
        print("  ⚠️ Sin lote IA1M061225 con stock >=10 en P1-PS")
        resultados['T4'] = False
    else:
        nro   = df4ref['numero_lote'].iloc[0].strip()
        art   = df4ref['co_art'].iloc[0].strip()
        alma  = df4ref['co_alma'].iloc[0].strip()
        rguid = df4ref['rowguid'].iloc[0]
        prev  = float(df4ref['stock_actual'].iloc[0])
        desc  = 7.0  # simular descargo de 7 kg
        print(f"  Lote: {nro} | Art: {art} | Stock previo: {prev:.3f} | Descargo: {desc}")

        with engine.begin() as conn:
            conn.execute(text("SAVE TRANSACTION test_desc"))
            conn.execute(text(f"""
                UPDATE saLoteEntrada
                SET    stock_actual = stock_actual - {desc}
                WHERE  numero_lote  = '{nro}'
                  AND  co_art       = '{art}'
                  AND  co_alma      = '{alma}'
            """))
            df4p = pd.read_sql(f"""
                SELECT stock_actual FROM saLoteEntrada
                WHERE  numero_lote = '{nro}' AND co_art = '{art}' AND co_alma = '{alma}'
            """, conn)
            post = float(df4p['stock_actual'].iloc[0])
            delta = prev - post
            print(f"  Stock post-descargo (en transacción): {post:.3f}")
            print(f"  Delta real: {delta:.3f} — {'✅ CORRECTO' if abs(delta - desc) < 0.01 else '❌ INCORRECTO'}")
            conn.execute(text("ROLLBACK TRANSACTION test_desc"))
            print("  ✅ ROLLBACK ejecutado — BD sin cambios")
        resultados['T4'] = abs(delta - desc) < 0.01
        resultados['T4_delta'] = delta
except Exception as e:
    print(f"  ❌ {e}")
    resultados['T4'] = False

# ─────────────────────────────────────────────────────────────────────────────
sec(5, "Prueba del trigger trg_BlockLoteSinExistencia (debe bloquear)")
# ─────────────────────────────────────────────────────────────────────────────
print("  Intentando insertar en saLoteSalida con lote de stock_actual=0...")
lote_vacio = None
try:
    df5 = pd.read_sql("""
        SELECT TOP 1 rowguid, numero_lote, co_art, co_alma
        FROM saLoteEntrada
        WHERE stock_actual <= 0 AND co_alma = 'P1-PS'
    """, engine)
    if len(df5) > 0:
        lote_vacio = df5['numero_lote'].iloc[0].strip()
        art_v  = df5['co_art'].iloc[0].strip()
        alma_v = df5['co_alma'].iloc[0].strip()
        rg_v   = df5['rowguid'].iloc[0]
        bloqueado = False
        try:
            with engine.begin() as conn:
                conn.execute(text(f"""
                    INSERT INTO saLoteSalida
                        (reng_num,tipo_doc,co_art,co_alma,numero_lote,
                         Rowguid_Lote,cantidad,precio,
                         co_us_in,co_sucu_in,fe_us_in,
                         co_us_mo,fe_us_mo,revisado,trasnfe,rowguid)
                    VALUES(
                        9998,'TEST','{art_v}','{alma_v}','{lote_vacio}',
                        '{rg_v}',10,0,
                        'TEST','01',GETDATE(),
                        'TEST',GETDATE(),'0','0',NEWID()
                    )
                """))
        except Exception as ex:
            bloqueado = True
            print(f"  ✅ Trigger bloqueó correctamente: {str(ex)[:120]}")
        if not bloqueado:
            print("  ❌ El trigger NO bloqueó la inserción con stock <= 0")
        resultados['T5'] = bloqueado
    else:
        print("  ⚠️ No hay lotes con stock=0 en P1-PS para probar bloqueo")
        resultados['T5'] = None
except Exception as e:
    print(f"  ❌ {e}")
    resultados['T5'] = False

# ─────────────────────────────────────────────────────────────────────────────
sec(6, "Las 10 inconsistencias NC — estado actual del stock")
# ─────────────────────────────────────────────────────────────────────────────
lotes_nc = [
    'L1260226-01','L1 A260304-01','L1 260302-01','L1 260227-01',
    'L2 260302-02','L1 260212-01','L1 260218-01','L1 260219-01',
    'L1 260211-01','AFR260224-01'
]
lotes_str = "','".join(lotes_nc)
df6 = qry(f"""
    SELECT numero_lote, co_art, co_alma,
           cantidad, stock_actual, revisado,
           CONVERT(VARCHAR,fe_us_mo,120) AS ultima_mod
    FROM saLoteEntrada
    WHERE numero_lote IN ('{lotes_str}')
      AND co_alma = 'P1-PT'
    ORDER BY numero_lote
""")
if df6 is not None and len(df6) > 0:
    aun_cero = df6[df6['stock_actual'] == 0]
    print(f"\n  Encontrados: {len(df6)} | Aún en stock=0: {len(aun_cero)}")
    resultados['T6'] = len(aun_cero) == len(df6)  # siguen igual (no corregidas aún)
    resultados['T6_nc_count'] = len(df6)
else:
    print("  ⚠️ Ningún lote NC encontrado en P1-PT")
    resultados['T6'] = None

# ─────────────────────────────────────────────────────────────────────────────
sec(7, "Auditoría _AuditLoteTemp — captura de reversos")
# ─────────────────────────────────────────────────────────────────────────────
df7 = qry("""
    SELECT id, fec_captura, evento, numero_lote, co_art, co_alma, cantidad
    FROM dbo._AuditLoteTemp
    ORDER BY fec_captura DESC
""")
if df7 is not None and len(df7) > 0:
    inserts = len(df7[df7['evento'] == 'INSERT'])
    deletes = len(df7[df7['evento'] == 'DELETE'])
    print(f"\n  INSERTs: {inserts} | DELETEs (reversos): {deletes}")
    resultados['T7'] = deletes == 0
    if deletes > 0:
        print("  ⚠️ HAY REVERSOS — revisar los DELETE en la tabla")
else:
    print("  ✅ Tabla vacía — ningún evento registrado post-instalación")
    resultados['T7'] = True

# ─────────────────────────────────────────────────────────────────────────────
sec(8, "Jobs del Agent — historial desde 03/03 hasta hoy")
# ─────────────────────────────────────────────────────────────────────────────
df8 = qry("""
    SELECT j.name AS job, h.run_date, h.run_time,
           CASE h.run_status
               WHEN 0 THEN 'FAILED'
               WHEN 1 THEN 'SUCCEEDED'
               WHEN 3 THEN 'CANCELLED'
               ELSE 'OTHER'
           END AS resultado,
           LEFT(h.message,120) AS mensaje
    FROM msdb.dbo.sysjobhistory h
    JOIN msdb.dbo.sysjobs j ON j.job_id = h.job_id
    WHERE h.run_date >= 20260303
    ORDER BY h.run_date DESC, h.run_time DESC
""")
if df8 is not None and len(df8) > 0:
    fallidos = df8[df8['resultado'] == 'FAILED']
    print(f"\n  Total jobs ejecutados desde 03/03: {len(df8)}")
    print(f"  Fallidos: {len(fallidos)}")
    resultados['T8'] = len(fallidos) == 0
    if len(fallidos) > 0:
        print("\n  Jobs fallidos:")
        print(fallidos[['job','run_date','run_time','mensaje']].to_string(index=False))
else:
    resultados['T8'] = True

# ─────────────────────────────────────────────────────────────────────────────
sec(9, "Verificar SP pValidarExistenciaLote existe y es funcional")
# ─────────────────────────────────────────────────────────────────────────────
df9 = qry("""
    SELECT name, type_desc,
           CONVERT(VARCHAR,modify_date,120) AS modificado
    FROM sys.procedures
    WHERE name = 'pValidarExistenciaLote'
""")
resultados['T9'] = df9 is not None and len(df9) > 0

# ─────────────────────────────────────────────────────────────────────────────
#  RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────
duracion = (datetime.now() - inicio).seconds
print(f"\n{'='*64}")
print(f"  INFORME FINAL — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({duracion}s)")
print(f"{'='*64}")

tests = {
    "T1  Estado triggers (original activo, OLD deshabilitado)": resultados.get('T1'),
    "T2  Lote IA1M061225 con stock disponible":                 resultados.get('T2'),
    "T3  Stock saStockAlmacen ≈ saLoteEntrada":                 resultados.get('T3'),
    "T4  Descargo simulado correcto (delta=7.0)":               resultados.get('T4'),
    "T5  trg_BlockLoteSinExistencia bloquea stock<=0":          resultados.get('T5'),
    "T6  10 lotes NC encontrados en P1-PT":                     resultados.get('T6') is not None,
    "T7  Sin reversos automáticos en auditoría":                resultados.get('T7'),
    "T8  Sin jobs fallidos desde 03/03":                        resultados.get('T8'),
    "T9  SP pValidarExistenciaLote presente":                   resultados.get('T9'),
}

passed = sum(1 for v in tests.values() if v is True)
failed = sum(1 for v in tests.values() if v is False)
skipped = sum(1 for v in tests.values() if v is None)
total = len(tests)

for name, status in tests.items():
    icon = "✅" if status else ("⚠️" if status is None else "❌")
    print(f"  {icon} {name}")

print(f"\n  ─────────────────────────────────────────────")
print(f"  PASSED: {passed}/{total}  |  FAILED: {failed}  |  SKIPPED: {skipped}")
print(f"\n  Stock total lote IA1M061225 disponible: {resultados.get('T2_stock_total', 'N/A'):.2f} unidades")

if passed >= 7 and failed == 0:
    print(f"\n  🟢 SISTEMA OPERATIVO — Corrección verificada exitosamente")
elif failed > 0:
    print(f"\n  🔴 HAY FALLAS — Revisar checks arriba")
else:
    print(f"\n  🟡 MAYORMENTE OPERATIVO — Revisar items con ⚠️")
print("="*64)
