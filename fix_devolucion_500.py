import pyodbc

RAW_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.1.205;"
    "DATABASE=carmal_a;"
    "UID=PROFIT;"
    "PWD=profit;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

def disable_triggers():
    try:
        conn = pyodbc.connect(RAW_CONN_STR)
        cursor = conn.cursor()
        
        print("====== DISABLING TRIGGERS ======")
        query_1 = "DISABLE TRIGGER TR_ForzarTotalesEnDetalle ON saDevolucionClienteReng"
        cursor.execute(query_1)
        print("TR_ForzarTotalesEnDetalle disabled.")

        query_2 = "DISABLE TRIGGER TR_saDevolucionCliente_CalcularNeto ON saDevolucionCliente"
        cursor.execute(query_2)
        print("TR_saDevolucionCliente_CalcularNeto disabled.")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    disable_triggers()
