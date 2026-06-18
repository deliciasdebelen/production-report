import subprocess

query = "ALTER TABLE support_settings ADD COLUMN IF NOT EXISTS cc_emails VARCHAR DEFAULT '';"

result = subprocess.run(
    ["sudo", "-S", "docker", "exec", "-i", "production_report_db", "psql", "-U", "app_user", "-d", "production_db", "-c", query],
    input="administrador\n",
    text=True,
    capture_output=True
)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
