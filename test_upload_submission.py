import requests
import os

# Create a dummy image
with open('test_image.jpg', 'wb') as f:
    f.write(os.urandom(1024))

url = 'http://127.0.0.1:8000/api/production'
cookies = {'user_id': '1'} # Assuming admin user ID 1

data = {
    'batch_qty': '10',
    'article_type': 'TEST_PRODUCT', # From manual text
    'kg_produced': '100.5',
    'presentation': '1KG',
    'boxes': '10',
    'pt_units': '100',
    
    # Optional fields
    'pt_lab': '0',
    'pt_burned': '0',
    'mp_containers': '0',
    'mp_caps_clean': '0',
    'mp_caps_dirty': '0',
    'mp_waste_kg': '0',
    
    'cons_type': '',
    'cons_count': '0',
    'cons_unit_weight': '0',
    'cons_qty': '0',
    
    'notes': 'Test auto-submission via script'
}

# files = {
#     'mp_waste_image': ('test_image.jpg', open('test_image.jpg', 'rb'), 'image/jpeg')
# }
files = {}

try:
    print("Enviando reporte con imagen...")
    response = requests.post(url, data=data, files=files, cookies=cookies)
    
    if response.status_code == 200:
        print("EXITO: Reporte guardado correctamente.")
        print(response.json())
    else:
        print(f"ERROR: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Excepcion: {e}")
finally:
    # Cleanup
    if os.path.exists('test_image.jpg'):
        os.remove('test_image.jpg')
