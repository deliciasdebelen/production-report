from py_mini_racer import MiniRacer

ctx = MiniRacer()
with open('temp_script.js', 'r', encoding='utf-8') as f:
    js = f.read()

try:
    ctx.eval(js)
    print("OK")
except Exception as e:
    print("Error:", str(e))
