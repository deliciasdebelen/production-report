from sqlalchemy.orm import Session
from sqlalchemy import func, text

def generate_next_order_number(db: Session, model):
    """
    Generates a 10-digit sequential ID string (e.g. '0000000001').
    Finds the max id in the table safely using Python to avoid SQL sorting issues.
    """
    try:
        # Fetch all order numbers.
        # This is safer than max() or sort() on string columns with potential legacy data.
        results = db.query(model.order_number).all()
        
        max_val = 0
        for r in results:
            val = r[0]
            if val and str(val).isdigit():
                v_int = int(str(val))
                if v_int > max_val:
                    max_val = v_int
        
        next_val = max_val + 1
        
        # Checking loop to ensure we don't collide with invisible records
        while True:
            candidate = f"{next_val:010d}"
            # Check if this candidates exists using Raw SQL to avoid ORM issues
            exists = db.execute(text(f"SELECT 1 FROM {model.__tablename__} WHERE order_number = :val"), {"val": candidate}).first()
            if not exists:
                return candidate
            next_val += 1
            print(f"DEBUG: Collision found for {candidate}, trying next...", flush=True)

    except Exception as e:
        print(f"Error generating ID in utils: {e}", flush=True)
        return "0000000001"

