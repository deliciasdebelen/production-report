from check_reng_neto_audit import engine, text

def check_lotes_discrepancy():
    lotes = [
        ("L1260226-01", "PT01P01X012", "P1-PT"),
        ("L2 260302-02", "PT01D01X011", "P1-PT"),
        ("L1 260212-01", "PT01P01X013", "P1-PT"),
        ("L1 260218-01", "PT01P01X013", "P1-PT"),
        ("L1 260219-01", "PT01P01X013", "P1-PT"),
    ]
    
    with engine.connect() as conn:
        for lote, art, alma in lotes:
            print(f"\\n{'='*50}\\nANALIZANDO LOTE: '{lote}' | ARTICULO: '{art}'\\n{'='*50}")
            
            # Revisar saLoteEntrada (Stock Actual)
            q_ent = text("""
                SELECT RTRIM(nro_lote) as lote, RTRIM(co_art) as co_art, RTRIM(co_alma) as co_alma, stock_act
                FROM saLoteEntrada
                WHERE nro_lote = :lote AND co_art = :art AND co_alma = :alma
            """)
            ent = conn.execute(q_ent, {"lote": lote, "art": art, "alma": alma}).fetchall()
            print("[saLoteEntrada]")
            if ent:
                for r in ent: print(" ", dict(r._mapping))
            else:
                print("  NO ENCONTRADO EN saLoteEntrada")
                
            # Revisar Movimientos de Entrada en Renglones (saAjusteReng, etc... pero podemos buscar todos los renglones q apunten a este rowguid si los hay, mejor vamos a buscar las tablas transaccionales por nro_lote si es aplicable, pero lotes no guardan lote_num directo, guardan rowguid... asi q usaremos el rowguid de saLoteEntrada para rastrear en saLoteSalida)
            q_ent_guid = text("""
                SELECT rowguid, cantidad 
                FROM saLoteEntrada 
                WHERE nro_lote = :lote AND co_art = :art AND co_alma = :alma
            """)
            ent_guids = conn.execute(q_ent_guid, {"lote": lote, "art": art, "alma": alma}).fetchall()
            
            for g in ent_guids:
                rowguid_ent = g.rowguid
                cantidad_inicial = g.cantidad
                print(f"\\n  [Información del Lote de Entrada: ROWGUID={rowguid_ent} | Cantidad Inicial={cantidad_inicial}]")
                
                # Revisar saLoteSalida vinculados
                q_salida = text("""
                    SELECT 
                        s.tipo_doc_s, 
                        RTRIM(s.num_doc_s) as num_doc_s, 
                        s.cantidad 
                    FROM saLoteSalida s
                    WHERE s.rowguid_lote_en = :guid
                """)
                salidas = conn.execute(q_salida, {"guid": rowguid_ent}).fetchall()
                print("  [Salidas Vinculadas (saLoteSalida)]")
                total_salida = 0
                for s in salidas:
                    print("   ", dict(s._mapping))
                    total_salida += float(s.cantidad)
                
                print(f"\\n  => SUMATORIA DE SALIDAS: {total_salida}")
                print(f"  => MATEMÁTICA REAL (Entrada - Salida): {float(cantidad_inicial) - total_salida}")

if __name__ == '__main__':
    check_lotes_discrepancy()
