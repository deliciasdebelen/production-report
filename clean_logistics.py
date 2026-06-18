
import os

path = r"c:\Users\ovargas\Projects\production-report\app\routers\logistics.py"

with open(path, "rb") as f:
    content = f.read()

# Find the valid end. We know "now": datetime.now()\n    })\n
# The last valid chars are closing brace and newline?
# Let's find "GUID-..." and then the new function. 
# Search for the newly added function end.
end_marker = b'        "now": datetime.now()\r\n    })'
# or \n depending on line endings. Windows \r\n
# Let's search for the text and truncate after it.

pos = content.find(b'"now": datetime.now()')
if pos != -1:
    # Find the next closing brace } and parenthesis )
    # roughly 20-50 chars after
    end_pos = content.find(b'})', pos)
    if end_pos != -1:
        # Include }) and a newline
        trunc_pos = end_pos + 2
        clean_content = content[:trunc_pos]
        
        with open(path, "wb") as f:
            f.write(clean_content)
        print("Truncated file successfully.")
    else:
        print("Could not find closing brace.")
else:
    print("Could not find end marker.")
