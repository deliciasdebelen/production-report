import pyodbc

print("Available ODBC Drivers:")
for driver in pyodbc.drivers():
    print(f" - {driver}")
