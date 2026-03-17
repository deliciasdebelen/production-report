import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

url = os.getenv('DATABASE_URL')
engine = sa.create_engine(url)

with engine.connect() as conn:
    result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='users'"))
    columns = [row[0] for row in result.fetchall()]
    print("USERS COLUMNS:", columns)
