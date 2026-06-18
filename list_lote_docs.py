from check_reng_neto_audit import engine, text

def list_discrepancy_docs():
    lotes = [
        {"lote": "L1260226-01", "art": "PT01P01X012", "alma": "P1-PT"},
        {"lote": "L2 260302-02", "art": "PT01D01X011", "alma": "P1-PT"},
        {"lote": "L1 260212-01", "art": "PT01P01X013", "alma": "P1-PT"},
        {"lote": "L1 260218-01", "art": "PT01P01X013", "alma": "P1-PT"},
        {"lote": "L1 260219-01", "art": "PT01P01X013", "alma": "P1-PT"},
    ]
    
    with engine.connect() as conn:
        for d in lotes:
            print(f"\\n{'='*70}\\nDOCUMENTOS DEL LOTE: '{d['lote']}' | ARTICULO: '{d['art']}'\\n{'='*70}")
            
            # Buscar el rowguid del lote de entrada
            q_ent = text("""
                SELECT rowguid, cantidad as lote_cantidad
                FROM saLoteEntrada
                WHERE numero_lote = :lote AND co_art = :art AND co_alma = :alma
            """)
            ents = conn.execute(q_ent, {"lote": d["lote"], "art": d["art"], "alma": d["alma"]}).fetchall()
            
            for ent in ents:
                print(f"LOTE DE ENTRADA {d['lote']} INGRESÓ CON UNA CANTIDAD DE: {float(ent.lote_cantidad)}\\n")
                
                # Traer los documentos de salida cruzando con renglones de venta (Factura/Nota Entrega)
                # Como saLoteSalida usa el rowguid_reng para apuntar al documento
                q_docs = text("""
                    SELECT 
                        s.tipo_doc, 
                        s.cantidad, 
                        s.fe_us_in as fecha_salida,
                        ISNULL(f.doc_num, ISNULL(n.doc_num, 'DESCONOCIDO')) as documento_origen
                    FROM saLoteSalida s
                    LEFT JOIN saFacturaVentaReng f ON s.rowguid_reng = f.rowguid AND s.tipo_doc = 'FACT'
                    LEFT JOIN saNotaEntregaVentaReng n ON s.rowguid_reng = n.rowguid AND s.tipo_doc = 'NENT'
                    WHERE s.Rowguid_Lote = :guid 
                    ORDER BY s.fe_us_in ASC
                """)
                
                docs = conn.execute(q_docs, {"guid": ent.rowguid}).fetchall()
                
                acumulado = 0.0
                print(f"{'FECHA':<22} | {'TIPO':<6} | {'NRO DOC':<15} | {'CANTIDAD':<10} | {'ACUM REBAJADO':<15}")
                print("-" * 75)
                for doc in docs:
                    qty = float(doc.cantidad)
                    acumulado += qty
                    
                    # Marcar con * los documentos que generaron el quiebre de stock
                    indicator = ""
                    if acumulado > float(ent.lote_cantidad):
                        indicator = "<-- GENERÓ NEGATIVO"
                        
                    print(f"{str(doc.fecha_salida)[:19]:<22} | {doc.tipo_doc:<6} | {str(doc.documento_origen):<15} | {qty:<10} | {acumulado:<15} {indicator}")
                
if __name__ == '__main__':
    list_discrepancy_docs()
