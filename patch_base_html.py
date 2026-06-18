import re

with open("app/templates/base.html", "r") as f:
    content = f.read()

if "sweetalert2" not in content.lower():
    content = content.replace(
        '</head>',
        '    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>\n</head>'
    )
    with open("app/templates/base.html", "w") as f:
        f.write(content)
    print("Patched base.html")
else:
    print("Sweetalert already in base.html")
