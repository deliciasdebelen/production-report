import os
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.external_db import SessionA, SessionM
from app.models import ProfitArticulo, ProfitStockAlmacen, ProfitFormula, ProfitFormulaReng
from sqlalchemy import text
import traceback

def sync_profit_data():
    db_local = SessionLocal()
    db_a = SessionA()
    db_m = SessionM()
    
    try:
        print("Starting ETL Sync from Profit Plus to Local Replica...")
        
        # 1. Sync saArticulo -> profit_articulo
        print("Syncing saArticulo...")
        art_query = text("SELECT RTrim(co_art), RTrim(art_des), RTrim(tipo), anulado FROM saArticulo")
        art_rows = db_a.execute(art_query).fetchall()
        
        db_local.execute(delete(ProfitArticulo))
        art_objects = [
            ProfitArticulo(co_art=r[0], art_des=r[1], tipo=r[2], anulado=bool(r[3]))
            for r in art_rows if r[0]
        ]
        db_local.bulk_save_objects(art_objects)
        db_local.commit()
        print(f" -> Synced {len(art_objects)} articulos.")
        
        # 2. Sync saStockAlmacen -> profit_stock_almacen
        print("Syncing saStockAlmacen...")
        stock_query = text("SELECT RTrim(co_art), RTrim(co_alma), stock FROM saStockAlmacen WHERE stock != 0")
        stock_rows = db_a.execute(stock_query).fetchall()
        
        db_local.execute(delete(ProfitStockAlmacen))
        stock_objects = [
            ProfitStockAlmacen(co_art=r[0], co_alma=r[1], stock=float(r[2] or 0.0))
            for r in stock_rows if r[0] and r[1]
        ]
        db_local.bulk_save_objects(stock_objects)
        db_local.commit()
        print(f" -> Synced {len(stock_objects)} stock records.")
        
        # 3. Sync NSPFormula -> profit_formula
        print("Syncing NSPFormula from carmal_m...")
        form_query = text("SELECT RTrim(co_for), RTrim(co_art), fpredeterminada FROM NSPFormula")
        form_rows = db_m.execute(form_query).fetchall()
        
        db_local.execute(delete(ProfitFormula))
        form_objects = [
            ProfitFormula(co_for=r[0], co_art=r[1], fpredeterminada=bool(r[2]))
            for r in form_rows if r[0] and r[1]
        ]
        db_local.bulk_save_objects(form_objects)
        db_local.commit()
        print(f" -> Synced {len(form_objects)} formulas.")
        
        # 4. Sync NSPFormulareng -> profit_formula_reng
        print("Syncing NSPFormulareng from carmal_m...")
        reng_query = text("SELECT RTrim(co_for), reng_num, RTrim(co_art), cantidad, RTrim(co_uni) FROM NSPFormulareng")
        reng_rows = db_m.execute(reng_query).fetchall()
        
        db_local.execute(delete(ProfitFormulaReng))
        reng_objects = [
            ProfitFormulaReng(co_for=r[0], reng_num=r[1], co_art=r[2], cantidad=float(r[3] or 0.0), co_uni=(r[4] or ""))
            for r in reng_rows if r[0] and r[2]
        ]
        db_local.bulk_save_objects(reng_objects)
        db_local.commit()
        print(f" -> Synced {len(reng_objects)} formula ingredients.")

        print("ETL Sync completed successfully!")
        
    except Exception as e:
        db_local.rollback()
        print(f"ETL Sync failed: {e}")
        traceback.print_exc()
    finally:
        db_local.close()
        db_a.close()
        db_m.close()

if __name__ == "__main__":
    sync_profit_data()
