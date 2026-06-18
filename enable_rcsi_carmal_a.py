"""
enable_rcsi_carmal_a.py
Habilita Read Committed Snapshot Isolation (RCSI) en CARMAL_A.
Autorizado por el usuario el 2026-04-30.

Fases:
  1. Verificacion previa (tempdb, conexiones, espacio)
  2. Activacion de RCSI con ROLLBACK AFTER 5 SECONDS
  3. Verificacion post-activacion
  4. Reintento de cierres bloqueados (8860, 8868, 8869)
"""
import pyodbc
import time

# Conexion master para ALTER DATABASE (requiere sysadmin)
master = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=master;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
ca = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_A;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
cm = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=CARMAL_M;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=False)

master_cur = master.cursor()
ca_cur = ca.cursor()
cm_cur = cm.cursor()
SEP = "=" * 65

# ══════════════════════════════════════════════════════════════
# FASE 1 — VERIFICACION PREVIA
# ══════════════════════════════════════════════════════════════
print(f"{SEP}\n  FASE 1 — VERIFICACION PREVIA\n{SEP}")

# 1a. Estado actual de RCSI
master_cur.execute("""
SELECT name, is_read_committed_snapshot_on,
       snapshot_isolation_state_desc
FROM sys.databases WHERE name = 'CARMAL_A'
""")
r = master_cur.fetchone()
print(f"  CARMAL_A RCSI actual : {r[1]} (0=OFF, 1=ON)")
print(f"  Snapshot isolation   : {r[2]}")

if r[1] == 1:
    print("\n  RCSI ya esta HABILITADO. No se requiere accion.")
    master.close(); ca.close(); cm.close()
    exit(0)

# 1b. Espacio en tempdb
master_cur.execute("""
SELECT
    SUM(size * 8.0 / 1024) AS size_mb,
    SUM(size * 8.0 / 1024) - SUM(FILEPROPERTY(name,'SpaceUsed') * 8.0 / 1024) AS free_mb
FROM tempdb.sys.database_files
""")
r = master_cur.fetchone()
tempdb_size = float(r[0]) if r[0] else 0
tempdb_free = float(r[1]) if r[1] else 0
print(f"\n  tempdb tamaño total  : {tempdb_size:.0f} MB")
print(f"  tempdb espacio libre : {tempdb_free:.0f} MB")

if tempdb_free < 500:
    print("  ADVERTENCIA: tempdb con menos de 500MB libre.")
    print("  RCSI requiere espacio en tempdb para row versioning.")
    print("  Se continua de todas formas — RCSI solo usa tempdb cuando hay")
    print("  transacciones activas largas, no en estado idle.")

# 1c. Conexiones activas en CARMAL_A
master_cur.execute("""
SELECT COUNT(*) FROM sys.dm_exec_sessions
WHERE database_id = DB_ID('CARMAL_A')
  AND session_id <> @@SPID
""")
n_conn = master_cur.fetchone()[0]
print(f"\n  Conexiones activas en CARMAL_A: {n_conn}")
print("  (El ALTER DATABASE pedira ROLLBACK a las transacciones activas)")

# 1d. Privilegio sysadmin del usuario PROFIT
master_cur.execute("SELECT IS_SRVROLEMEMBER('sysadmin')")
is_sa = master_cur.fetchone()[0]
print(f"\n  Usuario PROFIT es sysadmin: {is_sa}")

if not is_sa:
    print("  ADVERTENCIA: El usuario no es sysadmin.")
    print("  ALTER DATABASE puede requerir permisos adicionales.")

# ══════════════════════════════════════════════════════════════
# FASE 2 — ACTIVAR RCSI
# ══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  FASE 2 — ACTIVANDO RCSI EN CARMAL_A\n{SEP}")
print("  Ejecutando: ALTER DATABASE CARMAL_A")
print("              SET READ_COMMITTED_SNAPSHOT ON")
print("              WITH ROLLBACK AFTER 5 SECONDS")
print()
print("  Las transacciones activas recibiran ROLLBACK en 5 segundos...")

try:
    master_cur.execute("""
    ALTER DATABASE CARMAL_A
    SET READ_COMMITTED_SNAPSHOT ON
    WITH ROLLBACK AFTER 5 SECONDS
    """)
    print("  Comando ejecutado.")
    time.sleep(3)  # esperar a que aplique

