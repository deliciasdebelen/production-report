import psycopg2

DATABASE_URL = "postgresql://app_user:production_password@db:5432/production_db"

def seed_admin():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Insert or update the master admin user
        cursor.execute("""
            INSERT INTO users (
                id, username, password_hash, role, is_active
            ) VALUES (
                2, 'administrador', 
                '$2b$12$lPhHhHkSSw0yxDVaa47s7.Zg9dhoRljLvvvRzEriF8NCQbDfpAu/W',
                4, 1
            )
            ON CONFLICT (id) DO UPDATE SET 
                username = EXCLUDED.username,
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role,
                is_active = EXCLUDED.is_active;
        """)
        
        # In case the sequence is lower than 2
        cursor.execute("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));")
        
        conn.commit()
        print("Admin user 'administrador' seeded with password '111'")
        
    except Exception as e:
        print(f"Error seeding admin: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    seed_admin()
