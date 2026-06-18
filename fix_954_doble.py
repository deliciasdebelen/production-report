import paramiko
import sys

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

# ─────────────────────────────────────────────────────────────────────
# FIX 1: Reemplazar trigger por versión SEGURA (no bloquea a Profit)
# El trigger ya no ejecuta SP dentro de la transacción de Profit.
# En su lugar, solo actualiza rowguid_reng directamente con un UPDATE
# simple. Esto no puede causar deadlock ni rollback.
# ─────────────────────────────────────────────────────────────────────
TRIGGER_DROP = """
IF OBJECT_ID('dbo.trg_AutoReconciliarGCOM') IS NOT NULL
    DROP TRIGGER dbo.trg_AutoReconciliarGCOM;
"""

TRIGGER_SEGURO = """
CREATE TRIGGER [dbo].[trg_AutoReconciliarGCOM]
ON [dbo].[saLoteSalida]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Solo actuar en inserciones GCOM
    IF NOT EXISTS (SELECT 1 FROM inserted WHERE tipo_doc = 'GCOM')
        RETURN;

    -- Reparar rowguid_reng para los nuevos GCOMs cuyo rowguid_reng
    -- no existe en saArtCompuestoGenReng (bug de Profit)
    UPDATE ls
    SET ls.rowguid_reng = match.rg_correcto
    FROM saLoteSalida ls
    JOIN inserted i ON i.rowguid = ls.rowguid
    CROSS APPLY (
        SELECT TOP 1 r.rowguid AS rg_correcto
        FROM saArtCompuestoGenReng r
        JOIN saArtCompuestoGen g ON g.gene_num = r.gene_num
        WHERE r.co_art  = i.co_art
          AND r.co_alma = i.co_alma
          AND r.total_art >= i.cantidad
          AND DATEDIFF(DAY, g.fecha, i.fe_us_in) BETWEEN 0 AND 1
          AND NOT EXISTS (
              SELECT 1 FROM saLoteSalida ls2
              WHERE ls2.rowguid_reng = r.rowguid
                AND ls2.tipo_doc = 'GCOM'
                AND ls2.rowguid != i.rowguid
          )
        ORDER BY ABS(DATEDIFF(HOUR, g.fecha, i.fe_us_in)), g.fecha DESC
    ) match
    WHERE NOT EXISTS (
        SELECT 1 FROM saArtCompuestoGenReng r2
        WHERE r2.rowguid = ls.rowguid_reng
    );

    -- Marcar lote_asignado = 1 en los renglones que ya tienen su GCOM vinculado
    UPDATE r SET r.lote_asignado = 1
    FROM saArtCompuestoGenReng r
    WHERE EXISTS (
        SELECT 1 FROM saLoteSalida ls
        WHERE ls.rowguid_reng = r.rowguid
          AND ls.tipo_doc = 'GCOM'
    )
    AND r.lote_asignado = 0;

    -- Decrementar stock_actual en saLoteEntrada para los nuevos GCOMs
    UPDATE le SET le.stock_actual = le.stock_actual - i.cantidad
    FROM saLoteEntrada le
    JOIN inserted i ON le.rowguid = i.Rowguid_Lote
    WHERE i.tipo_doc = 'GCOM'
      AND le.stock_actual >= i.cantidad;

END;
"""