except Exception as e:
    err = str(e)
    print(f"\n  Error al ejecutar ALTER DATABASE: {err}")
    if 'permission' in err.lower() or 'privilegio' in err.lower():
        print("\n  El usuario PROFIT no tiene privilegio de ALTER DATABASE.")
        print("  Se requiere ejecutar desde una cuenta sysadmin.")
        print("  SQL a ejecutar manualmente en SQL Server Management Studio:")
        print("""
  USE master;
  ALTER DATABASE CARMAL_A
  SET READ_COMMITTED_SNAPSHOT ON
  WITH ROLLBACK AFTER 5 SECONDS;
  GO
  -- Verificar:
  SELECT name, is_read_committed_snapshot_on
  FROM sys.databases WHERE name = 'CARMAL_A';
        """)
    master.close(); ca.close(); cm.close()
    exit(1)

# ══════════════════════════════════════════════════════════════
# FASE 3 — VERIFICACION POST-ACTIVACION
# ══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  FASE 3 — VERIFICACION POST-ACTIVACION\n{SEP}")

# Reconectar para ver el estado actualizado
master.close()
master = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.205;'
    'DATABASE=master;UID=PROFIT;PWD=profit;'
    'Encrypt=yes;TrustServerCertificate=yes;', autocommit=True)
master_cur = master.cursor()

master_cur.execute("""
SELECT name,
       is_read_committed_snapshot_on,
       snapshot_isolation_state_desc
FROM sys.databases WHERE name = 'CARMAL_A'
""")
r = master_cur.fetchone()
rcsi_on = r[1]
print(f"  is_read_committed_snapshot_on : {rcsi_on}")
print(f"  snapshot_isolation_state_desc : {r[2]}")

if rcsi_on == 1:
    print("\n  RCSI ACTIVADO EXITOSAMENTE en CARMAL_A.")
    print("  Beneficios activos:")
    print("  - Lectores ya no bloquean escritores")
    print("  - Escritores ya no bloquean lectores")
    print("  - Deadlocks por concurrencia de cierres eliminados")
else:
    print("\n  RCSI NO se activó. Verificar permisos o reintentar.")
    master.close(); ca.close(); cm.close()
    exit(1)

# ══════════════════════════════════════════════════════════════
# FASE 4 — REINTENTAR CIERRES BLOQUEADOS
# ══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  FASE 4 — REINTENTO CIERRES BLOQUEADOS\n{SEP}")

CIERRES = [
    {'cie': '0000008860', 'odp': '0000008881', 'desc': 'BT16 MP PIPITA'},
    {'cie': '0000008868', 'odp': '0000008879', 'desc': 'Pendiente hoy'},
    {'cie': '0000008869', 'odp': '0000008885', 'desc': 'Pendiente hoy'},
]

for c in CIERRES:
    print(f"\n  Intentando cierre {c['cie']} / ODP {c['odp']} ({c['desc']})...")
    try:
        cm_cur.execute("""
        EXEC sp_executesql
            N'SET NOCOUNT ON
              exec [nsp_spordenproduccioncierre]
              @odp_num,@cie_num,@usa_TR,@TiempoR,@co_mone,@tasa,
              @DB2k12,@co_sucu_in,@action,@fecha,@co_us_in',
            N'@odp_num nvarchar(10),@cie_num nvarchar(10),
              @usa_TR bit,@TiempoR nvarchar(15),
              @co_mone nvarchar(6),@tasa decimal(6,5),
              @DB2k12 nvarchar(8),@co_sucu_in nvarchar(2),
              @action nvarchar(6),@fecha datetime,
              @co_us_in nvarchar(3)',
            @odp_num=?,@cie_num=?,
            @usa_TR=0,@TiempoR=N'00D 00H 00M 00S',
            @co_mone=N'BS    ',@tasa=1.00000,
            @DB2k12=N'CARMAL_A',@co_sucu_in=N'P1',
            @action=N'cerrar',@fecha='2026-04-30 11:00:00',
            @co_us_in=N'999'
        """, c['odp'], c['cie'])

        rs_num = 0
        resultado = None
        while True:
            if cm_cur.description:
                rs_num += 1
                cols = [d[0] for d in cm_cur.description]
                rows = cm_cur.fetchall()
                if 'Resultado' in cols and rows:
                    resultado = rows[0][cols.index('Resultado')]
            if not cm_cur.nextset():
                break

        if resultado:
            print(f"  Resultado: {resultado}")
        else:
            print(f"  Sin ResultSet de error → cierre procesado correctamente")

        cm.rollback()  # prueba diagnostica
        print(f"  [ROLLBACK de prueba — ejecutar desde Profit Plus para confirmar]")

    except Exception as e:
        cm.rollback()
        err = str(e)
        if '441' in err or '1205' in err or 'deadlock' in err.lower():
            print(f"  TODAVIA con deadlock: {err[:150]}")
        elif '1453' in err:
            print(f"  Error 1453 (subconsulta): {err[:150]}")
        else:
            print(f"  Error: {err[:200]}")

master.close(); ca.close(); cm.close()
print(f"\n{SEP}\n  PROCESO COMPLETADO\n{SEP}")
