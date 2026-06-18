import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
remote_path = "/home/administrador/sistema_ia_profit/docker-compose.yml"

def run_command(client, command):
    print(f"\n--- Running: {command} ---")
    stdin, stdout, stderr = client.exec_command(command)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"STDERR: {err}")

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password)
    
    sftp = client.open_sftp()
    
    print("Reading remote file...")
    with sftp.open(remote_path, 'r') as f:
        content = f.read().decode()
        
    print("-- Original Content Snippet --")
    # Show the weird command part
    start = content.find("command: /bin/sh")
    print(content[start:start+500])
    
    # Sanitize the command
    # We want to remove the huge whitespace gap
    # The command is: /bin/sh -c "sed ... && sed ... && n8n"
    
    # Regex to replace multiple spaces with single space won't work easily if newlines are involved
    # But we can reconstruct it.
    
    clean_command = '    command: /bin/sh -c "sed -i \'s/MinProtocol = TLSv1.2/MinProtocol = TLSv1.0/g\' /etc/ssl/openssl.cnf && sed -i \'s/CipherString = DEFAULT@SECLEVEL=2/CipherString = DEFAULT@SECLEVEL=1/g\' /etc/ssl/openssl.cnf && n8n"'
    
    lines = content.splitlines()
    new_lines = []
    
    skip = False
    for line in lines:
        if "command: /bin/sh" in line:
            new_lines.append(clean_command)
            # If the original command spanned multiple lines (due to the weird whitespace), we need to skip them.
            # The tool output earlier showed the whitespace was inside the string?
            # It looked like:
            # command: /bin/sh -c "sed ...
            # ...
            # =1/g' /etc/ssl/openssl.cnf && n8n"
            
            # If the current line doesn't end with quote, we might need to skip subsequent lines until we find the end quote?
            # Actually, looking at the previous output:
            # command: /bin/sh -c "sed -i 's/MinProtocol = TLSv1.2/MinProtocol = TLSv1.0/g' /etc/ssl/openssl.cnf && sed -i 's/CipherString = DEFAULT@SECLEVEL=2/CipherString = DEFAULT@SECLEVEL=
            # 
            # 
            # =1/g' /etc/ssl/openssl.cnf && n8n"
            
            # So I need to skip lines until I see the end of the command?
            # Or just filter out the garbage.
            
            # Let's see if the line ends properly.
            if line.strip().endswith('"'):
                skip = False
            else:
                skip = True
            continue
            
        if skip:
            if line.strip().endswith('"'):
                skip = False
            continue
            
        new_lines.append(line)
        
    final_content = "\n".join(new_lines)
    
    print("\n-- Modified Content Snippet --")
    start = final_content.find("command: /bin/sh")
    print(final_content[start:start+300])
    
    print("\nWriting fixed file...")
    with sftp.open(remote_path, 'w') as f:
        f.write(final_content)
            
    sftp.close()

    # Restart
    cmd = "cd /home/administrador/sistema_ia_profit && docker-compose up -d"
    run_command(client, cmd)
    
    # Verify status
    run_command(client, "docker ps --filter name=ia_musculo")

    client.close()
except Exception as e:
    print(f"Error: {e}")
