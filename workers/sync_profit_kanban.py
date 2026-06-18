import os
import sys
import json
import time
from sqlalchemy import create_engine, text

# Add parent directory to path to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.external_db import SQLALCHEMY_EXTERNAL_DATABASE_URL
from app.cache_utils import get_redis_client

def sync_pending_orders_to_redis():
    """
    Background worker that fetches pending invoices and delivery notes from Profit Plus
    and securely stores them in Redis for the Logistics Kanban board.
    Runs every 2 minutes.
    """
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Iniciando sincronizacion Kanban -> Redis...")
    redis = get_redis_client()
    
    if not redis:
        print("Redis no esta disponible. Saliendo del worker.")
        return
        
    try:
        engine = create_engine(SQLALCHEMY_EXTERNAL_DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            
            dialect = engine.dialect.name
            campo5_cond = "(f.campo5 IS NULL OR LTRIM(RTRIM(f.campo5)) = '')"
            limit_clause = "TOP 150" if dialect == "mssql" else ""
            limit_pg = "LIMIT 150" if dialect != "mssql" else ""
            
            # Query Invoices
            q_inv = text(f"""
                SELECT {limit_clause} 'FACT' as doc_type, f.doc_num, ISNULL(c.cli_des, 'CLIENTE DESCONOCIDO') AS client_name, f.fec_emis
                FROM saFacturaVenta f
                LEFT JOIN saCliente c ON f.co_cli = c.co_cli
                WHERE {campo5_cond} AND f.anulada = 0
                ORDER BY f.fec_emis DESC {limit_pg}
            """)
            
            # Query Delivery Notes
            q_nent = text(f"""
                SELECT {limit_clause} 'NENT' as doc_type, f.doc_num, ISNULL(c.cli_des, 'CLIENTE DESCONOCIDO') AS client_name, f.fec_emis
                FROM saNotaEntregaVenta f
                LEFT JOIN saCliente c ON f.co_cli = c.co_cli
                WHERE {campo5_cond} AND f.anulada = 0
                ORDER BY f.fec_emis DESC {limit_pg}
            """)
            
            invs = conn.execute(q_inv).fetchall()
            nents = conn.execute(q_nent).fetchall()
            
            results = []
            for r in invs + nents:
                 results.append({
                     "doc_type": str(r.doc_type).strip(),
                     "doc_num": str(r.doc_num).strip(),
                     "client_name": str(r.client_name).strip(),
                     "date": r.fec_emis.strftime('%Y-%m-%d') if r.fec_emis else ""
                 })
                 
            # Store in Redis (Key: kanban:pending_orders), expires in 5 minutes just in case worker dies
            cache_key = "kanban:pending_orders"
            redis.setex(cache_key, 300, json.dumps(results))
            
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exito. {len(results)} documentos cacheados en Redis.")
            
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error sincronizando a Redis: {e}")

if __name__ == "__main__":
    # Create workers directory if it doesn't exist just for cleanliness
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    
    # Run loop
    while True:
        sync_pending_orders_to_redis()
        # Sleep 2 minutes
        time.sleep(120)
