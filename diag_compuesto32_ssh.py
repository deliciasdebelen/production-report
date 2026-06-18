import paramiko

HOSTNAME = "192.168.1.205"
USERNAME = "Administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

SQL_QUERY = """
SET NOCOUNT ON;

DECLARE @articulo_acido NVARCHAR(50) = 'MP04N00X021';
DECLARE @articulo_azucar NVARCHAR(50) = 'MP01N00X153';
DECLARE @hoy DATE = GETDATE();

-- 1. Lotes de ACIDO CITRICO en el almacen P1-PS
SELECT
    'LOTES_ACIDO_CITRICO' AS query,
    la.NumLote,
    la.CodArticulo,
    la.DescArticulo,
    la.FechaVencimiento,
    la.CantidadActual,
    la.CodAlmacen,
    la.Estado,
    CASE WHEN la.FechaVencimiento < @hoy THEN 'VENCIDO' ELSE 'VIGENTE' END AS EstadoVencimiento
FROM saLoteArticulo la
WHERE la.CodArticulo = @articulo_acido
  AND la.CodAlmacen = 'P1-PS'
ORDER BY la.FechaVencimiento DESC;

-- 2. Todos los lotes de ACIDO CITRICO sin filtro de almacen
SELECT
    'LOTES_ACIDO_TODOS_ALMACENES' AS query,
    la.NumLote,
    la.CodArticulo,
    la.DescArticulo,
    la.FechaVencimiento,
    la.CantidadActual,
    la.CodAlmacen,
    la.Estado,
    CASE WHEN la.FechaVencimiento < @hoy THEN 'VENCIDO' ELSE 'VIGENTE' END AS EstadoVencimiento
FROM saLoteArticulo la
WHERE la.CodArticulo = @articulo_acido
  AND la.CantidadActual > 0
ORDER BY la.FechaVencimiento DESC;

-- 3. ODP de Compuesto 32 reciente
SELECT TOP 5
    'ODP_COMPUESTO32' AS query,
    op.NumOrdProduccion,
    op.CodArticulo,
    op.DescArticulo,
    op.FechaCreacion,
    op.Estado,
    op.Cantidad
FROM saOrdenProduccion op
WHERE op.DescArticulo LIKE '%COMPUESTO%32%'
   OR op.CodArticulo LIKE '%D17%'
ORDER BY op.FechaCreacion DESC;

-- 4. Verificar si el lote 3AX2112019 existe
SELECT
    'LOTE_3AX2112019' AS query,
    la.NumLote,
    la.CodArticulo,
    la.DescArticulo,
    la.FechaVencimiento,
    la.CantidadActual,
    la.CodAlmacen,
    la.Estado
FROM saLoteArticulo la
WHERE la.NumLote = '3AX2112019';
"""

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, PORT, USERNAME, PASSWORD, timeout=10)
        print(f"Conectado a {HOSTNAME}")
        
        # Run sqlcmd 
        escaped_query = SQL_QUERY.replace('"', '\\"').replace("'", "'\\''")
        cmd = f"sqlcmd -S localhost -U sa -P '{PASSWORD}' -d carmal_a -Q \"{SQL_QUERY.replace(chr(10), ' ')}\""
        
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        
        print("OUTPUT:")
        print(out[:5000])
        if err:
            print("STDERR:", err[:1000])
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run()
