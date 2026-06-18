"""Read diagnostic output"""
import subprocess, sys
result = subprocess.run(
    [sys.executable, "diag_cierre_8855.py"],
    capture_output=True, text=True, encoding='latin-1',
    cwd=r"c:\Users\ovargas\Projects\production-report"
)
print(result.stdout)
print(result.stderr)
