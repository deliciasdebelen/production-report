import sys
import os
import json
from sqlalchemy import text

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

# Add current path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Add current path to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.external_db import SessionA
from app.models import LogisticsDispatch, User

# We need a user to bypass auth or we can just patch the dependency.
from app.dependencies import get_current_user

# Setup Test Client
client = TestClient(app)

# Mock User with admin role
def override_get_current_user():
    return User(id=1, username="test_admin", role=1)

app.dependency_overrides[get_current_user] = override_get_current_user

def run_test():
    local_db = SessionLocal()
    ext_db = SessionA()
    
    print("--- INICIANDO CICLO DE PRUEBAS DE DESPACHO ---")
    
    try:
        # 1. Encontrar una factura pendiente en Profit Plus (campo5 IS NULL)
        print("1. Buscando factura pendiente de prueba...")
        query = text("""
            SELECT TOP 1 f.doc_num, f.co_cli, c.cli_des, r.co_art, r.total_art
            FROM saFacturaVenta f
            JOIN saCliente c ON f.co_cli = c.co_cli
            JOIN saFacturaVentaReng r ON f.doc_num = r.doc_num
            WHERE (f.campo5 IS NULL OR LTRIM(RTRIM(f.campo5)) = '')
            ORDER BY f.fec_emis DESC
        """)
        row = ext_db.execute(query).first()
        
        if not row:
            print("No hay facturas pendientes para probar. Abortando prueba.")
            return
            
        doc_num = row.doc_num.strip()
        client_name = row.cli_des.strip()
        co_art = row.co_art.strip()
        qty = float(row.total_art)
        
        print(f"   -> Factura seleccionada: {doc_num} (Cliente: {client_name})")
        
        # 2. Preparar el payload de creación de guía de despacho
        document_ref = f"GUIA-TEST-{doc_num}"
        items_payload = [
            {
                "client": client_name,
                "fact": doc_num,
                "item": f"Test Item ({co_art})",
                "qty": qty,
                "unit": "Unid",
                "total_cajas": 0,
                "unidad_cajas": "CAJ"
            }
        ]
        
        form_data = {
            "document_ref": document_ref,
            "imported_invoices": f"FACT:{doc_num}",
            "items": json.dumps(items_payload),
            "client_destination": client_name,
            "route_input": "Ruta Prueba Local"
        }
        
        # 3. Llamar a la API de Despacho (POST /logistics/dispatch)
        print(f"2. Guardando guía de despacho ({document_ref})...")
        response = client.post("/logistics/dispatch", data=form_data)
        
        if response.status_code != 200:
            print(f"   [FALLO] Fallo al crear la guia. Status: {response.status_code}")
            print(f"   Detalle: {response.text}")
            return
            
        data = response.json()
        dispatch_id = data.get("id")
        print(f"   [EXITO] Guia creada exitosamente (ID: {dispatch_id})")
        
        # 4. Validar que en Profit Plus se haya marcado el campo5 y campo6
        print("3. Validando marcaje en la BD Externa (Profit Plus)...")
        check_query = text("SELECT campo5, campo6 FROM saFacturaVenta WHERE doc_num = :doc")
        check_row = ext_db.execute(check_query, {"doc": doc_num}).first()
        
        if check_row and check_row.campo5 and check_row.campo6:
            print(f"   [EXITO] Validado: campo5 = '{check_row.campo5}', campo6 = '{check_row.campo6}'")
        else:
            print(f"   [FALLO] Fallo: Los campos en Profit Plus no se actualizaron.")
            
        # 5. Intentar crear nuevamente la misma guia para probar la validacion anti-duplicidad
        print("4. Verificando validacion multicriterio (Simulando segundo intento)...")
        form_data_dup = dict(form_data)
        form_data_dup["document_ref"] = f"GUIA-TEST-DUP-{doc_num}"
        response_dup = client.post("/logistics/dispatch", data=form_data_dup)
        
        if response_dup.status_code == 400:
            print("   [EXITO] Validado: El sistema bloqueo la duplicacion como se esperaba.")
        else:
            print("   [FALLO] Fallo: El sistema permitio duplicar el despacho.")
            
        # 6. Reversar la prueba (Limpieza)
        print("5. Reversando los cambios de la prueba...")
        
        # Reversar en Profit Plus
        reverse_query = text("UPDATE saFacturaVenta SET campo5 = NULL, campo6 = NULL WHERE doc_num = :doc")
        ext_db.execute(reverse_query, {"doc": doc_num})
        ext_db.commit()
        print(f"   [EXITO] Profit Plus: Factura {doc_num} restaurada (campo5/campo6 limpiados).")
        
        # Reversar en SQLite (Eliminar Log, la ruta de prueba no importa tanto pero la limpiamos)
        log_to_delete = local_db.query(LogisticsDispatch).filter(LogisticsDispatch.id == dispatch_id).first()
        if log_to_delete:
            local_db.delete(log_to_delete)
            local_db.commit()
            print(f"   [EXITO] SQLite Local: Guia {document_ref} eliminada.")
            
        print("--- PRUEBAS FINALIZADAS CON EXITO ---")

    except Exception as e:
        print(f"Error durante las pruebas: {e}")
        local_db.rollback()
        ext_db.rollback()
    finally:
        local_db.close()
        ext_db.close()

if __name__ == "__main__":
    run_test()
