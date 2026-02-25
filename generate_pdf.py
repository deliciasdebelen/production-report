
import markdown
from xhtml2pdf import pisa
import os

# Input and Output paths
input_md_path = r"C:\Users\ovargas\.gemini\antigravity\brain\b63ba4f5-dfd1-4ff4-810c-1b3e3dd60e67\guide_dev_deploy.md"
output_pdf_path = os.path.join(os.path.expanduser("~"), "Desktop", "Guia_Desarrollo_Despliegue.pdf")

# CSS for better formatting
css = """
<style>
    @page {
        size: letter;
        margin: 2cm;
    }
    body {
        font-family: Helvetica, sans-serif;
        font-size: 11pt;
    }
    h1 {
        font-size: 24pt;
        color: #2c3e50;
        border-bottom: 2px solid #2c3e50;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    h2 {
        font-size: 18pt;
        color: #34495e;
        margin-top: 25px;
        border-bottom: 1px solid #bdc3c7;
    }
    h3 {
        font-size: 14pt;
        color: #7f8c8d;
        margin-top: 15px;
    }
    code {
        background-color: #f7f7f7;
        font-family: Courier, monospace;
        padding: 2px 4px;
        border-radius: 4px;
    }
    pre {
        background-color: #f0f0f0;
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 5px;
        font-family: Courier, monospace;
        white-space: pre-wrap;
    }
    li {
        margin-bottom: 5px;
    }
</style>
"""

def convert_md_to_pdf(input_path, output_path):
    # 1. Read Markdown
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 2. Convert to HTML
    html_content = markdown.markdown(text, extensions=['fenced_code', 'tables'])
    
    # Add simple HTML structure and CSS
    full_html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        {css}
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # 3. Write PDF
    with open(output_path, "wb") as output_file:
        pisa_status = pisa.CreatePDF(
            full_html,
            dest=output_file,
            encoding='utf-8'
        )

    if pisa_status.err:
        print(f"ERROR: Failed to generate PDF: {pisa_status.err}")
    else:
        print(f"SUCCESS: PDF generated at {output_path}")

if __name__ == "__main__":
    convert_md_to_pdf(input_md_path, output_pdf_path)
