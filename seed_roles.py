
from app.database import SessionLocal
from app.models import Role
import json

db = SessionLocal()

# Simplified Perms for Defaults
# 1=KPI, 2=Prod, 3=Plan, 4=Admin, 5=Almacen, 6=Inventory, 7=Patrimonial
roles_data = [
    (1, "KPI", {"production": ["view"], "planning": ["view"], "logistics": ["view"]}),
    (2, "Produccion", {"production": ["view", "create", "edit"]}),
    (3, "Planificacion", {"planning": ["view", "create", "edit"]}), # Typo fixed from 'create', 'edit'
    (4, "Admin", {"all": ["*"]}), # Admin 4 logic bypasses this anyway, but good for completeness
    (5, "Almacen", {"logistics": ["view", "create", "edit", "print"]}),
    (6, "Inventario", {"inventory": ["view", "create", "edit"], "logistics": ["view"]}),
    (7, "Patrimonial", {"logistics": ["view", "print"]})
]

print("--- Seeding Roles ---")
for r_id, name, perms in roles_data:
    existing = db.query(Role).filter(Role.id == r_id).first()
    if not existing:
        print(f"Creating Role {r_id}: {name}")
        role = Role(id=r_id, name=name, permissions=json.dumps(perms))
        db.add(role)
    else:
        print(f"Role {r_id} exists. Updating perms.")
        existing.permissions = json.dumps(perms)
        
db.commit()
print("Seeding Complete.")
db.close()
