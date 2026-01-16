from app.external_db import get_external_db
from sqlalchemy import text

def debug_article():
    db = next(get_external_db())
    try:
        # 1. Find the article code
        search_term = "PIPITA Mayonesa low cost Tradicional Tambor 208L"
        print(f"Searching for: {search_term}")
        
        sql_find = text("SELECT co_art, art_des FROM saarticulo WHERE art_des LIKE :term")
        result = db.execute(sql_find, {"term": f"%{search_term[:20]}%"}).fetchall() # First 20 chars to be safe
        
        if not result:
            print("No article found.")
            return

        for row in result:
            print(f"Found: {row.co_art} - {row.art_des}")
            co_art = row.co_art
            
            # 2. List all units
            print(f"--- Units for {co_art} ---")
            sql_units = text("SELECT co_uni, equivalencia FROM saartunidad WHERE co_art = :co_art")
            units = db.execute(sql_units, {"co_art": co_art}).fetchall()
            
            for u in units:
                print(f"Unit: {u.co_uni}, Equiv: {u.equivalencia}")
                
            # 3. Test the specific query used in API
            print(f"--- API Query Test ---")
            sql_api = text("""
                SELECT ISNULL((SELECT TOP 1 equivalencia 
                     FROM saartunidad 
                     WHERE co_art = :co_art AND co_uni = 'CAJ'), 0) as box_equiv
            """)
            val = db.execute(sql_api, {"co_art": co_art}).scalar()
            print(f"API returns box_equiv: {val}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_article()
