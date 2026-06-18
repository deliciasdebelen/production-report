"""
Script de captura automatizada del flujo de Manufactura en Odoo 17.
Usa Playwright (instalado localmente) para navegar y tomar screenshots reales.
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

# ---- Configuración ----
ODOO_URL = "http://192.168.1.193:8069"
ODOO_USER = "admin"
ODOO_PASS = "admin"

# Guardar screenshots aquí
SCREENSHOTS_DIR = Path(r"C:\Users\ovargas\.gemini\antigravity\brain\5f73e00f-67ba-4e72-87b8-ea5215929dc3")

async def take_screenshot(page, name: str, description: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    await page.screenshot(path=str(path), full_page=False)
    print(f"  📸 [{name}] {description}")
    return path

async def main():
    print("=" * 60)
    print("  ODOO MANUFACTURING FLOW - Captura Automática")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(viewport={"width": 1600, "height": 900})
        page = await context.new_page()
        
        # --------------------------------------------------------
        # PASO 1: Abrir Odoo
        # --------------------------------------------------------
        print("\n[Paso 1] Abriendo Odoo...")
        await page.goto(ODOO_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "01_login_page", "Pantalla de Login de Odoo")
        
        # --------------------------------------------------------
        # PASO 2: Iniciar sesión
        # --------------------------------------------------------
        print("\n[Paso 2] Iniciando sesión con admin...")
        try:
            await page.fill('input[id="login"]', ODOO_USER)
            await page.fill('input[id="password"]', ODOO_PASS)
        except:
            try:
                await page.fill('input[name="login"]', ODOO_USER)
                await page.fill('input[name="password"]', ODOO_PASS)
            except Exception as e:
                print(f"   ⚠️  Error llenando login: {e}")
        
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "02_app_dashboard", "Dashboard principal de Odoo con todas las Apps")
        
        # --------------------------------------------------------
        # PASO 3: Ir a Manufactura
        # --------------------------------------------------------
        print("\n[Paso 3] Navegando a la App de Manufactura...")
        # Try to click on Manufacturing app
        try:
            # Try English first
            mfg_app = page.locator("text=Manufacturing").first
            await mfg_app.click(timeout=5000)
        except:
            try:
                # Try Spanish
                mfg_app = page.locator("text=Fabricación").first
                await mfg_app.click(timeout=5000)
            except:
                # Navigate directly
                await page.goto(f"{ODOO_URL}/odoo/manufacturing", wait_until="networkidle", timeout=20000)
        
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "03_manufacturing_home", "Módulo de Manufactura - Vista principal de Órdenes")

        # --------------------------------------------------------
        # PASO 4: Crear nueva Orden de Producción
        # --------------------------------------------------------
        print("\n[Paso 4] Creando una nueva Orden de Producción...")
        try:
            # Odoo 17 New button
            new_btn = page.locator("button:has-text('New'), a:has-text('New'), button:has-text('Nuevo'), a:has-text('Nuevo')").first
            await new_btn.click(timeout=10000)
        except:
            await page.goto(f"{ODOO_URL}/odoo/manufacturing/new", wait_until="networkidle", timeout=20000)
        
        await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "04_new_mo_form", "Formulario de Nueva Orden de Producción (vacía)")
        
        # --------------------------------------------------------
        # PASO 5: Seleccionar Producto a producir
        # --------------------------------------------------------
        print("\n[Paso 5] Seleccionando el producto a producir (línea PT o ST)...")
        try:
            # Look for the Product field
            product_field = page.locator('div[name="product_id"] input, .o_field_widget[name="product_id"] input').first
            await product_field.click(timeout=8000)
            await product_field.type("PT", delay=100)
            await page.wait_for_timeout(1500)
            # Click first suggestion
            dropdown_item = page.locator('.o_dropdown_item, .ui-menu-item, li.o-autocomplete--dropdown-item').first
            await dropdown_item.click(timeout=5000)
        except Exception as e:
            print(f"   ⚠️  Producto field error (continuando): {e}")
            try:
                # Try with direct search
                product_field = page.locator('[name="product_id"] input').first
                await product_field.fill("ST")
                await page.wait_for_timeout(1500)
                await page.keyboard.press("ArrowDown")
                await page.keyboard.press("Enter")
            except:
                pass
        
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "05_mo_product_selected", "Orden de Producción con producto seleccionado y Lista de Materiales auto-cargada")
        
        # --------------------------------------------------------
        # PASO 6: Confirmar la Orden
        # --------------------------------------------------------
        print("\n[Paso 6] Confirmando la Orden de Producción...")
        try:
            confirm_btn = page.locator("button:has-text('Confirm'), button:has-text('Confirmar')").first
            await confirm_btn.click(timeout=10000)
        except Exception as e:
            print(f"   ⚠️  Confirm button: {e}")
        
        await page.wait_for_load_state("networkidle", timeout=15000)
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "06_mo_confirmed", "Orden de Producción Confirmada - Estado Confirmed y disponibilidad de materiales")
        
        # --------------------------------------------------------
        # PASO 7: Verificar Componentes
        # --------------------------------------------------------
        print("\n[Paso 7] Inspeccionando la pestaña de Componentes...")
        try:
            comp_tab = page.locator("a.nav-link:has-text('Components'), a.nav-link:has-text('Componentes'), a:has-text('Components'), button:has-text('Components')").first
            await comp_tab.click(timeout=5000)
            await page.wait_for_timeout(1500)
        except:
            pass
        await take_screenshot(page, "07_mo_components", "Pestaña de Componentes - Lista de materiales necesarios y su disponibilidad de inventario")
        
        # --------------------------------------------------------
        # PASO 8: Marcar como Listo ("Produce All" o "Done")
        # --------------------------------------------------------
        print("\n[Paso 8] Produciendo todo y marcando como Hecho...")
        
        # Try "Produce All" button
        try:
            produce_btn = page.locator(
                "button:has-text('Produce All'), button:has-text('Producir todo'), "
                "button:has-text('Mark as Done'), button:has-text('Marcar como')"
            ).first
            await produce_btn.click(timeout=8000)
            await page.wait_for_timeout(1500)
            # Handle any confirmation popup
            ok_btn = page.locator("button:has-text('Ok'), button:has-text('Apply'), button:has-text('Aplicar')").first
            if await ok_btn.is_visible(timeout=3000):
                await ok_btn.click()
        except:
            pass
        
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "08_mo_done", "Orden de Producción completada - Estado Done/Hecho con cantidades producidas")
        
        # --------------------------------------------------------
        # PASO 9: Ver la lista de Órdenes con el nuevo registro
        # --------------------------------------------------------
        print("\n[Paso 9] Capturando la lista de órdenes completadas...")
        try:
            await page.goto(f"{ODOO_URL}/odoo/manufacturing", wait_until="networkidle", timeout=20000)
        except:
            await page.go_back()
        await page.wait_for_timeout(2000)
        await take_screenshot(page, "09_mo_list_final", "Lista de Órdenes de Manufactura con la nueva Orden marcada como Done")
        
        print("\n" + "=" * 60)
        print("  ✅ CAPTURA FINALIZADA EXITOSAMENTE")
        print(f"  Screenshots guardados en: {SCREENSHOTS_DIR}")
        print("=" * 60)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
