import psycopg2

DATABASE_URL = "postgresql://app_user:production_password@db:5432/production_db"

def seed_admin():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Insert or update the master admin user
        cursor.execute("""
            INSERT INTO users (
                id, username, email, hashed_password, role_id, is_active,
                first_name, last_name, employee_id, phone, address, settings_json
            ) VALUES (
                2, 'administrador', 'admin@carmal.com', 
                '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- simple bcrypt hash for "111"
                4, true,
                'Admin', 'Sistema', '0000', NULL, NULL, '{}'
            )
            ON CONFLICT (id) DO UPDATE SET 
                username = EXCLUDED.username,
                hashed_password = EXCLUDED.hashed_password,
                role_id = EXCLUDED.role_id,
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
