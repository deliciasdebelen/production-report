
from app.database import SessionLocal
from app import models
from datetime import datetime

print("Verifying Inbox Logic...")
db = SessionLocal()

# 1. Sync Tables (Status)
from app.database import engine
models.Base.metadata.create_all(bind=engine)

# 2. Get User & Message
user = db.query(models.User).order_by(models.User.id).first()
msg = db.query(models.Message).first()

if not user or not msg:
    print("Please seed data first.")
    exit()

print(f"User: {user.username}, Msg: {msg.id}")

# 3. Test Mark Read
print("Marking as Read...")
status = db.query(models.MessageStatus).filter_by(message_id=msg.id, user_id=user.id).first()
if not status:
    status = models.MessageStatus(message_id=msg.id, user_id=user.id)
    db.add(status)
status.is_read = True
db.commit()

# Verify
s2 = db.query(models.MessageStatus).filter_by(message_id=msg.id, user_id=user.id).first()
print(f"Is Read: {s2.is_read}")

# 4. Test Star
print("Toggling Star...")
s2.is_starred = True
db.commit()

s3 = db.query(models.MessageStatus).filter_by(message_id=msg.id, user_id=user.id).first()
print(f"Is Starred: {s3.is_starred}")

print("Verification Done.")
db.close()
