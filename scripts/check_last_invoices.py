import paramiko

HOSTNAME = "192.168.1.79"
USERNAME = "administrador"
PASSWORD = "GRW7czL3*"

def check_remote_data():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOSTNAME, port=22, username=USERNAME, password=PASSWORD)
        
        # We'll run a python script INSIDE the container to check data
        check_script = """
import sqlalchemy
from sqlalchemy import text
import urllib.parse

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
params_a = urllib.parse.quote_plus(RAW_CONN_STR)
EXTERNAL_DATABASE_URL = f'mssql+pyodbc:///?odbc_connect={params_a}'
engine = sqlalchemy.create_engine(EXTERNAL_DATABASE_URL)

with engine.connect() as conn:
    print('Checking last 10 invoices:')
    res = conn.execute(text('SELECT TOP 10 doc_num, descrip, co_cli, campo5 FROM saFacturaVenta ORDER BY doc_num DESC')).fetchall()
    for r in res:
        print(f'NUM: {r.doc_num.strip()} | CLI: {r.co_cli.strip()} | C5: [{r.campo5.strip() if r.campo5 else "NULL"}]')
"""
        # Echo the script into a file in the container and run it
        cmd = f"docker exec -i production-report python -c \"{check_script}\""
        stdin, stdout, stderr = client.exec_command(cmd)
        print(stdout.read().decode())
        print(stderr.read().decode())
        
        client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_remote_data()
