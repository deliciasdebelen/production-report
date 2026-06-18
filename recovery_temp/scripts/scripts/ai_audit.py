import sys
import os
import requests
import json
import pandas as pd

# AI Configuration
OLLAMA_HOST = "http://192.168.1.79:11434" # User's AI Muscle
MODEL = "llama3"

SYSTEM_PROMPT = """
Actúa como un auditor senior de Profit Plus. Analiza esta lista de discrepancias de inventario. 
Identifica los 3 artículos con mayor riesgo de quiebre de stock y sugiere si debemos generar un registro en saAjuste para corregir la diferencia. 
Toma en cuenta que el stock mínimo deseado es el valor en la columna Stock_Min_Definido.
"""

def analyze_audit():
    # 1. Read the audit results
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'audit_results.csv')
    if not os.path.exists(csv_path):
        print("Error: Audit results not found. Run run_audit.py first.")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    if df.empty:
        print("No discrepancies to analyze.")
        return

    # 2. Format data for the prompt
    # Convert dataframe to string/markdown table
    data_str = df.to_markdown(index=False)
    
    full_prompt = f"{SYSTEM_PROMPT}\n\nDATA:\n{data_str}"

    print(f"Sending analysis request to {OLLAMA_HOST} (model: {MODEL})...")

    # 3. Call Ollama
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": MODEL,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=60 # Wait up to 60s for analysis
        )
        
        if response.status_code == 200:
            result = response.json()
            analysis = result.get('response', 'No response field.')
            
            print("\n--- AI AUDIT ANALYSIS ---\n")
            print(analysis)
            
            # Save analysis
            output_file = os.path.join(os.path.dirname(__file__), '..', 'docs', 'ai_analysis.md')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# Informe de Auditoría Inteligente\n\n{analysis}")
            print(f"\nAnalysis saved to: {output_file}")
            
        else:
            print(f"Error from AI: {response.status_code} - {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"Could not connect to AI at {OLLAMA_HOST}. Is the 'ia_musculo' container running?")
    except Exception as e:
        print(f"Error during AI request: {e}")

if __name__ == "__main__":
    analyze_audit()
