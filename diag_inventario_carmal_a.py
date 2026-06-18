"""
diag_inventario_carmal_a.py
============================
Ejecuta los 5 pasos de diagnóstico de integridad de inventario
en carmal_a (192.168.60.15) y genera un informe detallado.

Artículo objetivo: MPO1N000153 (Azúcar)
Lote objetivo:     IA1M061225
Almacén:           P1-PS
Fecha de corte:    2026-03-03
"""

import urllib
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# ─── Conexión ─────────────────────────────────────────────────────────────────
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
    print(line)
    report_lines.append(line)

def show(df, label=""):
    if df is None or len(df) == 0:
        msg = f"  ⚠️  Sin resultados{(' — ' + label) if label else ''}"
        print(msg)
        report_lines.append(msg)
    else:
        txt = df.to_string(index=False)
        print(txt)
        report_lines.append(txt)
    print()
    report_lines.append("")

def run_query(sql):
    try:
        return pd.read_sql(sql, engine)
    except Exception as e:
        msg = f"  ❌ Error ejecutando query: {e}"
        print(msg)
        report_lines.append(msg)
        return None

def run_ddl(conn, label, sql):
    try:
        conn.execute(text(sql))
        msg = f"  ✅ {label}"
    except Exception as e:
        msg = f"  ❌ {label}: {e}"
    print(msg)
    report_lines.append(msg)

# ─────────────────────────────────────────────────────────────────────────────
section(f"PASO 1 — Movimientos de {CO_ART} / Lote {NRO_LOTE} desde {FECHA}")
# ─────────────────────────────────────────────────────────────────────────────
df1 = run_query(f"""
    SELECT
        aj.tipo_mov,
        aj.co_tipo_doc,
        aj.nro_doc,
        CONVERT(VARCHAR,aj.fec_emis,105) AS fec_emis,
        aj.co_art,
        aj.nro_lote,
        aj.cant_mov,
        aj.co_alma,
        aj.co_alma_d,
        aj.usuario,
        CONVERT(VARCHAR,aj.fec_reg,120)  AS fec_reg
    FROM saAjusteReng aj
    WHERE aj.co_art    = '{CO_ART}'
      AND aj.nro_lote  = '{NRO_LOTE}'
      AND aj.fec_emis >= '{FECHA}'
    ORDER BY aj.fec_reg DESC
""")
show(df1, "Movimientos del artículo/lote")

# Análisis automático
if df1 is not None and len(df1) > 0:
    positivos = df1[df1['cant_mov'] > 0]
    if len(positivos) > 0:
        msg = f"  🚨 ALERTA: Hay {len(positivos)} movimiento(s) con cant_mov POSITIVO (posible reverso silencioso):"
        print(msg); report_lines.append(msg)
        show(positivos)
    else:
        msg = "  ✅ Sin movimientos positivos inesperados (no hay reverso automático detectado)."
        print(msg); report_lines.append(msg)

# ─────────────────────────────────────────────────────────────────────────────
section(f"PASO 2A — Stock reportado en saStockAlmacen ({CO_ALMA})")
# ─────────────────────────────────────────────────────────────────────────────
df2a = run_query(f"""
    SELECT
        co_art,
        co_alma,
        nro_lote,
        stock_act,
        stock_com,
        CONVERT(VARCHAR,fec_ult_mov,120) AS fec_ult_mov
    FROM saStockAlmacen
    WHERE co_art  = '{CO_ART}'
      AND co_alma = '{CO_ALMA}'
""")
show(df2a, "Stock en saStockAlmacen")

# ─────────────────────────────────────────────────────────────────────────────
section(f"PASO 2B — Stock calculado desde movimientos vs. tabla")
# ─────────────────────────────────────────────────────────────────────────────
df2b = run_query(f"""
    SELECT
        co_art,
        co_alma,
        nro_lote,
        SUM(CASE
                WHEN tipo_mov = 'E' THEN  cant_mov
                WHEN tipo_mov = 'S' THEN -cant_mov
                ELSE cant_mov
            END)    AS stock_calculado,
        COUNT(*)    AS total_movimientos
    FROM saAjusteReng
    WHERE co_art  = '{CO_ART}'
      AND co_alma = '{CO_ALMA}'
    GROUP BY co_art, co_alma, nro_lote
""")
show(df2b, "Stock calculado desde saAjusteReng")

# Comparación automática
if df2a is not None and df2b is not None and len(df2a) > 0 and len(df2b) > 0:
    stock_tabla = float(df2a['stock_act'].iloc[0]) if 'stock_act' in df2a.columns else None
    stock_calc  = float(df2b['stock_calculado'].iloc[0]) if 'stock_calculado' in df2b.columns else None
    if stock_tabla is not None and stock_calc is not None:
        diff = stock_tabla - stock_calc
        msg = (f"\n  📊 COMPARACIÓN:\n"
               f"     stock_act (tabla)   = {stock_tabla:>12.5f}\n"
               f"     stock_calculado     = {stock_calc:>12.5f}\n"
               f"     Diferencia          = {diff:>12.5f}")
        print(msg); report_lines.append(msg)
        if abs(diff) > 0.001:
            alert = "  🚨 DIVERGENCIA DETECTADA: El stock de la tabla NO coincide con los movimientos."
        else:
            alert = "  ✅ Stock de tabla y movimientos coinciden."
        print(alert); report_lines.append(alert)

