from sqlalchemy.orm import Session
from sqlalchemy import func

def generate_next_order_number(db: Session, model):
    """
    Generates a 10-digit sequential ID string (e.g. '0000000001').
    Finds the max id in the table (or max order_number if possible) and increments.
    Since we are retrofitting, we might rely on the integer ID or parsing the last order_number.
    Let's rely on parsing specific order_number column.
    """
    # Find max order_number
    # We filter for those that look like numbers to avoid legacy data issues if any
    last_order = db.query(model.order_number)\
        .filter(model.order_number != None)\
        .order_by(model.order_number.desc())\
        .first()

    if not last_order or not last_order[0]:
        return "0000000001"
    
    try:
        last_val = int(last_order[0])
        next_val = last_val + 1
        return f"{next_val:010d}"
    except ValueError:
        # Fallback if non-numeric found
        return "0000000001"
