from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer
from app import models


def get_next_order_number(db: Session, model):
    # Fetch all order numbers to find max safely in Python
    # This avoids SQL casting issues with legacy string data
    try:
        results = db.query(model.order_number).all()
        max_id = 0
        print(f"DEBUG: Checking max ID for {model.__tablename__}")
        for r in results:
            val = r[0]
            # print(f"DEBUG: Found {val}") 
            if val and str(val).isdigit():
                val_int = int(str(val))
                if val_int > max_id:
                    max_id = val_int
        
        print(f"DEBUG: Calculated Max ID: {max_id}, Next: {max_id + 1}")
        return max_id + 1
    except Exception as e:
        print(f"Error generating ID: {e}")
        return 1

