import json
from sqlalchemy import create_engine, text

DB_PROFIT_M = "mssql+pymssql://profit:profit@192.168.1.205/CARMAL_M"
engine_m = create_engine(DB_PROFIT_M)

order_num = '0000008890'
article = 'MP01D16X05-33'

with engine_m.connect() as conn:
    print(f"--- Orden de Produccion {order_num} ---")
    res = conn.execute(text(f"SELECT * FROM mpOrdenProduccion WHERE req_num = '{order_num}'")).fetchall()
    if res:
        for row in res:
            print(dict(row._mapping))
    else:
        print("Not found in mpOrdenProduccion")
        
    print(f"\n--- Requisiciones para {order_num} ---")
    res = conn.execute(text(f"SELECT * FROM mpRequisicion WHERE req_num = '{order_num}'")).fetchall()
    req_ids = []
    for row in res:
        d = dict(row._mapping)
        print(d)
        req_ids.append(d['id'])
        
    if req_ids:
        req_ids_str = ",".join(str(i) for i in req_ids)
        print(f"\n--- Renglones de Requisicion ---")
        res = conn.execute(text(f"SELECT * FROM mpRequisicionReng WHERE id IN ({req_ids_str})")).fetchall()
        for row in res:
            print(dict(row._mapping))
            
        print(f"\n--- Lotes Asignados a la Requisicion ---")
        res = conn.execute(text(f"SELECT * FROM mpRequisicionLote WHERE id IN ({req_ids_str})")).fetchall()
        for row in res:
            print(dict(row._mapping))
            
    print(f"\n--- Lotes de Almacen para {article} ---")
    res = conn.execute(text(f"SELECT top 10 co_art, co_alma, nro_lote, fec_lote, stock FROM mpLoteStock WHERE co_art = '{article}' AND stock > 0")).fetchall()
    for row in res:
        print(dict(row._mapping))
