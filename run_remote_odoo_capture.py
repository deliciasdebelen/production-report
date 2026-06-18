import paramiko, time
from pathlib import Path

SSH_HOST = "192.168.1.79"
SSH_USER = "administrador"
SSH_PASS = "GRW7czL3*"

REMOTE_SCREENSHOTS_DIR = "/tmp/odoo_screenshots"
LOCAL_SCREENSHOTS_DIR = Path(r"C:\Users\ovargas\.gemini\antigravity\brain\5f73e00f-67ba-4e72-87b8-ea5215929dc3")

PLAYWRIGHT_SCRIPT = r'''
import asyncio, os, sys
from pathlib import Path
from playwright.async_api import async_playwright

ODOO_URL = "http://192.168.1.193:8069"
ODOO_USER = "admin"
ODOO_PASS = "admin"
SHOTS_DIR = Path("/tmp/odoo_screenshots")
SHOTS_DIR.mkdir(exist_ok=True)

async def shot(page, name, desc):
    path = SHOTS_DIR / f"{name}.png"
    await page.screenshot(path=str(path), full_page=False)
    print(f"SHOT:{name}:{desc}")
    return path

async def main():
    print("START")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(viewport={"width": 1600, "height": 900})
        page = await ctx.new_page()
        page.set_default_timeout(25000)

        # 1. Login
        print("STEP:1:Abriendo Odoo")
        try:
            await page.goto(ODOO_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            await shot(page, "01_login", "Pantalla de Login de Odoo")
        except Exception as e:
            print(f"ERROR_STEP1:{e}")
            sys.exit(1)

        print("STEP:2:Login con admin")
        try:
            await page.locator("#login").fill(ODOO_USER)
            await page.locator("#password").fill(ODOO_PASS)
            await page.locator("button[type=submit]").click()
            await page.wait_for_load_state("networkidle", timeout=25000)
            await page.wait_for_timeout(2000)
            await shot(page, "02_home", "Dashboard principal de Odoo")
        except Exception as e:
            print(f"WARN_STEP2:{e}")
            await shot(page, "02_home", "Post-Login state")

        print("STEP:3:Modulo Manufactura")
        try:
            await page.goto(ODOO_URL + "/odoo/manufacturing", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)
            await shot(page, "03_mfg_list", "Lista de Ordenes de Fabricacion")
        except Exception as e:
            print(f"WARN_STEP3:{e}")
            await shot(page, "03_mfg_list", "Modulo Manufactura")

        print("STEP:4:Nueva Orden")
        try:
            btns = page.locator("button:has-text('New'), a:has-text('New'), button:has-text('Nuevo'), a:has-text('Nuevo')")
            cnt = await btns.count()
            if cnt > 0:
                await btns.first.click()
            else:
                await page.goto(ODOO_URL + "/odoo/manufacturing/new", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2500)
            await shot(page, "04_new_mo", "Nueva Orden de Produccion - Formulario vacio")
        except Exception as e:
            print(f"WARN_STEP4:{e}")
            await shot(page, "04_new_mo", "Formulario nueva orden")

        print("STEP:5:Seleccionando producto")
        for term in ["ST", "PT", ""]:
            try:
                inp = page.locator('[name="product_id"] input, div[name="product_id"] input').first
                await inp.click()
                if term:
                    await inp.fill(term)
                    await page.wait_for_timeout(1800)
                dd = page.locator(".o-autocomplete--dropdown-item, .o_dropdown_item").first
                if await dd.is_visible(timeout=3000):
                    dd_text = await dd.inner_text()
                    await dd.click()
                    print(f"PRODUCT_SELECTED:{dd_text.strip()[:60]}")
                    break
            except Exception as e:
                print(f"TRY_PROD_{term}:{e}")
        await page.wait_for_timeout(2000)
        await shot(page, "05_product", "Producto seleccionado con Lista de Materiales auto-cargada")

        print("STEP:6:Confirmando Orden")
        try:
            c = page.locator("button:has-text('Confirm'), button:has-text('Confirmar')")
            if await c.count() > 0:
                await c.first.click()
                await page.wait_for_load_state("networkidle", timeout=20000)
                await page.wait_for_timeout(2000)
            await shot(page, "06_confirmed", "Orden Confirmada - Materiales reservados")
        except Exception as e:
            print(f"WARN_STEP6:{e}")
            await shot(page, "06_confirmed", "Estado post-confirmacion")

        print("STEP:7:Componentes")
        try:
            tabs = page.locator("a.nav-link:has-text('Component'), a.nav-link:has-text('Componente')")
            if await tabs.count() > 0:
                await tabs.first.click()
                await page.wait_for_timeout(1500)
            await shot(page, "07_components", "Pestaña Componentes - Lista de materiales y disponibilidad")
        except Exception as e:
            print(f"WARN_STEP7:{e}")
            await shot(page, "07_components", "Componentes")

        print("STEP:8:Producir todo")
        try:
            btns = page.locator("button:has-text('Produce All'), button:has-text('Producir todo'), button:has-text('Mark as Done'), button:has-text('Marcar')")
            if await btns.count() > 0:
                await btns.first.click()
                await page.wait_for_timeout(2000)
                for t in ["Apply", "Ok", "Aplicar", "Immediate"]:
                    try:
                        b = page.locator(f"button:has-text('{t}')").first
                        if await b.is_visible(timeout=2000):
                            await b.click()
                            break
                    except:
                        pass
                await page.wait_for_load_state("networkidle", timeout=20000)
                await page.wait_for_timeout(2000)
            await shot(page, "08_done", "Orden de Produccion completada - Estado Done")
        except Exception as e:
            print(f"WARN_STEP8:{e}")
            await shot(page, "08_done", "Estado final orden")

        print("STEP:9:Lista final de ordenes")
        try:
            await page.goto(ODOO_URL + "/odoo/manufacturing", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(2000)
            await shot(page, "09_final_list", "Lista de Ordenes completadas")
        except Exception as e:
            print(f"WARN_STEP9:{e}")
            await shot(page, "09_final_list", "Lista ordenes")

        await browser.close()
    print("DONE")
    import os
    files = sorted(os.listdir("/tmp/odoo_screenshots"))
    print(f"FILES:{','.join(files)}")

asyncio.run(main())
'''

