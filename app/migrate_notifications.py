from app.database import engine, Base
from app.models import NotificationSubscriber

def migrate():
    print("Creating NotificationSubscriber table...")
    NotificationSubscriber.__table__.create(bind=engine, checkfirst=True)
    print("Done.")

if __name__ == "__main__":
    migrate()
