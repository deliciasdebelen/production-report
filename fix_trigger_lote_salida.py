import paramiko

JUMP_HOST = "192.168.1.79"
JUMP_USER = "administrador"
JUMP_PASS = "GRW7czL3*"
PORT = 22

TARGET_SQL = "192.168.1.205"
SQL_USER = "profit"
SQL_PASS = "profit"
SQL_DB = "carmal_a"

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(JUMP_HOST, PORT, JUMP_USER, JUMP_PASS)

    print("=" * 80)
    print("APLICANDO CORRECCIÓN CON ARCHIVO SQL TEMPORAL (USANDO profit/profit)")
    print("=" * 80)

    # Definición de la corrección del trigger (usando /* */)
    alter_sql = """
    ALTER TRIGGER [dbo].[trg_BlockLoteSinExistencia]
    ON [dbo].[saLoteSalida]
    AFTER INSERT
    AS
    BEGIN
        SET NOCOUNT ON;

        /* BLOQUEO MEJORADO: Verificar por el rowguid único del lote de entrada (Rowguid_Lote)
           en lugar de hacer match por nombre del lote y almacén de manera general.
           Esto evita que registros históricos con stock negativo de un mismo número de lote bloqueen las salidas válidas. */
        IF EXISTS (
            SELECT 1
            FROM inserted i
            JOIN saLoteEntrada le 
                ON le.rowguid = i.Rowguid_Lote
            WHERE le.stock_actual < 0
        )
        BEGIN
            RAISERROR(
                'BLOQUEO: El lote indicado no tiene suficiente existencia disponible. La operacion ha sido cancelada.',
                16, 1
            )
            ROLLBACK TRANSACTION
            RETURN
        END
    END
    """
    
    # Escribimos el archivo SQL en el jump host
    sftp = client.open_sftp()
    sql_file_path = "/tmp/fix_trigger.sql"
    with sftp.file(sql_file_path, "w") as f:
        f.write(alter_sql)
    sftp.close()
    print(f"✅ Archivo SQL escrito en el Jump Host en {sql_file_path}")

    # Ejecutamos el archivo SQL usando -i
    cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm -v /tmp:/tmp mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {SQL_DB} -i {sql_file_path} 2>&1 | grep -v "password for"'
    )
    
    print("Ejecutando sqlcmd -i...")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    
    if out:
        print("Salida:")
        print(out)
    if err:
        print("Error:")
        print(err)
        
    print("✅ Proceso de ejecución finalizado!")

    # Verificamos
    print("\nVerificando nueva definición del trigger...")
    verify_cmd = (
        f'echo "{JUMP_PASS}" | sudo -S docker run --rm mcr.microsoft.com/mssql-tools '
        f'/opt/mssql-tools/bin/sqlcmd -S {TARGET_SQL} -U {SQL_USER} -P "{SQL_PASS}" '
        f'-d {SQL_DB} -W -Q "EXEC sp_helptext \'dbo.trg_BlockLoteSinExistencia\'" 2>&1 | grep -v "password for"'
    )
    stdin, stdout, stderr = client.exec_command(verify_cmd)
    print(stdout.read().decode(errors='replace').strip())

    client.close()

if __name__ == "__main__":
    run()
