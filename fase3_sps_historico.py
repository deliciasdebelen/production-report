import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22
TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def sqlcmd_raw(client, sql, db=SQL_DB):
    clean_sql = " ".join(sql.split()).replace('"', '\\"')
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {db} -y 0 -Q "{clean_sql}" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    return stdout.read().decode(errors='replace')

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 70)
    print("FASE 3: LECTURA SPs CLAVE Y TRIGGER COMPUESTO")
    print("=" * 70)

    # SP_CRM_compuesto_validado - parece relevante
    print("\n==== SP: SP_CRM_compuesto_validado ====")
    sql1 = "SELECT OBJECT_DEFINITION(OBJECT_ID('SP_CRM_compuesto_validado'))"
    print(sqlcmd_raw(client, sql1))

    # sp_ForzarGeneracion
    print("\n==== SP: sp_ForzarGeneracion ====")
    sql2 = "SELECT OBJECT_DEFINITION(OBJECT_ID('sp_ForzarGeneracion'))"
    print(sqlcmd_raw(client, sql2))

    # TrigEstado_saArtCompuestoGen - full
    print("\n==== TRIGGER: TrigEstado_saArtCompuestoGen (COMPLETO) ====")
    sql3 = "SELECT OBJECT_DEFINITION(OBJECT_ID('TrigEstado_saArtCompuestoGen'))"
    print(sqlcmd_raw(client, sql3))

    # trg_BlockLoteSinExistencia - full
    print("\n==== TRIGGER: trg_BlockLoteSinExistencia (COMPLETO) ====")
    sql4 = "SELECT OBJECT_DEFINITION(OBJECT_ID('trg_BlockLoteSinExistencia'))"
    print(sqlcmd_raw(client, sql4))

    # ActualizarFechaLote - full
    print("\n==== TRIGGER: ActualizarFechaLote (COMPLETO) ====")
    sql5 = "SELECT OBJECT_DEFINITION(OBJECT_ID('ActualizarFechaLote'))"
    print(sqlcmd_raw(client, sql5))

    # RepStockArticulosxLotexAlmacen_Carmal - this might show lot logic
    print("\n==== SP: RepStockArticulosxLotexAlmacen_Carmal ====")
    sql6 = "SELECT OBJECT_DEFINITION(OBJECT_ID('RepStockArticulosxLotexAlmacen_Carmal'))"
    print(sqlcmd_raw(client, sql6))

    # Analizar la relacion entre saLoteSalida y saArtCompuestoGenReng para gen exitosa HISTORICA
    print("\n==== ANALISIS: ¿Alguna vez hubo GCOM vinculado a GenReng? (historico) ====")
    sql7 = """
        SELECT TOP 20 ls.tipo_doc, ls.reng_num, ls.co_art, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               CAST(ls.Rowguid_Lote AS VARCHAR(50)) AS rg_lotesalida,
               r.gene_num, r.lote_asignado,
               CAST(r.rowguid AS VARCHAR(50)) AS rg_genreng
        FROM saLoteSalida ls
        LEFT JOIN saArtCompuestoGenReng r ON r.rowguid = ls.Rowguid_Lote
        WHERE ls.tipo_doc = 'GCOM'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd_raw(client, sql7))

    # ¿Cuándo fue el ÚLTIMO GCOM con vínculo exitoso?
    print("\n==== ANALISIS: GCOM con saArtCompuestoGenReng vinculado (HISTORICO) ====")
    sql8 = """
        SELECT TOP 20 ls.tipo_doc, ls.reng_num, ls.co_art, ls.numero_lote, ls.cantidad,
               CONVERT(VARCHAR, ls.fe_us_in, 120) AS fecha,
               r.gene_num, r.lote_asignado
        FROM saLoteSalida ls
        INNER JOIN saArtCompuestoGenReng r ON r.rowguid = ls.Rowguid_Lote
        WHERE ls.tipo_doc = 'GCOM'
        ORDER BY ls.fe_us_in DESC
    """
    print(sqlcmd_raw(client, sql8))

    client.close()

if __name__ == "__main__":
    run()
