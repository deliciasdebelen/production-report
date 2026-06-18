import sys
import os

# Ensure project root in path
sys.path.append(os.getcwd())

try:
    print("Attempting to import app.dependencies...")
    import app.dependencies
    print("Success: app.dependencies imported.")
    
    print("Attempting to import get_current_active_user...")
    from app.dependencies import get_current_active_user
    print("Success: get_current_active_user imported.")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"General Error: {e}")
