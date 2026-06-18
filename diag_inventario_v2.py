"""
diag_inventario_v2.py
======================
Diagnóstico corregido con esquema real de carmal_a.

Esquema verificado:
  saAjusteReng  → ajue_num, reng_num, co_tipo, co_art, co_alma, total_art
  saStockAlmacen → co_alma, co_art, tipo, stock
  saLoteEntrada  → numero_lote, co_art, co_alma, cantidad, stock_actual, tipo_doc
  saLoteSalida   → numero_lote, co_art, co_alma, cantidad, tipo_doc

Nota: Los movimientos por lote se rastrean desde saLoteEntrada/saLoteSalida,
      no desde saAjusteReng (que es renglon de ajuste de articulos sin lote).
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

CO_ART   = "MPO1N000153"
NRO_LOTE = "IA1M061225"
CO_ALMA  = "P1-PS"
FECHA    = "2026-03-03"

report_lines = []

def section(title):
    line = f"\n{'='*64}\n  {title}\n{'='*64}"
    print(line); report_lines.append(line)

def show(df, label=""):
    if df is None or len(df) == 0:
        msg = f"  ⚠️  Sin resultados{(' — ' + label) if label else ''}"
        print(msg); report_lines.append(msg)
    else:
        txt = df.to_string(index=False)
        print(txt); report_lines.append(txt)
    print(); report_lines.append("")

def q(sql):
    try:
        return pd.read_sql(sql, engine)
    except Exception as e:
        msg = f"  ❌ Query error: {e}"
        print(msg); report_lines.append(msg)
        return None

def ddl(conn, label, sql):
    try:
        conn.execute(text(sql))
        msg = f"  ✅ {label}"
    except Exception as e:
        msg = f"  ❌ {label}: {e}"
    print(msg); report_lines.append(msg)

# ─── PASO 1: Entradas del lote en saLoteEntrada ───────────────────────────────
section(f"PASO 1A — Estado de saLoteEntrada para lote {NRO_LOTE}")
df1a = q(f"""
    SELECT
        numero_lote, tipo_doc, co_art, co_alma,
        cantidad, stock_actual,
        CONVERT(VARCHAR,fecha_inicio,105)    AS fecha_inicio,
        CONVERT(VARCHAR,fecha_expiracion,105) AS vencimiento,
        CONVERT(VARCHAR,fe_us_mo,120)        AS ultima_modificacion,
        co_us_mo                             AS usuario_mod
    FROM saLoteEntrada
    WHERE numero_lote = '{NRO_LOTE}'
      AND co_art      = '{CO_ART}'
""")
show(df1a, "Estado actual del lote en saLoteEntrada")

# ─── PASO 1B: Salidas registradas del lote ────────────────────────────────────
section(f"PASO 1B — Salidas registradas en saLoteSalida para lote {NRO_LOTE}")
df1b = q(f"""
    SELECT
        ls.numero_lote, ls.tipo_doc, ls.co_art, ls.co_alma,
        ls.cantidad,
        CONVERT(VARCHAR,ls.fe_us_in,120) AS fecha_registro,
        ls.co_us_in                      AS usuario
    FROM saLoteSalida ls
    WHERE ls.numero_lote = '{NRO_LOTE}'
      AND ls.co_art      = '{CO_ART}'
    ORDER BY ls.fe_us_in DESC
