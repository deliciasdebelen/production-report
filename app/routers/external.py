from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..external_db import get_external_db
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/external",
    tags=["external"]
)

class ArticleSchema(BaseModel):
    code: str
    description: str
    unit: str
    box_equiv: float

@router.get("/articles", response_model=list[ArticleSchema])
def get_articles(category: str = None, db: Session = Depends(get_external_db)):
    try:
        if category == 'inventory':
            # New Query for Inventory: MP, ME, PT lines
            sql = text("""
                SELECT 
                    a.co_art as code,
                    a.art_des as description,
                    u.des_uni as unit,
                    ISNULL((
                        SELECT TOP 1 equivalencia 
                        FROM v_saArticulo_saArtUnidad 
                        WHERE co_art = a.co_art 
                        AND (co_uni = 'CAJ' OR des_uni LIKE '%CAJA%')
                    ), 0) as box_equiv
                FROM saArticulo a
                LEFT JOIN saartunidad au ON a.co_art = au.co_art AND au.equivalencia = 1
                LEFT JOIN saUnidad u ON au.co_uni = u.co_uni
                WHERE a.anulado = 0 AND a.co_lin IN ('MP', 'ME', 'PT')
                ORDER BY a.art_des
            """)
        else:
            # Default Query (Dispatch/Planning): PT only
            # User requested specific logic: Join saArtUnidad with co_uni = 'CAJ'
            sql = text("""
                SELECT 
                    a.co_art as code,
                    a.art_des as description,
                    u_base.des_uni as unit,
                    ISNULL(u_box.equivalencia, 0) as box_equiv
                FROM saArticulo a
                -- Base Unit (Equivalencia = 1)
                LEFT JOIN saArtUnidad au_base ON a.co_art = au_base.co_art AND au_base.equivalencia = 1
                LEFT JOIN saUnidad u_base ON au_base.co_uni = u_base.co_uni
                -- Box Unit (Specific User Logic)
                LEFT JOIN saArtUnidad u_box ON a.co_art = u_box.co_art AND u_box.co_uni = 'CAJ'
                WHERE a.anulado = 0 AND a.co_lin = 'PT'
                ORDER BY a.art_des
            """)
        
        result = db.execute(sql).fetchall()
        
        articles = []
        for row in result:
            articles.append({
                "code": str(row.code).strip(),
                "description": str(row.description).strip(),
                "unit": str(row.unit).strip() if row.unit else "N/A",
                "box_equiv": float(row.box_equiv)
            })
            
        return articles
    except Exception as e:
        print(f"Error fetching external articles: {e}")
        # Return mock data as fallback
        return [
            {"code": "ERR-001", "description": "ERROR CONEXION PROFIT - MODO OFFLINE", "unit": "UND", "box_equiv": 1.0},
            {"code": "PT-MOCK1", "description": "ARTICULO PRUEBA 1", "unit": "UND", "box_equiv": 12.0},
            {"code": "PT-MOCK2", "description": "ARTICULO PRUEBA 2", "unit": "KG", "box_equiv": 1.0},
        ]
