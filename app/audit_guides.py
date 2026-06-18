import sys
import os
sys.path.append('/app')
from app.database import SessionLocal
from app.models import LogisticsDispatch
import json
from collections import Counter

db = SessionLocal()

print("--- AUDITORIA DE GUIAS Y FACTURAS ---")
target_invoices = ['0000016480', '0000016443', '0000016454', '0000016476']
guides = db.query(LogisticsDispatch).all()

# Audit 1: Search where target invoices are used
invoice_locations = {inv: [] for inv in target_invoices}

print("\n1. Buscando las facturas reportadas en todas las guías...")
for g in guides:
    ref = g.document_ref
    
    for inv in target_invoices:
        if inv in ref:
            invoice_locations[inv].append(f"Guía ID: {g.id} (REF: {ref}) [Anulada: {g.is_annulled}]")
            
    if g.items_json:
        try:
            items = json.loads(g.items_json)
            for item in items:
                fact = item.get('fact', '')
                for inv in target_invoices:
                    if inv in fact and f"Guía ID: {g.id} (REF: {ref}) [Anulada: {g.is_annulled}]" not in invoice_locations[inv]:
                        invoice_locations[inv].append(f"Guía ID: {g.id} (REF: {ref}) [Anulada: {g.is_annulled}] (Encontrada en renglones)")
        except: pass

for inv, locs in invoice_locations.items():
    print(f"\nFactura {inv}:")
    if not locs:
        print("  -> NO SE ENCONTRO EN NINGUNA GUIA")
    for loc in locs:
        print(f"  -> {loc}")

# Audit 2: Check for internal duplicates in Guides 222 and 223
print("\n2. Revisando las guías 222 y 223 por duplicidad interna de renglones...")
for g in guides:
    if '222' in g.document_ref or '223' in g.document_ref:
        print(f"\nRevisando Guía ID: {g.id} (REF: {g.document_ref}) [Anulada: {g.is_annulled}]")
        if not g.items_json:
            print("  -> Sin renglones.")
            continue
            
        try:
            items = json.loads(g.items_json)
            print(f"  -> Total de renglones guardados: {len(items)}")
            
            item_keys = []
            for item in items:
                raw_item = item.get('item', '')
                fact = item.get('fact', '')
                lote = item.get('num_lote', '')
                qty = item.get('qty', '')
                key = f"{fact} | {raw_item} | Lote: {lote} | Qty: {qty}"
                item_keys.append(key)
                
            duplicates = [k for k, count in Counter(item_keys).items() if count > 1]
            if duplicates:
                print("  -> ¡SE ENCONTRARON DUPLICADOS INTERNOS EXACTOS EN LA GUIA!")
                for d in duplicates:
                    print(f"      - Duplicado: {d}")
            else:
                print("  -> No hay duplicados internos en esta guía.")
                
        except Exception as e:
            print(f"  -> Error leyendo JSON: {e}")
