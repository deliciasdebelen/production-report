"""
verificacion_final.py
======================
Verificación completa del estado post-parche en carmal_a (192.168.60.15):
1. Estado de triggers
2. Lotes del azúcar disponibles con stock real
3. Simular inserción en saLoteSalida (en transacción rollback) para probar el flujo
4. Leer tabla de auditoría _AuditLoteTemp
5. Resultado GO / NO-GO
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

def q(sql, label=""):
    try:
        df = pd.read_sql(sql, engine)
        if label:
            print(f"\n{'='*60}\n  {label}\n{'='*60}")
        print(df.to_string(index=False) if len(df) else "  (sin resultados)")
        return df
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return None

def ddl_safe(conn, label, sql):
    try:
        conn.execute(text(sql))
        print(f"  ✅ {label}")
        return True
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return False

# ─── 1. Estado de triggers ────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CHECK 1 — Estado de triggers post-parche")
print("="*60)
df_trg = q("""
    SELECT
        t.name                             AS trigger_nombre,
        o.name                             AS tabla,
        CASE t.is_disabled WHEN 1 THEN '🔴 DESHABILITADO' ELSE '🟢 ACTIVO' END AS estado,
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
ok_trigger = (df_trg is not None and
              any((df_trg['trigger_nombre'] == 'ActualizarFechaLote') &
                  (df_trg['estado'] == '🟢 ACTIVO')))
resultados['trigger_original_activo'] = ok_trigger

# ─── 2. Lotes disponibles del azúcar (co_art real de BD) ──────────────────────
print("\n" + "="*60)
print("  CHECK 2 — Lotes del artículo azúcar con stock en P1-PS")
print("="*60)

# Usar co_art real observado en BD (MP01N00X153)
df_lotes = q("""
    SELECT
        numero_lote, co_art, co_alma,
        cantidad, stock_actual, revisado,
        CONVERT(VARCHAR,fecha_inicio,105)     AS fecha_inicio,
        CONVERT(VARCHAR,fecha_expiracion,105) AS vencimiento
    FROM saLoteEntrada
    WHERE co_alma       = 'P1-PS'
      AND stock_actual  > 0
      AND (co_art LIKE 'MP01N00%' OR co_art LIKE 'MPO1N00%')
    ORDER BY stock_actual DESC
""")
ok_lotes = df_lotes is not None and len(df_lotes) > 0
resultados['lotes_disponibles'] = ok_lotes

# ─── 3. Estado del lote IA1M061225 en P1-PS ──────────────────────────────────
print("\n" + "="*60)
print("  CHECK 3 — Lote IA1M061225 en todos sus almacenes (con stock)")
print("="*60)
df_lote = q("""
    SELECT
        numero_lote, co_art, co_alma,
        cantidad, stock_actual, revisado,
        CONVERT(VARCHAR,fe_us_mo,120) AS ultima_mod
    FROM saLoteEntrada
    WHERE numero_lote = 'IA1M061225'
      AND stock_actual > 0
    ORDER BY stock_actual DESC
""")
resultados['lote_con_stock'] = df_lote is not None and len(df_lote) > 0

# ─── 4. Prueba de inserción simulada en saLoteSalida (ROLLBACK SAFE) ──────────
print("\n" + "="*60)
print("  CHECK 4 — Prueba de inserción en saLoteSalida (simulación en ROLLBACK)")
print("="*60)

