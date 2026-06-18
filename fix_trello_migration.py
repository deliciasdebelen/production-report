"""
Fix script to add the missing due_date column to project_cards.
"""
from app.database import engine
from sqlalchemy import text

def run_fix():
    print("Iniciando corrección de esquema (Añadiendo due_date a project_cards)...")
    try:
        with engine.connect() as conn:
            # Check if column exists first to be safe
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='project_cards' AND column_name='due_date'"
            ))
            if not result.fetchone():
                print("Agregando columna due_date...")
                conn.execute(text("ALTER TABLE project_cards ADD COLUMN due_date TIMESTAMP WITH TIME ZONE NULL;"))
                conn.commit()
                print("✅ Columna due_date agregada exitosamente.")
            else:
                print("La columna due_date ya existe.")
    except Exception as e:
        print(f"❌ Error aplicando correcciones: {e}")

if __name__ == "__main__":
    run_fix()
