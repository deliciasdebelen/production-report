from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer
from app import models

def get_next_order_number(db: Session, model):
    # Try to find max order_number casted to integer
    # Assumes order_number stores integers or string-integers
    try:
        max_id = db.query(func.max(cast(model.order_number, Integer))).scalar()
        if max_id:
            return max_id + 1
        return 1
    except:
        return 1
