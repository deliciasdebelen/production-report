import paramiko

hostname = "192.168.1.79"
username = "administrador"
password = "GRW7czL3*"
port = 22
base_path = "/home/administrador/sistema_ia_profit"
test_script_path = f"{base_path}/test_sql_connection.js"

# Node.js script to emulate n8n connection using 'mssql' (tedious)
# Note: We need to find where n8n keeps its node_modules or use global ones.
# In n8n images, they are usually in /usr/local/lib/node_modules/n8n/node_modules...
# Or we can try to install 'mssql' locally if allowed, but better to use existing.
# Actually, n8n wraps it. 
# Let's try a pure 'net' test first? No, we need MSSQL protocol test.
# Let's assume we can use a temporary install or try to find the module.
# Plan B: Just write the file and try to run it, if module missing, we'll see.
# n8n uses 'mssql' package which wraps 'tedious'.

js_content = """
const sql = require('mssql');

const config = {
    user: 'PROFIT',
    password: 'password_here', // Placeholder, will replace below
    server: '192.168.1.205', 
    database: 'carmal_a',
    port: 1433,
    options: {
        encrypt: true, // As per user screenshot
        trustServerCertificate: true, // As per user screenshot
        enableArithAbort: true,
        cryptoCredentialsDetails: {
            minVersion: 'TLSv1', // Force TLS v1 in driver
            ciphers: 'ALL:@SECLEVEL=0' // Redundant if OS handles it, but good for safety
        }
    }
};

// Override console.log to print nicely
console.log("Connecting to SQL Server...");

sql.connect(config).then(pool => {
    console.log("Connected! Running Query...");
    return pool.request().query('SELECT TOP 5 * FROM saArticulo');
}).then(result => {
    console.dir(result.recordset);
    sql.close();
}).catch(err => {
    console.error("SQL Error:", err);
    sql.close();
});
"""

# Replace password safely
js_content = js_content.replace("password_here", "profit") # User provided 'profit' in previous context/screenshot? No, screenshot had ******. 
# Wait, user provided credentials in Step 0: "administrador / GRW7czL3*" for SERVER.
# For SQL, step 33 `external_db.py` showed `UID=PROFIT; PWD=profit;`.
# Screenshot showed Login: PROFIT.
# So password is likely "profit" (lowercase) based on `external_db.py`.

def run_command(client, command):
    print(f"\n--- Running: {command} ---")
    stdin, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode()
    err = stderr.read().decode()
    print(out)
    if err:
        print(f"STDERR: {err}")
    return out

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password)
    
    sftp = client.open_sftp()
    
    # Write the JS file
    print(f"Creating {test_script_path}...")
    with sftp.open(test_script_path, 'w') as f:
        f.write(js_content)
        
    sftp.close()
    
    # Need to install mssql in a temp dir to run this test script unless we find n8n's internal modules
    # We can create a temp project folder in the volume
    setup_cmds = [
        f"mkdir -p {base_path}/test_sql",
        f"cp {test_script_path} {base_path}/test_sql/index.js",
        f"cd {base_path}/test_sql && docker run --rm -v {base_path}/test_sql:/app -w /app node:16-buster sh -c 'npm install mssql && node index.js'"
    ]
    # Actually, running a NEW container (node:16-buster) is a clever way to verify the connectivity 
    # independent of the n8n container, BUT it doesn't prove the n8n container is fixed.
    # It proves the OS/Network/Protocol combination works.
    
    # Better: Exec INSIDE ia_musculo to prove THAT container works.
    # But ia_musculo might not let us npm install easily.
    # ia_musculo (Debian) should have npm.
    
    exec_cmd = f"docker exec ia_musculo sh -c 'mkdir -p /tmp/test_sql && cd /tmp/test_sql && npm install mssql > /dev/null 2>&1 && mv /home/node/sistema_ia_profit/test_sql_connection.js . 2>/dev/null || echo \"Moving file...\" '"
    # Wait, mapping is tricky. I'll just write the content via echo or copy.
    
    # Let's simplify:
    # 1. Install mssql in /tmp inside container
    # 2. Run script
    
    run_command(client, "docker exec ia_musculo sh -c 'mkdir -p /tmp/sql_test && cd /tmp/sql_test && npm install mssql'")
    
    # Copy file content to container
    # Using docker cp is easy if I have the file locally? No, file is on REMOTE host.
    # remote host -> container
    run_command(client, f"docker cp {test_script_path} ia_musculo:/tmp/sql_test/test.js")
    
    # Run
    run_command(client, "docker exec ia_musculo node /tmp/sql_test/test.js")

    client.close()
except Exception as e:
    print(f"Error: {e}")
