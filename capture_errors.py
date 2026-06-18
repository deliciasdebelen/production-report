import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Listen for console messages and page errors
        page.on('console', lambda msg: print(f"CONSOLE {msg.type}: {msg.text}"))
        page.on('pageerror', lambda exc: print(f"PAGE ERROR: {exc}"))
        
        print("Navigating to page...")
        await page.goto('http://192.168.1.79:8000/logistics/dispatch', wait_until='networkidle')
        
        print("Done capturing errors. Closing...")
        await browser.close()

asyncio.run(main())
