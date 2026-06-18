import sys
import os
from sqlalchemy import create_engine

# Force SQLite for local migrations BEFORE importing models
os.environ["DATABASE_URL"] = "sqlite:///production.db"

# Ensure the root of the project is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import models

print("Aplicando migraciones Locales a production.db para flujo de despacho...")
engine = create_engine("sqlite:///production.db")
models.Base.metadata.create_all(bind=engine)
print("¡Migración completada! Las tablas de Odoo-Workflow han sido creadas.")
