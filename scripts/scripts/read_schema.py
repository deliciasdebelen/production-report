
import os
import re

file_path = "temp_schema.txt"

if not os.path.exists(file_path):
    print(f"File {file_path} not found.")
    exit(1)

try:
    with open(file_path, "r", encoding="utf-16") as f:
        content = f.read()
except UnicodeError:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file manually: {e}")
        exit(1)

# Print content around tables
if "saLoteEntrada" in content:
    print("\n--- saLoteEntrada Definition ---")
    match = re.search(r"Table saLoteEntrada \{([^}]+)\}", content, re.DOTALL)
    if match:
        print(match.group(1))

if "saLoteSalida" in content:
    print("\n--- saLoteSalida Definition ---")
    match = re.search(r"Table saLoteSalida \{([^}]+)\}", content, re.DOTALL)
    if match:
        print(match.group(1))
