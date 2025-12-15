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
def get_articles(db: Session = Depends(get_external_db)):
    try:
        # Query: Fetch base info + Box Equivalence (CAJ)
        # Using a subquery/OUTER APPLY for the specific 'CAJ' unit equivalence
        sql = text("""
            SELECT 
                a.co_art as code,
                a.art_des as description,
                u.des_uni as unit,
                ISNULL((SELECT TOP 1 equivalencia 
                 FROM saartunidad 
                 WHERE co_art = a.co_art AND co_uni = 'CAJ'), 0) as box_equiv
            FROM saarticulo a
            LEFT JOIN saartunidad au ON a.co_art = au.co_art AND au.equivalencia = 1
            LEFT JOIN saUnidad u ON au.co_uni = u.co_uni
            WHERE a.anulado = 0 AND a.co_art LIKE 'PT%'
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