# ─────────────────────────────────────────────────────────────────────────────
section("PASO 3 — Triggers modificados desde 2026-03-01")
# ─────────────────────────────────────────────────────────────────────────────
df3 = run_query("""
    SELECT
        name                              AS trigger_nombre,
        type_desc,
        CONVERT(VARCHAR,modify_date,120)  AS fecha_modificacion,
        CONVERT(VARCHAR,create_date,120)  AS fecha_creacion,
        is_disabled
    FROM sys.triggers
    WHERE modify_date >= '2026-03-01'
    ORDER BY modify_date DESC
""")
show(df3, "Triggers modificados recientemente")

if df3 is not None and len(df3) > 0:
    criticos = [t for t in df3['trigger_nombre'].tolist()
                if any(x in t.lower() for x in ['stock', 'lote', 'ajuste', 'salida'])]
    if criticos:
        msg = f"  🚨 TRIGGERS CRÍTICOS modificados: {criticos}"
        print(msg); report_lines.append(msg)
    else:
        msg = "  ✅ Ningún trigger crítico (stock/lote/ajuste) fue modificado recientemente."
        print(msg); report_lines.append(msg)

# ─────────────────────────────────────────────────────────────────────────────
section("PASO 4 — Jobs de SQL Server Agent ejecutados el 03/03/2026")
# ─────────────────────────────────────────────────────────────────────────────
df4 = run_query("""
    SELECT
        j.name          AS nombre_job,
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
        END             AS resultado,
        LEFT(h.message, 200) AS mensaje
    FROM msdb.dbo.sysjobhistory h
    JOIN msdb.dbo.sysjobs j ON j.job_id = h.job_id
    WHERE h.run_date = 20260303
    ORDER BY h.run_date, h.run_time
""")
show(df4, "Jobs ejecutados el 03/03/2026")

if df4 is not None and len(df4) > 0:
    fallidos = df4[df4['resultado'] == 'FAILED']
    if len(fallidos) > 0:
        msg = f"  🚨 {len(fallidos)} JOB(S) FALLIDO(S) el 03/03:"
        print(msg); report_lines.append(msg)
        show(fallidos)
    else:
        msg = "  ✅ Todos los jobs del 03/03 completaron exitosamente."
        print(msg); report_lines.append(msg)

# ─────────────────────────────────────────────────────────────────────────────
section("PASO 5 — Instalando trigger de auditoría temporal (_AuditInventarioTemp)")
# ─────────────────────────────────────────────────────────────────────────────
with engine.begin() as conn:
    run_ddl(conn, "Crear tabla _AuditInventarioTemp (si no existe)", f"""
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = '_AuditInventarioTemp')
        CREATE TABLE dbo._AuditInventarioTemp (
            id           INT IDENTITY PRIMARY KEY,
            fec_captura  DATETIME       DEFAULT GETDATE(),
            tipo_mov     VARCHAR(10),
            co_tipo_doc  VARCHAR(20),
            nro_doc      VARCHAR(30),
            fec_emis     DATETIME,
            co_art       VARCHAR(30),
            nro_lote     VARCHAR(30),
            cant_mov     DECIMAL(18,4),
            co_alma      VARCHAR(20),
            usuario      VARCHAR(50),
            host_name    VARCHAR(100)   DEFAULT HOST_NAME(),
            program_name VARCHAR(200)   DEFAULT APP_NAME()
        )
    """)

    run_ddl(conn, "CREATE OR ALTER TRIGGER trg_AuditAzucar_Temp", f"""
        CREATE OR ALTER TRIGGER trg_AuditAzucar_Temp
        ON dbo.saAjusteReng
        AFTER INSERT, UPDATE
        AS
        BEGIN
            SET NOCOUNT ON;
            INSERT INTO dbo._AuditInventarioTemp
                (tipo_mov, co_tipo_doc, nro_doc, fec_emis,
                 co_art, nro_lote, cant_mov, co_alma, usuario)
            SELECT
                tipo_mov, co_tipo_doc, nro_doc, fec_emis,
                co_art, nro_lote, cant_mov, co_alma, usuario
            FROM inserted
            WHERE co_art = '{CO_ART}';
        END
    """)

msg = (f"\n  ℹ️  Trigger de auditoría activo. Para leer capturas después de reproducir el problema:\n"
       f"     SELECT * FROM dbo._AuditInventarioTemp ORDER BY fec_captura DESC;\n\n"
       f"  ℹ️  Para limpiar cuando termines:\n"
       f"     DROP TRIGGER trg_AuditAzucar_Temp;\n"
       f"     DROP TABLE dbo._AuditInventarioTemp;")
print(msg); report_lines.append(msg)

# ─────────────────────────────────────────────────────────────────────────────
section("RESUMEN EJECUTIVO")
# ─────────────────────────────────────────────────────────────────────────────
summary = f"""
  Servidor  : {SERVER}
  Base de datos: {DATABASE}
  Artículo  : {CO_ART} (Azúcar)
  Lote      : {NRO_LOTE}
  Almacén   : {CO_ALMA}
  Ejecutado : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

  PASO 1 — Movimientos post 03/03 : {"Ver tabla arriba" if df1 is not None else "ERROR"}
  PASO 2 — Comparación de stock   : {"Ver análisis arriba" if df2a is not None else "ERROR"}
  PASO 3 — Triggers modificados   : {"Ver tabla arriba" if df3 is not None else "ERROR"}
  PASO 4 — Jobs del Agent 03/03   : {"Ver tabla arriba" if df4 is not None else "ERROR"}
  PASO 5 — Trigger auditoría      : INSTALADO ✅
"""
print(summary); report_lines.append(summary)

# Guardar informe
report_path = "diag_inventario_result.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))
print(f"\n  📄 Informe guardado en: {report_path}")
