import json
import os

def generate_markdown(json_file, md_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    tables = data.get("tables", {})
    fks = data.get("fks", [])
    
    # Organize FKs for easy lookup
    # outgoing[table] = [fk_info]
    outgoing_fks = {}
    incoming_fks = {}
    for fk in fks:
        pt = fk["parent_table"]
        rt = fk["referenced_table"]
        
        if pt not in outgoing_fks: outgoing_fks[pt] = []
        outgoing_fks[pt].append(fk)
        
        if rt not in incoming_fks: incoming_fks[rt] = []
        incoming_fks[rt].append(fk)

    with open(md_file, 'w', encoding='utf-8') as out:
        out.write("# Diccionario de Datos y ERD: `carmal_n` (Nómina 2kDoce)\n\n")
        out.write("Este documento contiene la estructura de la base de datos `carmal_n` del servidor `192.168.1.205`, incluyendo sus tablas, columnas y relaciones.\n\n")
        
        out.write("## Diagrama General de Relaciones (Principales)\n\n")
        out.write("Debido a la cantidad de tablas (96), a continuación se presenta un subconjunto representativo de las tablas con más relaciones (Top 15 centrales).\n\n")
        
        # Find top tables by number of relationships
        table_rel_count = {}
        for t in tables.keys():
            table_rel_count[t] = len(outgoing_fks.get(t, [])) + len(incoming_fks.get(t, []))
            
        top_tables = sorted(table_rel_count.keys(), key=lambda k: table_rel_count[k], reverse=True)[:15]
        
        out.write("```mermaid\nerDiagram\n")
        rendered_fks = set()
        for fk in fks:
            pt = fk["parent_table"]
            rt = fk["referenced_table"]
            if pt in top_tables and rt in top_tables:
                rel_id = f"{pt}-{rt}"
                if rel_id not in rendered_fks:
                    out.write(f"    {pt} }}|--|| {rt} : \"{fk['parent_column']} -> {fk['referenced_column']}\"\n")
                    rendered_fks.add(rel_id)
        out.write("```\n\n")
        
        out.write("## Diccionario de Tablas\n\n")
        
        # Sort tables alphabetically
        for t_name in sorted(tables.keys()):
            out.write(f"### Tabla: `{t_name}`\n\n")
            
            # Draw Mermaid for this specific table (1 level deep)
            out.write("```mermaid\nerDiagram\n")
            out.write(f"    {t_name} {{\n")
            for col in tables[t_name]:
                # Format type
                t_type = col["type"]
                if t_type in ["varchar", "char", "nchar", "nvarchar"]:
                    t_type += f"({col['length']})"
                
                # Check if it's an FK
                is_fk = ""
                for fk in outgoing_fks.get(t_name, []):
                    if fk["parent_column"] == col["column_name"]:
                        is_fk = "FK"
                        break
                        
                nl = "NULL" if col["nullable"] else "NOT NULL"
                out.write(f"        {t_type.replace(' ', '_')} {col['column_name']} {is_fk} \"{nl}\"\n")
            out.write("    }\n")
            
            # Draw relationships
            for fk in outgoing_fks.get(t_name, []):
                out.write(f"    {t_name} }}|--|| {fk['referenced_table']} : \"{fk['parent_column']}\"\n")
                
            for fk in incoming_fks.get(t_name, []):
                out.write(f"    {fk['parent_table']} }}|--|| {t_name} : \"{fk['parent_column']}\"\n")
                
            out.write("```\n\n")

if __name__ == "__main__":
    artifact_path = r"c:\Users\ovargas\.gemini\antigravity\brain\9e88accf-a30c-41b5-bcb4-7452b68c10be\carmal_n_schema.md"
    generate_markdown("carmal_n_schema_raw.json", artifact_path)
    print(f"Artifact successfully written to {artifact_path}")
