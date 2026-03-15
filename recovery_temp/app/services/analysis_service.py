from sqlalchemy import text
from ..external_db import engine_a, engine_m
import datetime

class AnalysisService:
    def __init__(self):
        self.engine_a = engine_a
        self.engine_m = engine_m

    def _execute_a(self, query: str, params: dict = None):
        try:
            with self.engine_a.connect() as conn:
                result = conn.execute(text(query), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result.fetchall()]
                return []
        except Exception as e:
            print(f"DB Error (carmal_a): {e}")
            return None

    def _execute_m(self, query: str, params: dict = None):
        try:
            with self.engine_m.connect() as conn:
                result = conn.execute(text(query), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result.fetchall()]
                return []
        except Exception as e:
            print(f"DB Error (carmal_m): {e}")
            return None

    # --- SALES & COLLECTIONS ---
    def get_sales_summary(self, date_str: str = None):
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # Total Sales Today
        query = """
            SELECT COUNT(*) as num_facturas, SUM(total_neto) as total_ventas, SUM(saldo) as saldo_pendiente
            FROM saFacturaVenta
            WHERE fec_emis >= :date_start AND fec_emis < DATEADD(day, 1, :date_end)
        """
        # Note: SQL Server date handling might need adjustment depending on column type (datetime vs date)
        # Assuming datetime, so we filter by range.
        params = {"date_start": date_str, "date_end": date_str}
        
        data = self._execute_a(query, params)
        if data: return data[0]
        return {"num_facturas": 0, "total_ventas": 0, "saldo_pendiente": 0}

    def get_top_clients(self, limit: int = 5):
        query = f"""
            SELECT TOP {limit} co_cli, des_cli, saldo 
            FROM saCliente 
            ORDER BY saldo DESC
        """
        return self._execute_a(query)

    # --- INVENTORY ---
    def get_stock_check(self, article_code: str):
        query = """
            SELECT s.co_alma, s.stock_act, a.art_des
            FROM saStockAlmacen s
            JOIN saArticulo a ON s.co_art = a.co_art
            WHERE s.co_art LIKE :art_code AND s.stock_act > 0
        """
        # Try stock_actual if stock_act fails
        try:
             return self._execute_a(query, {"art_code": f"%{article_code}%"})
        except:
             query = """
                SELECT s.co_alma, s.stock_actual as stock_act, a.art_des
                FROM saStockAlmacen s
                JOIN saArticulo a ON s.co_art = a.co_art
                WHERE s.co_art LIKE :art_code AND s.stock_actual > 0
            """
             return self._execute_a(query, {"art_code": f"%{article_code}%"})

    # --- AUDIT / DIAGNOSTICS ---
    def diagnose_batch_error(self, guid_or_ref: str):
        # Specific logic for the "P1-MP vs P1-PP" error type
        # Check saLoteSalida
        query = "SELECT * FROM saLoteSalida WHERE rowguid = :guid"
        res = self._execute_a(query, {"guid": guid_or_ref})
        
        if res:
             rec = res[0]
             return {
                 "status": "DETECTED",
                 "type": "Batch Mismatch",
                 "details": f"Lote Salida en '{rec.get('co_alma')}' pero regla de validación falló.",
                 "recommendation": "Verificar reglas de validación (NC.Co_Alma) en Triggers de saLoteSalida/Entrada."
             }
        return {"status": "NOT_FOUND", "details": "GUID no encontrado en tablas de lotes."}

analysis_service = AnalysisService()
