import os
import sys
import asyncio
from playwright.async_api import async_playwright

async def run():
    print("Starting Playwright test...")
    async with async_playwright() as p:
        try:
            # We use chromium
            browser = await p.chromium.launch(headless=True)
        except Exception as e:
            print("Failed to launch chromium. Make sure browsers are installed (playwright install chromium). Error:", e)
            return

        context = await browser.new_context()
        page = await context.new_page()

        # Step 1: Visit the quotation we just created
        quotation_url = "http://localhost:8111/quotations/quo_0027efcc7c40"
        print(f"Opening quotation: {quotation_url}")
        
        response = await page.goto(quotation_url)
        if response.status != 200:
            print(f"Failed to load page. Status: {response.status}")
            sys.exit(1)
            
        await page.wait_for_load_state("networkidle")
        
        # Check current theme text
        current_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
        print(f"Current Theme: {current_theme_text.strip()}")
        
        # It should be Prototype Theme initially, or whatever it is, let's just log it.
        # Step 2: Open Theme Modal
        print("Clicking Select Theme button...")
        await page.locator("#btn-select-template").click()
        
        # Wait for modal to be visible
        await page.locator("#template-modal").first.wait_for(state="visible")
        
        # Step 3: Check options
        options = await page.locator(".pb-domain-item .pb-domain-name").all_inner_texts()
        print(f"Available themes in modal: {options}")
        assert len(options) >= 3, "Expected at least 3 themes in the modal"
        
        # Step 4: Click Brochure Theme
        print("Switching to Brochure Theme...")
        await page.locator("text=Brochure Theme").first.click()
        
        # Wait for confirm modal
        await page.locator("#template-confirm-modal").first.wait_for(state="visible")
        await page.locator("text=Yes, switch theme").first.click()
        
        # The page will reload/navigate
        await page.wait_for_load_state("networkidle")
        
        # Check the theme changed
        new_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
        print(f"Theme after switch: {new_theme_text.strip()}")
        assert "Brochure" in new_theme_text, "Failed to switch to Brochure theme"

        # Step 5: Switch back to Prototype Theme
        print("Switching back to Prototype Theme...")
        await page.locator("#btn-select-template").click()
        await page.locator("#template-modal").first.wait_for(state="visible")
        await page.locator("text=Prototype Theme").first.click()
        
        await page.locator("#template-confirm-modal").first.wait_for(state="visible")
        await page.locator("text=Yes, switch theme").first.click()
        
        await page.wait_for_load_state("networkidle")
        
        final_theme_text = await page.locator("#btn-select-template .template-text").first.inner_text()
        print(f"Final Theme: {final_theme_text.strip()}")
        assert "Prototype" in final_theme_text, "Failed to switch to Prototype theme"
        
        print("✅ All Playwright tests passed successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
