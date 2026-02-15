
from sqlalchemy import text
from app.external_db import engine_a

def inspect_nrec():
    doc_num = '0000001237'
    art_code = 'MP01N00X152'
    
    with engine_a.connect() as conn:
        print(f"--- Inspecting NREC {doc_num} Data ---")
        
        # 1. Check Line Item Quantity
        q_line = text("""
            SELECT reng_num, co_art, total_art, rowguid
            FROM saNotaRecepcionCompraReng
            WHERE doc_num = :d AND co_art = :a
        """)
        line = conn.execute(q_line, {"d": doc_num, "a": art_code}).fetchone()
        
        if line:
            print(f"Line Item: Reng={line.reng_num}, TotalArt={line.total_art}, Rowguid={line.rowguid}")
            
            # 2. Check saLoteEntrada for this line
            q_lot = text("""
                SELECT rowguid, numero_lote, cantidad, co_alma, tipo_doc
                FROM saLoteEntrada
                WHERE rowguid_reng = :r
            """)
            lots = conn.execute(q_lot, {"r": line.rowguid}).fetchall()
            
            print(f"\n--- Linked Lots in saLoteEntrada ({len(lots)}) ---")
            total_lot_qty = 0
            for lot in lots:
                print(f"Lot: {lot.numero_lote}, Qty: {lot.cantidad}, Alma: {lot.co_alma}, Type: {lot.tipo_doc}, GUID: {lot.rowguid}")
                total_lot_qty += float(lot.cantidad)
            
            print(f"\nTotal Lot Qty: {total_lot_qty}")
            
            if abs(total_lot_qty - float(line.total_art)) > 0.01:
                print("MISMATCH: Lot Total != Line Total")
            else:
                print("MATCH: Lot Total == Line Total")
                
        else:
            print("Line item not found.")

if __name__ == "__main__":
    inspect_nrec()