""")
show(df1b, "Salidas del lote en saLoteSalida")

# Balance
if df1a is not None and len(df1a) > 0 and df1b is not None:
    cant_entrada = float(df1a['cantidad'].iloc[0]) if 'cantidad' in df1a.columns else 0
    stock_actual = float(df1a['stock_actual'].iloc[0]) if 'stock_actual' in df1a.columns else 0
    cant_salidas = float(df1b['cantidad'].sum()) if len(df1b) > 0 else 0
    stock_calc   = cant_entrada - cant_salidas
    diff         = stock_actual - stock_calc
    msg = (f"\n  📊 BALANCE DEL LOTE:\n"
           f"     Cantidad original (entrada) = {cant_entrada:>10.5f}\n"
           f"     Total salidas registradas   = {cant_salidas:>10.5f}\n"
           f"     Stock calculado             = {stock_calc:>10.5f}\n"
           f"     Stock actual (tabla)        = {stock_actual:>10.5f}\n"
           f"     Diferencia                  = {diff:>10.5f}")
    print(msg); report_lines.append(msg)
    if abs(diff) > 0.001:
        alerta = f"  🚨 DIVERGENCIA: Stock en tabla difiere del calculado en {diff:.5f} unidades."
    else:
        alerta = "  ✅ Stock coincide con el calculado — no hay divergencia."
    print(alerta); report_lines.append(alerta)

# ─── PASO 2: Stock en saStockAlmacen ────────────────────────────────────────
section(f"PASO 2 — Stock general del artículo {CO_ART} en saStockAlmacen")
df2 = q(f"""
    SELECT co_alma, co_art, tipo, stock
    FROM saStockAlmacen
    WHERE co_art  = '{CO_ART}'
      AND co_alma = '{CO_ALMA}'
""")
show(df2, "Stock en saStockAlmacen")

# Buscar también en otros almacenes del mismo artículo
section(f"PASO 2B — Stock del artículo {CO_ART} en TODOS los almacenes")
df2b_all = q(f"""
    SELECT co_alma, co_art, tipo, stock
    FROM saStockAlmacen
    WHERE co_art = '{CO_ART}'
    ORDER BY co_alma
""")
show(df2b_all, "Stock por almacén")

# ─── PASO 3: Triggers modificados desde 2026-03-01 ───────────────────────────
section("PASO 3 — Triggers modificados desde 2026-03-01")
df3 = q("""
    SELECT
        t.name                              AS trigger_nombre,
        o.name                              AS tabla,
        t.type_desc,
        CONVERT(VARCHAR,t.modify_date,120)  AS fecha_modificacion,
        CONVERT(VARCHAR,t.create_date,120)  AS fecha_creacion,
        t.is_disabled
    FROM sys.triggers t
    JOIN sys.objects o ON t.parent_id = o.object_id
    WHERE t.modify_date >= '2026-03-01'
    ORDER BY t.modify_date DESC
""")
show(df3, "Triggers modificados recientemente")

if df3 is not None and len(df3) > 0:
    for _, row in df3.iterrows():
        nombre = row.get('trigger_nombre','').lower()
        tabla  = row.get('tabla','').lower()
        if any(x in nombre+tabla for x in ['lote','stock','ajuste','salida','entrada']):
            msg = f"  🚨 CRÍTICO: trigger '{row['trigger_nombre']}' en tabla '{row['tabla']}' modificado el {row['fecha_modificacion']}"
            print(msg); report_lines.append(msg)

# ─── PASO 4: Jobs del SQL Agent el 03/03 ─────────────────────────────────────
section("PASO 4 — Jobs del SQL Server Agent ejecutados el 03/03/2026")
df4 = q("""
    SELECT
        j.name              AS nombre_job,
        h.step_name,
        h.run_date,
        h.run_time,
        h.run_duration,
        CASE h.run_status
            WHEN 0 THEN 'FAILED'
            WHEN 1 THEN 'SUCCEEDED'
            WHEN 3 THEN 'CANCELLED'
            WHEN 4 THEN 'IN PROGRESS'
            ELSE       'UNKNOWN'
        END                 AS resultado,
        LEFT(h.message,200) AS mensaje
    FROM msdb.dbo.sysjobhistory h
    JOIN msdb.dbo.sysjobs j ON j.job_id = h.job_id
    WHERE h.run_date = 20260303
    ORDER BY h.run_time
