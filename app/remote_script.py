import sys
sys.path.append('/app')
from app.database import SessionLocal
from app.models import LogisticsDispatch
import json
from collections import Counter

db = SessionLocal()

for guide_num in ['GUIA-00000222', 'GUIA-00000223']:
    g = db.query(LogisticsDispatch).filter(LogisticsDispatch.document_ref.like(f"{guide_num}%")).first()
    if g:
        print(f"\\n--- GUIA {g.document_ref} ---")
        try:
            items = json.loads(g.items_json)
            print(f"Total renglones guardados: {len(items)}")
            
            item_keys = []
            for item in items:
                fact = item.get('fact', '')
                raw_item = item.get('item', '')
                lote = item.get('num_lote', '')
                qty = item.get('qty', '')
                item_keys.append(f"{fact} | {raw_item} | Lote: {lote} | Qty: {qty}")
                
            dups = [k for k, count in Counter(item_keys).items() if count > 1]
            if dups:
                print("-> ¡DUPLICADOS INTERNOS ENCONTRADOS!")
                for d in dups:
                    print(f"   - {d} (Aparece {Counter(item_keys)[d]} veces)")
            else:
                print("-> Sin duplicados internos.")
        except Exception as e:
            print(f"Error parseando JSON: {e}")
    else:
        print(f"No se encontro Guia {guide_num}")
