"""
seed_roles_pg.py - Seeds the roles table in PostgreSQL before the main migration.
Run inside the web container or on the host with psycopg2 installed.
"""
import psycopg2
import sys

PG_DSN = "postgresql://app_user:production_password@db:5432/production_db"

if len(sys.argv) > 1:
    PG_DSN = sys.argv[1]

roles = [
    (1, 'KPI', '{}'),
    (2, 'Produccion', '{}'),
    (3, 'Planificacion', '{}'),
    (4, 'Administrador', '{}'),
    (5, 'Almacen', '{}'),
    (6, 'Inventario', '{}'),
    (7, 'Patrimonial', '{}'),
    (8, 'Director', '{}'),
]

try:
    # Parse DSN  
    dsn = PG_DSN.replace("postgresql://", "").replace("postgres://", "")
    user_pass, rest = dsn.split("@", 1)
    user, password = user_pass.split(":", 1)
    host_port, dbname = rest.split("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 5432

    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    cur = conn.cursor()

    for role_id, name, perms in roles:
        cur.execute(
            "INSERT INTO roles (id, name, permissions) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (role_id, name, perms)
        )
    
    conn.commit()
    print("[OK] Roles seeded successfully:")
    cur.execute("SELECT id, name FROM roles ORDER BY id")
    for row in cur.fetchall():
        print(f"  {row[0]} - {row[1]}")
    cur.close()
    conn.close()

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
