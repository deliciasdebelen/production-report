
from app.database import SessionLocal
from app import models
from datetime import datetime, timedelta

db = SessionLocal()

# Seed Channels
print("Seeding Channels...")
general = db.query(models.Channel).filter_by(name="general").first()
if not general:
    general = models.Channel(name="general", type="channel")
    db.add(general)

admin_ch = db.query(models.Channel).filter_by(name="Administrators").first()
if not admin_ch:
    admin_ch = models.Channel(name="Administrators", type="channel")
    db.add(admin_ch)

db.commit()

# Seed Messages
print("Seeding Messages...")
if db.query(models.Message).count() == 0:
    # Need a user
    user = db.query(models.User).first()
    if not user:
        print("No users found. Creating temp user...")
        user = models.User(username="admin", password_hash="hash")
        db.add(user)
        db.commit()

    if user:
        # 1. Notification
        m1 = models.Message(
            body="Error de SMS: Contacto. Ocurrió un error al enviar un SMS",
            message_type="notification",
            created_at=datetime.now(),
            author_id=None, # System
            channel_id=general.id
        )
        
        # 2. OdooBot
        m2 = models.Message(
            body="Not exactly. To continue the tour, send an emoji: type :) and press enter.",
            message_type="comment",
            created_at=datetime.now() - timedelta(minutes=5),
            author_id=None, # System/Bot
            channel_id=general.id
        )

        # 3. Chat
        m3 = models.Message(
            body="Building B3, second floor to the right :-).",
            message_type="comment",
            created_at=datetime.now() - timedelta(days=1),
            author_id=user.id,
            channel_id=admin_ch.id
        )
        
        db.add(m1)
        db.add(m2)
        db.add(m3)
        db.commit()
        print("Messages seeded.")
    else:
        print("Skipping messages: User 'administrador' required.")
else:
    print("Messages already exist.")

db.close()
