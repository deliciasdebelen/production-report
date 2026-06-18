import os
import codecs

# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diagrama Carmal A</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        .diagram-container {{ margin-bottom: 50px; }}
        h1 {{ border-bottom: 2px solid #ccc; padding-bottom: 10px; }}
        .filename {{ font-size: 0.8em; color: gray; margin-bottom: 10px; }}
        
        @media print {{
            .no-print {{ display: none; }}
            body {{ margin: 0; }}
        }}
    </style>
</head>
<body>

<div class="no-print">
    <h1>Diagrama Base de Datos (Carmal)</h1>
    <p>Presione <strong>Ctrl + P</strong> para guardar como PDF.</p>
    <hr>
</div>

<div class="diagram-container">
    <div class="mermaid">
{mermaid_code}
    </div>
</div>

</body>
</html>
"""

def read_file_safely(path):
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with codecs.open(path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', errors='ignore')

def generate_single_viewer():
    docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    input_mmd = os.path.join(docs_dir, 'diagrama_carmal.mmd') # We copied this earlier
    output_html = os.path.join(docs_dir, 'diagrama_carmal.html')
    
    if not os.path.exists(input_mmd):
        print(f"Error: {input_mmd} not found.")
        return

    print(f"Reading {input_mmd}...")
    code = read_file_safely(input_mmd)
    
    final_html = HTML_TEMPLATE.format(mermaid_code=code)
    
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print(f"Generated: {output_html}")

if __name__ == "__main__":
    generate_single_viewer()
