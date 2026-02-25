from app.database import engine, Base
from app.models import AIFunctionality, AIParameter
from sqlalchemy import text

def migrate():
    print("Creating AI Parameters tables...")
    # SQL Server syntax for checking if table exists, or just use Base.metadata.create_all which is safe
    # But often create_all doesn't update existing tables, only creates new ones.
    # Since these are new tables, create_all is perfect.
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")

    # Initialize default data
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if we have defaults
        if db.query(AIFunctionality).count() == 0:
            print("Seeding default AI functionalities...")
            f1 = AIFunctionality(name="Optimization", description="Optimización de procesos de producción")
            f2 = AIFunctionality(name="Audit", description="Auditoría de consistencia de datos")
            f3 = AIFunctionality(name="Predictive", description="Análisis predictivo de inventario")
            
            db.add_all([f1, f2, f3])
            db.commit()
            
            # Add some parameters
            p1 = AIParameter(functionality_id=f1.id, key="efficiency_target", value="0.95", description="Meta de eficiencia global")
            p2 = AIParameter(functionality_id=f2.id, key="tolerance_threshold", value="0.02", description="Tolerancia de error en auditoría")
            
            db.add_all([p1, p2])
            db.commit()
            print("Seeding complete.")
        else:
            print("AI data already exists.")
            
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
