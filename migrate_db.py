import sqlite3

def add_columns():
    conn = sqlite3.connect('production.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE production_reports ADD COLUMN mp_waste_kg FLOAT DEFAULT 0.0")
        print("Added mp_waste_kg column.")
    except sqlite3.OperationalError:
        print("mp_waste_kg column already exists.")

    try:
        cursor.execute("ALTER TABLE production_reports ADD COLUMN mp_waste_image STRING DEFAULT NULL")
        print("Added mp_waste_image column.")
    except sqlite3.OperationalError:
        print("mp_waste_image column already exists.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_columns()
