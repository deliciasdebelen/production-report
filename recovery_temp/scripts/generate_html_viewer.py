import os
import glob
import codecs

# HTML Template
# Doubled curly braces for JS object literal to escape Python .format()
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Schemas</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true }});
    </script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        .diagram-container {{ margin-bottom: 50px; page-break-after: always; }}
        h1 {{ border-bottom: 2px solid #ccc; padding-bottom: 10px; }}
        .filename {{ font-size: 0.8em; color: gray; margin-bottom: 10px; }}
        
        @media print {{
            .no-print {{ display: none; }}
            body {{ margin: 0; }}
            .diagram-container {{ page-break-after: always; }}
        }}
    </style>
</head>
<body>

<div class="no-print">
    <h1>Database Diagrams</h1>
    <p>To save as PDF: Press <strong>Ctrl + P</strong> (or File -> Print) and choose <strong>"Save as PDF"</strong>.</p>
    <hr>
</div>

{content}

</body>
</html>
"""

DIAGRAM_BLOCK_TEMPLATE = """
<div class="diagram-container">
    <h2>{title}</h2>
    <div class="filename">Source: {filename}</div>
    <div class="mermaid">
{mermaid_code}
    </div>
</div>
"""

def read_file_safely(path):
    # Try utf-8 first, then latin-1, then cp1252
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for enc in encodings:
        try:
            with codecs.open(path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
            
    # If all fail, read as binary and decode ignoring errors
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', errors='ignore')

def generate_viewer():
    docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    output_file = os.path.join(docs_dir, 'diagrams_viewer.html')
    
    # Find all .mmd files
    mmd_files = glob.glob(os.path.join(docs_dir, '*.mmd'))
    mmd_files.sort()
    
    if not mmd_files:
        print("No .mmd files found.")
        return
        
    print(f"Found files: {mmd_files}")
    content_html = ""
    
    for mmd_path in mmd_files:
        filename = os.path.basename(mmd_path)
        title = filename.replace('_schema.mmd', '').replace('.mmd', '').replace('_', ' ').title()
        
        print(f"Reading {filename}...")
        code = read_file_safely(mmd_path)
            
        content_html += DIAGRAM_BLOCK_TEMPLATE.format(
            title=title,
            filename=filename,
            mermaid_code=code
        )
    
    final_html = HTML_TEMPLATE.format(content=content_html)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
        
    print(f"Viewer generated at: {output_file}")

if __name__ == "__main__":
    generate_viewer()
