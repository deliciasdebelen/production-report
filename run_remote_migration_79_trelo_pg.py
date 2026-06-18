import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"
PORT = 22

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOSTNAME, PORT, USERNAME, PASSWORD)

cmd = f"""docker ps --format '{{{{.Names}}}}' | grep db"""

stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode()
err = stderr.read().decode()
db_name = out.strip()

cmd = f"""docker exec {db_name} psql -U app_user -d production_db -c "
ALTER TABLE project_cards ADD COLUMN IF NOT EXISTS start_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE project_cards ADD COLUMN IF NOT EXISTS is_milestone BOOLEAN DEFAULT FALSE;
ALTER TABLE project_cards ADD COLUMN IF NOT EXISTS story_points DOUBLE PRECISION DEFAULT 0.0;
ALTER TABLE project_cards ADD COLUMN IF NOT EXISTS parent_id VARCHAR;
ALTER TABLE project_cards DROP CONSTRAINT IF EXISTS project_cards_parent_id_fkey;
ALTER TABLE project_cards ADD CONSTRAINT project_cards_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES project_cards(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS project_card_status_history (
    id SERIAL PRIMARY KEY,
    card_id VARCHAR NOT NULL REFERENCES project_cards(id) ON DELETE CASCADE,
    old_list_id VARCHAR REFERENCES project_lists(id) ON DELETE SET NULL,
    new_list_id VARCHAR REFERENCES project_lists(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS ix_project_card_status_history_id ON project_card_status_history(id);
CREATE INDEX IF NOT EXISTS ix_project_card_status_history_card_id ON project_card_status_history(card_id);
CREATE INDEX IF NOT EXISTS ix_project_card_status_history_old_list_id ON project_card_status_history(old_list_id);
CREATE INDEX IF NOT EXISTS ix_project_card_status_history_new_list_id ON project_card_status_history(new_list_id);


CREATE TABLE IF NOT EXISTS project_activity_logs (
    id SERIAL PRIMARY KEY,
    card_id VARCHAR NOT NULL REFERENCES project_cards(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR NOT NULL,
    description TEXT,
    old_value TEXT,
    new_value TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);
CREATE INDEX IF NOT EXISTS ix_project_activity_logs_id ON project_activity_logs(id);
CREATE INDEX IF NOT EXISTS ix_project_activity_logs_card_id ON project_activity_logs(card_id);
"
"""

stdin, stdout, stderr = client.exec_command(cmd)
out = stdout.read().decode()
err = stderr.read().decode()
print("OUT:", out)
if err: print("ERR:", err)

client.close()
