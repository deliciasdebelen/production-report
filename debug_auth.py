from app.auth_utils import verify_password
from app.database import SessionLocal
from app.models import User

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        print(f"User found: {user.username}")
        print(f"Hash: {user.password_hash}")
        is_valid = verify_password("admin", user.password_hash)
        print(f"Verify 'admin': {is_valid}")
    else:
        print("User not found.")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
