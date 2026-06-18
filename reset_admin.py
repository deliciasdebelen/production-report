from app.auth_utils import get_password_hash
from app.database import SessionLocal
from app.models import User

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "admin").first()
    if user:
        print(f"Found admin. Old hash: {user.password_hash}")
        new_hash = get_password_hash("admin")
        user.password_hash = new_hash
        db.commit()
        print(f"Password reset to 'admin'. New hash: {new_hash}")
    else:
        print("Admin user not found!")
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
