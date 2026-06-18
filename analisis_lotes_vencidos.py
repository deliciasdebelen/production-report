import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
TARGET_SQL = "192.168.1.205"
SQL_USER  = "profit"
SQL_PASS  = "profit"

def rf(client, fname, db):
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {fname} 2>&1 | grep -v "password for"'
    )
    _, o, _ = client.exec_command(cmd, timeout=60)
    return o.read().decode(errors='replace').strip()

def write_sql(sftp, fname, sql):
    with sftp.file(fname, 'w') as f:
        f.write(sql)

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(JUMP_HOST, 22, JUMP_USER, JUMP_PASS)
sftp = c.open_sftp()

SEP = "=" * 70

print(SEP)
print("ANÁLISIS DE IMPACTO — Lotes Vencidos en carmal_m")
print(SEP)

# ── 1. OPs PROCESADAS pendientes de cierre ──────────────────────────
print("\n[1] ÓRDENES PROCESADAS pendientes de cierre en carmal_m")
write_sql(sftp, '/tmp/q1.sql', """
    SELECT p.odp_num,
           p.co_art AS art_producido,
           LEFT(p.descripcion,35) AS descripcion,
           CONVERT(VARCHAR,p.fec_ini,103) AS fecha_op,
           p.cantidad,
           p.status
    FROM NSPOrdenproduccion p
    WHERE p.status = 'PROCESADA'
    ORDER BY p.fec_ini DESC
""")
print(rf(c, '/tmp/q1.sql', 'carmal_m'))

# ── 2. MP de las OPs PROCESADAS ─────────────────────────────────────
print("\n[2] MATERIAS PRIMAS requeridas por OPs PROCESADAS")
write_sql(sftp, '/tmp/q2.sql', """
    SELECT p.odp_num,
           r.co_art AS materia_prima,
           r.requerida,
           r.recibida,
           r.solicitada
    FROM NSPOrdenproduccionReng r
    JOIN NSPOrdenproduccion p ON p.odp_num = r.odp_num
    WHERE p.status = 'PROCESADA'
    ORDER BY p.fec_ini DESC, r.odp_num, r.co_art
""")
print(rf(c, '/tmp/q2.sql', 'carmal_m'))

# ── 3. RESUMEN ejecutivo lotes vencidos con stock>0 ─────────────────
print("\n[3] RESUMEN: Lotes vencidos con stock>0 en carmal_a (por artículo/almacén)")
write_sql(sftp, '/tmp/q3.sql', """
    SELECT
        le.co_art,
        LEFT(ar.art_des,35)                          AS descripcion,
        ar.co_uni,
        le.co_alma,
        COUNT(DISTINCT le.numero_lote)               AS cant_lotes,
        CAST(SUM(le.stock_actual) AS DECIMAL(18,3))  AS stock_total,
        CAST(SUM(le.stock_actual * le.precio) AS DECIMAL(18,2)) AS valor_bs,
        MIN(DATEDIFF(DAY,le.fecha_expiracion,GETDATE())) AS min_dias_venc,
        MAX(DATEDIFF(DAY,le.fecha_expiracion,GETDATE())) AS max_dias_venc,
        SUM(CASE WHEN le.precio=0 THEN 1 ELSE 0 END) AS lotes_precio0,
        CASE WHEN le.co_art IN (
            SELECT DISTINCT r2.co_art
            FROM [CARMAL_M].[dbo].[NSPOrdenproduccionReng] r2
            JOIN [CARMAL_M].[dbo].[NSPOrdenproduccion] p2 ON p2.odp_num=r2.odp_num
            WHERE p2.status='PROCESADA'
        ) THEN 'SI' ELSE 'No' END AS bloquea_cierre_op
    FROM saLoteEntrada le
    JOIN saArticulo ar ON ar.co_art=le.co_art
    WHERE le.stock_actual     > 0
      AND le.fecha_expiracion < GETDATE()
      AND le.tipo_doc IN ('AJUS','NREC','COMP','GCOM','TRAS')
    GROUP BY le.co_art, ar.art_des, ar.co_uni, le.co_alma
    ORDER BY
        CASE WHEN le.co_art IN (
            SELECT DISTINCT r2.co_art
            FROM [CARMAL_M].[dbo].[NSPOrdenproduccionReng] r2
            JOIN [CARMAL_M].[dbo].[NSPOrdenproduccion] p2 ON p2.odp_num=r2.odp_num
            WHERE p2.status='PROCESADA'
        ) THEN 0 ELSE 1 END ASC,
        SUM(le.stock_actual * le.precio) DESC
""")
print(rf(c, '/tmp/q3.sql', 'carmal_a'))