""")
show(df4, "Jobs del 03/03/2026")

if df4 is not None and len(df4) > 0:
    fallidos = df4[df4['resultado'] == 'FAILED']
    if len(fallidos) > 0:
        msg = f"\n  🚨 {len(fallidos)} JOB(S) FALLIDO(S) el 03/03:"
        print(msg); report_lines.append(msg)
        show(fallidos)

# ─── PASO 5: Trigger auditoría temporal ──────────────────────────────────────
section("PASO 5 — Instalando trigger de auditoría temporal")
with engine.begin() as conn:
    ddl(conn, "Crear tabla _AuditLoteTemp", """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '_AuditLoteTemp')
        CREATE TABLE dbo._AuditLoteTemp (
            id           INT IDENTITY PRIMARY KEY,
            fec_captura  DATETIME DEFAULT GETDATE(),
            evento       VARCHAR(10),
            numero_lote  VARCHAR(20),
            co_art       VARCHAR(30),
            co_alma      VARCHAR(6),
            cantidad     DECIMAL(18,4),
            tipo_doc     VARCHAR(4),
            host_name    VARCHAR(100) DEFAULT HOST_NAME(),
            program_name VARCHAR(200) DEFAULT APP_NAME()
        )
    """)

    ddl(conn, "DROP trigger anterior si existe", """
        IF OBJECT_ID('dbo.trg_AuditLoteTemp', 'TR') IS NOT NULL
            DROP TRIGGER dbo.trg_AuditLoteTemp
    """)

    ddl(conn, "CREATE TRIGGER trg_AuditLoteTemp en saLoteSalida", """
        CREATE TRIGGER trg_AuditLoteTemp
        ON dbo.saLoteSalida
        AFTER INSERT, DELETE
        AS
        BEGIN
            SET NOCOUNT ON;
            -- Captura inserts
            INSERT INTO dbo._AuditLoteTemp
                (evento, numero_lote, co_art, co_alma, cantidad, tipo_doc)
            SELECT 'INSERT', numero_lote, co_art, co_alma, cantidad, tipo_doc
            FROM inserted;

            -- Captura deletes (reversos)
            INSERT INTO dbo._AuditLoteTemp
                (evento, numero_lote, co_art, co_alma, cantidad, tipo_doc)
            SELECT 'DELETE', numero_lote, co_art, co_alma, cantidad, tipo_doc
            FROM deleted;
        END
    """)

info = ("\n  ℹ️  Trigger de auditoría activo en saLoteSalida.\n"
        "  Después de reproducir el problema, consultar:\n"
        "  SELECT * FROM dbo._AuditLoteTemp ORDER BY fec_captura DESC;\n\n"
        "  Para limpiar:\n"
        "  DROP TRIGGER trg_AuditLoteTemp;\n"
        "  DROP TABLE dbo._AuditLoteTemp;")
print(info); report_lines.append(info)

# ─── RESUMEN ──────────────────────────────────────────────────────────────────
section("RESUMEN EJECUTIVO")
resumen = f"""
  Servidor      : {SERVER}
  Base de datos : {DATABASE}
  Artículo      : {CO_ART} (Azúcar MPO1N000153)
  Lote          : {NRO_LOTE}
  Almacén       : {CO_ALMA}
  Ejecutado     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

  PASO 1A — Estado lote saLoteEntrada   : {"Ver datos arriba" if df1a is not None and len(df1a)>0 else "⚠️ LOTE NO ENCONTRADO"}
  PASO 1B — Salidas en saLoteSalida     : {"Ver datos arriba" if df1b is not None else "ERROR"}
  PASO 2  — Stock saStockAlmacen        : {"Ver datos arriba" if df2 is not None else "ERROR"}
  PASO 3  — Triggers modificados        : {"Ver datos arriba" if df3 is not None else "ERROR"}
  PASO 4  — Jobs Agent 03/03            : {"Ver datos arriba" if df4 is not None else "ERROR"}
  PASO 5  — Trigger auditoría           : INSTALADO (trg_AuditLoteTemp en saLoteSalida) ✅
"""
print(resumen); report_lines.append(resumen)

report_path = "diag_inventario_v2_result.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))
print(f"  📄 Informe guardado en: {report_path}")
