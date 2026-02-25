
import os

snippet_path = r"app/routers/logistics_snippet.py"
logistics_path = r"app/routers/logistics.py"

with open(snippet_path, "r", encoding="utf-8") as f:
    snippet = f.read()

with open(logistics_path, "r", encoding="utf-8") as f:
    content = f.read()

with open(logistics_path, "a", encoding="utf-8") as f:
    f.write("\n\n")
    f.write(snippet)
print("Appended print_dispatch.")
