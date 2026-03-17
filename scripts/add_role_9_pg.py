import psycopg2

DATABASE_URL = "postgresql://app_user:production_password@db:5432/production_db"

def add_role_9():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Insert role 9 if not exists
        cursor.execute("""
            INSERT INTO roles (id, name, permissions)
            VALUES (9, 'Soporte (Solo Crear)', '{}')
            ON CONFLICT (id) DO NOTHING;
        """)
        
        conn.commit()
        print("Role 9 successfully inserted or already exists in PostgreSQL.")
        
    except Exception as e:
        print(f"Error adding Role 9: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    add_role_9()
