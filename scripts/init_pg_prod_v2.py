import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect("192.168.1.79", username="administrador", password="GRW7czL3*")

sftp = client.open_sftp()
print("Uploading migration scripts to .79 host...")
sftp.put("scripts/migrate_sqlite_to_pg_standalone.py", "/tmp/migrate_sqlite_to_pg_standalone.py")
sftp.put("scripts/migrate_sqlite_to_pg.py", "/tmp/migrate_sqlite_to_pg.py")
sftp.close()

print("Ensure web container is up...")
client.exec_command("echo 'GRW7czL3*' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml up -d web")

print("Copying seeding scripts to the server...")
sftp = client.open_sftp()
sftp.put("scripts/seed_roles_pg.py", "/home/administrador/apps/production-report/app/seed_roles_pg.py")
sftp.put("scripts/add_role_9_pg.py", "/home/administrador/apps/production-report/app/add_role_9_pg.py")
sftp.close()

print("Executing seeding scripts on the production PG database...")
cmd1 = "echo 'GRW7czL3*' | sudo -S docker exec production-report python /app/seed_roles_pg.py"
client.exec_command(cmd1)

cmd2 = "echo 'GRW7czL3*' | sudo -S docker exec production-report python /app/add_role_9_pg.py"
client.exec_command(cmd2)

print("Restarting web container fully to connect to PostgreSQL...")
cmd3 = "echo 'GRW7czL3*' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml stop web && echo 'GRW7czL3*' | sudo -S docker-compose -f /home/administrador/apps/production-report/docker-compose.yml up -d web"
stdin, stdout, stderr = client.exec_command(cmd3)

print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

client.close()
print("PostgreSQL migration finalized and web container restarted.")
