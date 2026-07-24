import os
import sys
import asyncio
import httpx
from playwright.async_api import async_playwright

async def run():
    print("Creating a new quotation...")
    # Import the payload from existing script
    from generate_sara_2pax_quotation import payload
    import uuid
    
    quotation_id = f"quo_{uuid.uuid4().hex[:12]}"
    print(f"Generating quotation with ID: {quotation_id}")
    
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"http://localhost:8111/quotations?lang=en&brand=capella_travel",
            json=payload,
            timeout=10
        )
        if res.status_code != 200:
            print("Failed to create quotation", res.text)
            sys.exit(1)
        data = res.json()
        quotation_url = data.get("quotationUrl", f"http://localhost:8111/quotations/{quotation_id}")

    print("Starting Playwright test...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Opening quotation: {quotation_url}")
        
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        
        response = await page.goto(quotation_url)
        await page.wait_for_load_state("networkidle")
        
        # Check current theme text
        current_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
        print(f"Initial Theme: {current_theme_text.strip()}")
        assert "Prototype" in current_theme_text, "Failed: Default theme is not Prototype Theme"
        
        # Step 2: Open Theme Modal
        print("Clicking Select Theme button...")
        await page.locator("#btn-select-template").click()
        await page.locator("#template-modal").first.wait_for(state="visible")
        
        # Step 3: Check options
        options = await page.locator(".pb-domain-item .pb-domain-name").all_inner_texts()
        print(f"Available options in modal: {options}")
        
        # Step 4: Click Brochure Theme
        print("Switching to Brochure Theme...")
        # Step 4: Click Brochure Theme
        print("Switching to Brochure Theme...")
        await page.locator("text=Brochure Theme").first.click()
        
        await page.locator("#template-confirm-modal").first.wait_for(state="visible")
        await page.locator("#btn-confirm-switch").first.click()
        
        print("Waiting for reload...")
        for _ in range(20):
            await page.wait_for_timeout(500)
            try:
                new_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
                if "Brochure" in new_theme_text:
                    break
            except Exception:
                pass
        
        # Check the theme changed
        new_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
        print(f"Theme after switch: {new_theme_text.strip()}")
        assert "Brochure" in new_theme_text, f"Failed to switch to Brochure theme, got {new_theme_text}"

        # Step 5: Switch back to Prototype Theme
        print("Switching back to Prototype Theme...")
        await page.locator("#btn-select-template").click()
        await page.locator("#template-modal").first.wait_for(state="visible")
        await page.locator("text=Prototype Theme").first.click()
        
        await page.locator("#template-confirm-modal").first.wait_for(state="visible")
        await page.locator("#btn-confirm-switch").first.click()
        
        print("Waiting for reload...")
        for _ in range(20):
            await page.wait_for_timeout(500)
            try:
                final_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
                if "Prototype" in final_theme_text:
                    break
            except Exception:
                pass
        
        final_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
        print(f"Final Theme: {final_theme_text.strip()}")
        assert "Prototype" in final_theme_text, f"Failed to switch back to Prototype theme, got {final_theme_text}"
        
        print("✅ All Playwright tests passed successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
