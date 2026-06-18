from app.database import SessionLocal, engine
from app import models

def init_support_data():
    db = SessionLocal()
    
    # Create Tables
    models.Base.metadata.create_all(bind=engine)
    
    # 1. Departments
    depts = ["IT", "Infraestructura", "Software", "Administrativo"]
    for name in depts:
        if not db.query(models.SupportDepartment).filter_by(name=name).first():
            db.add(models.SupportDepartment(name=name))
            print(f"Added Dept: {name}")

    # 2. Status
    statuses = [
        ("Abierto", "#EF4444"), # Red
        ("En Proceso", "#F59E0B"), # Amber
        ("Pendiente Repuesto", "#8B5CF6"), # Purple
        ("Cerrado", "#10B981") # Green
    ]
    for name, color in statuses:
        if not db.query(models.SupportStatus).filter_by(name=name).first():
            db.add(models.SupportStatus(name=name, color_hex=color))
            print(f"Added Status: {name}")
            
    # 3. Priority
    priorities = [
        ("Baja", 1),
        ("Media", 2),
        ("Alta", 3),
        ("Urgente", 4)
    ]
    for name, level in priorities:
         if not db.query(models.SupportPriority).filter_by(name=name).first():
            db.add(models.SupportPriority(name=name, level=level))
            print(f"Added Priority: {name}")
            
    # 4. Types
    types = ["Hardware", "Conectividad", "Software ERP", "Accesos", "Impresoras"]
    for name in types:
        if not db.query(models.SupportType).filter_by(name=name).first():
            db.add(models.SupportType(name=name))
            print(f"Added Type: {name}")

    db.commit()
    db.close()
    print("Support Data Initialized.")

if __name__ == "__main__":
    init_support_data()
