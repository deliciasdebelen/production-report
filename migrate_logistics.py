from app.database import engine, Base
from app.models import LogisticsReceptionProduction, LogisticsReceptionMerchandise, LogisticsDispatch

def migrate():
    print("Migrating Logistics Tables...")
    # This will create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("Done!")

if __name__ == "__main__":
    migrate()