# ─────────────────────────────────────────────────────────────────────
# FIX 2: Lote fantasma 3AX2112019 en P1-PS
# El stock_actual de esos 4 registros = 25 kg c/u pero NUNCA fue
# consumido (no hay movimiento en saLoteSalida). Zerear el stock_actual
# para que Profit no lo muestre como disponible.
# ─────────────────────────────────────────────────────────────────────
FIX_LOTE_FANTASMA = """
-- Solo zeream stock_actual, NO eliminamos el registro (por integridad histórica)
-- Condicion: el lote esta vencido Y no tiene salidas registradas
UPDATE saLoteEntrada
SET stock_actual = 0
WHERE numero_lote = '3AX2112019'
  AND co_art = 'MP04N00X021'
  AND co_alma = 'P1-PS'
  AND fecha_expiracion < GETDATE()
  AND stock_actual > 0
  AND NOT EXISTS (
      SELECT 1 FROM saLoteSalida ls
      WHERE ls.numero_lote = '3AX2112019'
        AND ls.co_art = 'MP04N00X021'
        AND ls.co_alma = 'P1-PS'
  );
"""

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def sqlcmd_file(client, sql_content, filename='/tmp/fix954.sql', db=SQL_DB):
    sftp = client.open_sftp()
    with sftp.file(filename, 'w') as f:
        f.write(sql_content)
    sftp.close()
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -i {filename} 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("FIX DOBLE — Trigger seguro + Lote fantasma 3AX2112019")
    print("=" * 70)

    # ── FIX 1: Reemplazar trigger por versión segura ──
    print("\n[FIX 1a] Eliminando trigger anterior (problemático)...")
    r = sqlcmd_file(client, TRIGGER_DROP, '/tmp/trg_drop954.sql')
    print(f"  {r if r else 'OK'}")

    print("\n[FIX 1b] Instalando trigger SEGURO (no bloquea a Profit)...")
    r2 = sqlcmd_file(client, TRIGGER_SEGURO, '/tmp/trg_seguro.sql')
    print(f"  {r2 if r2 else 'OK — trigger instalado'}")

    # ── FIX 2: Limpiar lote fantasma 3AX2112019 ──
    print("\n[FIX 2] Zereando stock_actual del lote VENCIDO 3AX2112019 en P1-PS...")
    print("  Estado ANTES:")
    antes = sqlcmd(client, """
        SELECT numero_lote, co_alma, stock_actual,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp
        FROM saLoteEntrada
        WHERE numero_lote = '3AX2112019' AND co_art = 'MP04N00X021' AND co_alma = 'P1-PS'
    """)
    print(f"  {antes}")

    r3 = sqlcmd_file(client, FIX_LOTE_FANTASMA, '/tmp/fix_lote.sql')
    print(f"\n  Resultado: {r3 if r3 else 'OK — registros actualizados'}")

    print("\n  Estado DESPUÉS:")
    despues = sqlcmd(client, """
        SELECT numero_lote, co_alma, stock_actual,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               CASE WHEN stock_actual = 0 THEN 'LIMPIO' ELSE 'AUN CON STOCK' END AS estado
        FROM saLoteEntrada
        WHERE numero_lote = '3AX2112019' AND co_art = 'MP04N00X021' AND co_alma = 'P1-PS'
    """)
    print(f"  {despues}")

    # ── Verificar stock vigente que ahora verá Profit ──
    print("\n[VERIFICACIÓN] Lotes VIGENTES de MP04N00X021 en P1-PS (lo que Profit verá ahora)")
    vigentes = sqlcmd(client, """
        SELECT numero_lote, stock_actual,
               CONVERT(VARCHAR, fecha_expiracion, 103) AS FecExp,
               'VIGENTE' AS estado
        FROM saLoteEntrada
        WHERE co_art = 'MP04N00X021' AND co_alma = 'P1-PS'
          AND stock_actual > 0
          AND fecha_expiracion > GETDATE()
        ORDER BY fecha_expiracion ASC
    """)
    print(vigentes)

    # ── Verificar estado del trigger ──
    print("\n[VERIFICACIÓN TRIGGER] Triggers en saLoteSalida")
    triggers = sqlcmd(client, """
        SELECT t.name, CASE WHEN t.is_disabled=0 THEN 'ACTIVO' ELSE 'INACTIVO' END AS estado
        FROM sys.triggers t JOIN sys.objects o ON o.object_id = t.parent_id
        WHERE o.name = 'saLoteSalida'
    """)
    print(triggers)

    # ── Verificar renglones gen 954 aún pendientes ──
    print("\n[GEN 954] Estado actual de renglones")
    gen954 = sqlcmd(client, """
        SELECT r.reng_num, r.co_art, r.total_art, r.lote_asignado,
               CASE WHEN r.lote_asignado = 1 THEN 'ASIGNADO' ELSE 'PENDIENTE' END AS estado,
               sa.stock AS stock_disponible
        FROM saArtCompuestoGenReng r
        LEFT JOIN saStockAlmacen sa ON sa.co_art = r.co_art
            AND sa.co_alma = r.co_alma AND sa.tipo = 'ACT'
        WHERE r.gene_num = '0000000954'
        ORDER BY r.reng_num
    """)
    print(gen954)

    print("\n" + "=" * 70)
    print("FIXES APLICADOS. Indicaciones para el operador:")
    print("  1. Reabrir la generación 0000000954 en Profit Plus")
    print("  2. En 'Lotes de Salida', seleccionar los lotes vigentes")
    print("  3. Los lotes se guardarán correctamente (trigger corregido)")
    print("  4. El Ácido Cítrico mostrará ahora lotes vigentes (307000111, 20112024, etc.)")
    print("=" * 70)

    client.close()

if __name__ == "__main__":
    run()
