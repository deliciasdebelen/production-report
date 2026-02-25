import sys
import os

# Add project root to sys.path to allow importing app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base
# Import models to ensure they are registered with Base
from app import models
from sqlalchemy import inspect
from sqlalchemy.orm import RelationshipProperty

def generate_mermaid_diagram():
    # Only verify models are loaded
    # print(f"Found models: {Base.registry.mappers}")

    mmd_lines = ["erDiagram"]

    # Iterate over all mappers (tables)
    for mapper in Base.registry.mappers:
        model = mapper.class_
        table_name = model.__tablename__
        
        # Add table definition
        mmd_lines.append(f"    {table_name} {{")
        
        # Add columns
        for column in mapper.columns:
            col_name = column.name
            col_type = str(column.type).replace(" ", "_") # Mermaid doesn't like spaces in types
            
            # Identify PK and FK
            modifiers = []
            if column.primary_key:
                modifiers.append("PK")
            if column.foreign_keys:
                modifiers.append("FK")
            
            modifier_str = f" {', '.join(modifiers)}" if modifiers else ""
            
            mmd_lines.append(f"        {col_type} {col_name}{modifier_str}")
        
        mmd_lines.append("    }")

    # Add relationships
    # We iterate again or do it in the same loop. 
    # To avoid duplicates (A->B and B->A), we might need to track them.
    # For Mermaid, direction doesn't strictly matter for the visual line, 
    # but cardinality does: ||--o{, }|--||, etc.
    
    # Simple approach: Iterate all foreign keys
    for mapper in Base.registry.mappers:
        table_name = mapper.tables[0].name
        
        for column in mapper.columns:
            for fk in column.foreign_keys:
                target_table = fk.column.table.name
                # Relationship: target_table ||--o{ source_table (usually)
                # We assume standard One-to-Many for simplicity unless we inspect relationships deeply
                mmd_lines.append(f"    {target_table} ||--o{{ {table_name} : \"has\"")

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'database_schema.mmd')

    with open(output_file, 'w') as f:
        f.write("\n".join(mmd_lines))
    
    print(f"Diagram generated at: {output_file}")

if __name__ == "__main__":
    generate_mermaid_diagram()
