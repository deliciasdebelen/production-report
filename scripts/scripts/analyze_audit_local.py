import pandas as pd
import os

def analyze_locally():
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'audit_results.csv')
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error: {e}")
        return

    # Fix column names if needed. CSV headers: 
    # Codigo,Descripcion,Stock_Min_Definido,Stock_Max_Definido,Stock_Admin_Calculado,Total_en_Lotes,Diferencia_Fisica
    
    # Calculate Discrepancy (Admin says X, Physical says Y)
    # Risk of Stockout = Admin > Physical (We think we have it, but we don't)
    # Discrepancy = Admin - Physical
    df['Missing_Stock'] = df['Stock_Admin_Calculado'] - df['Total_en_Lotes']
    
    # Sort by missing stock (Highest missing first)
    top_risks = df.sort_values(by='Missing_Stock', ascending=False).head(3)
    
    report_lines = ["# 🤖 Informe de Auditoría (Generado por IA)\n"]
    report_lines.append("He analizado las discrepancias de inventario comparando el Stock Administrativo (Teórico) con los Lotes (Físico).\n")
    report_lines.append("Se identificaron artículos con **Alto Riesgo de Quiebre** (El sistema cree que hay stock, pero no está en lotes).\n")
    
    report_lines.append("## 🚨 Top 3 Artículos Críticos\n")
    
    for _, row in top_risks.iterrows():
        missing = row['Missing_Stock']
        admin = row['Stock_Admin_Calculado']
        physical = row['Total_en_Lotes']
        code = row['Codigo']
        desc = row['Descripcion']
        
        report_lines.append(f"### 1. {desc} ({code})")
        report_lines.append(f"- **Diferencia Crítica:** Faltan **{missing:,.2f}** unidades.")
        report_lines.append(f"- **Estado:** Admin dice **{admin:,.2f}**, Realidad (Lotes): **{physical:,.2f}**.")
        report_lines.append(f"- **Recomendación:** ⚠️ **URGENTE:** Generar `saAjuste` de salida por {missing:,.2f} para sincerar el inventario. Verificar si hubo consumo no reportado.\n")

    output_file = os.path.join(os.path.dirname(__file__), '..', 'docs', 'ai_analysis.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
        
    print(f"Analysis generated at {output_file}")

if __name__ == "__main__":
    analyze_locally()
