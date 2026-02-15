
from sqlalchemy import text
from app.external_db import engine_a

def check_units():
    with engine_a.connect() as conn:
        q = text("""
            SELECT co_art, COUNT(*) as cnt
            FROM saArtUnidad
            WHERE uni_principal = 1
            GROUP BY co_art
            HAVING COUNT(*) > 1
        """)
        results = conn.execute(q).fetchall()
        
        if results:
            print(f"FOUND {len(results)} articles with multiple MAIN units!")
            for row in results:
                print(f"Art: {row.co_art} - Count: {row.cnt}")
        else:
            print("No duplicate Main Units found in saArtUnidad.")

if __name__ == "__main__":
    check_units()
