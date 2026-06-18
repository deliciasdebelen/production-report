import asyncio
from playwright.async_api import async_playwright

async def test_support_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to login page...")
        await page.goto("http://192.168.1.79:8000/login")
        
        # We need to login first
        try:
            print("Logging in...")
            await page.fill('input[name="username"]', "administrador")
            await page.fill('input[name="password"]', "admin") # Assuming admin/admin or try something else
            await page.click('button[type="submit"]')
            await page.wait_for_url("**/")
        except Exception as e:
            print("Login failed or not needed, continuing...")

        print("Navigating to support tickets...")
        await page.goto("http://192.168.1.79:8000/support/tickets")
        
        try:
            # Wait for tickets to load
            await page.wait_for_selector('#ticketsTableBody tr td', timeout=5000)
            
            # Click the first attachment button in the list
            print("Testing attachment button in the list view...")
            attachment_btn = await page.query_selector('button[title="Ver Adjunto"]')
            
            if attachment_btn:
                await attachment_btn.click()
                print("Clicked attachment button in list.")
                
                # Check if modal is visible
                is_visible = await page.is_visible('#imageModal')
                print(f"Image modal visible (list view): {is_visible}")
                
                # Close modal
                close_btn = await page.query_selector('#imageModal span')
                await close_btn.click()
                print("Closed image modal.")
            else:
                print("No tickets with attachments found in the list.")

            # Click the first ticket details button
            print("Testing ticket detail modal...")
            detail_btn = await page.query_selector('button[title="Ver Detalles del Ticket"]')
            if detail_btn:
                await detail_btn.click()
                print("Clicked ticket details button.")
                
                # Check if ticket modal is visible
                is_visible = await page.is_visible('#ticketDetailModal')
                print(f"Ticket detail modal visible: {is_visible}")
                
                # Click the attachment button inside the modal
                modal_attachment_btn = await page.query_selector('#tdAttachmentBtn')
                if modal_attachment_btn and await modal_attachment_btn.is_visible():
                    await modal_attachment_btn.click()
                    print("Clicked attachment button inside ticket details.")
                    
                    # Check if image modal is visible
                    img_visible = await page.is_visible('#imageModal')
                    print(f"Image modal visible (detail view): {img_visible}")
                else:
                    print("No attachment for this ticket inside details modal.")
            else:
                print("No tickets found to view details.")
                
        except Exception as e:
            print(f"Test encountered an error: {e}")
            
        finally:
            await browser.close()
            print("Test finished.")

if __name__ == "__main__":
    asyncio.run(test_support_ui())
