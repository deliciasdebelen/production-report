import os
from sqlalchemy import create_engine, text

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url)
try:
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE logistics_dispatch ADD COLUMN is_annulled BOOLEAN DEFAULT FALSE;'))
        print('DONE')
except Exception as e:
    print(e)