# Obtener el rowguid del lote con más stock disponible
try:
    df_rowguid = pd.read_sql("""
        SELECT TOP 1
            rowguid, numero_lote, co_art, co_alma, stock_actual
        FROM saLoteEntrada
        WHERE numero_lote   = 'IA1M061225'
          AND co_alma       = 'P1-PS'
          AND stock_actual  > 0
        ORDER BY stock_actual DESC
    """, engine)

    if len(df_rowguid) == 0:
        print("  ⚠️  No hay lote IA1M061225 con stock en P1-PS — buscando cualquier lote del azúcar...")
        df_rowguid = pd.read_sql("""
            SELECT TOP 1
                rowguid, numero_lote, co_art, co_alma, stock_actual
            FROM saLoteEntrada
            WHERE co_alma       = 'P1-PS'
              AND stock_actual  > 0
              AND (co_art LIKE 'MP01N00%' OR co_art LIKE 'MPO1N00%')
            ORDER BY stock_actual DESC
        """, engine)

    if len(df_rowguid) > 0:
        rowguid     = df_rowguid['rowguid'].iloc[0]
        nro_lote    = df_rowguid['numero_lote'].iloc[0]
        co_art      = df_rowguid['co_art'].iloc[0]
        co_alma     = df_rowguid['co_alma'].iloc[0]
        stock_prev  = float(df_rowguid['stock_actual'].iloc[0])
        cant_test   = 1.0  # cantidad mínima de prueba

        print(f"  Lote seleccionado: {nro_lote} | Artículo: {co_art} | Almacén: {co_alma}")
        print(f"  Stock previo: {stock_prev:.5f} | Cantidad de prueba: {cant_test:.5f}")

        with engine.begin() as conn:
            # Iniciar savepoint para rollback seguro
            conn.execute(text("SAVE TRANSACTION prueba_salida"))

            insert_ok = ddl_safe(conn,
                f"INSERT en saLoteSalida (lote={nro_lote}, cant={cant_test})",
                f"""
                INSERT INTO saLoteSalida
                    (reng_num, tipo_doc, co_art, co_alma, numero_lote,
                     Rowguid_Lote, cantidad, precio,
                     co_us_in, co_sucu_in, fe_us_in,
                     revisado, trasnfe)
                VALUES (
                    9999, 'TEST', '{co_art}', '{co_alma}', '{nro_lote}',
                    '{rowguid}', {cant_test}, 0,
                    'AUDIT', '01', GETDATE(),
                    '0', '0'
                )
                """)

            if insert_ok:
                # Verificar que el trigger de bloqueo NO revirtió (si hubiera revertido,
                # la conexión estaría en estado de error)
                df_post = pd.read_sql(f"""
                    SELECT stock_actual FROM saLoteEntrada
                    WHERE numero_lote = '{nro_lote}'
                      AND co_alma     = '{co_alma}'
                      AND co_art      = '{co_art}'
                """, conn)
                stock_post = float(df_post['stock_actual'].iloc[0]) if len(df_post) else stock_prev

                print(f"  Stock post-inserción (antes de rollback): {stock_post:.5f}")
                delta = stock_prev - stock_post
                print(f"  Delta (descuento real): {delta:.5f}")
                resultados['descargo_funciona'] = delta > 0
                resultados['stock_prev']  = stock_prev
                resultados['stock_post']  = stock_post

            # Siempre hacer ROLLBACK de la prueba — no dejar datos sucios
            conn.execute(text("ROLLBACK TRANSACTION prueba_salida"))
            print("  ✅ ROLLBACK de prueba ejecutado — sin datos persistidos")

except Exception as e:
    print(f"  ❌ Error en prueba de inserción: {e}")
    resultados['descargo_funciona'] = False

# ─── 5. Tabla de auditoría ────────────────────────────────────────────────────
print("\n" + "="*60)
print("  CHECK 5 — Tabla _AuditLoteTemp (últimos eventos capturados)")
print("="*60)
df_audit = q("""
    SELECT TOP 20
        id, fec_captura, evento, numero_lote,
        co_art, co_alma, cantidad, tipo_doc,
        host_name, program_name
    FROM dbo._AuditLoteTemp
    ORDER BY fec_captura DESC
""")
resultados['audit_tiene_datos'] = df_audit is not None and len(df_audit) > 0

if df_audit is not None and len(df_audit) > 0:
    n_insert = len(df_audit[df_audit['evento'] == 'INSERT'])
    n_delete = len(df_audit[df_audit['evento'] == 'DELETE'])
    print(f"\n  📊 INSERTs capturados: {n_insert}")
    print(f"  📊 DELETEs capturados (reversos): {n_delete}")
    resultados['reversos_detectados'] = n_delete > 0

# ─── VEREDICTO FINAL ──────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"  VEREDICTO FINAL — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

checks = {
    "Trigger original ActualizarFechaLote activo": resultados.get('trigger_original_activo', False),
    "Lotes azúcar con stock disponible en P1-PS":  resultados.get('lotes_disponibles', False),
    "Lote IA1M061225 con stock > 0":              resultados.get('lote_con_stock', False),
    "Descargo de inventario funciona (delta > 0)": resultados.get('descargo_funciona', False),
}

all_ok = True
for check, status in checks.items():
    icon = "✅" if status else "❌"
    print(f"  {icon} {check}")
    if not status:
        all_ok = False

reversos = resultados.get('reversos_detectados', False)
print(f"\n  {'⚠️' if reversos else '✅'} Reversos automáticos detectados en auditoría: {'SÍ — INVESTIGAR' if reversos else 'NO — Limpio'}")

print("\n" + "="*60)
if all_ok and not reversos:
    print("  🟢 RESULTADO: CORRECCIÓN EXITOSA — Sistema operativo")
elif all_ok and reversos:
    print("  🟡 RESULTADO: PARCHE APLICADO pero hay reversos previos en auditoría")
else:
    print("  🔴 RESULTADO: HAY CHECKS FALLIDOS — Revisar detalles arriba")
print("="*60)
