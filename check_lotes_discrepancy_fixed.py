from check_reng_neto_audit import engine, text

def check_lotes_discrepancy_fixed():
    lotes = [
        ("L1260226-01", "PT01P01X012", "P1-PT"),
        ("L2 260302-02", "PT01D01X011", "P1-PT"),
        ("L1 260212-01", "PT01P01X013", "P1-PT"),
        ("L1 260218-01", "PT01P01X013", "P1-PT"),
        ("L1 260219-01", "PT01P01X013", "P1-PT"),
    ]
    
    with engine.connect() as conn:
        for lote, art, alma in lotes:
            print(f"\\n{'='*60}\\nANALIZANDO LOTE: '{lote}' | ARTICULO: '{art}'\\n{'='*60}")
            
            # Revisar saLoteEntrada (Stock Actual)
            q_ent = text("""
                SELECT rowguid, RTRIM(numero_lote) as lote, RTRIM(co_art) as co_art, 
                       RTRIM(co_alma) as co_alma, cantidad as cantidad_inicial, stock_actual,
                       tipo_doc, reng_num
                FROM saLoteEntrada
                WHERE numero_lote = :lote AND co_art = :art AND co_alma = :alma
            """)
            ent_guids = conn.execute(q_ent, {"lote": lote, "art": art, "alma": alma}).fetchall()
            
            if not ent_guids:
                print("  NO ENCONTRADO EN saLoteEntrada")
                continue
                
            for g in ent_guids:
                guid = g.rowguid
                cantidad_inicial = g.cantidad_inicial
                stock_actual = g.stock_actual
                
                print(f"  [Entrada] ROWGUID: {guid} | Doc: {g.tipo_doc}-{g.reng_num} | Inicial: {cantidad_inicial} | Stock Actual Registrado: {stock_actual}")
                
                # Revisar saLoteSalida vinculados
                q_salida = text("""
                    SELECT 
                        tipo_doc, 
                        reng_num, 
                        cantidad 
                    FROM saLoteSalida
                    WHERE Rowguid_Lote = :guid OR (numero_lote = :lote AND co_art = :art)
                """) # Usamos ambas por si acaso pierde el guid pero tiene el string
                
                salidas = conn.execute(q_salida, {"guid": guid, "lote": lote, "art": art}).fetchall()
                print("  [Salidas Vinculadas (saLoteSalida)]")
                total_salida = 0
                for s in salidas:
                    print("   - Doc:", s.tipo_doc, "| Reng:", s.reng_num, "| Cantidad:", s.cantidad)
                    total_salida += float(s.cantidad)
                
                if not salidas:
                    print("   (Sin salidas registradas)")
                
                matematica = float(cantidad_inicial) - total_salida
                print(f"\\n  => SUMATORIA DE SALIDAS: {total_salida}")
                print(f"  => MATEMÁTICA REAL (Entrada - Salida): {matematica}")
                if matematica != float(stock_actual):
                    print(f"  ❌ DISCREPANCIA DETECTADA! Profit dice {stock_actual}, pero la cuenta da {matematica}")
                else:
                    print(f"  ✅ CUADRA PERFECTAMENTE")

if __name__ == '__main__':
    check_lotes_discrepancy_fixed()
