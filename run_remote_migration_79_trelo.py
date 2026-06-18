"""
Migración completa del módulo de Proyectos (Trelo/Kanban) en 192.168.1.79
Crea todas las tablas base + las columnas y tablas extendidas (Traza/Timeline).
Opera directamente sobre la BD del host via paramikoSFTP + python3 remoto.
Usa CREATE TABLE IF NOT EXISTS + ALTER TABLE idempotente (safe to re-run).
"""
import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22
REMOTE_DB = "/home/administrador/apps/production-report/production.db"

# ─── DDL completo del módulo Projects ────────────────────────────────────────
MIGRATION_SCRIPT = f"""
import sqlite3

conn = sqlite3.connect('{REMOTE_DB}')
cur  = conn.cursor()

# ── 1. project_boards ────────────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_boards (
    id         VARCHAR PRIMARY KEY,
    title      VARCHAR NOT NULL,
    background VARCHAR DEFAULT "#714B67",
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
print("1. project_boards OK")

# ── 2. project_lists ─────────────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_lists (
    id         VARCHAR PRIMARY KEY,
    title      VARCHAR NOT NULL,
    "order"    REAL    NOT NULL DEFAULT 1000.0,
    board_id   VARCHAR NOT NULL REFERENCES project_boards(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_lists_board_id ON project_lists(board_id)")
print("2. project_lists OK")

# ── 3. project_cards (full schema incl. Traza fields) ────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_cards (
    id           VARCHAR PRIMARY KEY,
    title        VARCHAR NOT NULL,
    description  TEXT,
    "order"      REAL    NOT NULL DEFAULT 1000.0,
    list_id      VARCHAR NOT NULL REFERENCES project_lists(id)  ON DELETE CASCADE,
    color        VARCHAR,
    due_date     DATETIME,
    start_date   DATETIME,
    parent_id    VARCHAR REFERENCES project_cards(id) ON DELETE SET NULL,
    is_milestone BOOLEAN DEFAULT 0,
    story_points REAL    DEFAULT 0.0,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_cards_list_id    ON project_cards(list_id)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_cards_parent_id  ON project_cards(parent_id)")
print("3. project_cards OK")

# Columnas Traza sobre tabla existente (idempotente)
existing_cols = [r[1] for r in cur.execute("PRAGMA table_info(project_cards)").fetchall()]
traza_cols = [
    ("start_date",   "DATETIME"),
    ("parent_id",    "VARCHAR"),
    ("is_milestone", "BOOLEAN DEFAULT 0"),
    ("story_points", "REAL DEFAULT 0.0"),
]
for col_name, col_def in traza_cols:
    if col_name not in existing_cols:
        cur.execute(f"ALTER TABLE project_cards ADD COLUMN {{col_name}} {{col_def}}")
        print(f"   + columna {{col_name}} agregada a project_cards")

# ── 4. project_comments ──────────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_comments (
    id         VARCHAR PRIMARY KEY,
    text       TEXT    NOT NULL,
    card_id    VARCHAR NOT NULL REFERENCES project_cards(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_comments_card_id ON project_comments(card_id)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_comments_user_id ON project_comments(user_id)")
print("4. project_comments OK")

# ── 5. project_card_members ──────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_card_members (
    id         VARCHAR PRIMARY KEY,
    card_id    VARCHAR NOT NULL REFERENCES project_cards(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_card_members_card_id ON project_card_members(card_id)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_card_members_user_id ON project_card_members(user_id)")
print("5. project_card_members OK")

# ── 6. project_labels ────────────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_labels (
    id       VARCHAR PRIMARY KEY,
    name     VARCHAR NOT NULL,
    color    VARCHAR NOT NULL DEFAULT "#3b82f6",
    board_id VARCHAR NOT NULL REFERENCES project_boards(id) ON DELETE CASCADE
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_labels_board_id ON project_labels(board_id)")
print("6. project_labels OK")

# ── 7. project_card_labels ───────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_card_labels (
    id       VARCHAR PRIMARY KEY,
    card_id  VARCHAR NOT NULL REFERENCES project_cards(id)  ON DELETE CASCADE,
    label_id VARCHAR NOT NULL REFERENCES project_labels(id) ON DELETE CASCADE
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_card_labels_card_id  ON project_card_labels(card_id)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_card_labels_label_id ON project_card_labels(label_id)")
print("7. project_card_labels OK")

# ── 8. project_checklists ────────────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_checklists (
    id         VARCHAR PRIMARY KEY,
    title      VARCHAR  NOT NULL DEFAULT "Checklist",
    card_id    VARCHAR  NOT NULL REFERENCES project_cards(id) ON DELETE CASCADE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_checklists_card_id ON project_checklists(card_id)")
print("8. project_checklists OK")

# ── 9. project_checklist_items ───────────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_checklist_items (
    id             VARCHAR PRIMARY KEY,
    text           VARCHAR  NOT NULL,
    is_completed   BOOLEAN  DEFAULT 0,
    checklist_id   VARCHAR  NOT NULL REFERENCES project_checklists(id) ON DELETE CASCADE,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_project_checklist_items_cl_id ON project_checklist_items(checklist_id)")
print("9. project_checklist_items OK")

# ── 10. project_card_status_history (Traza) ──────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_card_status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id     VARCHAR  NOT NULL REFERENCES project_cards(id)  ON DELETE CASCADE,
    old_list_id VARCHAR  REFERENCES project_lists(id) ON DELETE SET NULL,
    new_list_id VARCHAR  REFERENCES project_lists(id) ON DELETE SET NULL,
    user_id     INTEGER  REFERENCES users(id)         ON DELETE SET NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_pcsh_card_id ON project_card_status_history(card_id)")
print("10. project_card_status_history OK")

# ── 11. project_activity_logs (Audit) ────────────────────────────────────────
cur.execute('''
CREATE TABLE IF NOT EXISTS project_activity_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id     VARCHAR  NOT NULL REFERENCES project_cards(id) ON DELETE CASCADE,
    user_id     INTEGER  REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR  NOT NULL,
    description TEXT,
    old_value   TEXT,
    new_value   TEXT,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
cur.execute("CREATE INDEX IF NOT EXISTS ix_pal_card_id ON project_activity_logs(card_id)")
cur.execute("CREATE INDEX IF NOT EXISTS ix_pal_user_id ON project_activity_logs(user_id)")
print("11. project_activity_logs OK")

conn.commit()
conn.close()

print("")
print("=== MIGRACION COMPLETA. Todas las tablas del modulo Proyectos creadas. ===")
"""

