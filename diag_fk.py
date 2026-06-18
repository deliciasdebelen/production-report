import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def sqlcmd(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -W -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace').strip()

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("DIAGNÓSTICO: FK_saLoteSalida_saLoteEntrada")
    print("=" * 70)

    # 1. Ver la FK
    print("\n[1] FK constraint en saLoteSalida")
    sql1 = """
        SELECT 
            fk.name AS fk_name,
            tp.name AS parent_table,
            cp.name AS parent_col,
            tr.name AS ref_table,
            cr.name AS ref_col
        FROM sys.foreign_keys fk
        JOIN sys.tables tp ON tp.object_id = fk.parent_object_id
        JOIN sys.tables tr ON tr.object_id = fk.referenced_object_id
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN sys.columns cp ON cp.object_id = fk.parent_object_id AND cp.column_id = fkc.parent_column_id
        JOIN sys.columns cr ON cr.object_id = fk.referenced_object_id AND cr.column_id = fkc.referenced_column_id
        WHERE tp.name = 'saLoteSalida'
    """
    print(sqlcmd(client, sql1))

    # 2. Entender qué columna tiene la FK
    # FK_saLoteSalida_saLoteEntrada relaciona Rowguid_Lote con rowguid de saLoteEntrada
    # Esto significa que Rowguid_Lote DEBE existir en saLoteEntrada.rowguid
    # No en saArtCompuestoGenReng.rowguid como pensaba
    
    # 3. Verificar: el Rowguid_Lote de los GCOMs en saLoteEntrada
    print("\n[2] ¿Los Rowguid_Lote de GCOMs existen en saLoteEntrada.rowguid?")
    sql2 = """
        SELECT ls.co_art, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               CAST(ls.Rowguid_Lote AS VARCHAR(50)) AS rg_lote,
               CASE WHEN le.rowguid IS NOT NULL THEN 'SI EXISTE en saLoteEntrada' 
                    ELSE '*** NO EXISTE ***' END AS en_lote_entrada
        FROM saLoteSalida ls
        LEFT JOIN saLoteEntrada le ON le.rowguid = ls.Rowguid_Lote
        WHERE ls.tipo_doc = 'GCOM'
          AND ls.fe_us_in >= '2026-01-01'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd(client, sql2))

    # 4. Ver registro saLoteEntrada de los lotes usados en GCOMs
    print("\n[3] Registros saLoteEntrada para los lotes de GCOMs huérfanos")
    sql3 = """
        SELECT le.rowguid, le.co_art, le.co_alma, le.numero_lote, 
               le.cantidad, le.stock_actual,
               CONVERT(VARCHAR, le.fecha_expiracion, 103) AS FecExp
        FROM saLoteEntrada le
        WHERE le.numero_lote IN ('506000033', '04042025', '000156-02072025')
          AND le.co_art = 'MP04N00X021'
          AND le.co_alma = 'P1-PS'
    """
    print(sqlcmd(client, sql3))

    # 5. NUEVO ENTENDIMIENTO:
    # saLoteSalida.Rowguid_Lote → FK → saLoteEntrada.rowguid
    # NO apunta a saArtCompuestoGenReng.rowguid
    # Entonces el vínculo con GenReng se hace de otra forma
    
    # 6. ¿Cómo se vincula saLoteSalida con saArtCompuestoGenReng entonces?
    print("\n[4] ¿Cómo se vincula saLoteSalida con saArtCompuestoGenReng? (ver todas las FKs)")
    sql4 = """
        SELECT 
            fk.name AS fk_name,
            tp.name AS parent_table,
            cp.name AS parent_col,
            tr.name AS ref_table,
            cr.name AS ref_col
        FROM sys.foreign_keys fk
        JOIN sys.tables tp ON tp.object_id = fk.parent_object_id
        JOIN sys.tables tr ON tr.object_id = fk.referenced_object_id
        JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN sys.columns cp ON cp.object_id = fk.parent_object_id AND cp.column_id = fkc.parent_column_id
        JOIN sys.columns cr ON cr.object_id = fk.referenced_object_id AND cr.column_id = fkc.referenced_column_id
        WHERE tp.name IN ('saLoteSalida', 'saArtCompuestoGenReng', 'saArtCompuestoGen')
        ORDER BY tp.name
    """
    print(sqlcmd(client, sql4))

    # 7. Verificar: el rowguid_reng en saLoteSalida (si existe)
    print("\n[5] Columnas de saLoteSalida (todas)")
    sql5 = """
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'saLoteSalida' ORDER BY ORDINAL_POSITION
    """
    print(sqlcmd(client, sql5))

    # 8. Ver un GCOM completo con todos sus campos
    print("\n[6] Un registro GCOM completo (todos los campos)")
    sql6 = """
        SELECT * FROM saLoteSalida
        WHERE tipo_doc = 'GCOM' AND fe_us_in >= '2026-05-21'
        ORDER BY fe_us_in DESC
    """
    print(sqlcmd(client, sql6))

    client.close()

if __name__ == "__main__":
    run()
