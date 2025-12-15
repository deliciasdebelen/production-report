import pyodbc
import sys

server = "192.168.1.205"
user = "PROFIT"
password = "profit"
database = "carmal_a"

# Connection string with encryption parameters based on user input
conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

print(f"Connecting to {server} using pyodbc...")

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 co_art, art_des FROM saarticulo")
    row = cursor.fetchone()
    print("SUCCESS: Connected via pyodbc!")
    print(f"Row: {row}")
    conn.close()
except Exception as e:
    print(f"pyodbc FAILURE: {e}")
    sys.exit(1)
