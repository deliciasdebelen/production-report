from check_reng_neto_audit import engine, text

def apply_lotes_fix():
    data = [
        {"lote": "L1260226-01", "art": "PT01P01X012", "alma": "P1-PT", "expected": -24.0},
        {"lote": "L2 260302-02", "art": "PT01D01X011", "alma": "P1-PT", "expected": -60.0},
        {"lote": "L1 260212-01", "art": "PT01P01X013", "alma": "P1-PT", "expected": -122.0},
        {"lote": "L1 260218-01", "art": "PT01P01X013", "alma": "P1-PT", "expected": -96.0},
        {"lote": "L1 260219-01", "art": "PT01P01X013", "alma": "P1-PT", "expected": -624.0},
    ]
    
    with engine.begin() as conn: # Uso .begin() para auto-commit
        print("--- INICIANDO CORRECCION DE LOTES DEVUELTOS (NEGATIVOS) ---")
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
                
                # Check if this row is the exact one causing the validation error
                if abs(real_stock - d["expected"]) < 0.01 and float(ent.stock_actual) == 0.0:
                    print(f"✔️ Corrigiendo Lote {ent.lote} (Rowguid: {ent.rowguid}). de 0.0 a {real_stock}")
                    upd = text("""
                        UPDATE saLoteEntrada 
                        SET stock_actual = :real_stock
                        WHERE rowguid = :guid
                    """)
                    conn.execute(upd, {"real_stock": real_stock, "guid": ent.rowguid})
        print("--- ACTUALIZACION FINALIZADA ---")

if __name__ == '__main__':
    apply_lotes_fix()
