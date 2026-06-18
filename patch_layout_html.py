with open("app/templates/layout.html", "r") as f:
    content = f.read()

if "sweetalert2" not in content.lower():
    if "<!-- Scripts -->" in content:
        content = content.replace(
            '<!-- Scripts -->',
            '<!-- Scripts -->\n    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>'
        )
    elif "</head>" in content:
        content = content.replace(
            '</head>',
            '    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>\n</head>'
        )
    with open("app/templates/layout.html", "w") as f:
        f.write(content)
    print("Patched layout.html")
else:
    print("Sweetalert already in layout.html")
