"""
Migración que asegura que las tablas de Proyectos (Trello Clone) 
existen en la base de datos (PostgreSQL/SQLite).
"""
import sys
import os

# Ensure the app module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine
from app.models import Base

def migrate():
    print("Iniciando migración de tablas para el módulo Proyectos...")
    try:
        # Esto creará las tablas si no existen. Las que ya existen se omiten.
        # No altera columnas existentes, pero es suficiente para las tablas nuevas.
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas de Proyectos creadas exitosamente.")
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")

if __name__ == "__main__":
    migrate()