# ── 4. DETALLE lotes vencidos que BLOQUEAN cierres de OP ────────────
print("\n[4] DETALLE: Lotes vencidos que bloquean cierres de OP PROCESADAS")
write_sql(sftp, '/tmp/q4.sql', """
    SELECT
        le.co_art, LEFT(ar.art_des,30) AS descripcion,
        le.co_alma, le.numero_lote,
        CAST(le.stock_actual AS DECIMAL(18,3)) AS stock,
        le.precio,
        CONVERT(VARCHAR,le.fecha_expiracion,103) AS fec_exp,
        DATEDIFF(DAY,le.fecha_expiracion,GETDATE()) AS dias_vencido,
        le.tipo_doc,
        CASE WHEN le.precio=0 THEN 'PRECIO=0 tambien' ELSE 'precio OK' END AS precio_estado
    FROM saLoteEntrada le
    JOIN saArticulo ar ON ar.co_art=le.co_art
    WHERE le.stock_actual     > 0
      AND le.fecha_expiracion < GETDATE()
      AND le.tipo_doc IN ('AJUS','NREC','COMP','GCOM','TRAS')
      AND le.co_art IN (
          SELECT DISTINCT r2.co_art
          FROM [CARMAL_M].[dbo].[NSPOrdenproduccionReng] r2
          JOIN [CARMAL_M].[dbo].[NSPOrdenproduccion] p2 ON p2.odp_num=r2.odp_num
          WHERE p2.status='PROCESADA'
      )
    ORDER BY le.co_art, le.fecha_expiracion DESC
""")
print(rf(c, '/tmp/q4.sql', 'carmal_a'))

# ── 5. nsp_obtenerlotes — donde filtra vencidos ─────────────────────
print("\n[5] nsp_obtenerlotes — FILTRO de fecha_expiracion (cómo descarta vencidos)")
write_sql(sftp, '/tmp/q5.sql', """
    SELECT SUBSTRING(sm.definition,3000,3000) AS fragmento
    FROM sys.sql_modules sm
    JOIN sys.objects o ON o.object_id=sm.object_id
    WHERE o.name='nsp_obtenerlotes'
""")
print(rf(c, '/tmp/q5.sql', 'carmal_m'))

# ── 6. TOTALES GLOBALES ──────────────────────────────────────────────
print("\n[6] TOTALES GLOBALES — impacto lotes vencidos")
write_sql(sftp, '/tmp/q6.sql', """
    SELECT
        COUNT(*)                                   AS total_registros,
        COUNT(DISTINCT co_art)                     AS articulos_afectados,
        COUNT(DISTINCT co_alma)                    AS almacenes_afectados,
        CAST(SUM(stock_actual) AS DECIMAL(18,2))   AS stock_total_vencido,
        CAST(SUM(stock_actual*precio) AS DECIMAL(18,2)) AS valor_total_bs,
        SUM(CASE WHEN precio=0 THEN 1 ELSE 0 END) AS lotes_precio_cero,
        MAX(DATEDIFF(DAY,fecha_expiracion,GETDATE())) AS max_dias_vencido
    FROM saLoteEntrada
    WHERE stock_actual     > 0
      AND fecha_expiracion < GETDATE()
      AND tipo_doc IN ('AJUS','NREC','COMP','GCOM','TRAS')
""")
print(rf(c, '/tmp/q6.sql', 'carmal_a'))

sftp.close()
c.close()
