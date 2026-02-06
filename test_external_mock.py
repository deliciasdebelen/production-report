from app.routers import external
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from collections import namedtuple

def test_get_batches():
    print("Testing get_batches logic...")
    
    # Mock row with stock_actual
    RowWithStock = namedtuple("Row", ["co_art", "art_des", "LoteEntrada", "stock_actual"])
    row1 = RowWithStock(co_art="TEST1", art_des="Desc1", LoteEntrada="LOTE1", stock_actual=10.5)

    # Mock row WITHOUT stock_actual
    RowNoStock = namedtuple("Row", ["co_art", "art_des", "LoteEntrada"])
    row2 = RowNoStock(co_art="TEST2", art_des="Desc2", LoteEntrada="LOTE2")

    # Mock DB
    mock_db = MagicMock(spec=Session)
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [row1, row2]
    mock_db.execute.return_value = mock_result
    
    # Test
    try:
        batches = external.get_batches("TEST-CODE", db=mock_db)
        print("Batches result:")
        for b in batches:
            print(f"- {b}")
        
        # Verify
        assert batches[0].stock == 10.5
        assert batches[1].stock == 0.0
        print("Code is robust (handled both rows).")

    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    test_get_batches()
