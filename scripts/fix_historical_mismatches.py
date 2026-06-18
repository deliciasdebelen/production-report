import sys
sys.path.append('/app')
import json
from app.database import SessionLocal
from app.external_db import engine_a
from app.models import LogisticsDispatch
from sqlalchemy import text

def fix_dispatch(dispatch_id, correct_guide_prefix):
    db = SessionLocal()
    dispatch = db.query(LogisticsDispatch).filter(LogisticsDispatch.id == dispatch_id).first()
    if not dispatch:
        print(f"Error: Dispatch with ID {dispatch_id} not found locally.")
        return
        
    old_ref = dispatch.document_ref
    print(f"Current Reference: {old_ref}")
    
    if ' | ' in old_ref:
        parts = old_ref.split(' | ', 1)
        new_ref = f"{correct_guide_prefix} | {parts[1]}"
        imported_invoices = parts[1].replace("Fact: ", "").strip()
    else:
        new_ref = correct_guide_prefix
        imported_invoices = ""
        
    print(f"New Reference to set: {new_ref}")
    
    # Update local PostgreSQL
    dispatch.document_ref = new_ref
    db.commit()
    print("PostgreSQL local database updated successfully.")
    
    if not imported_invoices:
        print("No imported invoices found in reference, skipping Profit update.")
        return
        
    docs = imported_invoices.split(',')
    dispatch_date_str = dispatch.date.strftime('%Y-%m-%d %H:%M:%S')
    
    with engine_a.connect() as conn:
        trans = conn.begin()
        try:
            for doc in docs:
                doc = doc.strip()
                if ':' in doc:
                    parts = doc.split(':')
                    prefix = parts[0].strip().upper()
                    doc_num = parts[1].strip()
                    table_name = "saFacturaVenta" if prefix == "FACT" else "saNotaEntregaVenta"
                    
                    # Check current values
                    check_query = text(f"SELECT campo5, campo6 FROM {table_name} WHERE doc_num = :doc_num")
                    row = conn.execute(check_query, {"doc_num": doc_num}).fetchone()
                    
                    current_campo5 = row[0] if row else None
                    current_campo6 = row[1] if row else None
                    
                    # Update campo6 to new_ref (truncated to 60 chars)
                    # If campo5 is None, set it to dispatch_date_str
                    # If campo5 is already set, keep it!
                    if current_campo5 is None or str(current_campo5).strip() == "":
                        update_sql = f"UPDATE {table_name} SET campo5 = :date_val, campo6 = :guide_val WHERE doc_num LIKE :doc_val"
                        params = {
                            "date_val": dispatch_date_str,
                            "guide_val": new_ref[:60],
                            "doc_val": f"%{doc_num}%"
                        }
                    else:
                        update_sql = f"UPDATE {table_name} SET campo6 = :guide_val WHERE doc_num LIKE :doc_val"
                        params = {
                            "guide_val": new_ref[:60],
                            "doc_val": f"%{doc_num}%"
                        }
                        
                    res = conn.execute(text(update_sql), params)
                    print(f"Updated {doc} in Profit ({table_name}). Rows affected: {res.rowcount}")
                    
            trans.commit()
            print("Profit database updated successfully.")
        except Exception as e:
            trans.rollback()
            print(f"Error updating Profit database: {e}")

if __name__ == '__main__':
    # Fix Dispatch ID 129 to GUIA-00000129
    fix_dispatch(129, "GUIA-00000129")