# ─── Ejecutar vía SSH ────────────────────────────────────────────────────────
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)

print(f"Conectado a {HOSTNAME}. Subiendo script de migracion...")

sftp = client.open_sftp()
with sftp.file("/tmp/migrate_projects_full.py", "w") as f:
    f.write(MIGRATION_SCRIPT)
sftp.close()

print("Ejecutando migracion en el servidor host...")
stdin, stdout, stderr = client.exec_command("python3 /tmp/migrate_projects_full.py", timeout=30)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")

print("\n=== OUTPUT ===")
print(out)
if err:
    print("=== ERRORES ===")
    print(err)

client.close()

# ─── Re-verificar conteos post-migración ─────────────────────────────────────
print("\n=== VERIFICACION POST-MIGRACION ===")
import sqlite3
# No podemos abrir la BD remota directamente, usamos paramiko nuevamente
client2 = paramiko.SSHClient()
client2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client2.connect(HOSTNAME, PORT, USERNAME, PASSWORD)

verify_script = f"""
import sqlite3
conn = sqlite3.connect('{REMOTE_DB}')
tables = [
    'project_boards','project_lists','project_cards',
    'project_comments','project_card_members','project_labels',
    'project_card_labels','project_checklists','project_checklist_items',
    'project_card_status_history','project_activity_logs'
]
for t in tables:
    n = conn.execute(f'SELECT COUNT(*) FROM {{t}}').fetchone()[0]
    print(f'{{t}}|{{n}}')
conn.close()
"""

sftp2 = client2.open_sftp()
with sftp2.file("/tmp/verify_projects.py", "w") as f:
    f.write(verify_script)
sftp2.close()

stdin, stdout, stderr = client2.exec_command("python3 /tmp/verify_projects.py", timeout=15)
vout = stdout.read().decode(errors="replace")
client2.close()

print(f"\n{'Tabla':<42} {'Registros':>10}  Estado")
print("-" * 60)
for line in vout.splitlines():
    if "|" in line:
        t, n = line.strip().split("|", 1)
        flag = "[OK]" if n.isdigit() else "[ERROR]"
        print(f"{t:<42} {n:>10}  {flag}")
