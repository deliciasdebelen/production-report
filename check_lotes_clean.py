from check_reng_neto_audit import engine, text

def report_clean():
    data = [
        {"lote": "L1260226-01", "art": "PT01P01X012", "alma": "P1-PT", "expected": -24.0},
        {"lote": "L2 260302-02", "art": "PT01D01X011", "alma": "P1-PT", "expected": -60.0},
        {"lote": "L1 260212-01", "art": "PT01P01X013", "alma": "P1-PT", "expected": -122.0},
        {"lote": "L1 260218-01", "art": "PT01P01X013", "alma": "P1-PT", "expected": -96.0},
        {"lote": "L1 260219-01", "art": "PT01P01X013", "alma": "P1-PT", "expected": -624.0},
    ]
    
    with engine.connect() as conn:
        for d in data:
            q_ent = text("""
                SELECT rowguid, RTRIM(numero_lote) as lote, cantidad, stock_actual
                FROM saLoteEntrada
                WHERE numero_lote = :lote AND co_art = :art AND co_alma = :alma
            """)
            ents = conn.execute(q_ent, {"lote": d["lote"], "art": d["art"], "alma": d["alma"]}).fetchall()
            
            for ent in ents:
                q_sal = text("""
                    SELECT SUM(cantidad) as total_salidas
                    FROM saLoteSalida
                    WHERE Rowguid_Lote = :guid 
                """)
                sal_res = conn.execute(q_sal, {"guid": ent.rowguid}).scalar()
                sal_res = float(sal_res or 0)
                
                real_stock = float(ent.cantidad) - sal_res
                
                print(f"Lote: {d['lote']} | Entrada: {float(ent.cantidad)} | Salidas: {sal_res} | Calc Real: {real_stock} | Esperado Profit: {d['expected']} | Stock BD: {float(ent.stock_actual)}")

if __name__ == '__main__':
    report_clean()