def run_cmd(client, cmd, timeout=120):
    _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    return out, err

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"[1] Conectando a {SSH_HOST}...")
client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=30)
print("    Conectado.")

print("[2] Subiendo script...")
sftp = client.open_sftp()
with sftp.open("/tmp/capture_odoo.py", 'w') as f:
    f.write(PLAYWRIGHT_SCRIPT)
sftp.close()
print("    Script subido.")

print("[3] Ejecutando captura (puede tardar 60-90 segundos)...")
_, stdout, _ = client.exec_command(
    "PATH=$PATH:/home/administrador/.local/bin python3 /tmp/capture_odoo.py 2>&1",
    timeout=180
)
# Stream real-time
prev = ""
while not stdout.channel.exit_status_ready():
    if stdout.channel.recv_ready():
        chunk = stdout.channel.recv(2048).decode(errors='replace')
        for line in chunk.splitlines():
            if line.strip():
                print(f"    {line.strip()}")
    time.sleep(0.5)

remaining = stdout.read().decode(errors='replace')
for line in remaining.splitlines():
    if line.strip():
        print(f"    {line.strip()}")

print("[4] Descargando screenshots...")
LOCAL_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

sftp = client.open_sftp()
try:
    files = sorted(sftp.listdir(REMOTE_SCREENSHOTS_DIR))
    png_files = [f for f in files if f.endswith('.png')]
    print(f"    Encontrados: {png_files}")
    
    downloaded = []
    for fn in png_files:
        rp = f"{REMOTE_SCREENSHOTS_DIR}/{fn}"
        lp = LOCAL_SCREENSHOTS_DIR / fn
        sftp.get(rp, str(lp))
        downloaded.append(lp)
        print(f"    Descargado: {fn}")
    
    sftp.close()
    client.close()
    print(f"\n=== COMPLETADO: {len(downloaded)} imagenes descargadas ===")
    for d in downloaded:
        print(f"  {d}")
        
except FileNotFoundError as e:
    print(f"    ERROR: {e}")
    sftp.close()
    client.close()
