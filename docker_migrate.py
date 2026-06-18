from app.database import engine
from app import models

print("Ejecutando creacion de tablas faltantes en production.db...")
models.Base.metadata.create_all(bind=engine)
print("Migracion finalizada con exito.")
