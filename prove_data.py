from app.external_db import get_external_db
from sqlalchemy import text

db = next(get_external_db())

try:
    print("--- DATA VERIFICATION ---")
    
    # 1. Product from Production Order (Works)
    # "Las Delicias de Belén Mayonesa Premium Tradicional"
    sql_mayo = text("SELECT co_art, art_des FROM saArticulo WHERE art_des LIKE '%Mayonesa Premium Tradicional%'")
    mayos = db.execute(sql_mayo).fetchall()
    for m in mayos:
        print(f"\n[WORKING] {m.art_des} ({m.co_art})")
        units = db.execute(text(f"SELECT * FROM v_saArticulo_saArtUnidad WHERE co_art = '{m.co_art}'")).fetchall()
        for u in units:
             print(f"  - Unit: {u.co_uni} ({u.des_uni}) = {u.equivalencia}")

    # 2. Suspect Products (200g Mermeladas)
    print("\n\n[SUSPECT] Checking 200g items...")
    sql_200 = text("SELECT co_art, art_des FROM saArticulo WHERE art_des LIKE '%Mermelada%200g%'")
    merms = db.execute(sql_200).fetchall()
    
    for m in merms:
        has_box = False
        box_factor = 0
        units = db.execute(text(f"SELECT * FROM v_saArticulo_saArtUnidad WHERE co_art = '{m.co_art}'")).fetchall()
        for u in units:
            if 'CAJ' in u.des_uni.upper() or u.co_uni == 'CAJ':
                has_box = True
                box_factor = u.equivalencia
        
        status = "✅ OK" if has_box else "❌ MISSING BOX"
        print(f"{status} | {m.art_des[:50]}... | Factor: {box_factor}")

finally:
    db.close()
