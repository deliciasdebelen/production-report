import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

print("Updating docker-compose.yml to force PostgreSQL connection...")
bash_script = """
cd /home/administrador/apps/production-report
# Use sed to add the DATABASE_URL environment variable to the web service if it doesn't exist
# A safer way is to just inject it directly into the docker-compose.yml using python or basic bash
cat << 'EOF' > patch_compose.py
import yaml
compose_file = '/home/administrador/apps/production-report/docker-compose.yml'
with open(compose_file, 'r') as f:
    data = yaml.safe_load(f)
    if 'environment' not in data['services']['web']:
        data['services']['web']['environment'] = []
    
    env_vars = data['services']['web']['environment']
    
    # Remove any existing DATABASE_URL
    if isinstance(env_vars, list):
        filtered = [e for e in env_vars if not e.startswith('DATABASE_URL=')]
        filtered.append('DATABASE_URL=postgresql://app_user:production_password@db:5432/production_db')
        data['services']['web']['environment'] = filtered
    elif isinstance(env_vars, dict):
        env_vars['DATABASE_URL'] = 'postgresql://app_user:production_password@db:5432/production_db'
        data['services']['web']['environment'] = env_vars

with open(compose_file, 'w') as f:
    yaml.dump(data, f)
EOF

python3 patch_compose.py

echo "Restarting web container to apply new DATABASE_URL environment variable..."
docker-compose -f /home/administrador/apps/production-report/docker-compose.yml down
docker-compose -f /home/administrador/apps/production-report/docker-compose.yml up -d
"""

cmd = f"echo 'GRW7czL3*' | sudo -S bash -c '{bash_script}'"
stdin, stdout, stderr = client.exec_command(cmd)

print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

client.close()
