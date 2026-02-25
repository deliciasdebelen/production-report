
from app.database import SessionLocal, engine
from app.models import Base, Role
from sqlalchemy import text
import json

def migrate_roles():
    print("Creating 'roles' table if not exists...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Default Roles based on legacy comments:
    # 1=KPI, 2=Prod, 3=Plan, 4=Admin, 5=Almacen, 6=Inventory, 7=Patrimonial
    
    default_roles = [
        {"id": 1, "name": "KPI / Visualizador", "perms": {"kpi": ["view"], "visor": ["view"]}},
        {"id": 2, "name": "Producción", "perms": {"production": ["view", "create", "edit"], "visor": ["view"]}},
        {"id": 3, "name": "Planificación", "perms": {"planning": ["view", "create", "edit"], "visor": ["view"]}},
        {"id": 4, "name": "Administrador", "perms": {"all": ["*"]}},
        {"id": 5, "name": "Almacén", "perms": {"logistics": ["view", "reception"]}},
        {"id": 6, "name": "Inventario", "perms": {"inventory": ["view", "create", "edit"], "logistics": ["view"]}},
        {"id": 7, "name": "Patrimonial", "perms": {"logistics": ["view", "print"]}},
    ]
    
    print("Seeding Roles...")
    for data in default_roles:
        existing = db.query(Role).filter(Role.id == data["id"]).first()
        if not existing:
            role = Role(
                id=data["id"],
                name=data["name"],
                permissions=json.dumps(data["perms"])
            )
            db.add(role)
            print(f"Added Role: {data['name']}")
        else:
            print(f"Role {data['name']} already exists.")
            # Un-comment to force update permissions during dev
            # existing.permissions = json.dumps(data["perms"])
            
    try:
        db.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Error migrating: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_roles()
