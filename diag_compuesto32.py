import pyodbc

SERVER = "192.168.1.205"
DATABASE = "carmal_a"
USERNAME = "sa"
PASSWORD = "GRW7czL3*"

def connect():
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes"
    return pyodbc.connect(conn_str)

def run():
    conn = connect()
    cursor = conn.cursor()
    
    print("=" * 60)
    print("1. BUSCANDO ODP/OC relacionadas con Mermelada Compuesto 32")
    print("=" * 60)
    cursor.execute("""
        SELECT TOP 20 
            op.NumOrdProduccion,
            op.CodArticulo,
            op.DescArticulo,
            op.FechaCreacion,
            op.Estado,
            op.Cantidad,
            op.CantProd
        FROM saOrdenProduccion op
        WHERE op.DescArticulo LIKE '%Mermelada%' 
           OR op.DescArticulo LIKE '%Compuesto 32%'
           OR op.CodArticulo LIKE '%COMP%32%'
        ORDER BY op.FechaCreacion DESC
    """)
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"ODP: {r[0]} | Art: {r[1]} | Desc: {r[2]} | Fecha: {r[3]} | Estado: {r[4]} | Cant: {r[5]} | CantProd: {r[6]}")
    else:
        print("No se encontraron ODP de Mermelada Compuesto 32")
    
    print("\n" + "=" * 60)
    print("2. REVISANDO TABLA saLoteArticulo para compuesto 32")
    print("=" * 60)
    cursor.execute("""
        SELECT TOP 30
            la.NumLote,
            la.CodArticulo,
            la.DescArticulo,
            la.FechaFabricacion,
            la.FechaVencimiento,
            la.CantidadActual,
            la.CantidadOriginal,
            la.CodAlmacen,
            la.Estado
        FROM saLoteArticulo la
        WHERE la.DescArticulo LIKE '%Mermelada%'
           OR la.DescArticulo LIKE '%Compuesto 32%'
           OR la.CodArticulo LIKE '%COMP%32%'
           OR la.CodArticulo LIKE '%MERM%32%'
        ORDER BY la.FechaFabricacion DESC
    """)
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"Lote: {r[0]} | Art: {r[1]} | Desc: {r[2]} | FabFech: {r[3]} | VencFech: {r[4]} | CantAct: {r[5]:.2f} | CantOrig: {r[6]:.2f} | Alm: {r[7]} | Estado: {r[8]}")
    else:
        print("No se encontraron lotes de Mermelada Compuesto 32")

    print("\n" + "=" * 60)
    print("3. BUSCANDO el articulo en saArticulo")
    print("=" * 60)
    cursor.execute("""
        SELECT TOP 10
            a.CodArticulo,
            a.DesArticulo,
            a.TipoArticulo,
            a.Unidad,
            a.SaldoActual
        FROM saArticulo a
        WHERE a.DesArticulo LIKE '%Mermelada%Compuesto%'
           OR a.DesArticulo LIKE '%Compuesto%32%'
           OR a.CodArticulo LIKE '%COMP%32%'
        ORDER BY a.CodArticulo
    """)
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"Cod: {r[0]} | Desc: {r[1]} | Tipo: {r[2]} | Unidad: {r[3]} | Saldo: {r[4]}")
    else:
        print("No se encontró el artículo")

    print("\n" + "=" * 60)
    print("4. REVISANDO errores de traslado recientes (saTraslado)")
    print("=" * 60)
    cursor.execute("""
        SELECT TOP 20
            t.NumTraslado,
            t.FechaTraslado,
            t.Estado,
            t.Descripcion,
            t.AlmacenOrigen,
            t.AlmacenDestino
        FROM saTraslado t
        WHERE t.FechaTraslado >= DATEADD(day, -60, GETDATE())
        ORDER BY t.FechaTraslado DESC
    """)
    rows = cursor.fetchall()
    if rows:
        for r in rows:
            print(f"Traslado: {r[0]} | Fecha: {r[1]} | Estado: {r[2]} | Desc: {r[3]} | De: {r[4]} => A: {r[5]}")
    else:
        print("No se encontraron traslados recientes")
    
    conn.close()

if __name__ == "__main__":
    run()
